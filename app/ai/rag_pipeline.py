"""
app/ai/rag_pipeline.py
High-Performance Tiered RAG Pipeline with Student Profile Personalization, Real-Time "Next Class Now" Interception,
Fast Greeting Interception, In-Memory DataFrames, Dynamic Category-Trimmed Prompts, and Streaming Generator Support.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
from typing import Dict, Any, List, Optional, Generator, Tuple
from collections import OrderedDict
from dotenv import load_dotenv

# Indian Standard Time (IST, UTC+05:30) Timezone definition
IST = ZoneInfo("Asia/Kolkata")

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
    process_campus_navigation_context,
    process_subject_context,
    resolve_day_and_date,
    generate_followup_suggestions,
    resolve_student_profile_query,
    get_navigation_map_url,
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
    (r".*(who are you|what is your name|what can you do|what are you|help me|what information can svit ai help|what information can you help|how can you help|what can svit ai help)\b", "I am the **SVIT AI Assistant**, designed to assist students and faculty at Sardar Vallabhbhai Patel Institute of Technology (SVIT), Vasad.\n\nI can help you with:\n* 📅 **Timetables & Class Schedules**\n* 📍 **'Next Class Now' Real-time Status**\n* 📢 **Exam Notices & Deadlines**\n* 👨‍🏫 **Faculty & HOD Details**\n* 🗺️ **Interactive Campus Maps & Room Navigation**\n* 💼 **Placements & Packages**\n* 🚌 **Bus Routes & Transportation**\n* 🍔 **Canteen & Campus Amenities**"),
    (r"^(thank you|thanks|thx|thank you so much)\b", "You're very welcome{name_suffix}! 😊 Feel free to ask if you need any other help with SVIT academics or campus details."),
    (r"^(bye|goodbye|see you)\b", "Goodbye{name_suffix}! Have a great day ahead! 🚀")
]

# Patterns for Real-Time "Next Class Now"
NEXT_CLASS_PATTERNS = [
    r'\b(?:next|current|upcoming)\s*(?:class|lecture|session|period|lab|subject)\b',
    r'\bwhere\s*(?:do|should|can)\s*i\s*go\s*(?:now|next|right now|for next class|for class|for lecture)\b',
    r'\bwhere\s*(?:do|should|can)\s*i\s*go\s*$',
    r'\bwhere\s*is\s*my\s*(?:next\s*)?(?:class|subject|lecture)\b',
    r'\bwhat\s*class\s*(?:do\s*i\s*have\s*)?(?:right\s*)?now\b',
    r'\bclass\s*(?:right\s*)?now\b',
    r'\bwhat\s*is\s*next\s*class\b',
    r'\bwhere\s*to\s*go\s*now\b',
    r'\bwhere\s*is\s*my\s*next\s*(?:class|lecture|subject)\b',
    r'\bwhere\s*is\s*my\s*lecture\b'
]

# In-Memory Response Cache for duplicate queries
_RESPONSE_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_MAX_RESPONSE_CACHE = 100


def clear_response_cache() -> None:
    """Clears in-memory RAG response cache upon dataset mutation."""
    _RESPONSE_CACHE.clear()


def route_query_sources(user_message: str) -> list[tuple[str, float]]:
    """
    Detects query intent via keyword matching from INTENT_CONFIG 
    and returns a prioritized, deduplicated list of (source_filename, weight) tuples.
    Location queries ("where is ...") prioritize facilities/campus_info sources.
    Room code queries (e.g., "AR-101") route to rooms_facilities.csv.
    """
    msg = user_message.lower()

    # Room code pattern: 2-4 letter prefix + dash + 2-3 digits (e.g., AR-101, CO-203, ME-105)
    if re.search(r'\b[a-z]{2,4}[-.]?\d{2,3}\b', msg):
        return [("rooms_facilities.csv", 1.0), ("campus_info.csv", 0.5), ("general_faq.csv", 0.1)]

    is_location_query = any(k in msg for k in ["where is", "where", "locate", "find", "how to reach", "location of"])

    # For location queries, check facilities/campus_info first so they aren't
    # overshadowed by generic placement/faculty/departments intent matches
    if is_location_query:
        location_first_intents = ["facilities", "campus_info"]
        for intent_key in location_first_intents:
            if intent_key in INTENT_CONFIG:
                config = INTENT_CONFIG[intent_key]
                if any(keyword in msg for keyword in config["keywords"]):
                    return config["sources"]

    source_map = {}
    for intent, config in INTENT_CONFIG.items():
        if any(keyword in msg for keyword in config["keywords"]):
            for src, weight in config["sources"]:
                if src not in source_map or weight > source_map[src]:
                    source_map[src] = weight
                    
    if source_map:
        return sorted(source_map.items(), key=lambda x: x[1], reverse=True)
    return [("campus_info.csv", 1.0), ("facilities.csv", 0.95), ("general_faq.csv", 0.5)]


class RAGPipeline:
    def __init__(self, force_rebuild: bool = False):
        print("[RAG] Initializing Optimized Tiered RAG Pipeline with Student Personalization...")
        self.force_rebuild = force_rebuild
        self._vector_store = None
        self._llm = None

    def clear_cache(self):
        """Clears RAG response cache."""
        clear_response_cache()

    @property
    def vector_store(self):
        if self._vector_store is None:
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            chroma_dir = os.path.join(project_root, "chroma_db")

            # Build or Load ChromaDB Store
            if self.force_rebuild or not os.path.exists(chroma_dir):
                raw_docs = load_csv_knowledge_base()
                chunks = chunk_documents(raw_docs)
                self._vector_store = build_or_load_vector_store(
                    chunks,
                    force_rebuild=True
                )
            else:
                self._vector_store = build_or_load_vector_store()
        return self._vector_store

    @property
    def llm(self):
        if self._llm is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            model_name = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

            if not api_key:
                raise ValueError("[Error] OPENROUTER_API_KEY environment variable is not configured.")

            print(f"[RAG] Using OpenRouter Model: {model_name}")

            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model_name=model_name,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1,
                max_tokens=768,
                default_headers={
                    "HTTP-Referer": "https://svit-ai.vercel.app",
                    "X-Title": "SVIT AI Assistant",
                }
            )
        return self._llm


    def _prepare_rag_context(
        self, 
        question: str, 
        top_k: int = 8, 
        filter_dict: dict = None,
        user_profile: dict = None
    ) -> Tuple[str, Optional[str], List[str], str]:
        """
        Prepares the context string, map image, sources, and detected intent category
        incorporating logged-in student profile metadata and authoritative campus datasets.
        """
        msg = question.lower().strip()

        # Fallback navigation map image resolution
        map_image = None
        nav_intent_keywords = [
            "where", "location", "reach", "map", "direction", "directions", 
            "way", "route", "locate", "find", "building", "block", "take me",
            "how to go", "how to reach", "navigate", "near", "what is near", "gate",
            "parking", "canteen", "library", "ground", "court", "auditorium"
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
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
        ]

        notice_keywords = [
            'notice', 'announcement', 'exam form', 'mid-term', 'submission',
            'fee', 'holiday', 'result', 're-check', 'circular', 'hall ticket'
        ]

        faculty_keywords = [
            'faculty', 'professor', 'teacher', 'prof', 'dr.',
            'who teaches', 'faculty for', 'professor for', 'teacher for', 'teaches',
            'hod', 'head of department', 'cabin', 'faculty detail',
            'registrar', 'student section', 'contact number', 'phone number', 'email address'
        ]

        placement_keywords = [
            'placement drive', 'package', 'lpa', 'salary', 
            'recruiter', 'highest package', 'upcoming placement', 'placement stats',
            'placement statistics', 'average package'
        ]

        subject_keywords = [
            'subject', 'subjects', 'syllabus', 'curriculum', 'course code',
            'subjects for', 'subjects in', 'what subjects', 'which subjects'
        ]

        events_keywords = [
            'event', 'events', 'workshop', 'workshops', 'seminar', 'symposium',
            'hackathon', 'competition', 'fest', 'techfest', 'cultural fest'
        ]

        transport_keywords = ['bus', 'route', 'transport', 'commute', 'pickup', 'driver', 'bus pass']
        library_keywords = ['library', 'book', 'issue', 'fine', 'author', 'reading room', 'journal']
        contact_keywords = ['contact', 'phone', 'email', 'office', 'admin', 'number', 'address']

        # -------------------------------------------------------------
        # 1. CAMPUS NAVIGATION / LANDMARK / FACILITIES CHECK FIRST
        # -------------------------------------------------------------
        nav_res = process_campus_navigation_context(question)
        if len(nav_res) == 4:
            nav_ctx, nav_img, nav_srcs, nav_loc = nav_res
        else:
            nav_ctx, nav_img, nav_srcs = nav_res
            nav_loc = None

        if nav_ctx:
            if nav_img and not map_image:
                clean_img = nav_img.replace('/static/', '').lstrip('/')
                map_image = clean_img

            intent_category = "facilities" if any("facilities.csv" in s for s in nav_srcs) else "campus_info"
            return nav_ctx, map_image, nav_srcs, intent_category, nav_loc

        # -------------------------------------------------------------
        # 2. SUBJECTS / CURRICULUM CHECK
        # -------------------------------------------------------------
        is_subject = any(k in msg for k in subject_keywords) and not any(k in msg for k in ['time', 'schedule', 'room'])
        if is_subject:
            subj_ctx, subj_srcs = process_subject_context(question, user_profile=user_profile)
            if subj_ctx and "NO_SUBJECTS" not in subj_ctx:
                return subj_ctx, None, subj_srcs, "subjects", None

        # -------------------------------------------------------------
        # 3. TIMETABLE CHECK
        # -------------------------------------------------------------
        is_timetable = any(k in msg for k in timetable_keywords)
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
            return context, map_image, sources, intent_category, None

        # -------------------------------------------------------------
        # 4. NOTICES & ANNOUNCEMENTS
        # -------------------------------------------------------------
        is_notice = any(k in msg for k in notice_keywords)
        if is_notice:
            intent_category = "notice"
            context = process_notice_context([], question, user_profile=user_profile)
            retrieved_docs = retrieve_context_tiered(
                self.vector_store,
                question,
                source_weights=[("notices.csv", 1.0)],
                top_k=top_k
            )
            admin_snippets = [doc.page_content for doc, _ in retrieved_docs if doc.metadata.get('source_type') == 'admin_document']
            if admin_snippets:
                context = "\n\n---\n\n".join(admin_snippets) + ("\n\n" + context if context else "")
            elif "notices.csv (Row" not in context:
                context = process_notice_context(retrieved_docs, question, user_profile=user_profile)

            sources = []
            for doc, _ in retrieved_docs:
                if doc.metadata.get('source_type') == 'admin_document':
                    doc_src = doc.metadata.get('source') or doc.metadata.get('document_name') or 'Official Document'
                    page_num = doc.metadata.get('page_number', 1)
                    sources.append(f"{doc_src} (Page {page_num})")

            csv_sources = re.findall(r'notices\.csv \(Row \d+\)', context)
            sources.extend(csv_sources)
            if not sources:
                sources = ["notices.csv"]
            return context, map_image, sources, intent_category, None

        # -------------------------------------------------------------
        # 5. FACULTY & DEPARTMENT
        # -------------------------------------------------------------
        is_faculty = any(k in msg for k in faculty_keywords)
        if is_faculty:
            intent_category = "faculty"
            context = process_faculty_context([], question, user_profile=user_profile)
            if "departments.csv (Row" not in context:
                retrieved_docs = retrieve_context_tiered(
                    self.vector_store,
                    question,
                    source_weights=[("faculty.csv", 1.0), ("departments.csv", 0.9)],
                    top_k=top_k
                )
                context = process_faculty_context(retrieved_docs, question, user_profile=user_profile)

            sources = re.findall(r'(?:departments|faculty)\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["faculty.csv", "departments.csv"]
            return context, map_image, sources, intent_category, None

        # -------------------------------------------------------------
        # 6. EVENTS & WORKSHOPS
        # -------------------------------------------------------------
        is_events = any(k in msg for k in events_keywords)
        if is_events:
            intent_category = "events"
            context = process_events_context(question)
            retrieved_docs = retrieve_context_tiered(
                self.vector_store,
                question,
                source_weights=[("events.csv", 1.0)],
                top_k=top_k
            )
            admin_snippets = [doc.page_content for doc, _ in retrieved_docs if doc.metadata.get('source_type') == 'admin_document']
            if admin_snippets:
                context = "\n\n---\n\n".join(admin_snippets) + ("\n\n" + context if context else "")
            elif "events.csv (Row" not in context:
                context = "\n\n---\n\n".join([doc.page_content for doc, _ in retrieved_docs])

            sources = []
            for doc, _ in retrieved_docs:
                if doc.metadata.get('source_type') == 'admin_document':
                    doc_src = doc.metadata.get('source') or doc.metadata.get('document_name') or 'Official Document'
                    page_num = doc.metadata.get('page_number', 1)
                    sources.append(f"{doc_src} (Page {page_num})")

            csv_sources = re.findall(r'events\.csv \(Row \d+\)', context)
            sources.extend(csv_sources)
            if not sources:
                sources = ["events.csv"]
            return context, map_image, sources, intent_category, None

        # -------------------------------------------------------------
        # 7. PLACEMENTS & DRIVES
        # -------------------------------------------------------------
        is_placement = any(k in msg for k in placement_keywords)
        if is_placement:
            intent_category = "placement"
            context = process_placement_context(question, user_profile=user_profile)
            sources = re.findall(r'placements\.csv \(Row \d+\)', context)
            if not sources:
                sources = ["placements.csv"]
            return context, map_image, sources, intent_category, None

        # -------------------------------------------------------------
        # 8. GENERAL VECTOR RETRIEVAL (Transport, Canteen, Library, Contact, FAQs)
        # -------------------------------------------------------------
        is_transport = any(k in msg for k in transport_keywords)
        is_library = any(k in msg for k in library_keywords)
        is_contact = any(k in msg for k in contact_keywords)

        if is_transport:
            intent_category = "transport"
        elif is_library:
            intent_category = "library"
        elif is_contact:
            intent_category = "contact"

        # Detect campus_info / facilities intent for location-aware source routing
        campus_facility_keywords = [
            "medical", "first aid", "reading room", "girls room", "girls common",
            "placement cell", "training & placement", "training and placement",
            "transport office", "main gate", "parking area", "parking",
            "auditorium", "seminar hall", "amphitheatre", "amphitheater",
            "gymnasium", "sports complex", "library", "central library",
            "canteen", "campus", "gate", "block", "building", "where is"
        ]
        if intent_category == "general" and any(k in msg for k in campus_facility_keywords):
            intent_category = "campus_info"

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

        sources = []
        seen = set()
        for doc, score in results:
            if doc.metadata.get('source_type') == 'admin_document' or 'page_number' in doc.metadata:
                doc_src = doc.metadata.get('source') or doc.metadata.get('document_name') or 'Official Document'
                page_num = doc.metadata.get('page_number', 1)
                src = f"{doc_src} (Page {page_num})"
                seen.add(src)
                sources.append(src)

        context = "\n\n---\n\n".join([doc.page_content for doc, _ in results])

        return context, map_image, sources, intent_category, None

    def _format_context_as_direct_answer(
        self, 
        question: str, 
        context: str, 
        intent_category: str, 
        user_profile: dict = None
    ) -> str:
        """
        Builds a clean, structured direct Markdown answer with compact mobile cards
        from extracted RAG context when external LLM is unavailable or unconfigured.
        """
        if not context or 'NO_DATA' in context or 'NO_CLASSES' in context or 'NO_NOTICES_FOUND' in context or 'NO_FACULTY_DETAILS_FOUND' in context:
            if intent_category == 'timetable':
                return "### 📅 Timetable & Schedule\n\nNo classes are currently scheduled for the selected day or semester. Please check your department notice board for special lab batch allocations."
            elif intent_category == 'placement':
                return "### 💼 SVIT Placement Opportunities\n\nNo matching placement records found. Please check with the Training & Placement Cell (T&P) for current drive schedules."
            elif intent_category == 'faculty':
                return "### 👨‍🏫 Faculty Information\n\nNo specific faculty record found for your search. Please ask for the faculty name or visit the Department Head office."
            else:
                return (
                    f"Thank you for asking about **\"{question}\"**!\n\n"
                    "I am the **SVIT AI Assistant**. I could not find a specific record in the local database for this query. "
                    "For official academic details, please consult your department coordinator or the student section."
                )

        # 1. CAMPUS NAVIGATION / LOCATION / FACILITIES FORMATTING
        if intent_category in ('campus_info', 'navigation', 'facilities'):
            entries = []
            blocks = [b.strip() for b in context.split('---') if b.strip()]
            for block in blocks:
                name_m = re.search(r'Place Name:\s*([^\n|]+)|Facility Name:\s*([^\n|]+)', block)
                pid_m = re.search(r'Place ID:\s*([^\n|]+)|Facility ID:\s*([^\n|]+)', block)
                zone_m = re.search(r'Campus Zone:\s*([^\n|]+)|Building / Block:\s*([^\n|]+)|Location / Landmark:\s*([^\n|]+)', block)
                lm_m = re.search(r'Landmark Reference:\s*([^\n|]+)', block)
                desc_m = re.search(r'Description:\s*([^\n|]+)', block)
                cat_m = re.search(r'Category:\s*([^\n|]+)', block)
                amen_m = re.search(r'Amenities & Equipment:\s*([^\n|]+)|Amenities & Features:\s*([^\n|]+)', block)
                cap_m = re.search(r'Capacity:\s*([^\n|]+)', block)
                stat_m = re.search(r'Status:\s*([^\n|]+)', block)
                
                name = (name_m.group(1) or name_m.group(2)).strip() if name_m else None
                if not name:
                    continue
                pid = (pid_m.group(1) or pid_m.group(2)).strip() if pid_m else ''
                zone = (zone_m.group(1) or zone_m.group(2) or (zone_m.group(3) if len(zone_m.groups()) >= 3 else '')).strip() if zone_m else ''
                lm = lm_m.group(1).strip() if lm_m else ''
                desc = desc_m.group(1).strip() if desc_m else ''
                cat = cat_m.group(1).strip() if cat_m else ''
                amen = (amen_m.group(1) or amen_m.group(2)).strip() if amen_m else ''
                cap = cap_m.group(1).strip() if cap_m else ''
                stat = stat_m.group(1).strip() if stat_m else ''
                
                card_lines = [f"* 📍 **{name}**{' (' + pid + ')' if pid else ''}"]
                if cat: card_lines.append(f"  * 🏷️ **Category:** {cat}")
                if zone: card_lines.append(f"  * 🏢 **Building / Location:** {zone}")
                if lm: card_lines.append(f"  * 📌 **Landmark:** {lm}")
                if cap and cap != 'N/A': card_lines.append(f"  * 👥 **Capacity:** {cap}")
                if desc: card_lines.append(f"  * 📝 **Description:** {desc}")
                if amen and amen != 'N/A': card_lines.append(f"  * 🛠️ **Amenities & Equipment:** {amen}")
                if stat and stat.lower() != 'active': card_lines.append(f"  * ℹ️ **Status:** {stat}")
                entries.append("\n".join(card_lines))
                
            if entries:
                return "### 📍 Campus Facility & Location Details\n\n" + "\n\n".join(entries)
            
            clean_ctx = re.sub(r'\[Source:.*?\]', '', context).strip()
            return f"### 📍 Campus Facility & Location Details\n\n{clean_ctx}"

        # 2. SUBJECTS FORMATTING
        elif intent_category == 'subjects':
            entries = []
            lines = context.split('\n')
            for line in lines:
                if 'Subject:' in line:
                    s_m = re.search(r'Subject:\s*([^|]+)', line)
                    p_m = re.search(r'Program:\s*([^|]+)', line)
                    d_m = re.search(r'Department:\s*([^|]+)', line)
                    sem_m = re.search(r'Semester:\s*([^|]+)', line)
                    if s_m:
                        entries.append(f"* 📖 **{s_m.group(1).strip()}** *(Sem {sem_m.group(1).strip() if sem_m else ''}, {d_m.group(1).strip() if d_m else ''})*")
            if entries:
                return "### 📚 Academic Subjects & Curriculum\n\n" + "\n".join(entries)
            clean_ctx = re.sub(r'\[Source:.*?\]', '', context).strip()
            return f"### 📚 Academic Subjects & Curriculum\n\n{clean_ctx}"

        # 3. TIMETABLE FORMATTING (Structured Compact Cards)
        elif intent_category == 'timetable':
            lines = context.split('\n')
            target_m = re.search(r'PERSONALIZED_STUDENT_SCHEDULE:\s*(.+)', context)
            date_m = re.search(r'HEADER_DATE:\s*(.+)', context)
            
            header_parts = ["### 📅 Class Schedule & Timetable\n"]
            if target_m:
                header_parts.append(f"🎯 **Target:** {target_m.group(1).strip()}")
            if date_m:
                header_parts.append(f"📆 **Date:** {date_m.group(1).strip()}\n")
                
            entries = []
            for line in lines:
                if 'Time:' in line and 'Subject:' in line:
                    time_m = re.search(r'Time:\s*([^|]+)', line)
                    subj_m = re.search(r'Subject:\s*([^|]+)', line)
                    fac_m = re.search(r'Faculty:\s*([^|]+)', line)
                    room_m = re.search(r'Room:\s*([^|]+)', line)
                    prog_m = re.search(r'Program:\s*([^|]+)', line)
                    dept_m = re.search(r'Department:\s*([^|]+)', line)
                    sem_m = re.search(r'Sem:\s*([^|]+)', line)
                    div_m = re.search(r'Div:\s*([^|]+)', line)
                    
                    t_str = time_m.group(1).strip() if time_m else 'N/A'
                    s_str = subj_m.group(1).strip() if subj_m else 'N/A'
                    f_str = fac_m.group(1).strip() if fac_m else 'N/A'
                    r_str = room_m.group(1).strip() if room_m else 'N/A'
                    p_str = prog_m.group(1).strip() if prog_m else ''
                    d_str = dept_m.group(1).strip() if dept_m else ''
                    sem_str = sem_m.group(1).strip() if sem_m else ''
                    div_str = div_m.group(1).strip() if div_m else ''
                    
                    meta_tags = []
                    if d_str and d_str != 'N/A': meta_tags.append(d_str)
                    if p_str and p_str != 'N/A': meta_tags.append(f"Prog: {p_str}")
                    if sem_str and sem_str != 'N/A': meta_tags.append(f"Sem {sem_str}")
                    if div_str and div_str != 'N/A': meta_tags.append(f"Div {div_str}")
                    meta_str = f" *({', '.join(meta_tags)})*" if meta_tags else ""
                    
                    card = (
                        f"* 🕐 **{t_str}** — **{s_str}**\n"
                        f"  * 👨‍🏫 **Faculty:** {f_str}\n"
                        f"  * 📍 **Room / Lab:** **{r_str}**{meta_str}"
                    )
                    entries.append(card)
                    
            if entries:
                header_parts.append("\n\n".join(entries))
                return "\n".join(header_parts)
            
            clean_ctx = re.sub(r'HEADER_DATE:.*?\n|TARGET_DAY:.*?\n|NAVIGATION_MAP_URL:.*?\n|\[Source:.*?\]', '', context)
            return f"### 📅 Class Schedule & Timetable\n\n{clean_ctx.strip()}"

        # 4. EVENTS FORMATTING (Structured Compact Cards)
        elif intent_category == 'events':
            entries = []
            lines = context.split('\n')
            for line in lines:
                if 'Event:' in line and 'Venue:' in line:
                    ev_m = re.search(r'Event:\s*([^|]+)', line)
                    date_m = re.search(r'Date:\s*([^|]+)', line)
                    venue_m = re.search(r'Venue:\s*([^|]+)', line)
                    desc_m = re.search(r'Description:\s*([^|]+)', line)
                    
                    ev_str = ev_m.group(1).strip() if ev_m else 'College Event'
                    d_str = date_m.group(1).strip() if date_m else 'TBA'
                    v_str = venue_m.group(1).strip() if venue_m else 'Campus'
                    desc_str = desc_m.group(1).strip() if desc_m else ''
                    
                    card = (
                        f"* 🎪 **{ev_str}**\n"
                        f"  * 📅 **Date & Time:** {d_str}\n"
                        f"  * 📍 **Venue:** **{v_str}**\n"
                        f"  * 📝 **Description:** {desc_str}"
                    )
                    entries.append(card)
                    
            if entries:
                return "### 📢 Upcoming SVIT Events & Workshops\n\n" + "\n\n".join(entries)
                
            clean_ctx = re.sub(r'HEADER_EVENT_LIST:\s*|\[Source:.*?\]', '', context)
            return f"### 📢 Upcoming SVIT Events & Workshops\n\n{clean_ctx.strip()}"

        # 5. FACULTY FORMATTING (Structured Compact Cards)
        elif intent_category == 'faculty':
            entries = []
            blocks = [b.strip() for b in context.split('---') if b.strip()]
            for block in blocks:
                name_m = re.search(r'Full Name:\s*([^|\n]+)|HOD / Faculty:\s*([^|\n]+)', block)
                dept_m = re.search(r'Department:\s*([^|\n]+)', block)
                desig_m = re.search(r'Designation:\s*([^|\n]+)', block)
                subj_m = re.search(r'Subject:\s*([^|\n]+)', block)
                cabin_m = re.search(r'Cabin:\s*([^|\n]+)|Building/Cabin:\s*([^|\n]+)', block)
                email_m = re.search(r'Email:\s*([^|\n]+)', block)
                phone_m = re.search(r'Phone:\s*([^|\n]+)', block)
                prog_m = re.search(r'Program:\s*([^|\n]+)', block)
                
                name = (name_m.group(1) or name_m.group(2)).strip() if name_m else None
                if not name:
                    continue
                dept = dept_m.group(1).strip() if dept_m else ''
                desig = desig_m.group(1).strip() if desig_m else ''
                subj = subj_m.group(1).strip() if subj_m else ''
                cabin = (cabin_m.group(1) or cabin_m.group(2)).strip() if cabin_m else ''
                email = email_m.group(1).strip() if email_m else ''
                phone = phone_m.group(1).strip() if phone_m else ''
                prog = prog_m.group(1).strip() if prog_m else ''
                
                desig_badge = f" *({desig})*" if desig else ""
                dept_info = f"{dept} ({prog})" if (dept and prog) else (dept or prog)
                
                card_lines = [f"* 👤 **{name}**{desig_badge}"]
                if dept_info: card_lines.append(f"  * 🏛️ **Department:** {dept_info}")
                if subj: card_lines.append(f"  * 📖 **Subject:** {subj}")
                if cabin and cabin != 'N/A': card_lines.append(f"  * 📍 **Cabin / Office:** **{cabin}**")
                if email and email != 'N/A': card_lines.append(f"  * ✉️ **Email:** `{email}`")
                if phone and phone != 'N/A': card_lines.append(f"  * 📞 **Contact:** {phone}")
                
                entries.append("\n".join(card_lines))
                
            if entries:
                return "### 👨‍🏫 Faculty & Department Details\n\n" + "\n\n".join(entries)
                
            clean_ctx = re.sub(r'NAVIGATION_MAP_URL:.*?\n|departments\.csv \(Row \d+\):\s*', '', context)
            return f"### 👨‍🏫 Faculty & Department Details\n\n{clean_ctx.strip()}"

        # 6. PLACEMENTS FORMATTING (Macro Stats + Compact Company Cards)
        elif intent_category == 'placement':
            peak_m = re.search(r'Highest Package:\s*([^\n]+)', context)
            avg_m = re.search(r'Average Package:\s*([^\n]+)', context)
            rec_m = re.search(r'Top Recruiting Companies:\s*([^\n]+)', context)
            
            header_lines = ["### 💼 SVIT Placement Drives & Statistics\n"]
            if peak_m and avg_m:
                header_lines.append(f"📊 **Highest Package:** {peak_m.group(1).strip()} &nbsp;|&nbsp; 📈 **Average Package:** {avg_m.group(1).strip()}")
            if rec_m:
                header_lines.append(f"🏢 **Top Recruiters:** {rec_m.group(1).strip()}\n")
                
            drives = []
            lines = context.split('\n')
            for line in lines:
                if 'Company:' in line and 'Package:' in line:
                    comp_m = re.search(r'Company:\s*([^|]+)', line)
                    pkg_m = re.search(r'Package:\s*([^|]+)', line)
                    dept_m = re.search(r'Department:\s*([^|]+)|Dept:\s*([^|]+)', line)
                    status_m = re.search(r'Status:\s*([^|]+)', line)
                    
                    c_str = comp_m.group(1).strip() if comp_m else 'Company'
                    pk_str = pkg_m.group(1).strip() if pkg_m else 'N/A'
                    d_str = (dept_m.group(1) or dept_m.group(2)).strip() if dept_m else ''
                    st_str = status_m.group(1).strip() if status_m else 'Active'
                    
                    card = (
                        f"* 💼 **{c_str}** — **₹{pk_str}**\n"
                        f"  * 🎓 **Eligible Depts:** {d_str}\n"
                        f"  * 📋 **Drive Status:** {st_str}"
                    )
                    drives.append(card)
                    
            if drives:
                header_lines.append("#### 🏢 Active & Upcoming Recruitment Drives\n")
                header_lines.append("\n\n".join(drives))
                return "\n".join(header_lines)
                
            clean_ctx = re.sub(r'\[Source:.*?\]', '', context)
            return f"### 💼 SVIT Placement Drives & Statistics\n\n{clean_ctx.strip()}"

        # 7. NOTICES FORMATTING (Structured Notice Cards)
        elif intent_category == 'notices':
            entries = []
            lines = context.split('\n')
            for line in lines:
                if 'Notice Title:' in line:
                    t_m = re.search(r'Notice Title:\s*([^|]+)', line)
                    d_m = re.search(r'Date:\s*([^|]+)', line)
                    det_m = re.search(r'Details:\s*([^|]+)', line)
                    tgt_m = re.search(r'Target Dept/Sem:\s*([^|]+)', line)
                    
                    t_str = t_m.group(1).strip() if t_m else 'Official Notice'
                    d_str = d_m.group(1).strip() if d_m else ''
                    det_str = det_m.group(1).strip() if det_m else ''
                    tgt_str = tgt_m.group(1).strip() if tgt_m else 'All Students'
                    
                    date_badge = f" *({d_str})*" if d_str and d_str != 'N/A' else ""
                    card = (
                        f"* 📌 **{t_str}**{date_badge}\n"
                        f"  * 📝 **Details:** {det_str}\n"
                        f"  * 🎯 **Applicable to:** {tgt_str}"
                    )
                    entries.append(card)
                    
            if entries:
                return "### 📌 Official Notices & Circulars\n\n" + "\n\n".join(entries)
                
            clean_ctx = re.sub(r'HEADER_NOTICE_LIST:\s*|\[Source:.*?\]', '', context)
            return f"### 📌 Official Notices & Circulars\n\n{clean_ctx.strip()}"

        # 8. GENERAL / FAQ / DEFAULT FORMATTING
        else:
            blocks = [b.strip() for b in context.split('---') if b.strip()]
            if blocks:
                clean_blocks = []
                for b in blocks[:3]:
                    clean_b = re.sub(r'\[Source:.*?\]', '', b).strip()
                    if clean_b:
                        clean_blocks.append(clean_b)
                return f"### ℹ️ SVIT Campus Information\n\n" + "\n\n---\n\n".join(clean_blocks)
            return f"### ℹ️ SVIT Campus Information\n\n{context.strip()}"

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
        3. Fast Spatial Room/Floor Navigation (0ms)
        4. Response Cache Lookup
        5. In-Memory Context Processing with student defaults
        6. Category-Trimmed Prompt with Student Metadata + OpenRouter LLM (or robust direct context fallback)
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
        # ---------------------------------------------------------
        # STEP 0.1: RESOLVE "MY DEPARTMENT" LOCATION
        # ---------------------------------------------------------
        user_dept = user_profile.get("department") if user_profile else None
        is_my_dept_location = bool(re.search(r'\b(where|location|locate|find|building|block|reach|direction|directions|how to go|how to reach|way to|kaha|kahan|kidhar)\b', clean_q)) and bool(re.search(r'\b(my department|my dept|my branch|my building)\b', clean_q))
        if is_my_dept_location and user_dept:
            nav_result = find_location(f"where is {user_dept} department")
            if nav_result:
                nav_image_path = f"navigation_maps/{nav_result['image']}"
                dept_bldg = nav_result.get("formatted_text", "")
                ans_text = f"📍 **{user_dept}** (Your Registered Department)\n\n" + dept_bldg.replace(f"📍 **{nav_result['department']}**\n\n", "")
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", ans_text)
                suggestions = generate_followup_suggestions(question, "navigation", ans_text, user_profile=user_profile)
                return {
                    "answer": ans_text,
                    "image": nav_image_path,
                    "location": nav_result,
                    "sources": ["departments.csv", "campus_info.csv", "student_profile.db"],
                    "navigation": nav_result,
                    "suggestions": suggestions
                }

        # ---------------------------------------------------------
        # STEP 0.2: FAST DIRECT STUDENT PROFILE RESOLUTION
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
        # STEP 0.5: FAST NEXT CLASS REAL-TIME INTERCEPTION (0ms)
        # ---------------------------------------------------------
        nav_bypass_words = ['transport', 'office', 'canteen', 'food', 'gate', 'library', 'auditorium', 'sports', 'gym', 'hostel', 'parking', 'amphitheatre', 'placement', 'cell', 'reading room', 'girls room']
        is_nav_keyword = any(k in clean_q for k in nav_bypass_words)
        if not is_nav_keyword and any(re.search(p, clean_q) for p in NEXT_CLASS_PATTERNS):
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
        # STEP 1: FAST SPATIAL ROOM / FLOOR NAVIGATION LOOKUP (0ms)
        # ---------------------------------------------------------
        # For specific lab codes (L1-L5) or room numbers (201-405), resolve instantly via building floor plans
        if re.search(r'\b(?:lab\s*l[1-5]|room\s*[2-4]0[1-5]|[2-4]0[1-5])\b', clean_q):
            nav_result = find_location(question)
            if nav_result:
                nav_image_path = f"navigation_maps/{nav_result['image']}"
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", nav_result["formatted_text"])
                suggestions = generate_followup_suggestions(question, "navigation", nav_result["formatted_text"], user_profile=user_profile)
                return {
                    "answer": nav_result["formatted_text"],
                    "image": nav_image_path,
                    "location": nav_result,
                    "sources": ["rooms_facilities.csv", "campus_info.csv"],
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
        context, map_image, sources, intent_category, location_info = self._prepare_rag_context(
            question, top_k=top_k, filter_dict=filter_dict, user_profile=user_profile
        )

        history = memory_manager.format_history_for_prompt(session_id)
        current_date_str = datetime.now(IST).strftime("%A, %d %B %Y")

        prompt = get_dynamic_system_prompt(
            intent_category=intent_category,
            current_date=current_date_str,
            history=history,
            context=context,
            question=question,
            user_profile=user_profile
        )

        # ---------------------------------------------------------
        # STEP 4: LLM INFERENCE OR DIRECT CONTEXT FORMATTING
        # ---------------------------------------------------------
        try:
            response = self.llm.invoke(prompt)
            answer = response.content
            answer = re.sub(r'!\[.*?\]\(.*?\)', '', answer).strip()
        except Exception as e:
            print(f"[RAG] LLM inference fallback ({e}) -> using formatted knowledge base context.")
            answer = self._format_context_as_direct_answer(question, context, intent_category, user_profile=user_profile)

        # Save to session memory
        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", answer)

        suggestions = generate_followup_suggestions(
            question, 
            intent_category, 
            answer,
            user_profile=user_profile
        )

        result_payload = {
            "answer": answer,
            "image": map_image,
            "location": location_info,
            "sources": sources,
            "suggestions": suggestions
        }

        # Cache valid responses (up to _MAX_RESPONSE_CACHE)
        if len(_RESPONSE_CACHE) >= _MAX_RESPONSE_CACHE:
            _RESPONSE_CACHE.popitem(last=False)
        _RESPONSE_CACHE[cache_key] = result_payload

        return result_payload

    def stream_answer_question(
        self, 
        question: str, 
        session_id: str = "default_user", 
        top_k: int = 8,
        filter_dict: dict = None,
        user_profile: dict = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams personalized RAG answer chunk-by-chunk for Server-Sent Events (SSE).
        """
        clean_q = question.strip().lower()
        user_name = user_profile.get('full_name') if user_profile else ""
        first_name = user_name.split()[0] if user_name else ""
        name_suffix = f" {first_name}" if first_name else ""

        # Step 0: Fast greetings
        for pattern, reply_tmpl in FAST_GREETINGS:
            if re.search(pattern, clean_q):
                reply = reply_tmpl.format(name_suffix=name_suffix)
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", reply)
                suggestions = generate_followup_suggestions(question, "general", reply, user_profile=user_profile)
                yield {"chunk": reply, "done": False}
                yield {"done": True, "answer": reply, "image": None, "sources": ["SVIT Assistant Greeting"], "suggestions": suggestions}
                return

        # Step 0.1: My Department Location
        user_dept = user_profile.get("department") if user_profile else None
        is_my_dept_location = bool(re.search(r'\b(where|location|locate|find|building|block|reach|direction|directions|how to go|how to reach|way to|kaha|kahan|kidhar)\b', clean_q)) and bool(re.search(r'\b(my department|my dept|my branch|my building)\b', clean_q))
        if is_my_dept_location and user_dept:
            nav_result = find_location(f"where is {user_dept} department")
            if nav_result:
                nav_image_path = f"navigation_maps/{nav_result['image']}"
                dept_bldg = nav_result.get("formatted_text", "")
                ans_text = f"📍 **{user_dept}** (Your Registered Department)\n\n" + dept_bldg.replace(f"📍 **{nav_result['department']}**\n\n", "")
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", ans_text)
                suggestions = generate_followup_suggestions(question, "navigation", ans_text, user_profile=user_profile)
                yield {"chunk": ans_text, "done": False}
                yield {"done": True, "answer": ans_text, "image": nav_image_path, "location": nav_result, "sources": ["departments.csv", "campus_info.csv", "student_profile.db"], "suggestions": suggestions}
                return

        # Step 0.2: Profile query
        profile_ans = resolve_student_profile_query(question, user_profile=user_profile)
        if profile_ans:
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", profile_ans)
            suggestions = ["Show today's timetable 📅", "Where is my next class right now? 📍", "Who is my HOD? 👨‍🏫"]
            yield {"chunk": profile_ans, "done": False}
            yield {"done": True, "answer": profile_ans, "image": None, "sources": ["student_profile.db"], "suggestions": suggestions}
            return

        # Step 0.5: Next class now
        nav_bypass_words = ['transport', 'office', 'canteen', 'food', 'gate', 'library', 'auditorium', 'sports', 'gym', 'hostel', 'parking', 'amphitheatre', 'placement', 'cell', 'reading room', 'girls room']
        is_nav_keyword = any(k in clean_q for k in nav_bypass_words)
        if not is_nav_keyword and any(re.search(p, clean_q) for p in NEXT_CLASS_PATTERNS):
            ans_text, nav_map, srcs = process_next_class_context(question, user_profile=user_profile)
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", ans_text)
            suggestions = generate_followup_suggestions(question, "timetable", ans_text, user_profile=user_profile)
            yield {"chunk": ans_text, "done": False}
            yield {"done": True, "answer": ans_text, "image": nav_map, "sources": srcs, "suggestions": suggestions}
            return

        # Step 1: Spatial Room / Floor Navigation
        if re.search(r'\b(?:lab\s*l[1-5]|room\s*[2-4]0[1-5]|[2-4]0[1-5])\b', clean_q):
            nav_result = find_location(question)
            if nav_result:
                nav_image_path = f"navigation_maps/{nav_result['image']}"
                memory_manager.add_message(session_id, "user", question)
                memory_manager.add_message(session_id, "assistant", nav_result["formatted_text"])
                suggestions = generate_followup_suggestions(question, "navigation", nav_result["formatted_text"], user_profile=user_profile)
                yield {"chunk": nav_result["formatted_text"], "done": False}
                yield {"done": True, "answer": nav_result["formatted_text"], "image": nav_image_path, "location": nav_result, "sources": ["rooms_facilities.csv", "campus_info.csv"], "suggestions": suggestions}
                return

        # Step 3: Prepare Context & Dynamic Prompt
        context, map_image, sources, intent_category, location_info = self._prepare_rag_context(
            question, top_k=top_k, filter_dict=filter_dict, user_profile=user_profile
        )

        history = memory_manager.format_history_for_prompt(session_id)
        current_date_str = datetime.now(IST).strftime("%A, %d %B %Y")

        prompt = get_dynamic_system_prompt(
            intent_category=intent_category,
            current_date=current_date_str,
            history=history,
            context=context,
            question=question,
            user_profile=user_profile
        )

        full_answer = ""
        try:
            for chunk in self.llm.stream(prompt):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    full_answer += content
                    yield {"chunk": content, "done": False}
        except Exception as e:
            print(f"[RAG] LLM stream fallback ({e}) -> using direct context formatting.")
            full_answer = self._format_context_as_direct_answer(question, context, intent_category, user_profile=user_profile)
            yield {"chunk": full_answer, "done": False}

        full_answer = re.sub(r'!\[.*?\]\(.*?\)', '', full_answer).strip()

        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", full_answer)

        suggestions = generate_followup_suggestions(
            question,
            intent_category,
            full_answer,
            user_profile=user_profile
        )

        yield {
            "done": True,
            "answer": full_answer,
            "image": map_image,
            "location": location_info,
            "sources": sources,
            "suggestions": suggestions
        }


def get_rag_pipeline(force_rebuild: bool = False) -> RAGPipeline:
    return RAGPipeline(force_rebuild=force_rebuild)