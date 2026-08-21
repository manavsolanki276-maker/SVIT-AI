"""
app/ai/rag_pipeline.py
High-Performance Tiered RAG Pipeline with Student Profile Personalization, Real-Time "Next Class Now" Interception,
Fast Greeting Interception, In-Memory DataFrames, Dynamic Category-Trimmed Prompts, and Streaming Generator Support.
"""
import datetime
import os
import re
from typing import Dict, Any, List, Optional, Generator, Tuple
from collections import OrderedDict
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
from app.ai.prompt import get_dynamic_system_prompt, SYSTEM_PROMPT_TEMPLATE

# Data context processors and Navigation Engine
from app.ai.navigation import find_location
from app.ai.data_processor import (
    process_placement_context,
    process_timetable_context,
    process_next_class_context,
    process_notice_context,
    process_faculty_context,
    process_events_context,
    resolve_day_and_date,
    generate_followup_suggestions,
    resolve_student_profile_query,
    MAP_LOOKUP,
)

# =========================================================
# FAST-PATH GREETINGS & STATIC SMALL TALK (0ms Overhead)
# =========================================================
FAST_GREETINGS = [
    (r"^(hi|hello|hey|hola|namaste|greetings)\b", "Hello{name_suffix}! 👋 I am the official SVIT AI Assistant. How can I help you today with your classes, timetables, notices, faculty details, or campus navigation?"),
    (r"^(good morning)\b", "Good morning{name_suffix}! ☀️ How can I assist you with SVIT academics or campus information today?"),
    (r"^(good afternoon)\b", "Good afternoon{name_suffix}! 🌤️ How can I help you today?"),
    (r"^(good evening)\b", "Good evening{name_suffix}! 🌙 How can I assist you with your SVIT queries?"),
    (r"^(who are you|what is your name|what can you do|what are you|help)\b", "I am the **SVIT AI Assistant**, designed to assist students and faculty at Sardar Vallabhbhai Patel Institute of Technology (SVIT), Vasad.\n\nI can help you with:\n* 📅 **Timetables & Class Schedules**\n* 📍 **'Next Class Now' Real-time Status**\n* 📢 **Exam Notices & Deadlines**\n* 👨‍🏫 **Faculty & HOD Details**\n* 🗺️ **Interactive Campus Maps & Room Navigation**\n* 💼 **Placements & Packages**\n* 🚌 **Bus Routes & Transportation**\n* 🍔 **Canteen & Campus Amenities**"),
    (r"^(thank you|thanks|thx|thank you so much)\b", "You're very welcome{name_suffix}! 😊 Feel free to ask if you need any other help with SVIT academics or campus details."),
    (r"^(bye|goodbye|see you)\b", "Goodbye{name_suffix}! Have a great day ahead! 🚀")
]

# Patterns for Real-Time "Next Class Now"
NEXT_CLASS_PATTERNS = [
    r'\b(?:next|current|upcoming)\s*(?:class|lecture|session|period|lab|room)\b',
    r'\bwhere\s*(?:do|should|can)\s*i\s*go\b',
    r'\bwhere\s*is\s*my\s*(?:next\s*)?class\b',
    r'\bwhat\s*class\s*(?:do\s*i\s*have\s*)?(?:right\s*)?now\b',
    r'\bclass\s*(?:right\s*)?now\b',
    r'\bwhat\s*is\s*next\b',
    r'\bwhere\s*to\s*go\s*now\b',
    r'\bwhere\s*is\s*my\s*next\s*class\b',
    r'\bwhere\s*is\s*my\s*lecture\b'
]

# In-Memory Response Cache for duplicate queries
_RESPONSE_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_MAX_RESPONSE_CACHE = 100


def route_query_sources(user_message: str) -> list[tuple[str, float]]:
    """
    Detects query intent via keyword matching from INTENT_CONFIG 
    and returns a prioritized list of (source_filename, weight) tuples.
    """
    msg = user_message.lower()
    for intent, config in INTENT_CONFIG.items():
        if any(keyword in msg for keyword in config["keywords"]):
            return config["sources"]
    return []


class RAGPipeline:
    def __init__(self, force_rebuild: bool = False):
        print("[RAG] Initializing Optimized Tiered RAG Pipeline with Student Personalization...")

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        chroma_dir = os.path.join(project_root, "chroma_db")

        # Build or Load ChromaDB Store
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
            raise ValueError("[Error] OPENROUTER_API_KEY not found in .env file.")

        print(f"[RAG] Using OpenRouter Model: {model_name}")

        # Initialize OpenRouter Client with fast token budget
        self.llm = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=768,
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "SVIT AI Assistant",
            }
        )

    def _prepare_rag_context(
        self, 
        question: str, 
        top_k: int = 8, 
        filter_dict: dict = None,
        user_profile: dict = None
    ) -> Tuple[str, Optional[str], List[str], str]:
        """
        Prepares the context string, map image, sources, and detected intent category
        incorporating logged-in student profile metadata.
        """
        msg = question.lower().strip()

        # Fallback navigation map image resolution
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

        # Extended domain intent keywords
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

        transport_keywords = ['bus', 'route', 'transport', 'commute', 'pickup', 'driver']
        library_keywords = ['library', 'book', 'issue', 'fine', 'author', 'reading room', 'journal']
        contact_keywords = ['contact', 'phone', 'email', 'office', 'admin', 'number', 'address']

        is_timetable = any(k in msg for k in timetable_keywords)
        is_notice = any(k in msg for k in notice_keywords)
        is_faculty = any(k in msg for k in faculty_keywords)
        is_placement = any(k in msg for k in placement_keywords)
        is_events = any(k in msg for k in events_keywords)
        is_transport = any(k in msg for k in transport_keywords)
        is_library = any(k in msg for k in library_keywords)
        is_contact = any(k in msg for k in contact_keywords)

        sources = []
        context = ""
        intent_category = "general"

        # Option A: Timetable (Personalized)
        if is_timetable:
            intent_category = "timetable"
            context = process_timetable_context([], question, user_profile=user_profile)
            if "timetable.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("timetable.csv", 1.0)],
                    top_k=top_k
                )
                context = process_timetable_context(retrieved_docs, question, user_profile=user_profile)

            sources = re.findall(r'timetable\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["timetable.csv"]

        # Option B: Notices (Personalized)
        elif is_notice:
            intent_category = "notices"
            context = process_notice_context([], question, user_profile=user_profile)
            if "notices.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("notices.csv", 1.0)],
                    top_k=top_k
                )
                context = process_notice_context(retrieved_docs, question, user_profile=user_profile)

            sources = re.findall(r'notices\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["notices.csv"]

        # Option C: Faculty / Department (Personalized)
        elif is_faculty:
            intent_category = "faculty"
            context = process_faculty_context([], question, user_profile=user_profile)
            if "departments.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("departments.csv", 1.0)],
                    top_k=top_k
                )
                context = process_faculty_context(retrieved_docs, question, user_profile=user_profile)

            sources = re.findall(r'departments\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["departments.csv"]

        # Option D: Events / Workshops
        elif is_events:
            intent_category = "events"
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

        # Option E: Placements & Campus Drives (In-Memory Fast Retrieval)
        elif is_placement:
            intent_category = "placement"
            context = process_placement_context(question, user_profile=user_profile)
            sources = re.findall(r'placements\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["placements.csv"]

        # Option F: Vector Search (Transport, Library, Canteen, FAQs)
        else:
            if is_transport:
                intent_category = "transport"
            elif is_library:
                intent_category = "library"
            elif is_contact:
                intent_category = "contact"

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

            context = "\n\n---\n\n".join([doc.page_content for doc, _ in results])

        return context, map_image, sources, intent_category

    def answer_question(
        self, 
        question: str, 
        session_id: str = "default_user", 
        top_k: int = 8,
        filter_dict: dict = None,
        user_profile: dict = None
    ) -> dict:
        """
        Executes personalized RAG workflow:
        1. Fast Greeting Interception (0ms)
        2. Fast Next Class Real-time Interception (0ms)
        3. Fast Spatial Navigation Interception (0ms)
        4. Response Cache Lookup
        5. In-Memory Context Processing with student defaults
        6. Category-Trimmed Prompt with Student Metadata + OpenRouter LLM
        """
        clean_q = question.strip().lower()
        user_name = user_profile.get('full_name') if user_profile else ""
        first_name = user_name.split()[0] if user_name else ""
        name_suffix = f" {first_name}" if first_name else ""

        # ---------------------------------------------------------
        # STEP 0: FAST-PATH GREETING & SMALL TALK (0ms)
        # ---------------------------------------------------------
        for pattern, reply_tmpl in FAST_GREETINGS:
            if re.search(pattern, clean_q):
                reply = reply_tmpl.format(name_suffix=name_suffix)
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", reply)
                suggestions = generate_followup_suggestions(question, "general", reply, user_profile=user_profile)
                return {
                    "answer": reply,
                    "image": None,
                    "sources": ["SVIT Assistant Greeting"],
                    "suggestions": suggestions
                }

        # ---------------------------------------------------------
        # STEP 0.2: FAST-PATH DIRECT PROFILE QUERY RESOLUTION (0ms)
        # ---------------------------------------------------------
        profile_ans = resolve_student_profile_query(question, user_profile=user_profile)
        if profile_ans:
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", profile_ans)
            suggestions = [
                "Show today's timetable 📅",
                "Where is my next class right now? 📍",
                "Who is my HOD? 👨‍🏫"
            ]
            return {
                "answer": profile_ans,
                "image": None,
                "sources": ["student_profile.db"],
                "suggestions": suggestions
            }

        # ---------------------------------------------------------
        # STEP 0.5: FAST-PATH "NEXT CLASS NOW" REAL-TIME ANALYZER (0ms)
        # ---------------------------------------------------------
        if any(re.search(p, clean_q) for p in NEXT_CLASS_PATTERNS):
            ans_text, nav_map, srcs = process_next_class_context(question, user_profile=user_profile)
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", ans_text)
            suggestions = generate_followup_suggestions(question, "timetable", ans_text, user_profile=user_profile)
            return {
                "answer": ans_text,
                "image": nav_map,
                "sources": srcs,
                "suggestions": suggestions
            }

        # ---------------------------------------------------------
        # STEP 1: NAVIGATION MODULE INTERCEPTION (0ms)
        # ---------------------------------------------------------
        nav_result = find_location(question)
        if nav_result:
            nav_image_path = f"navigation_maps/{nav_result['image']}"
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", nav_result["formatted_text"])
            suggestions = generate_followup_suggestions(question, "navigation", nav_result["formatted_text"], user_profile=user_profile)
            return {
                "answer": nav_result["formatted_text"],
                "image": nav_image_path,
                "sources": ["SVIT Navigation Directory"],
                "navigation": nav_result,
                "suggestions": suggestions
            }

        # ---------------------------------------------------------
        # STEP 2: CACHED QUERY LOOKUP (Profile-Aware)
        # ---------------------------------------------------------
        prof_key = (
            f"{user_profile.get('program')}_{user_profile.get('department')}_"
            f"{user_profile.get('semester')}_{user_profile.get('division')}_"
            f"{user_profile.get('batch')}"
        ) if user_profile else "none"
        cache_key = f"{clean_q}_{prof_key}_{top_k}"
        if cache_key in _RESPONSE_CACHE:
            cached_res = _RESPONSE_CACHE[cache_key]
            _RESPONSE_CACHE.move_to_end(cache_key)
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", cached_res["answer"])
            return cached_res

        # ---------------------------------------------------------
        # STEP 3: PREPARE CONTEXT & DYNAMIC PROMPT WITH PROFILE
        # ---------------------------------------------------------
        context, map_image, sources, intent_category = self._prepare_rag_context(
            question, top_k=top_k, filter_dict=filter_dict, user_profile=user_profile
        )

        history = memory_manager.format_history_for_prompt(session_id)
        current_date_str = datetime.datetime.now().strftime("%A, %d %B YYYY")

        prompt = get_dynamic_system_prompt(
            intent_category=intent_category,
            current_date=current_date_str,
            history=history,
            context=context,
            question=question,
            user_profile=user_profile
        )

        # ---------------------------------------------------------
        # STEP 4: LLM INFERENCE
        # ---------------------------------------------------------
        response = self.llm.invoke(prompt)
        answer = response.content

        # Strip hallucinated markdown image tags
        answer = re.sub(r'!\[.*?\]\(.*?\)', '', answer).strip()

        # Save to session memory
        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", answer)

        suggestions = generate_followup_suggestions(question, intent_category, answer, user_profile=user_profile)

        result = {
            "answer": answer,
            "image": map_image,
            "sources": sources,
            "suggestions": suggestions
        }

        # Store in LRU cache
        if len(_RESPONSE_CACHE) >= _MAX_RESPONSE_CACHE:
            _RESPONSE_CACHE.popitem(last=False)
        _RESPONSE_CACHE[cache_key] = result

        return result

    def stream_answer_question(
        self, 
        question: str, 
        session_id: str = "default_user", 
        top_k: int = 8,
        user_profile: dict = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming generator yielding incremental tokens with student profile personalization.
        """
        clean_q = question.strip().lower()
        user_name = user_profile.get('full_name') if user_profile else ""
        first_name = user_name.split()[0] if user_name else ""
        name_suffix = f" {first_name}" if first_name else ""

        # 1. Fast Greeting
        for pattern, reply_tmpl in FAST_GREETINGS:
            if re.search(pattern, clean_q):
                reply = reply_tmpl.format(name_suffix=name_suffix)
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", reply)
                suggestions = generate_followup_suggestions(question, "general", reply, user_profile=user_profile)
                yield {"chunk": reply, "done": False}
                yield {"done": True, "answer": reply, "image": None, "sources": ["SVIT Assistant Greeting"], "suggestions": suggestions}
                return

        # 1.2 Fast Direct Student Profile Query Resolution
        profile_ans = resolve_student_profile_query(question, user_profile=user_profile)
        if profile_ans:
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", profile_ans)
            suggestions = [
                "Show today's timetable 📅",
                "Where is my next class right now? 📍",
                "Who is my HOD? 👨‍🏫"
            ]
            yield {"chunk": profile_ans, "done": False}
            yield {
                "done": True,
                "answer": profile_ans,
                "image": None,
                "sources": ["student_profile.db"],
                "suggestions": suggestions
            }
            return

        # 1.5 Fast Next Class Real-time Interception
        if any(re.search(p, clean_q) for p in NEXT_CLASS_PATTERNS):
            ans_text, nav_map, srcs = process_next_class_context(question, user_profile=user_profile)
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", ans_text)
            suggestions = generate_followup_suggestions(question, "timetable", ans_text, user_profile=user_profile)
            yield {"chunk": ans_text, "done": False}
            yield {"done": True, "answer": ans_text, "image": nav_map, "sources": srcs, "suggestions": suggestions}
            return

        # 2. Fast Navigation
        nav_result = find_location(question)
        if nav_result:
            nav_image_path = f"navigation_maps/{nav_result['image']}"
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", nav_result["formatted_text"])
            suggestions = generate_followup_suggestions(question, "navigation", nav_result["formatted_text"], user_profile=user_profile)
            yield {"chunk": nav_result["formatted_text"], "done": False}
            yield {"done": True, "answer": nav_result["formatted_text"], "image": nav_image_path, "sources": ["SVIT Navigation Directory"], "suggestions": suggestions}
            return

        # 3. Context & Dynamic Prompt with Profile
        context, map_image, sources, intent_category = self._prepare_rag_context(
            question, top_k=top_k, user_profile=user_profile
        )
        history = memory_manager.format_history_for_prompt(session_id)
        current_date_str = datetime.datetime.now().strftime("%A, %d %B YYYY")

        prompt = get_dynamic_system_prompt(
            intent_category=intent_category,
            current_date=current_date_str,
            history=history,
            context=context,
            question=question,
            user_profile=user_profile
        )

        # 4. Stream LLM tokens live
        accumulated_chunks = []
        try:
            for chunk in self.llm.stream(prompt):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    accumulated_chunks.append(content)
                    yield {"chunk": content, "done": False}

            full_answer = "".join(accumulated_chunks)
            full_answer = re.sub(r'!\[.*?\]\(.*?\)', '', full_answer).strip()

            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", full_answer)
            suggestions = generate_followup_suggestions(question, intent_category, full_answer, user_profile=user_profile)

            yield {
                "done": True,
                "answer": full_answer,
                "image": map_image,
                "sources": sources,
                "suggestions": suggestions
            }

        except Exception as e:
            print(f"[Error] Error during streaming: {e}")
            yield {"done": True, "error": str(e)}

    def query(self, question: str, session_id: str = "default_user", **kwargs) -> dict:
        return self.answer_question(question, session_id=session_id, **kwargs)

    def get_answer(self, question: str, session_id: str = "default_user", **kwargs) -> dict:
        return self.answer_question(question, session_id=session_id, **kwargs)


# =========================================================
# SINGLETON INSTANCE & HELPER API FUNCTIONS
# =========================================================
_rag_singleton = None


def get_rag_pipeline(force_rebuild: bool = False) -> RAGPipeline:
    global _rag_singleton
    if _rag_singleton is None or force_rebuild:
        _rag_singleton = RAGPipeline(force_rebuild=force_rebuild)
    return _rag_singleton


def get_bot_response(question: str, session_id: str = "default_user", user_profile: dict = None) -> dict:
    pipeline = get_rag_pipeline()
    return pipeline.answer_question(question, session_id=session_id, user_profile=user_profile)