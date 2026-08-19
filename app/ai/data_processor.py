import os
import re
import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple

# =========================================================================
# STATIC MAP & LOCATION LOOKUP DIRECTORY
# Maps user query keywords to exact image filenames in app/static/navigation_maps
# =========================================================================
MAP_LOOKUP: Dict[str, str] = {
    # ---------------------------------------------------------------------
    # 1. DIPLOMA BUILDING (TOP PRIORITY - ALL 5 COURSES)
    # ---------------------------------------------------------------------
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

    # ---------------------------------------------------------------------
    # 2. DEGREE / POSTGRADUATE DEPARTMENTS
    # ---------------------------------------------------------------------
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

    # ---------------------------------------------------------------------
    # 3. ADMIN BLOCK & ALL LOCATED FACILITIES
    # ---------------------------------------------------------------------
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

    # ---------------------------------------------------------------------
    # 4. OUTDOOR SPORTS & PAVILION
    # ---------------------------------------------------------------------
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

    # ---------------------------------------------------------------------
    # 5. AMENITIES & OTHER CAMPUS LOCATIONS
    # ---------------------------------------------------------------------
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
# HELPER FUNCTIONS FOR CONTEXT PROCESSING AND DATES
# =========================================================================

def resolve_day_and_date(question: str) -> Tuple[str, str]:
    """
    Resolves target day of week and formatted date string from question text.
    Defaults to today's date if no specific day keyword is found.
    """
    today = datetime.datetime.now()
    clean_q = question.lower()

    if "tomorrow" in clean_q:
        target = today + datetime.timedelta(days=1)
    elif "yesterday" in clean_q:
        target = today - datetime.timedelta(days=1)
    else:
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        matched_day = None
        for day in days:
            if day in clean_q:
                matched_day = day
                break

        if matched_day:
            current_day_idx = today.weekday()
            target_day_idx = days.index(matched_day)
            days_ahead = target_day_idx - current_day_idx
            if days_ahead < 0:
                days_ahead += 7
            target = today + datetime.timedelta(days=days_ahead)
        else:
            target = today

    day_name = target.strftime("%A")
    date_str = target.strftime("%d %B %Y")
    return day_name, date_str


def process_timetable_context(retrieved_docs: List[Any], question: str) -> str:
    """
    Directly filters timetable.csv by day, program type (Diploma vs BE), 
    semester, and division using Pandas.
    """
    try:
        # Load timetable.csv
        csv_path = os.path.join(os.getcwd(), "data", "timetable.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.getcwd(), "timetable.csv")
            
        df = pd.read_csv(csv_path)
        clean_q = question.lower()

        # Resolve target day
        day_name, date_str = resolve_day_and_date(question)

        # 1. Filter by Day
        filtered_df = df[df['Day'].str.lower() == day_name.lower()]

        # 2. Filter by Program Type (Diploma vs Degree)
        if "diploma" in clean_q:
            filtered_df = filtered_df[filtered_df['Program'].str.lower().str.contains("diploma", na=False)]
        elif "be" in clean_q or "degree" in clean_q:
            filtered_df = filtered_df[~filtered_df['Program'].str.lower().str.contains("diploma", na=False)]

        # 3. Filter by Semester (e.g., "sem 3", "3rd sem", "semester 3")
        sem_match = re.search(r'\b(?:sem|semester)\s*([1-8])\b', clean_q)
        if sem_match:
            sem_num = int(sem_match.group(1))
            filtered_df = filtered_df[filtered_df['Semester'] == sem_num]

        # 4. Filter by Division (e.g., "div a", "division a", "a div")
        div_match = re.search(r'\b(?:div|division)\s*([a-c])\b', clean_q)
        if div_match:
            div_letter = div_match.group(1).upper()
            filtered_df = filtered_df[filtered_df['Division'].str.upper() == div_letter]

        if filtered_df.empty:
            return f"HEADER_DATE: {day_name}, {date_str}\nSTATUS: NO_CLASSES"

        # Format retrieved rows into clean context string
        context_lines = [f"HEADER_DATE: {day_name}, {date_str}"]
        for idx, row in filtered_df.iterrows():
            context_lines.append(
                f"Time: {row['Start Time']} - {row['End Time']} | "
                f"Subject: {row['Subject']} | "
                f"Faculty: {row['Faculty']} | "
                f"Room: {row['Room']} | "
                f"[Source: timetable.csv (Row {idx + 2})]"
            )

        return "\n".join(context_lines)

    except Exception as e:
        print(f"Error filtering timetable CSV: {e}")
        return "STATUS: NO_CLASSES"


def process_notice_context(retrieved_docs: List[Any], question: str) -> str:
    """Formats retrieved notices context into a clean string."""
    if not retrieved_docs:
        return "No specific notices found matching your query."

    formatted_chunks = []
    for doc in retrieved_docs:
        page_content = getattr(doc, "page_content", str(doc))
        meta = getattr(doc, "metadata", {})
        row = meta.get("row", "N/A")
        formatted_chunks.append(f"{page_content}\n[Source: notices.csv (Row {row})]")

    return "\n\n---\n\n".join(formatted_chunks)


def process_faculty_context(retrieved_docs: List[Any], question: str) -> str:
    """Formats retrieved faculty context into a clean string."""
    if not retrieved_docs:
        return "Faculty or department information not found."

    formatted_chunks = []
    for doc in retrieved_docs:
        page_content = getattr(doc, "page_content", str(doc))
        meta = getattr(doc, "metadata", {})
        row = meta.get("row", "N/A")
        formatted_chunks.append(f"{page_content}\n[Source: departments.csv (Row {row})]")

    return "\n\n---\n\n".join(formatted_chunks)


def process_placement_context(results: List[Tuple[Any, float]], question: str) -> str:
    """Formats placement and campus drive context into a clean string."""
    if not results:
        return "Placement details not found."

    formatted_chunks = []
    for doc, _ in results:
        page_content = getattr(doc, "page_content", str(doc))
        meta = getattr(doc, "metadata", {})
        row = meta.get("row", "N/A")
        formatted_chunks.append(f"{page_content}\n[Source: placements.csv (Row {row})]")

    return "\n\n---\n\n".join(formatted_chunks)


def get_map_filename(query: str) -> str:
    """
    Scans a query against MAP_LOOKUP using word boundary checks
    and returns the matching filename or a default campus map.
    """
    clean_q = query.lower()
    sorted_keys = sorted(MAP_LOOKUP.keys(), key=len, reverse=True)

    for key in sorted_keys:
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, clean_q):
            return MAP_LOOKUP[key]

    return "SVIT with all dep.jpeg"

def resolve_day_and_date(query: str) -> dict:
    """
    Resolves relative time keywords ('today', 'tomorrow') or explicit day names
    into both the target day name ('Wednesday') and a formatted date string.
    """
    # 1. Handle possessive suffixes FIRST (e.g. "tomorrow's" -> "tomorrow")
    msg = re.sub(r"['’]s\b", "", query, flags=re.IGNORECASE)
    msg = msg.replace('"', '').replace("'", "").strip().lower()

    now = datetime.datetime.now()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    # 2. Check for relative day keywords using sub-string/word matches
    if "tomorrow" in msg:
        target_date = now + datetime.timedelta(days=1)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y")
        }

    if "today" in msg:
        return {
            "day_name": now.strftime("%A"),
            "formatted_date": now.strftime("%A, %d %B %Y")
        }

    # 3. Check for explicit day names or 3-letter abbreviations
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

    # 4. Default to "today" if no temporal keywords are found
    return {
        "day_name": now.strftime("%A"),
        "formatted_date": now.strftime("%A, %d %B %Y")
    }


def resolve_day_name(query: str) -> str:
    return resolve_day_and_date(query)["day_name"]


def process_timetable_context(docs: list, query: str) -> str:
    """
    Processes timetable context using robust multi-tiered Pandas CSV lookups
    supporting all SVIT Programs (Diploma, BE, ME, BCA, MCA) and all Departments.
    Detects ambiguous or incomplete metadata queries (Semester/Division/Subject) to prompt the user for clarification.
    Injects visual navigation URLs if location keywords are detected.
    """
    date_info = resolve_day_and_date(query)
    target_day = date_info["day_name"]
    formatted_date = date_info["formatted_date"]

    cleaned_query = query.replace('"', '').replace("'", "").strip()
    msg = cleaned_query.lower()

    # --- PROGRAM EXTRACTION ---
    is_diploma = "diploma" in msg
    is_be = any(k in msg for k in ["be", "b.e", "btech", "b.tech", "degree"])
    is_me = any(k in msg for k in ["me", "m.e", "mtech", "m.tech", "master"])
    is_bca = "bca" in msg
    is_mca = "mca" in msg

    # --- METADATA EXTRACTION ---
    div_match = re.search(r'\b(?:division|div|sec|section)?\s*([a-c])\b', msg, re.IGNORECASE)
    target_div = div_match.group(1).upper() if div_match else None

    sem_match = re.search(r'\b(?:sem|semester)\s*(\d+)\b', msg, re.IGNORECASE)
    target_sem = sem_match.group(1) if sem_match else None

    year_match = re.search(r'\b(fy|sy|ty|ly|final year|first year|second year|third year)\b', msg, re.IGNORECASE)
    target_year = year_match.group(1).upper() if year_match else None

    # --- SUBJECT PATTERN EXTRACTION (e.g. "Who teaches Python Programming") ---
    subj_match = re.search(r'(?:teaches|faculty for|professor for|teacher for|schedule for)\s+([a-zA-Z0-9\s]+?)(?:\s+for|\s+in|\s*$)', msg, re.IGNORECASE)
    target_subject = subj_match.group(1).strip() if subj_match else None

    # --- DEPARTMENT EXTRACTION MAP ---
    dept_map = {
        "computer engineering": r"computer engineering|computer|\bce\b|\bco\b|\bcse\b",
        "civil": r"\bcivil\b|\bcivil engineering\b",
        "artificial intelligence": r"artificial intelligence|\bai\b|\baiml\b",
        "data science": r"data science|\bds\b",
        "automobile": r"automobile|auto",
        "computer applications": r"computer applications|\bbca\b|\bmca\b",
        "electrical": r"electrical|\bee\b",
        "electronics": r"electronics|communication|\bec\b",
        "information technology": r"information technology|\bit\b",
        "mechanical": r"mechanical|mech"
    }

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
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        csv_path = os.path.join(project_root, "knowledge_base", "timetable.csv")

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)

            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()

            col_map = {str(c).lower(): c for c in df.columns}

            day_col = col_map.get("day")
            dept_col = col_map.get("department") or col_map.get("dept")
            div_col = col_map.get("division") or col_map.get("div")
            sem_col = col_map.get("semester") or col_map.get("sem")
            year_col = col_map.get("year")
            prog_col = col_map.get("program")
            subj_col = col_map.get("subject")

            # --- STEP 1: DAY FILTER ---
            if day_col and not any(k in msg for k in ["who teaches", "faculty for", "professor for", "where is", "location", "how to reach"]):
                matched_df = df[df[day_col].str.lower().str.startswith(target_day[:3].lower(), na=False)].copy()
            else:
                matched_df = df.copy()

            # --- STEP 2: DEPARTMENT FILTER ---
            if dept_col and target_dept_regex and not matched_df.empty:
                temp_df = matched_df[matched_df[dept_col].str.lower().str.contains(target_dept_regex, regex=True, na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # --- STEP 3: PROGRAM FILTER ---
            if prog_col and is_be and not matched_df.empty:
                temp_df = matched_df[matched_df[prog_col].str.lower().str.contains("be|b.e|btech|degree", regex=True, na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # --- STEP 4: YEAR FILTER ---
            if year_col and target_year and not matched_df.empty:
                temp_df = matched_df[matched_df[year_col].str.upper().str.contains(target_year, na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # --- STEP 5: SUBJECT FILTER ---
            if subj_col and target_subject and not matched_df.empty:
                temp_df = matched_df[matched_df[subj_col].str.lower().str.contains(re.escape(target_subject.lower()), na=False)]
                if not temp_df.empty:
                    matched_df = temp_df

            # --- STEP 6: EVALUATE MATCHING SEMESTERS AND DIVISIONS ---
            actual_sems = []
            if sem_col and not matched_df.empty:
                if target_sem:
                    temp_df = matched_df[matched_df[sem_col].str.contains(str(target_sem), na=False)]
                    if not temp_df.empty:
                        matched_df = temp_df
                else:
                    raw_sems = matched_df[sem_col].dropna().unique().tolist()
                    actual_sems = sorted([s for s in raw_sems if str(s).isdigit()], key=int)

            actual_divs = []
            if div_col and not matched_df.empty:
                if target_div:
                    temp_df = matched_df[matched_df[div_col].str.upper() == target_div]
                    if not temp_df.empty:
                        matched_df = temp_df
                else:
                    raw_divs = matched_df[div_col].dropna().unique().tolist()
                    actual_divs = sorted([d.upper() for d in raw_divs if d.strip() and d.upper() != 'NAN'])

            # --- STEP 7: CHECK AMBIGUOUS METADATA (MISSING SEMESTER) ---
            if not target_sem and len(actual_sems) > 1 and len(matched_df) > 8:
                sem_str = " or ".join([f"Sem {s}" for s in actual_sems])
                return (
                    f"HEADER_DATE: {formatted_date}\n"
                    f"TARGET_DAY: {target_day}\n"
                    f"STATUS: AMBIGUOUS_METADATA\n"
                    f"NOTE_TO_AI: The user's query is missing the Semester (found matches for {sem_str}). "
                    f"Politely ask the student to specify which semester ({sem_str}) they are in."
                )

            # --- STEP 8: CHECK AMBIGUOUS METADATA (MISSING DIVISION) ---
            if not target_div and len(actual_divs) > 1 and len(matched_df) > 8:
                div_str = " or ".join([f"Div {d}" for d in actual_divs])
                return (
                    f"HEADER_DATE: {formatted_date}\n"
                    f"TARGET_DAY: {target_day}\n"
                    f"STATUS: AMBIGUOUS_METADATA\n"
                    f"NOTE_TO_AI: The user's query is missing the Division (found matches for {div_str}). "
                    f"Politely ask the student to specify which division ({div_str}) they belong to."
                )

            if len(matched_df) > 20:
                matched_df = matched_df.head(20)

            if not matched_df.empty:
                for idx, row in matched_df.iterrows():
                    row_str = (
                        f"Time: {row.get('start_time', row.get('Start_Time', 'N/A'))} - {row.get('end_time', row.get('End_Time', 'N/A'))} | "
                        f"Subject: {row.get('subject', row.get('Subject', 'N/A'))} | "
                        f"Faculty: {row.get('faculty', row.get('Faculty', 'N/A'))} | "
                        f"Room: {row.get('room', row.get('Room', 'N/A'))} | "
                        f"Program: {row.get('program', row.get('Program', 'N/A'))} | "
                        f"Department: {row.get('department', row.get('Department', 'N/A'))} | "
                        f"Year: {row.get('year', row.get('Year', 'N/A'))} | "
                        f"Sem: {row.get('semester', row.get('Semester', row.get('sem', 'N/A')))} | "
                        f"Div: {row.get('division', row.get('Division', row.get('div', 'N/A')))}"
                    )
                    pandas_blocks.append(f"timetable.csv (Row {idx + 2}): {row_str}")

    except Exception as e:
        print(f"Pandas direct lookup error: {e}")

    # Check for visual map image reference
    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if pandas_blocks:
        context_str = f"HEADER_DATE: {formatted_date}\nTARGET_DAY: {target_day}\n{map_note}"
        context_str += f"NOTE_TO_AI: These schedule entries ARE ALREADY correctly retrieved for {target_day} ({formatted_date}). Do not recalculate dates.\n\n"
        context_str += "\n\n---\n\n".join(pandas_blocks)
        return context_str

    return f"HEADER_DATE: {formatted_date}\nTARGET_DAY: {target_day}\n{map_note}\nSTATUS: NO_CLASSES"


def process_notice_context(docs: list, query: str) -> str:
    """
    Parses notices.csv for exam forms, deadlines, fee updates, and general announcements.
    """
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    keywords = re.findall(r'\b(exam|form|fee|submission|mid-term|holiday|result|re-check|hall ticket|notice)\b', cleaned_query)
    notice_blocks = []

    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        csv_path = os.path.join(project_root, "knowledge_base", "notices.csv")

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)

            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()

            matched_df = df.copy()

            sem_match = re.search(r'\b(?:sem|semester)\s*(\d+)\b', cleaned_query)
            if sem_match:
                sem_col = next((c for c in df.columns if c.lower() in ['semester', 'sem']), None)
                if sem_col:
                    temp_df = matched_df[matched_df[sem_col].str.contains(sem_match.group(1), na=False)]
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
        print(f"Notice lookup error: {e}")

    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if notice_blocks:
        return f"RELEVANT NOTICES:\n{map_note}" + "\n".join(notice_blocks)

    if docs:
        return f"{map_note}\n" + "\n".join([d.page_content for d, _ in docs])

    return f"{map_note}STATUS: NO_NOTICES_FOUND"


def process_faculty_context(docs: list, query: str) -> str:
    """
    Parses department/faculty datasets for HOD details, cabin numbers, designations, and emails.
    """
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    faculty_blocks = []

    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        csv_path = os.path.join(project_root, "knowledge_base", "departments.csv")

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)

            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()

            matched_df = df.copy()

            name_match = re.search(r'(?:prof|dr|hod)\.?\s*([a-zA-Z]+)', cleaned_query)
            if name_match:
                name = name_match.group(1).lower()
                cols = [c for c in df.columns if c.lower() in ['hod', 'faculty_name', 'name', 'professor']]
                if cols:
                    mask = matched_df[cols].apply(lambda row: row.str.lower().str.contains(name, na=False)).any(axis=1)
                    if mask.any():
                        matched_df = matched_df[mask]

            for idx, row in matched_df.iterrows():
                fac_str = (
                    f"Department: {row.get('department', row.get('Department', 'N/A'))} | "
                    f"HOD / Faculty: {row.get('hod', row.get('HOD', row.get('faculty_name', 'N/A')))} | "
                    f"Cabin: {row.get('cabin', row.get('Cabin', 'N/A'))} | "
                    f"Email: {row.get('email', row.get('Email', 'N/A'))}"
                )
                faculty_blocks.append(f"departments.csv (Row {idx + 2}): {fac_str}")

    except Exception as e:
        print(f"Faculty lookup error: {e}")

    map_url = get_navigation_map_url(query)
    map_note = f"\nNAVIGATION_MAP_URL: {map_url}\n" if map_url else ""

    if faculty_blocks:
        return f"FACULTY & DEPARTMENT DETAILS:\n{map_note}" + "\n".join(faculty_blocks)

    if docs:
        return f"{map_note}\n" + "\n".join([d.page_content for d, _ in docs])

    return f"{map_note}STATUS: NO_FACULTY_DETAILS_FOUND"


def process_placement_context(docs: List[Any], query: str) -> str:
    """
    Parses placement CSV document chunks, extracts targeted companies/departments,
    computes macro stats (Highest LPA, Average LPA), and formats clean context for LLM.
    """
    if not docs:
        return "STATUS: NO_PLACEMENT_DATA"

    msg = query.lower()

    # Standardize docs list whether it comes as (doc, score) tuple or single doc object
    normalized_docs = []
    for item in docs:
        if isinstance(item, (tuple, list)):
            doc = item[0]
            score = item[1] if len(item) > 1 else 0.0
        else:
            doc = item
            score = 0.0
        normalized_docs.append((doc, score))

    raw_text = "\n".join([doc.page_content for doc, _ in normalized_docs])

    # 1. Company and Filter Intent Matching
    companies = ['nvidia', 'oracle', 'tcs', 'infosys', 'wipro', 'capgemini', 'l&t', 'amazon', 'reliance', 'tata']
    mentioned_company = next((c for c in companies if c in msg), None)
    upcoming_only = any(k in msg for k in ['upcoming', 'next', 'open', 'registration', 'active'])

    context_lines = []

    # 2. Extract Macro Stats (Highest LPA & Average LPA)
    lpa_matches = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*LPA', raw_text, re.IGNORECASE)]
    if lpa_matches:
        highest_lpa = max(lpa_matches)
        avg_lpa = round(sum(lpa_matches) / len(lpa_matches), 1)
        context_lines.append("--- SUMMARY PLACEMENT STATS ---")
        context_lines.append(f"Highest Package: {highest_lpa} LPA")
        context_lines.append(f"Average Package: {avg_lpa} LPA")
        context_lines.append(f"Total Drives Evaluated: {len(normalized_docs)}\n")

    context_lines.append("--- RELEVANT PLACEMENT DRIVES DATA ---")

    # 3. Format Drives Content with Row Citations
    matched_count = 0
    for doc, _ in normalized_docs:
        content = doc.page_content.strip()
        meta = getattr(doc, "metadata", {})
        row = meta.get("row", "N/A")

        if mentioned_company and mentioned_company not in content.lower():
            continue
        if upcoming_only and not any(status in content.lower() for status in ['upcoming', 'registration open', 'open', 'scheduled']):
            continue

        context_lines.append(f"{content} | [Source: placements.csv (Row {row})]")
        matched_count += 1

    # Fallback to full raw text if strict filters yielded no matches
    if matched_count == 0:
        return raw_text

    return "\n".join(context_lines)
    
def process_events_context(question: str) -> str:
    """
    Directly processes events.csv and formats upcoming events.
    """
    import pandas as pd
    import os
    
    try:
        csv_path = os.path.join(os.getcwd(), "data", "events.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.getcwd(), "events.csv")
            
        df = pd.read_csv(csv_path)
        clean_q = question.lower()

        # Filter by AI topic if requested
        if "ai" in clean_q or "artificial intelligence" in clean_q:
            df = df[df['Event/Workshop Name'].str.lower().str.contains('ai|artificial intelligence|machine learning', na=False)]

        if df.empty:
            return "STATUS: NO_EVENTS_FOUND"

        context_lines = ["HEADER_EVENT_LIST:"]
        for idx, row in df.head(5).iterrows():
            context_lines.append(
                f"Event: {row['Event/Workshop Name']} | "
                f"Date: {row.get('Date & Time', row.get('Date', 'TBA'))} | "
                f"Venue: {row.get('Venue', 'Main Campus')} | "
                f"Description: {row.get('Description', 'N/A')} | "
                f"[Source: events.csv (Row {idx + 2})]"
            )

        return "\n".join(context_lines)

    except Exception as e:
        print(f"Error reading events CSV: {e}")
        return "STATUS: NO_EVENTS_FOUND"
    
def get_navigation_map_url(query: str) -> str:
    """
    Resolves the navigation map URL path for a given query string.
    """
    map_file = get_map_filename(query)
    if map_file:
        return f"/static/navigation_maps/{map_file}"
    return "/static/navigation_maps/SVIT with all dep.jpeg"

    return "\n\n".join(context_lines)