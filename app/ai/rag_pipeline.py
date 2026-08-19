"""
app/ai/rag_pipeline.py
Tiered RAG Pipeline using OpenRouter + Llama-3.3-70B and ChromaDB.
"""
import datetime
import os
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

from app.ai.config import INTENT_CONFIG
from app.ai.loader import load_csv_knowledge_base
from app.ai.chunker import chunk_documents
from app.ai.vector_store import build_or_load_vector_store
from app.ai.retriever import retrieve_context_tiered
from app.ai.memory import memory_manager
from app.ai.prompt import SYSTEM_PROMPT_TEMPLATE

# Data context processors and Navigation Engine
from app.ai.navigation import find_location
from app.ai.data_processor import (
    process_placement_context,
    process_timetable_context,
    process_notice_context,
    process_faculty_context,
    process_events_context,
    resolve_day_and_date,
    MAP_LOOKUP,
)


def route_query_sources(user_message: str) -> list[tuple[str, float]]:
    """
    Detects query intent via keyword matching from INTENT_CONFIG 
    and returns a prioritized list of (source_filename, weight) tuples.
    """
    msg = user_message.lower()

    for intent, config in INTENT_CONFIG.items():
        if any(keyword in msg for keyword in config["keywords"]):
            return config["sources"]

    return []  # Triggers safety fallback in retriever if unmapped


class RAGPipeline:
    def __init__(self, force_rebuild: bool = False):
        print("Initializing Tiered RAG Pipeline with OpenRouter...")

        # Resolve Project Root Directory
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        chroma_dir = os.path.join(project_root, "chroma_db")

        # Build or Load ChromaDB Persisted Store
        if force_rebuild or not os.path.exists(chroma_dir):
            raw_docs = load_csv_knowledge_base()
            chunks = chunk_documents(raw_docs)
            self.vector_store = build_or_load_vector_store(
                chunks,
                force_rebuild=True
            )
        else:
            self.vector_store = build_or_load_vector_store()

        # Read OpenRouter API Key & Model settings
        api_key = os.getenv("OPENROUTER_API_KEY")
        model_name = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

        if not api_key:
            raise ValueError("❌ OPENROUTER_API_KEY not found in .env file.")

        print(f"Using OpenRouter Model: {model_name}")

        # Initialize OpenRouter Client via ChatOpenAI
        self.llm = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=1024,
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SVIT AI Assistant",
            }
        )

    def answer_question(
        self, 
        question: str, 
        session_id: str = "default_user", 
        top_k: int = 10,
        filter_dict: dict = None
    ) -> dict:
        """
        Executes end-to-end RAG workflow:
        1. High-priority Navigation Module check (intercepts location queries BEFORE LLM)
        2. Resolve fallback map images via MAP_LOOKUP (only for location queries)
        3. Direct Pandas CSV retrieval for timetables/notices/faculty/events with Vector Store fallback
        4. Tiered ChromaDB vector retrieval for general queries
        5. Context processing, formatting, and OpenRouter LLM inference
        6. Clean structured JSON output
        """
        msg = question.lower()

        # ---------------------------------------------------------
        # STEP 0: NAVIGATION MODULE INTERCEPTION (EXECUTED BEFORE LLM)
        # ---------------------------------------------------------
        nav_result = find_location(question)
        if nav_result:
            # Construct map path matching static folder directory structure
            nav_image_path = f"navigation_maps/{nav_result['image']}"
            
            # Save interaction to session memory
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", nav_result["formatted_text"])

            return {
                "answer": nav_result["formatted_text"],
                "image": nav_image_path,
                "sources": ["SVIT Navigation Directory"],
                "navigation": nav_result
            }

        # ---------------------------------------------------------
        # STEP 1: RESOLVE FALLBACK NAVIGATION MAP IMAGE
        # ---------------------------------------------------------
        map_image = None
        
        nav_intent_keywords = [
            "where", "location", "reach", "map", "direction", "directions", 
            "way", "route", "locate", "find", "building", "block", "take me",
            "how to go", "how to reach", "navigate"
        ]

        if any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in nav_intent_keywords):
            sorted_map_keys = sorted(MAP_LOOKUP.keys(), key=len, reverse=True)
            for key in sorted_map_keys:
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, msg):
                    map_image = f"navigation_maps/{MAP_LOOKUP[key]}"
                    break

        # Extended keyword triggers for domain context modules
        timetable_keywords = [
            'tt', 't.t', 't.t.', 'sched', 'lec',
            'timetable', 'time table', 'timetabel', 'time tabel', 'timetabl', 'tabel', 'table',
            'schedule', 'shedule', 'skedule', 'class', 'classes', 'lecture', 'lectures', 
            'timing', 'timings', 'slot', 'slots', 'period', 'periods',
            'today', 'tomorrow', 'yesterday',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
            'who teaches', 'faculty for', 'professor for', 'teacher for', 'subject for'
        ]

        notice_keywords = [
            'notice', 'announcement', 'exam form', 'mid-term', 'submission',
            'fee', 'holiday', 'result', 're-check', 'circular', 'hall ticket'
        ]

        faculty_keywords = [
            'hod', 'head of department', 'cabin', 'faculty detail',
            'registrar', 'student section', 'contact number', 'phone number', 'email address'
        ]

        placement_keywords = [
            'placement', 'drive', 'package', 'lpa', 'salary', 
            'recruiter', 'highest package', 'upcoming placement'
        ]

        events_keywords = [
            'event', 'events', 'workshop', 'workshops', 'seminar', 'symposium',
            'hackathon', 'competition', 'fest', 'techfest', 'cultural fest'
        ]

        is_timetable = any(k in msg for k in timetable_keywords)
        is_notice = any(k in msg for k in notice_keywords)
        is_faculty = any(k in msg for k in faculty_keywords)
        is_placement = any(k in msg for k in placement_keywords)
        is_events = any(k in msg for k in events_keywords)

        sources = []

        # ---------------------------------------------------------
        # OPTION A: TIMETABLE DIRECT PANDAS PATH WITH VECTOR FALLBACK
        # ---------------------------------------------------------
        if is_timetable:
            context = process_timetable_context([], question)
            
            if "timetable.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("timetable.csv", 1.0)],
                    top_k=top_k
                )
                context = process_timetable_context(retrieved_docs, question)

            sources = re.findall(r'timetable\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["timetable.csv"]

        # ---------------------------------------------------------
        # OPTION B: NOTICES DIRECT PATH WITH VECTOR FALLBACK
        # ---------------------------------------------------------
        elif is_notice:
            context = process_notice_context([], question)

            if "notices.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("notices.csv", 1.0)],
                    top_k=top_k
                )
                context = process_notice_context(retrieved_docs, question)

            sources = re.findall(r'notices\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["notices.csv"]

        # ---------------------------------------------------------
        # OPTION C: FACULTY / DEPARTMENT DIRECT PATH WITH VECTOR FALLBACK
        # ---------------------------------------------------------
        elif is_faculty:
            context = process_faculty_context([], question)

            if "departments.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("departments.csv", 1.0)],
                    top_k=top_k
                )
                context = process_faculty_context(retrieved_docs, question)

            sources = re.findall(r'departments\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["departments.csv"]

        # ---------------------------------------------------------
        # OPTION D: EVENTS / WORKSHOPS DIRECT PATH WITH VECTOR FALLBACK
        # ---------------------------------------------------------
        elif is_events:
            context = process_events_context(question)

            if "events.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("events.csv", 1.0)],
                    top_k=top_k
                )
                context = "\n\n---\n\n".join([doc.page_content for doc, _ in retrieved_docs])

            sources = re.findall(r'events\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["events.csv"]

        # ---------------------------------------------------------
        # OPTION E: VECTOR SEARCH PATH (PLACEMENTS, BUS ROUTES, CANTEEN, ETC.)
        # ---------------------------------------------------------
        else:
            if filter_dict and "source" in filter_dict:
                source_cascade = [(filter_dict["source"], 1.0)]
            else:
                source_cascade = route_query_sources(question)

            results = retrieve_context_tiered(
                self.vector_store,
                question,
                source_weights=source_cascade,
                top_k=top_k
            )

            seen = set()
            for doc, score in results:
                src = (
                    f"{doc.metadata.get('source', 'Unknown')} "
                    f"(Row {doc.metadata.get('row', 'N/A')})"
                )
                if src not in seen:
                    seen.add(src)
                    sources.append(src)

            if is_placement:
                context = process_placement_context(results, question)
            else:
                context = "\n\n---\n\n".join([doc.page_content for doc, _ in results])

        # ---------------------------------------------------------
        # COMMON STEP: PROMPT GENERATION & LLM INFERENCE
        # ---------------------------------------------------------
        history = memory_manager.format_history_for_prompt(session_id)
        current_date_str = datetime.datetime.now().strftime("%A, %d %B YYYY")

        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            current_date=current_date_str,
            history=history,
            context=context,
            question=question
        )

        response = self.llm.invoke(prompt)
        answer = response.content

        # Strip out any lingering markdown image tags if hallucinated by the LLM
        answer = re.sub(r'!\[.*?\]\(.*?\)', '', answer).strip()

        # Save to session memory
        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", answer)

        return {
            "answer": answer,
            "image": map_image,  # Returns map image path only for navigation queries, else None
            "sources": sources
        }

    def query(self, question: str, session_id: str = "default_user", **kwargs) -> dict:
        """Alias method ensuring backwards compatibility with callers invoking .query()."""
        return self.answer_question(question, session_id=session_id, **kwargs)

    def get_answer(self, question: str, session_id: str = "default_user", **kwargs) -> dict:
        """Alias method ensuring backwards compatibility with callers invoking .get_answer()."""
        return self.answer_question(question, session_id=session_id, **kwargs)


# ---------------------------------------------------------
# SINGLETON INSTANCE & HELPER API FUNCTIONS
# ---------------------------------------------------------
_rag_singleton = None


def get_rag_pipeline(force_rebuild: bool = False) -> RAGPipeline:
    """Provides a thread-safe singleton instance of RAGPipeline."""
    global _rag_singleton
    if _rag_singleton is None or force_rebuild:
        _rag_singleton = RAGPipeline(force_rebuild=force_rebuild)
    return _rag_singleton


def get_bot_response(question: str, session_id: str = "default_user") -> dict:
    """Primary entry point for external web routes."""
    pipeline = get_rag_pipeline()
    return pipeline.answer_question(question, session_id=session_id)