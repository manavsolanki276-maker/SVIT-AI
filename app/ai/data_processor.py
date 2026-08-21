"""
app/ai/data_processor.py
High-performance In-Memory Pandas Context Processors with Student Profile Personalization
and Real-Time "Next Class Now" / "Where Do I Go Right Now?" schedule analyzer.
"""
import os
import re
import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# =========================================================================
# STATIC MAP & LOCATION LOOKUP DIRECTORY
# =========================================================================
MAP_LOOKUP: Dict[str, str] = {
    # 1. Diploma Building
    "diploma computer engineering": "diploma dep.jpeg",
    "diploma computer": "diploma dep.jpeg",
    "diploma ce": "diploma dep.jpeg",
    "diploma information technology": "diploma dep.jpeg",
    "diploma it": "diploma dep.jpeg",
    "diploma mechanical engineering": "diploma dep.jpeg",
    "diploma mechanical": "diploma dep.jpeg",
    "diploma electrical engineering": "diploma dep.jpeg",
    "diploma electrical": "diploma dep.jpeg",
    "diploma civil engineering": "diploma dep.jpeg",
    "diploma civil": "diploma dep.jpeg",
    "diploma department": "diploma dep.jpeg",
    "diploma block": "diploma dep.jpeg",
    "diploma": "diploma dep.jpeg",

    # 2. Degree / PG Departments
    "computer engineering": "Computer dep.jpeg",
    "computer department": "Computer dep.jpeg",
    "computer": "Computer dep.jpeg",
    "information technology": "IT dep.jpeg",
    "it department": "IT dep.jpeg",
    "it": "IT dep.jpeg",
    "mechanical department": "Mechanical dep.jpeg",
    "mechanical": "Mechanical dep.jpeg",
    "civil department": "Civil dep.jpeg",
    "civil": "Civil dep.jpeg",
    "electrical department": "Electrical dep.jpeg",
    "electrical": "Electrical dep.jpeg",
    "electronics & communication": "E&C dep.jpeg",
    "electronics and communication": "E&C dep.jpeg",
    "electronics": "E&C dep.jpeg",
    "ec": "E&C dep.jpeg",
    "aeronautical engineering": "Aero dep.jpeg",
    "aeronautical": "Aero dep.jpeg",
    "aero department": "Aero dep.jpeg",
    "aero": "Aero dep.jpeg",
    "mca & bca": "MCA&BCA.jpeg",
    "mca and bca": "MCA&BCA.jpeg",
    "mca": "MCA&BCA.jpeg",
    "bca": "MCA&BCA.jpeg",

    # 3. Admin Block & Facilities
    "admin": "Admin dep.jpeg",
    "admin building": "Admin dep.jpeg",
    "administration": "Admin dep.jpeg",
    "admin block": "Admin dep.jpeg",
    "library": "Admin dep.jpeg",
    "central library": "Admin dep.jpeg",
    "librari": "Admin dep.jpeg",
    "reading room": "Admin dep.jpeg",
    "book bank": "Admin dep.jpeg",
    "indoor sports": "Admin dep.jpeg",
    "indoor sports room": "Admin dep.jpeg",
    "sports room": "Admin dep.jpeg",
    "girls room": "Admin dep.jpeg",
    "girls common room": "Admin dep.jpeg",
    "girls rest room": "Admin dep.jpeg",

    # 4. Outdoor Sports & Pavilion
    "sports court": "Sports court.png",
    "sports ground": "Sports court.png",
    "outdoor sports": "Sports court.png",
    "pavilion": "Sports court.png",
    "pavellinon": "Sports court.png",
    "paviloin": "Sports court.png",
    "playground": "Sports court.png",
    "cricket ground": "Sports court.png",
    "volleyball court": "Sports court.png",
    "basketball court": "Sports court.png",

    # 5. Amenities & Campus Locations
    "canteen": "SVIT Canteen loc.png",
    "central canteen": "SVIT Canteen loc.png",
    "stationary": "Stationarys.png",
    "stationery": "Stationarys.png",
    "xerox shop": "Stationarys.png",
    "bus stop": "Bus stop.png",
    "bus stand": "Bus stop.png",
    "campus": "SVIT with all dep.jpeg",
    "all departments": "SVIT with all dep.jpeg",
}

# =========================================================================
# IN-MEMORY DATAFRAME CACHE (ZERO DISK I/O AFTER FIRST LOAD)
# =========================================================================
_DF_CACHE: Dict[str, pd.DataFrame] = {}

def get_cached_dataframe(filename: str) -> Optional[pd.DataFrame]:
    """
    Returns an in-memory cached copy of a knowledge base CSV DataFrame.
    """
    if filename in _DF_CACHE:
        return _DF_CACHE[filename]

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    possible_paths = [
        os.path.join(project_root, "knowledge_base", filename),
        os.path.join(project_root, "knowledge_base", "faq", filename),
        os.path.join(os.getcwd(), "knowledge_base", filename),
        os.path.join(os.getcwd(), "data", filename),
        os.path.join(os.getcwd(), filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, dtype=str)
                df = df.fillna("")
                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
                _DF_CACHE[filename] = df
                return df
            except Exception as e:
                print(f"[Cache] Error loading {filename}: {e}")
                return None

    return None


def preload_all_dataframes() -> None:
    """Preloads critical knowledge base DataFrames into memory at startup."""
    critical_files = [
        "timetable.csv",
        "departments.csv",
        "notices.csv",
        "events.csv",
        "placements.csv",
        "faculty.csv",
        "transport.csv",
        "canteen.csv",
        "library_books.csv",
    ]
    loaded_count = 0
    for fname in critical_files:
        if get_cached_dataframe(fname) is not None:
            loaded_count += 1
    print(f"[Cache] In-memory DataFrame cache ready: {loaded_count}/{len(critical_files)} datasets preloaded.")


# =========================================================
# DATE & TEMPORAL RESOLUTION HELPERS
# =========================================================

def parse_time_to_minutes(t_str: str) -> Optional[int]:
    """Converts timetable time strings ('09:00', '11:15', '01:15', '02:00', '03:00') to minutes since midnight."""
    if not t_str or not isinstance(t_str, str):
        return None
    cleaned = t_str.strip().lower().replace("am", "").replace("pm", "").strip()
    match = re.match(r'^(\d{1,2})[:.](\d{2})$', cleaned)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    # Timetable PM hour conversion (classes run 9 AM to 5 PM)
    if hours < 8:
        hours += 12
    return hours * 60 + minutes


def format_minutes_to_time_str(mins: int) -> str:
    """Converts minutes since midnight to clean 12-hour AM/PM format."""
    hours = mins // 60
    minutes = mins % 60
    suffix = "AM" if hours < 12 else "PM"
    display_hour = hours if hours <= 12 else hours - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{minutes:02d} {suffix}"


def resolve_day_and_date(query: str) -> dict:
    """
    Resolves relative time keywords ('today', 'tomorrow', 'yesterday') or explicit day names
    into both the target day name ('Wednesday') and a formatted date string.
    """
    msg = re.sub(r"['’]s\b", "", query, flags=re.IGNORECASE)
    msg = msg.replace('"', '').replace("'", "").strip().lower()

    now = datetime.datetime.now()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    if "tomorrow" in msg:
        target_date = now + datetime.timedelta(days=1)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y")
        }

    if "yesterday" in msg:
        target_date = now - datetime.timedelta(days=1)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y")
        }

    if "today" in msg:
        return {
            "day_name": now.strftime("%A"),
            "formatted_date": now.strftime("%A, %d %B %Y")
        }

    for day in days:
        if re.search(r'\b' + day + r'\b', msg) or re.search(r'\b' + day[:3] + r'\b', msg):
            days_ahead = days.index(day) - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now + datetime.timedelta(days=days_ahead)
            return {
                "day_name": day.capitalize(),
                "formatted_date": target_date.strftime("%A, %d %B %Y")
            }

    return {
        "day_name": now.strftime("%A"),
        "formatted_date": now.strftime("%A, %d %B %Y")
    }


def resolve_day_name(query: str) -> str:
    return resolve_day_and_date(query)["day_name"]


def get_map_filename(query: str) -> str:
    clean_q = query.lower()
    sorted_keys = sorted(MAP_LOOKUP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, clean_q):
            return MAP_LOOKUP[key]
    return "SVIT with all dep.jpeg"


def get_navigation_map_url(query: str) -> str:
    map_file = get_map_filename(query)
    if map_file:
        return f"/static/navigation_maps/{map_file}"
    return "/static/navigation_maps/SVIT with all dep.jpeg"


# =========================================================================
# DOMAIN CONTEXT PROCESSORS WITH STUDENT PERSONALIZATION
# =========================================================================

def process_next_class_context(query: str, user_profile: dict = None) -> Tuple[str, Optional[str], List[str]]:
    """
    Computes real-time lecture status (Current Class In Progress vs Upcoming Next Class)
    based on the current clock time and the logged-in student's schedule.
    """
    now = datetime.datetime.now()
    current_day = now.strftime("%A")
    formatted_date = now.strftime("%A, %d %B %Y")
    current_time_str = now.strftime("%I:%M %p")
    current_mins = now.hour * 60 + now.minute

    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or "Computer Engineering"
    prof_sem = str(user_profile.get("semester") or "3")
    prof_div = str(user_profile.get("division") or "A").strip().upper()
    prof_name = user_profile.get("full_name") or "Student"

    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    div_match = re.search(r'\b(?:division|div|sec|section)[\s\-:]*([a-c])\b|\b([a-c])\s*(?:division|div|sec|section)\b', cleaned_query, re.IGNORECASE)
    target_div = (div_match.group(1) or div_match.group(2)).upper() if div_match else prof_div

    sem_match = re.search(r'\b(?:sem|semester)[\s\-:]*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s*(?:sem|semester)\b', cleaned_query, re.IGNORECASE)
    target_sem = (sem_match.group(1) or sem_match.group(2)) if sem_match else prof_sem

    df = get_cached_dataframe("timetable.csv")
    if df is None or df.empty:
        return "No timetable records available.", None, ["timetable.csv"]

    col_map = {str(c).lower(): c for c in df.columns}
    day_col = col_map.get("day")
    dept_col = col_map.get("department") or col_map.get("dept")
    div_col = col_map.get("division") or col_map.get("div")
    sem_col = col_map.get("semester") or col_map.get("sem")

    matched_df = df[df[day_col].str.lower().str.startswith(current_day[:3].lower(), na=False)].copy()
    if matched_df.empty:
        return (
            f"🎉 **NO CLASSES SCHEDULED TODAY!**\n\n"
            f"Today is **{formatted_date}** (Weekend/Holiday).\n"
            f"There are no classes scheduled today for {prof_dept} (Sem {target_sem} - Div {target_div}). Enjoy your day! 🚀",
            None,
            ["timetable.csv"]
        )

    if dept_col and prof_dept:
        prof_dept_clean = prof_dept.strip().lower()
        dept_match_df = matched_df[matched_df[dept_col].str.lower().str.strip() == prof_dept_clean]
        if not dept_match_df.empty:
            matched_df = dept_match_df
        else:
            dept_keyword = prof_dept.split()[0].lower()
            matched_df = matched_df[matched_df[dept_col].str.lower().str.contains(dept_keyword, na=False)]

    if sem_col and target_sem:
        matched_df = matched_df[matched_df[sem_col].astype(str).str.contains(str(target_sem), na=False)]

    if div_col and target_div:
        matched_df = matched_df[matched_df[div_col].astype(str).str.upper() == target_div.upper()]

    if matched_df.empty:
        return (
            f"No classes found for {prof_dept} (Sem {target_sem} - Div {target_div}) on {current_day}.",
            None,
            ["timetable.csv"]
        )

    parsed_classes = []
    for idx, row in matched_df.iterrows():
        s_raw = str(row.get('start_time', row.get('Start_Time', ''))).strip()
        e_raw = str(row.get('end_time', row.get('End_Time', ''))).strip()
        s_min = parse_time_to_minutes(s_raw)
        e_min = parse_time_to_minutes(e_raw)
        if s_min is not None and e_min is not None:
            parsed_classes.append({
                "subject": row.get('subject', 'Subject'),
                "faculty": row.get('faculty', 'Faculty'),
                "room": row.get('room', 'Room'),
                "start_min": s_min,
                "end_min": e_min,
                "start_str": format_minutes_to_time_str(s_min),
                "end_str": format_minutes_to_time_str(e_min),
                "row_num": idx + 2
            })

    parsed_classes.sort(key=lambda x: x["start_min"])

    if not parsed_classes:
        return "Timetable class timings could not be determined.", None, ["timetable.csv"]

    current_class = None
    next_class = None
    upcoming_classes = []

    for item in parsed_classes:
        if item["start_min"] <= current_mins < item["end_min"]:
            current_class = item
        elif item["start_min"] > current_mins:
            upcoming_classes.append(item)

    if upcoming_classes:
        next_class = upcoming_classes[0]

    active_room = current_class["room"] if current_class else (next_class["room"] if next_class else parsed_classes[0]["room"])
    map_file = "Computer dep.jpeg"
    if "diploma" in prof_dept.lower() or "diploma" in active_room.lower():
        map_file = "diploma dep.jpeg"
    elif "civil" in prof_dept.lower() or "ci" in active_room.lower():
        map_file = "Civil dep.jpeg"
    elif "mech" in prof_dept.lower() or "me" in active_room.lower():
        map_file = "Mechanical dep.jpeg"
    elif "it" in prof_dept.lower() or "in" in active_room.lower():
        map_file = "IT dep.jpeg"
    elif "admin" in active_room.lower():
        map_file = "Admin dep.jpeg"

    map_path = f"navigation_maps/{map_file}"

    header = f"### 📍 Real-Time Class Status for {prof_name}\n"
    header += f"**{prof_dept} | Sem {target_sem} - Div {target_div}** (Current Time: **{current_time_str}**, {current_day})\n\n"

    body_parts = []
    if current_class:
        body_parts.append(
            f"🔴 **CLASS IN PROGRESS RIGHT NOW:**\n"
            f"* 📖 **Subject:** **{current_class['subject']}**\n"
            f"* 🏫 **Room / Location:** **{current_class['room']}**\n"
            f"* ⏰ **Timing:** {current_class['start_str']} - {current_class['end_str']}\n"
            f"* 👨‍🏫 **Faculty:** {current_class['faculty']}\n"
        )
        if next_class:
            body_parts.append(
                f"⏭️ **UPCOMING NEXT CLASS TODAY:**\n"
                f"* 📖 **Subject:** **{next_class['subject']}**\n"
                f"* 🏫 **Room / Location:** **{next_class['room']}**\n"
                f"* ⏰ **Starts At:** **{next_class['start_str']}** (until {next_class['end_str']})\n"
                f"* 👨‍🏫 **Faculty:** {next_class['faculty']}\n"
            )
    elif next_class:
        mins_until = next_class['start_min'] - current_mins
        time_desc = f"in {mins_until} minutes" if mins_until < 60 else f"at {next_class['start_str']}"
        body_parts.append(
            f"⏰ **YOUR NEXT CLASS TODAY ({time_desc}):**\n"
            f"* 📖 **Subject:** **{next_class['subject']}**\n"
            f"* 🏫 **Room / Location:** **{next_class['room']}**\n"
            f"* ⏰ **Time Slot:** **{next_class['start_str']} - {next_class['end_str']}**\n"
            f"* 👨‍🏫 **Faculty:** {next_class['faculty']}\n"
        )
        if len(upcoming_classes) > 1:
            later = upcoming_classes[1]
            body_parts.append(f"*Following that:* **{later['subject']}** in **{later['room']}** at **{later['start_str']}**.\n")
    else:
        last_class = parsed_classes[-1]
        body_parts.append(
            f"✅ **ALL CLASSES COMPLETED FOR TODAY!**\n"
            f"You have no more lectures scheduled for today ({current_day}).\n\n"
            f"*Your last lecture was **{last_class['subject']}** at **{last_class['start_str']} - {last_class['end_str']}**.*\n\n"
            f"Enjoy the rest of your day! 🎉 *(You can ask 'What is my timetable tomorrow?' to preview tomorrow's schedule)*"
        )

    sources = ["timetable.csv (Real-Time Analyzer)"]
    return header + "\n".join(body_parts), map_path, sources


def process_timetable_context(docs: list, query: str, user_profile: dict = None) -> str:
    """
    Processes timetable queries using in-memory DataFrames and automatically injects
    the logged-in student's department, semester, and division without asking for clarification.
    """
    date_info = resolve_day_and_date(query)
    target_day = date_info["day_name"]
    formatted_date = date_info["formatted_date"]

    cleaned_query = query.replace('"', '').replace("'", "").strip()
    msg = cleaned_query.lower()

    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or "Computer Engineering"
    prof_sem = str(user_profile.get("semester") or "3") if user_profile.get("semester") else "3"
    prof_div = str(user_profile.get("division") or "A").strip().upper()
    prof_name = user_profile.get("full_name") or "Student"

    prof_prog = (user_profile.get("program") or "").strip()
    is_diploma = "diploma" in msg or "diploma" in prof_prog.lower() or "diploma" in prof_dept.lower()
    is_be = any(k in msg for k in ["be", "b.e", "btech", "b.tech", "degree"]) or prof_prog.upper() == "BE"
    is_me = any(k in msg for k in ["me", "m.e", "mtech", "m.tech", "master"]) or prof_prog.upper() == "ME"
    is_bca = "bca" in msg or prof_prog.upper() == "BCA"
    is_mca = "mca" in msg or prof_prog.upper() == "MCA"

    # 2. Division Extraction (Explicit Query Override > Profile > Default 'A')
    div_match = re.search(r'\b(?:division|div|sec|section)[\s\-:]*([a-c])\b|\b([a-c])\s*(?:division|div|sec|section)\b', msg, re.IGNORECASE)
    if div_match:
        target_div = (div_match.group(1) or div_match.group(2)).upper()
    else:
        target_div = prof_div if prof_div else "A"

    # 3. Semester Extraction (Explicit Query Override > Profile > Default '3')
    sem_match = re.search(r'\b(?:sem|semester)[\s\-:]*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s*(?:sem|semester)\b', msg, re.IGNORECASE)
    if sem_match:
        target_sem = sem_match.group(1) or sem_match.group(2)
    else:
        target_sem = prof_sem if prof_sem else "3"

    # 4. Year Extraction
    year_match = re.search(r'\b(fy|sy|ty|ly|final year|first year|second year|third year)\b', msg, re.IGNORECASE)
    target_year = year_match.group(1).upper() if year_match else None

    # 5. Subject Pattern Extraction
    subj_match = re.search(r'(?:teaches|faculty for|professor for|teacher for|schedule for)\s+([a-zA-Z0-9\s]+?)(?:\s+for|\s+in|\s*$)', msg, re.IGNORECASE)
    target_subject = subj_match.group(1).strip() if subj_match else None

    dept_map = {
        "computer engineering": r"computer engineering|\bce\b|\bco\b|\bcse\b",
        "civil engineering": r"\bcivil\b|\bcivil engineering\b",
        "mechanical engineering": r"mechanical|mech",
        "electrical engineering": r"electrical|\bee\b",
        "information technology": r"information technology|\bit\b",
        "electronics & communication": r"electronics|communication|\bec\b",
        "automobile engineering": r"automobile|auto",
        "artificial intelligence & machine learning": r"artificial intelligence|machine learning|\bai\b|\baiml\b",
        "data science": r"data science|\bds\b",
        "computer applications": r"computer applications|\bbca\b|\bmca\b"
    }

    # 6. Department Extraction (Query Override > Profile)
    target_dept_regex = None
    if "computer engineering" in msg or re.search(r'\b(ce|co|cse)\b', msg):
        target_dept_regex = r"computer engineering|computer|\bce\b|\bco\b|\bcse\b"
    elif "civil" in msg:
        target_dept_regex = r"\bcivil\b|\bcivil engineering\b"
    else:
        for dept_key, regex_pattern in dept_map.items():
            if dept_key in msg:
                target_dept_regex = regex_pattern
                break

    if not target_dept_regex and prof_dept:
        prof_dept_lower = prof_dept.lower()
        for dept_key, regex_pattern in dept_map.items():
            if dept_key in prof_dept_lower:
                target_dept_regex = regex_pattern
                break
        if not target_dept_regex:
            target_dept_regex = re.escape(prof_dept_lower)

    if not target_dept_regex:
        if is_bca or is_mca:
            target_dept_regex = r"computer applications|\bbca\b|\bmca\b"
        elif re.search(r'\b(it)\b', msg):
            target_dept_regex = r"information technology|\bit\b"
        elif re.search(r'\b(ec)\b', msg):
            target_dept_regex = r"electronics|communication|\bec\b"
        elif re.search(r'\b(ee)\b', msg):
            target_dept_regex = r"electrical|\bee\b"
        elif re.search(r'\b(mech)\b', msg):
            target_dept_regex = r"mechanical|mech"

    pandas_blocks = []

    try:
        df = get_cached_dataframe("timetable.csv")

        if df is not None and not df.empty:
            col_map = {str(c).lower(): c for c in df.columns}

            day_col = col_map.get("day")
            dept_col = col_map.get("department") or col_map.get("dept")
            div_col = col_map.get("division") or col_map.get("div")
            sem_col = col_map.get("semester") or col_map.get("sem")
            year_col = col_map.get("year")
            prog_col = col_map.get("program")
            subj_col = col_map.get("subject")

            # 1. Day filter
            if day_col and not any(k in msg for k in ["who teaches", "faculty for", "professor for", "where is", "location", "how to reach"]):
                matched_df = df[df[day_col].str.lower().str.startswith(target_day[:3].lower(), na=False)].copy()
            else:
                matched_df = df.copy()

            # 2. Department filter
            if dept_col and target_dept_regex and not matched_df.empty:
                temp_df = matched_df[matched_df[dept_col].str.lower().str.contains(target_dept_regex, regex=True, na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # 3. Program filter
            if prog_col and not matched_df.empty:
                if is_be:
                    temp_df = matched_df[matched_df[prog_col].str.upper() == "BE"]
                    if not temp_df.empty: matched_df = temp_df
                elif is_diploma:
                    temp_df = matched_df[matched_df[prog_col].str.lower().str.contains("diploma", na=False)]
                    if not temp_df.empty: matched_df = temp_df
                elif is_me:
                    temp_df = matched_df[matched_df[prog_col].str.upper() == "ME"]
                    if not temp_df.empty: matched_df = temp_df
                elif is_bca:
                    temp_df = matched_df[matched_df[prog_col].str.upper() == "BCA"]
                    if not temp_df.empty: matched_df = temp_df
                elif is_mca:
                    temp_df = matched_df[matched_df[prog_col].str.upper() == "MCA"]
                    if not temp_df.empty: matched_df = temp_df

            # 4. Year filter
            if year_col and target_year and not matched_df.empty:
                temp_df = matched_df[matched_df[year_col].str.upper().str.contains(target_year, na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # 5. Subject filter
            if subj_col and target_subject and not matched_df.empty:
                temp_df = matched_df[matched_df[subj_col].str.lower().str.contains(re.escape(target_subject.lower()), na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # 6. Semester filter
            if sem_col and target_sem and not matched_df.empty:
                temp_df = matched_df[matched_df[sem_col].astype(str).str.contains(str(target_sem), na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # 7. Division filter
            if div_col and target_div and not matched_df.empty:
                temp_df = matched_df[matched_df[div_col].astype(str).str.upper() == target_div.upper()]
                if not temp_df.empty:
                    matched_df = temp_df

            if len(matched_df) > 15:
                matched_df = matched_df.head(15)

            if not matched_df.empty:
                for idx, row in matched_df.iterrows():
                    row_str = (
                        f"Time: {row.get('start_time', row.get('Start_Time', row.get('Start Time', 'N/A')))} - {row.get('end_time', row.get('End_Time', row.get('End Time', 'N/A')))} | "
                        f"Subject: {row.get('subject', row.get('Subject', 'N/A'))} | "
                        f"Faculty: {row.get('faculty', row.get('Faculty', 'N/A'))} | "
                        f"Room: {row.get('room', row.get('Room', 'N/A'))} | "
                        f"Program: {row.get('program', row.get('Program', 'N/A'))} | "
                        f"Department: {row.get('department', row.get('Department', 'N/A'))} | "
                        f"Sem: {row.get('semester', row.get('Semester', row.get('sem', 'N/A')))} | "
                        f"Div: {row.get('division', row.get('Division', row.get('div', 'N/A')))}"
                    )
                    pandas_blocks.append(f"timetable.csv (Row {idx + 2}): {row_str}")

    except Exception as e:
        print(f"[Error] Timetable lookup error: {e}")

    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if pandas_blocks:
        context_str = f"HEADER_DATE: {formatted_date}\nTARGET_DAY: {target_day}\n{map_note}"
        context_str += f"PERSONALIZED_STUDENT_SCHEDULE: For {prof_name} ({prof_dept}, Sem {target_sem}, Div {target_div})\n"
        context_str += f"NOTE_TO_AI: These schedule entries ARE ALREADY correctly filtered and retrieved for {target_day} ({formatted_date}). Output them clearly in a clean Markdown table. Do not ask for Division or Semester.\n\n"
        context_str += "\n\n---\n\n".join(pandas_blocks)
        return context_str

    return f"HEADER_DATE: {formatted_date}\nTARGET_DAY: {target_day}\n{map_note}\nSTATUS: NO_CLASSES"


def process_notice_context(docs: list, query: str, user_profile: dict = None) -> str:
    """Parses notices with student profile filtering for semester and department."""
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    keywords = re.findall(r'\b(exam|form|fee|submission|mid-term|holiday|result|re-check|hall ticket|notice)\b', cleaned_query)
    notice_blocks = []

    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or ""
    prof_sem = str(user_profile.get("semester") or "") if user_profile.get("semester") else None

    try:
        df = get_cached_dataframe("notices.csv")
        if df is not None and not df.empty:
            matched_df = df.copy()

            sem_match = re.search(r'\b(?:sem|semester)\s*(\d+)\b', cleaned_query)
            target_sem = sem_match.group(1) if sem_match else prof_sem

            if target_sem:
                sem_col = next((c for c in df.columns if c.lower() in ['semester', 'sem']), None)
                if sem_col:
                    temp_df = matched_df[matched_df[sem_col].str.contains(str(target_sem), na=False) | matched_df[sem_col].str.lower().str.contains("all", na=False)]
                    if not temp_df.empty:
                        matched_df = temp_df

            if prof_dept and not any(d in cleaned_query for d in ["computer", "mechanical", "civil", "electrical", "it"]):
                dept_col = next((c for c in df.columns if c.lower() in ['department', 'dept', 'department_name']), None)
                if dept_col:
                    dept_keyword = prof_dept.split()[0].lower()
                    temp_df = matched_df[matched_df[dept_col].str.lower().str.contains(dept_keyword, na=False) | matched_df[dept_col].str.lower().str.contains("all", na=False)]
                    if not temp_df.empty:
                        matched_df = temp_df

            if keywords:
                pattern = "|".join(keywords)
                content_cols = [c for c in df.columns if c.lower() in ['title', 'notice', 'description', 'subject', 'category']]
                if content_cols:
                    mask = matched_df[content_cols].apply(lambda row: row.str.contains(pattern, case=False, na=False)).any(axis=1)
                    if mask.any():
                        matched_df = matched_df[mask]

            if len(matched_df) > 5:
                matched_df = matched_df.head(5)

            for idx, row in matched_df.iterrows():
                notice_str = (
                    f"Notice Title: {row.get('title', row.get('Title', 'N/A'))} | "
                    f"Date: {row.get('date', row.get('Date', 'N/A'))} | "
                    f"Details: {row.get('description', row.get('Details', 'N/A'))} | "
                    f"Target Dept/Sem: {row.get('department', 'All')} Sem {row.get('semester', 'All')}"
                )
                notice_blocks.append(f"notices.csv (Row {idx + 2}): {notice_str}")

    except Exception as e:
        print(f"[Error] Notice lookup error: {e}")

    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if notice_blocks:
        return f"RELEVANT NOTICES:\n{map_note}" + "\n".join(notice_blocks)

    if docs:
        return f"{map_note}\n" + "\n".join([d.page_content for d, _ in docs])

    return f"{map_note}STATUS: NO_NOTICES_FOUND"


def process_faculty_context(docs: list, query: str, user_profile: dict = None) -> str:
    """Parses department and faculty details, automatically defaulting to student's department for HOD queries."""
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    faculty_blocks = []

    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or "Computer Engineering"

    try:
        df = get_cached_dataframe("departments.csv")
        if df is not None and not df.empty:
            matched_df = df.copy()

            name_match = re.search(r'(?:prof|dr|hod)\.?\s*([a-zA-Z]+)', cleaned_query)
            if name_match:
                name = name_match.group(1).lower()
                cols = [c for c in df.columns if c.lower() in ['hod', 'hod_name', 'faculty_name', 'name', 'professor']]
                if cols:
                    mask = matched_df[cols].apply(lambda row: row.str.lower().str.contains(name, na=False)).any(axis=1)
                    if mask.any():
                        matched_df = matched_df[mask]

            is_my_hod_query = any(k in cleaned_query for k in ["my hod", "who is my hod", "our hod", "department hod", "who is the hod"])
            has_explicit_dept = any(d in cleaned_query for d in ["computer", "mechanical", "civil", "electrical", "it", "aero", "bca", "mca", "diploma"])

            if (is_my_hod_query or not has_explicit_dept) and prof_dept:
                dept_col = next((c for c in df.columns if c.lower() in ['department_name', 'department', 'dept']), None)
                if dept_col:
                    dept_keyword = prof_dept.split()[0].lower()
                    temp_df = matched_df[matched_df[dept_col].str.lower().str.contains(dept_keyword, na=False)]
                    if not temp_df.empty:
                        matched_df = temp_df

                if "diploma" in prof_dept.lower() or "diploma" in cleaned_query:
                    prog_col = next((c for c in df.columns if 'program' in c.lower()), None)
                    if prog_col:
                        p_df = matched_df[matched_df[prog_col].str.lower() == 'diploma']
                        if not p_df.empty:
                            matched_df = p_df
                elif "be" in prof_dept.lower() or "be" in cleaned_query:
                    prog_col = next((c for c in df.columns if 'program' in c.lower()), None)
                    if prog_col:
                        p_df = matched_df[matched_df[prog_col].str.upper() == 'BE']
                        if not p_df.empty:
                            matched_df = p_df

            for idx, row in matched_df.iterrows():
                dept_val = row.get('department_name') or row.get('department') or row.get('Department') or 'N/A'
                hod_val = row.get('hod_name') or row.get('hod') or row.get('HOD') or row.get('faculty_name') or row.get('full_name') or 'N/A'
                loc_val = row.get('building') or row.get('cabin') or row.get('Cabin') or 'N/A'
                email_val = row.get('department_email') or row.get('email') or row.get('Email') or 'N/A'
                phone_val = row.get('contact_number') or row.get('phone') or ''
                prog_val = row.get('program') or ''

                fac_str = f"Department: {dept_val} ({prog_val}) | HOD / Faculty: {hod_val} | Building/Cabin: {loc_val} | Email: {email_val}"
                if phone_val:
                    fac_str += f" | Phone: {phone_val}"

                faculty_blocks.append(f"departments.csv (Row {idx + 2}): {fac_str}")

    except Exception as e:
        print(f"[Error] Faculty lookup error: {e}")

    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if faculty_blocks:
        return f"FACULTY & DEPARTMENT DETAILS:\n{map_note}" + "\n".join(faculty_blocks)

    if docs:
        return f"{map_note}\n" + "\n".join([d.page_content for d, _ in docs])

    return f"{map_note}STATUS: NO_FACULTY_DETAILS_FOUND"


def process_placement_context(query: str, user_profile: dict = None, docs: List[Any] = None) -> str:
    """
    Parses placements.csv using fast in-memory DataFrame lookup and computes exact
    macro statistics (highest package, average package, total drives) along with
    relevant company drive details matching the student's department or explicit query filters.
    """
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or ""

    try:
        df = get_cached_dataframe("placements.csv")
        if df is None or df.empty:
            return "STATUS: NO_PLACEMENT_DATA"

        matched_df = df.copy()

        # 1. Company Filter
        companies = [
            'siemens', 'microsoft', 'cognizant', 'ibm', 'google', 'oracle', 
            'wipro', 'capgemini', 'nvidia', 'larsen & toubro', 'l&t', 'bosch', 
            'adani', 'reliance', 'tcs', 'tata consultancy', 'accenture', 
            'amazon', 'ltimindtree', 'hcltech', 'infosys'
        ]
        matched_company = next((c for c in companies if c in cleaned_query), None)
        if matched_company:
            comp_search = "larsen & toubro" if matched_company == "l&t" else ("tata consultancy" if matched_company == "tcs" else matched_company)
            temp_df = matched_df[matched_df['company_name'].str.lower().str.contains(re.escape(comp_search), na=False)]
            if not temp_df.empty:
                matched_df = temp_df

        # 2. Department Filter
        dept_keywords = {
            "computer": "computer",
            "information technology": "information technology",
            "it": "information technology",
            "artificial intelligence": "artificial intelligence",
            "ai": "artificial intelligence",
            "data science": "data science",
            "civil": "civil",
            "mechanical": "mechanical",
            "electrical": "electrical",
            "electronics": "electronics",
            "automobile": "automobile",
            "mca": "computer applications",
            "bca": "computer applications"
        }

        query_dept = next((v for k, v in dept_keywords.items() if re.search(r'\b' + re.escape(k) + r'\b', cleaned_query)), None)
        if query_dept:
            temp_df = matched_df[matched_df['department'].str.lower().str.contains(query_dept, na=False)]
            if not temp_df.empty:
                matched_df = temp_df
        elif prof_dept and not matched_company and any(k in cleaned_query for k in ["my department", "for my branch", "eligible for me", "my placements"]):
            dept_key = prof_dept.split()[0].lower()
            temp_df = matched_df[matched_df['department'].str.lower().str.contains(dept_key, na=False)]
            if not temp_df.empty:
                matched_df = temp_df

        # 3. Status Filter
        if any(k in cleaned_query for k in ['upcoming', 'next', 'open', 'registration', 'active']):
            temp_df = matched_df[matched_df['status'].str.lower().str.contains('upcoming|open', na=False)]
            if not temp_df.empty:
                matched_df = temp_df

        # 4. Compute Placement Macro Stats
        valid_packages = []
        for val in df['package_lpa']:
            try:
                p_num = float(str(val).replace('LPA', '').strip())
                valid_packages.append(p_num)
            except (ValueError, TypeError):
                pass

        overall_highest = max(valid_packages) if valid_packages else 17.9
        overall_avg = round(sum(valid_packages) / len(valid_packages), 2) if valid_packages else 10.67

        subset_packages = []
        for val in matched_df['package_lpa']:
            try:
                p_num = float(str(val).replace('LPA', '').strip())
                subset_packages.append(p_num)
            except (ValueError, TypeError):
                pass

        matched_highest = max(subset_packages) if subset_packages else overall_highest
        matched_avg = round(sum(subset_packages) / len(subset_packages), 2) if subset_packages else overall_avg

        context_lines = []
        context_lines.append("--- SUMMARY PLACEMENT STATISTICS ---")
        context_lines.append(f"Highest Package: {matched_highest} LPA (Overall Campus Peak: {overall_highest} LPA)")
        context_lines.append(f"Average Package: {matched_avg} LPA")
        context_lines.append(f"Total Matching Drives: {len(matched_df)}")
        context_lines.append("Top Recruiting Companies: Siemens, Microsoft, NVIDIA, Google, Oracle, IBM, TCS, Wipro, L&T, Amazon, Reliance, Adani, Capgemini, Bosch, HCLTech\n")

        context_lines.append("--- RELEVANT COMPANY PLACEMENT DRIVES ---")
        
        try:
            matched_df['pkg_numeric'] = pd.to_numeric(matched_df['package_lpa'], errors='coerce')
            matched_df = matched_df.sort_values(by='pkg_numeric', ascending=False)
        except Exception:
            pass

        for idx, row in matched_df.head(8).iterrows():
            drive_info = (
                f"* Company: {row.get('company_name', 'N/A')} | "
                f"Package: {row.get('package_lpa', 'N/A')} LPA | "
                f"Role: {row.get('job_role', 'N/A')} | "
                f"Eligible: {row.get('department', 'All')} ({row.get('program', 'Degree/Diploma')}) | "
                f"Criteria: {row.get('eligibility', '60% throughout')} | "
                f"Drive Date: {row.get('drive_date', 'TBA')} | "
                f"Deadline: {row.get('registration_deadline', 'TBA')} | "
                f"Status: {row.get('status', 'Open')} | "
                f"[Source: placements.csv (Row {idx + 2})]"
            )
            context_lines.append(drive_info)

        return "\n".join(context_lines)

    except Exception as e:
        print(f"[Error] Placement context processing: {e}")
        return "STATUS: NO_PLACEMENT_DATA"


def process_events_context(question: str) -> str:
    """Directly processes events using in-memory DataFrame."""
    try:
        df = get_cached_dataframe("events.csv")
        if df is None or df.empty:
            return "STATUS: NO_EVENTS_FOUND"

        clean_q = question.lower()
        matched_df = df.copy()

        if "ai" in clean_q or "artificial intelligence" in clean_q:
            name_col = next((c for c in df.columns if 'name' in c.lower() or 'event' in c.lower()), None)
            if name_col:
                matched_df = matched_df[matched_df[name_col].str.lower().str.contains('ai|artificial intelligence|machine learning', na=False)]

        if matched_df.empty:
            return "STATUS: NO_EVENTS_FOUND"

        context_lines = ["HEADER_EVENT_LIST:"]
        for idx, row in matched_df.head(5).iterrows():
            context_lines.append(
                f"Event: {row.get('Event/Workshop Name', row.get('event_name', row.get('Name', 'Event')))} | "
                f"Date: {row.get('Date & Time', row.get('Date', row.get('date', 'TBA')))} | "
                f"Venue: {row.get('Venue', row.get('venue', 'Main Campus'))} | "
                f"Description: {row.get('Description', row.get('description', 'N/A'))} | "
                f"[Source: events.csv (Row {idx + 2})]"
            )

        return "\n".join(context_lines)

    except Exception as e:
        print(f"[Error] Reading events CSV: {e}")
        return "STATUS: NO_EVENTS_FOUND"


def generate_followup_suggestions(query: str, intent_category: str = "general", answer: str = "", user_profile: dict = None) -> List[str]:
    """
    Generates 2-3 dynamic contextual follow-up chips based on the query and intent category.
    """
    q_lower = query.lower()
    
    if intent_category == "timetable" or any(k in q_lower for k in ["timetable", "schedule", "classes", "lecture"]):
        return [
            "Where is my next class right now? 📍",
            "Show tomorrow's timetable 📅",
            "Who is the faculty for this subject? 👨‍🏫"
        ]
    elif intent_category == "faculty" or any(k in q_lower for k in ["hod", "faculty", "cabin", "professor"]):
        return [
            "Where is their cabin located? 📍",
            "Show department timetable 📅",
            "Department contact details 📞"
        ]
    elif intent_category == "placement" or any(k in q_lower for k in ["placement", "package", "drive", "salary", "lpa"]):
        return [
            "What is the highest package? 💰",
            "Show upcoming placement drives 💼",
            "NVIDIA placement criteria 🎯"
        ]
    elif intent_category == "notices" or any(k in q_lower for k in ["notice", "exam", "fee", "holiday", "submission"]):
        return [
            "When is the next mid-term exam? 📝",
            "Check exam form notice 📢",
            "Show holiday list 🌴"
        ]
    elif intent_category == "events" or any(k in q_lower for k in ["event", "workshop", "hackathon"]):
        return [
            "Where is this event venue? 📍",
            "Show upcoming workshops 🎪",
            "How to register? 📝"
        ]
    elif intent_category == "transport" or any(k in q_lower for k in ["bus", "route", "pickup", "commute"]):
        return [
            "What is bus route 2 timing? 🚌",
            "Show all pickup points 📍",
            "Transport semester fee details 💳"
        ]
    elif any(k in q_lower for k in ["where", "room", "floor", "building", "reach", "direction", "map", "locate", "next class"]):
        return [
            "Who is the faculty in this room? 👨‍🏫",
            "Show department floor map 🗺️",
            "Where is the department HOD cabin? 📍"
        ]
    else:
        return [
            "Where is my next class now? 📍",
            "Show today's timetable 📅",
            "Top placement companies & packages 💼"
        ]


def resolve_student_profile_query(query: str, user_profile: dict = None) -> Optional[str]:
    """
    Directly answers student-specific profile queries from the authenticated session
    to prevent generic FAQ or knowledge-base overrides.
    """
    if not user_profile:
        return None

    q = query.lower().strip()
    
    # Exclude questions about college in general (e.g. "what courses does svit offer" or "list all departments")
    if any(k in q for k in ["svit offer", "all department", "all course", "list of course", "available course", "branches in svit", "courses in svit"]):
        return None

    has_self_ref = any(k in q for k in ["my", "i ", "i am", "am i", "me", "profile", "who am i", "mine"])
    
    is_asking_dept_and_course = ("department" in q or "dept" in q or "branch" in q) and ("course" in q or "program" in q or "stream" in q)
    is_asking_course = any(k in q for k in ["my course", "my program", "which course", "what course", "which program", "what program", "my degree", "my diploma"]) or (has_self_ref and any(k in q for k in ["course name", "program name"]))
    is_asking_dept = any(k in q for k in ["my department", "my dept", "my branch", "which department", "what department", "what is my department", "which dept"]) or (has_self_ref and "department" in q)
    is_asking_sem = any(k in q for k in ["my semester", "my sem", "which semester", "what semester", "what is my semester", "which sem"])
    is_asking_div = any(k in q for k in ["my division", "my div", "my section", "which division", "what division", "what is my division", "which div"])
    is_asking_batch = any(k in q for k in ["my batch", "which batch", "what is my batch", "what batch"])
    is_asking_enrollment = any(k in q for k in ["my enrollment", "my enrollment number", "my roll number", "my id", "my student id"])
    is_asking_full_profile = any(k in q for k in ["who am i", "my profile", "my details", "about me", "my info", "my information", "show my profile", "what is my name", "what are my details"])

    if not (is_asking_dept_and_course or is_asking_course or is_asking_dept or is_asking_sem or is_asking_div or is_asking_batch or is_asking_enrollment or is_asking_full_profile):
        return None

    prog = user_profile.get("program") or "BE"
    dept = user_profile.get("department") or "Computer Engineering"
    sem = user_profile.get("semester") or "3"
    div = user_profile.get("division") or "A"
    batch = user_profile.get("batch") or "A1"
    name = user_profile.get("full_name") or "Student"
    enroll = user_profile.get("enrollment_no") or ""

    if is_asking_dept_and_course:
        return (
            f"According to your student profile, here are your registered details:\n"
            f"* 🎓 **Program / Course:** {prog}\n"
            f"* 🏢 **Department:** {dept}\n"
            f"* 📅 **Semester:** Semester {sem}\n"
            f"* 🏷️ **Division & Batch:** Division {div} (Batch {batch})"
        )

    if is_asking_course:
        return f"According to your student profile, your Program / Course is **{prog}** (in the **{dept}** department)."

    if is_asking_dept:
        return f"According to your student profile, your Department is **{dept}** (Program: **{prog}**, Semester {sem})."

    if is_asking_sem:
        return f"According to your student profile, you are currently in **Semester {sem}** ({prog} {dept}, Division {div})."

    if is_asking_div:
        return f"According to your student profile, you are in **Division {div}** (Batch: {batch}, {prog} {dept} Sem {sem})."

    if is_asking_batch:
        return f"According to your student profile, your Batch is **{batch}** (Division {div}, {prog} {dept} Sem {sem})."

    if is_asking_enrollment:
        return f"Your registered Enrollment Number is **{enroll}** ({name}, {prog} {dept})."

    if is_asking_full_profile:
        return (
            f"Here are your registered student profile details:\n"
            f"* 👤 **Full Name:** {name}\n"
            f"* 🆔 **Enrollment Number:** {enroll or 'N/A'}\n"
            f"* 🎓 **Program / Course:** {prog}\n"
            f"* 🏢 **Department:** {dept}\n"
            f"* 📅 **Semester:** Semester {sem}\n"
            f"* 🏷️ **Division & Batch:** Division {div} (Batch {batch})"
        )

    return None


# Run initial preloading on import
preload_all_dataframes()