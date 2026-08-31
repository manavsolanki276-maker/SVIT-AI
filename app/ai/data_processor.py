"""
app/ai/data_processor.py
High-performance In-Memory Pandas Context Processors with Student Profile Personalization
and Real-Time "Next Class Now" / "Where Do I Go Right Now?" schedule analyzer.
"""
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Indian Standard Time (IST, UTC+05:30) Timezone definition
IST = ZoneInfo("Asia/Kolkata")

def get_ist_now() -> datetime:
    """Returns the current timezone-aware datetime in Asia/Kolkata (IST)."""
    return datetime.now(IST)

# =========================================================================
# STATIC MAP & LOCATION LOOKUP DIRECTORY
# =========================================================================
# =========================================================================
# STATIC MAP & LOCATION LOOKUP DIRECTORY
# =========================================================================
MAP_LOOKUP: Dict[str, str] = {
    # 1. Master Campus Entry, Gates, Parking, Garden, Overview
    "main gate": "SVIT with all dep.jpeg",
    "gate": "SVIT with all dep.jpeg",
    "campus entry": "SVIT with all dep.jpeg",
    "entrance": "SVIT with all dep.jpeg",
    "entrance gate": "SVIT with all dep.jpeg",
    "entry gate": "SVIT with all dep.jpeg",
    "main entrance": "SVIT with all dep.jpeg",
    "college gate": "SVIT with all dep.jpeg",
    "front gate": "SVIT with all dep.jpeg",
    "campus gate": "SVIT with all dep.jpeg",
    "parking": "SVIT with all dep.jpeg",
    "parking area": "SVIT with all dep.jpeg",
    "vehicle parking": "SVIT with all dep.jpeg",
    "two wheeler parking": "SVIT with all dep.jpeg",
    "four wheeler parking": "SVIT with all dep.jpeg",
    "central garden": "SVIT with all dep.jpeg",
    "amphitheatre": "SVIT with all dep.jpeg",
    "open amphitheatre": "SVIT with all dep.jpeg",
    "open air amphitheatre": "SVIT with all dep.jpeg",
    "open theatre": "SVIT with all dep.jpeg",
    "campus": "SVIT with all dep.jpeg",
    "all departments": "SVIT with all dep.jpeg",
    "svit": "SVIT with all dep.jpeg",
    "architecture": "SVIT with all dep.jpeg",
    "architecture block": "SVIT with all dep.jpeg",
    "architecture department": "SVIT with all dep.jpeg",
    "hostel": "SVIT with all dep.jpeg",
    "campus main entrance gate": "SVIT with all dep.jpeg",

    # 2. Degree / PG Department Buildings & Labs
    "computer engineering block": "Computer dep.jpeg",
    "computer engineering": "Computer dep.jpeg",
    "computer department": "Computer dep.jpeg",
    "computer": "Computer dep.jpeg",
    "ai & ml department": "Computer dep.jpeg",
    "ai & ml": "Computer dep.jpeg",
    "ai/ml": "Computer dep.jpeg",
    "artificial intelligence": "Computer dep.jpeg",
    "data science department": "Computer dep.jpeg",
    "data science": "Computer dep.jpeg",
    "innovation & ai lab": "Computer dep.jpeg",
    "innovation lab": "Computer dep.jpeg",
    "computer lab": "Computer dep.jpeg",

    "information technology block": "IT dep.jpeg",
    "information technology": "IT dep.jpeg",
    "it department": "IT dep.jpeg",
    "it block": "IT dep.jpeg",
    "it": "IT dep.jpeg",

    "mechanical engineering block": "Mechanical dep.jpeg",
    "mechanical engineering": "Mechanical dep.jpeg",
    "mechanical department": "Mechanical dep.jpeg",
    "mechanical": "Mechanical dep.jpeg",
    "mechanical workshop": "Mechanical dep.jpeg",
    "workshop": "Mechanical dep.jpeg",

    "civil engineering block": "Civil dep.jpeg",
    "civil engineering": "Civil dep.jpeg",
    "civil department": "Civil dep.jpeg",
    "civil": "Civil dep.jpeg",
    "civil lab": "Civil dep.jpeg",

    "electrical engineering block": "Electrical dep.jpeg",
    "electrical engineering": "Electrical dep.jpeg",
    "electrical department": "Electrical dep.jpeg",
    "electrical": "Electrical dep.jpeg",
    "electrical lab": "Electrical dep.jpeg",

    "electronics & communication block": "E&C dep.jpeg",
    "electronics & communication": "E&C dep.jpeg",
    "electronics and communication": "E&C dep.jpeg",
    "electronics": "E&C dep.jpeg",
    "ec department": "E&C dep.jpeg",
    "ec block": "E&C dep.jpeg",
    "ec lab": "E&C dep.jpeg",
    "ec": "E&C dep.jpeg",
    "e&c": "E&C dep.jpeg",

    "aeronautical engineering block": "Aero dep.jpeg",
    "aeronautical engineering": "Aero dep.jpeg",
    "aeronautical": "Aero dep.jpeg",
    "aero department": "Aero dep.jpeg",
    "aero block": "Aero dep.jpeg",
    "aero": "Aero dep.jpeg",

    "mca & bca": "MCA&BCA.jpeg",
    "mca and bca": "MCA&BCA.jpeg",
    "mca department": "MCA&BCA.jpeg",
    "bca department": "MCA&BCA.jpeg",
    "mca": "MCA&BCA.jpeg",
    "bca": "MCA&BCA.jpeg",
    "lcmca block": "MCA&BCA.jpeg",

    # 3. Diploma Building & All Diploma Departments (Blocks A–G)
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
    "diploma ec": "diploma dep.jpeg",
    "diploma automobile": "diploma dep.jpeg",
    "diploma department": "diploma dep.jpeg",
    "diploma block": "diploma dep.jpeg",
    "diploma building": "diploma dep.jpeg",
    "diploma canteen": "diploma dep.jpeg",
    "diploma": "diploma dep.jpeg",

    # 4. Administration Block, Central Library, Reading Room, Medical, T&P, Auditoriums
    "administration block": "Admin dep.jpeg",
    "administration office & accounts": "Admin dep.jpeg",
    "administration building": "Admin dep.jpeg",
    "admin block": "Admin dep.jpeg",
    "admin building": "Admin dep.jpeg",
    "admin": "Admin dep.jpeg",
    "administration": "Admin dep.jpeg",
    "central library": "Admin dep.jpeg",
    "library": "Admin dep.jpeg",
    "librari": "Admin dep.jpeg",
    "reading room": "Admin dep.jpeg",
    "reading hall": "Admin dep.jpeg",
    "book bank": "Admin dep.jpeg",
    "girls room": "Admin dep.jpeg",
    "girls common room": "Admin dep.jpeg",
    "girls rest room": "Admin dep.jpeg",
    "ladies room": "Admin dep.jpeg",
    "medical room": "Admin dep.jpeg",
    "medical & first aid room": "Admin dep.jpeg",
    "medical": "Admin dep.jpeg",
    "first aid room": "Admin dep.jpeg",
    "first aid": "Admin dep.jpeg",
    "training & placement cell": "Admin dep.jpeg",
    "training and placement cell": "Admin dep.jpeg",
    "training & placement": "Admin dep.jpeg",
    "training and placement": "Admin dep.jpeg",
    "placement cell": "Admin dep.jpeg",
    "placement office": "Admin dep.jpeg",
    "t&p cell": "Admin dep.jpeg",
    "t&p office": "Admin dep.jpeg",
    "t&p": "Admin dep.jpeg",
    "tpo": "Admin dep.jpeg",
    "college auditorium": "Admin dep.jpeg",
    "auditorium": "Admin dep.jpeg",
    "central seminar hall": "Admin dep.jpeg",
    "seminar hall": "Admin dep.jpeg",
    "principal office": "Admin dep.jpeg",
    "accounts office": "Admin dep.jpeg",
    "examination cell": "Admin dep.jpeg",

    # 5. Sports Complex, Cricket Ground, Gymnasium & Courts
    "sports complex & gymnasium": "Sports court.png",
    "sports complex": "Sports court.png",
    "gymnasium": "Sports court.png",
    "gym": "Sports court.png",
    "cricket ground": "Sports court.png",
    "sports ground": "Sports court.png",
    "playground": "Sports court.png",
    "sports court": "Sports court.png",
    "pavilion": "Sports court.png",
    "pavellinon": "Sports court.png",
    "basketball court": "Sports court.png",
    "volleyball court": "Sports court.png",
    "outdoor sports": "Sports court.png",

    # 6. Transport, Bus Stand & Parking
    "bus parking": "Bus stop.png",
    "transport office": "Bus stop.png",
    "bus stop": "Bus stop.png",
    "bus stand": "Bus stop.png",
    "transport hub": "Bus stop.png",
    "transport coordinator": "Bus stop.png",

    # 7. Food & Canteen
    "central food court & canteen": "SVIT Canteen loc.png",
    "central canteen": "SVIT Canteen loc.png",
    "canteen": "SVIT Canteen loc.png",
    "food court": "SVIT Canteen loc.png",
    "cafeteria": "SVIT Canteen loc.png",
    "mess": "SVIT Canteen loc.png",

    # 8. Amenities
    "stationary": "Stationarys.png",
    "stationery": "Stationarys.png",
    "xerox shop": "Stationarys.png",
    "print shop": "Stationarys.png"
}

# =========================================================================
# IN-MEMORY DATAFRAME CACHE (ZERO DISK I/O AFTER FIRST LOAD)
# =========================================================================
_DF_CACHE: Dict[str, pd.DataFrame] = {}


def resolve_entity_map_image(entity_dict: dict) -> str:
    """
    Deterministically resolves the authoritative map image filename based on entity record metadata.
    """
    pid = str(entity_dict.get('place_id') or entity_dict.get('facility_id') or '').strip().upper()
    name = str(entity_dict.get('place_name') or entity_dict.get('facility_name') or '').strip().lower()
    cat = str(entity_dict.get('category') or '').strip().lower()
    zone = str(entity_dict.get('zone') or entity_dict.get('location') or entity_dict.get('building') or '').strip().lower()
    bldg = str(entity_dict.get('building') or '').strip().lower()

    # 1. By exact Place ID / Facility ID
    # Main Gate / Campus Entry / Parking / Amphitheatre / Architecture / Hostel
    if pid in ("P001", "P039", "P040", "P029", "P038", "FAC-010", "FAC-012"):
        return "SVIT with all dep.jpeg"

    # Bus Parking & Transport Office
    if pid in ("P025", "P026"):
        return "Bus stop.png"

    # Sports Complex & Cricket Ground
    if pid in ("P023", "P024", "FAC-009"):
        return "Sports court.png"

    # Central Canteen / Food Court
    if pid in ("P027", "FAC-011"):
        return "SVIT Canteen loc.png"

    # Diploma Canteen & Diploma Departments A-G
    if pid in ("P028", "P030", "P031", "P032", "P033", "P034", "P035", "P036"):
        return "diploma dep.jpeg"

    # Computer Dept & Labs
    if pid in ("P003", "P009", "P010", "P016", "P017"):
        return "Computer dep.jpeg"

    # IT Block
    if pid == "P004":
        return "IT dep.jpeg"

    # Civil Block & Civil Lab
    if pid in ("P005", "P018"):
        return "Civil dep.jpeg"

    # Mechanical Block & Workshop
    if pid in ("P006", "P019"):
        return "Mechanical dep.jpeg"

    # Electrical Block & Electrical Lab
    if pid in ("P007", "P020"):
        return "Electrical dep.jpeg"

    # EC Block & EC Lab
    if pid in ("P008", "P021"):
        return "E&C dep.jpeg"

    # MCA & BCA Departments
    if pid in ("P011", "P012"):
        return "MCA&BCA.jpeg"

    # Admin Block & Associated Facilities (Central Library, Reading Room, Medical Room, T&P, Auditoriums)
    if pid in ("P002", "P013", "P014", "P015", "P022", "P037", "FAC-001", "FAC-002", "FAC-003", "FAC-004", "FAC-005", "FAC-006", "FAC-007", "FAC-008"):
        return "Admin dep.jpeg"

    # 2. Fallback to name/zone matching
    if "diploma" in name or "diploma" in zone or "diploma" in bldg:
        return "diploma dep.jpeg"
    if "sports" in name or "cricket" in name or "gym" in name or "sports" in cat:
        return "Sports court.png"
    if "canteen" in name or "food" in name or "cafeteria" in name:
        return "SVIT Canteen loc.png"
    if "bus" in name or "transport" in name:
        return "Bus stop.png"
    if "admin" in name or "library" in name or "reading" in name or "medical" in name or "placement" in name or "auditorium" in name or "seminar" in name:
        return "Admin dep.jpeg"
    if "computer" in name or "data science" in name or "ai" in name or "computer" in zone:
        return "Computer dep.jpeg"
    if "information technology" in name or "it block" in name:
        return "IT dep.jpeg"
    if "civil" in name or "civil" in zone:
        return "Civil dep.jpeg"
    if "mechanical" in name or "workshop" in name:
        return "Mechanical dep.jpeg"
    if "electrical" in name:
        return "Electrical dep.jpeg"
    if "electronics" in name or "ec" in name:
        return "E&C dep.jpeg"
    if "mca" in name or "bca" in name:
        return "MCA&BCA.jpeg"
    if "stationary" in name or "stationery" in name:
        return "Stationarys.png"

    return "SVIT with all dep.jpeg"


def invalidate_ai_caches(module_key: str = None, item_data: dict = None, is_delete: bool = False) -> None:
    """
    Invalidates in-memory DataFrame cache, response cache, and vector cache
    when Admin CRUD actions occur.
    """
    global _DF_CACHE
    if module_key:
        mod_clean = str(module_key).strip().lower()
        for k in list(_DF_CACHE.keys()):
            if mod_clean in k or k.startswith(mod_clean):
                _DF_CACHE.pop(k, None)
    else:
        _DF_CACHE.clear()

    try:
        from app.ai.retriever import clear_vector_cache
        clear_vector_cache()
    except Exception:
        pass

    try:
        from app.ai.rag_pipeline import clear_response_cache
        clear_response_cache()
    except Exception:
        pass


def get_cached_dataframe(filename: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """
    Returns an in-memory cached copy of a knowledge base dataset DataFrame.
    Checks MongoDB Atlas first, then falls back to local CSV files.
    """
    if not force_refresh and filename in _DF_CACHE:
        return _DF_CACHE[filename]

    # 1. Try loading from MongoDB Atlas collection first
    try:
        from app.database.mongodb import get_collection
        coll_name = filename.replace('.csv', '').lower().replace(' ', '_')
        if coll_name in ('subject', 'subjects'):
            coll = get_collection('subjects')
        elif coll_name in ('rooms', 'rooms_facilities'):
            coll = get_collection('rooms_facilities')
        elif coll_name == 'facilities':
            coll = get_collection('facilities')
        elif coll_name == 'campus_info':
            coll = get_collection('campus_info')
        else:
            coll = get_collection(coll_name)

        if coll is not None:
            docs = list(coll.find({}, {'_id': 0}))
            if docs and len(docs) > 0:
                df = pd.DataFrame(docs).fillna("")
                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
                _DF_CACHE[filename] = df
                return df
    except Exception as e:
        pass

    # 2. Fallback to local CSV files
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
                try:
                    df = pd.read_csv(path, dtype=str, sep=None, engine='python')
                except Exception:
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
        "campus_info.csv",
        "facilities.csv",
        "departments.csv",
        "rooms_facilities.csv",
        "subject.csv",
        "subjects.csv",
        "timetable.csv",
        "notices.csv",
        "events.csv",
        "placements.csv",
        "faculty.csv",
        "transport.csv",
        "canteen.csv",
        "contact.csv",
        "library_books.csv",
        "campus_info.csv",
        "facilities.csv",
        "rooms_facilities.csv",
    ]
    loaded_count = 0
    for fname in critical_files:
        if get_cached_dataframe(fname) is not None:
            loaded_count += 1
    print(f"[Cache] In-memory DataFrame cache ready: {loaded_count}/{len(critical_files)} datasets preloaded.")


# =========================================================
# DATE & TEMPORAL RESOLUTION HELPERS
# =========================================================

MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

def parse_time_to_minutes(t_str: str) -> Optional[int]:
    """Converts timetable and transport time strings ('07:15 AM', '09:00', '11:15', '01:15', '02:00', '03:00') to minutes since midnight."""
    if not t_str or not isinstance(t_str, str):
        return None
    cleaned = t_str.strip().upper()
    is_pm = "PM" in cleaned
    is_am = "AM" in cleaned
    cleaned = cleaned.replace("AM", "").replace("PM", "").strip()
    match = re.match(r'^(\d{1,2})[:.](\d{2})$', cleaned)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    if is_pm and hours < 12:
        hours += 12
    elif is_am and hours == 12:
        hours = 0
    elif not is_pm and not is_am and hours < 8: # Timetable PM hour conversion (classes run 9 AM to 5 PM)
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
    Robust natural language calendar and relative date resolver.
    Accurately handles:
      - '15 September 2026', '15th September 2026', 'September 15, 2026'
      - '15 September', '15 Sept', '15/09/2026', '15-09-2026', '15/9'
      - 'tomorrow', 'today', 'yesterday', 'day after tomorrow'
      - 'Monday', 'Tuesday', 'next Monday', etc.
    """
    raw_msg = str(query or '').strip()
    msg = re.sub(r"['’]s\b", "", raw_msg, flags=re.IGNORECASE)
    msg = msg.replace('"', '').replace("'", "").strip().lower()

    now = get_ist_now()
    default_year = now.year

    # 1. Check explicit standard numeric dates (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)
    iso_match = re.search(r'\b(202\d)[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b', msg)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            target_date = datetime(y, m, d, tzinfo=IST)
            return {
                "day_name": target_date.strftime("%A"),
                "formatted_date": target_date.strftime("%A, %d %B %Y"),
                "iso_date": target_date.strftime("%Y-%m-%d"),
                "is_explicit_date": True
            }
        except ValueError:
            pass

    dmy_match = re.search(r'\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])(?:[-/.](202\d|\d{2}))?\b', msg)
    if dmy_match:
        d = int(dmy_match.group(1))
        m = int(dmy_match.group(2))
        raw_y = dmy_match.group(3)
        if raw_y:
            y = int(raw_y) if len(raw_y) == 4 else 2000 + int(raw_y)
        else:
            y = default_year
        try:
            target_date = datetime(y, m, d, tzinfo=IST)
            return {
                "day_name": target_date.strftime("%A"),
                "formatted_date": target_date.strftime("%A, %d %B %Y"),
                "iso_date": target_date.strftime("%Y-%m-%d"),
                "is_explicit_date": True
            }
        except ValueError:
            pass

    # 2. Check Textual Date formats (e.g. '15 September 2026', '15th Sept', 'September 15')
    month_regex = r'(?:january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)'

    day_month_match = re.search(r'\b(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+(' + month_regex + r')(?:\s+(202\d))?\b', msg)
    if day_month_match:
        d = int(day_month_match.group(1))
        m_str = day_month_match.group(2).lower()
        m = MONTH_NAMES.get(m_str, 1)
        raw_y = day_month_match.group(3)
        y = int(raw_y) if raw_y else default_year
        try:
            target_date = datetime(y, m, d, tzinfo=IST)
            return {
                "day_name": target_date.strftime("%A"),
                "formatted_date": target_date.strftime("%A, %d %B %Y"),
                "iso_date": target_date.strftime("%Y-%m-%d"),
                "is_explicit_date": True
            }
        except ValueError:
            pass

    month_day_match = re.search(r'\b(' + month_regex + r')\s+(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?(?:\s+(202\d))?\b', msg)
    if month_day_match:
        m_str = month_day_match.group(1).lower()
        m = MONTH_NAMES.get(m_str, 1)
        d = int(month_day_match.group(2))
        raw_y = month_day_match.group(3)
        y = int(raw_y) if raw_y else default_year
        try:
            target_date = datetime(y, m, d, tzinfo=IST)
            return {
                "day_name": target_date.strftime("%A"),
                "formatted_date": target_date.strftime("%A, %d %B %Y"),
                "iso_date": target_date.strftime("%Y-%m-%d"),
                "is_explicit_date": True
            }
        except ValueError:
            pass

    # 3. Relative date keywords
    if "day after tomorrow" in msg:
        target_date = now + timedelta(days=2)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y"),
            "iso_date": target_date.strftime("%Y-%m-%d"),
            "is_explicit_date": False
        }

    if "tomorrow" in msg:
        target_date = now + timedelta(days=1)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y"),
            "iso_date": target_date.strftime("%Y-%m-%d"),
            "is_explicit_date": False
        }

    if "yesterday" in msg:
        target_date = now - timedelta(days=1)
        return {
            "day_name": target_date.strftime("%A"),
            "formatted_date": target_date.strftime("%A, %d %B %Y"),
            "iso_date": target_date.strftime("%Y-%m-%d"),
            "is_explicit_date": False
        }

    if "today" in msg or "tonight" in msg:
        return {
            "day_name": now.strftime("%A"),
            "formatted_date": now.strftime("%A, %d %B %Y"),
            "iso_date": now.strftime("%Y-%m-%d"),
            "is_explicit_date": False
        }

    # 4. Explicit Weekday Name
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        if re.search(r'\b' + day + r'\b', msg) or re.search(r'\b' + day[:3] + r'\b', msg):
            target_weekday = days.index(day)
            current_weekday = now.weekday()
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
            return {
                "day_name": day.capitalize(),
                "formatted_date": target_date.strftime("%A, %d %B %Y"),
                "iso_date": target_date.strftime("%Y-%m-%d"),
                "is_explicit_date": True
            }

    # Default fallback: Today
    return {
        "day_name": now.strftime("%A"),
        "formatted_date": now.strftime("%A, %d %B %Y"),
        "iso_date": now.strftime("%Y-%m-%d"),
        "is_explicit_date": False
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


def process_transport_context(query: str, user_profile: dict = None) -> Tuple[str, Optional[str], List[str], Optional[Dict[str, Any]]]:
    """
    Intelligent SVIT Bus & Transport Assistant context processor.
    Resolves routes, stops, departure times, next/last bus, and location metadata.
    """
    df = get_cached_dataframe("transport.csv")
    if df is None or df.empty:
        return "No bus transport records are currently available.", None, ["transport.csv"], None

    raw_query = str(query or '').strip()
    clean_q = re.sub(r'[^\w\s\-\:]', ' ', raw_query).lower()

    now = get_ist_now()
    current_time_str = now.strftime("%I:%M %p")
    current_mins = now.hour * 60 + now.minute

    # Parse transport intent keywords
    is_next_bus = any(k in clean_q for k in ["next bus", "upcoming bus", "bus right now", "next route", "bus leaving now", "next available bus"])
    is_last_bus = any(k in clean_q for k in ["last bus", "final bus", "latest bus", "end bus"])
    
    # Parse explicit time requested (e.g., 'at 8 AM', '7:30', '8am', '07:15')
    time_match = re.search(r'\b(?:at|around|by|before|after)?\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b', clean_q)
    target_time_min = None
    if time_match:
        raw_t = time_match.group(1).strip()
        if re.search(r'\d', raw_t) and not any(k in raw_t for k in ["svit", "bus", "route"]):
            if ":" not in raw_t and ("am" in raw_t or "pm" in raw_t or any(raw_t.startswith(h) for h in ["6", "7", "8", "9"])):
                num = re.findall(r'\d+', raw_t)[0]
                suffix = "PM" if "pm" in raw_t else "AM"
                raw_t = f"{num}:00 {suffix}"
            target_time_min = parse_time_to_minutes(raw_t)

    matched_df = df.copy()

    # Route ID filter (R01 - R40)
    route_id_match = re.search(r'\b(r\d{1,2})\b', clean_q)
    if route_id_match:
        r_id = route_id_match.group(1).upper()
        if len(r_id) == 2:
            r_id = f"R0{r_id[1]}"
        r_match_df = matched_df[matched_df['route_id'].str.upper() == r_id]
        if not r_match_df.empty:
            matched_df = r_match_df

    # Extract location tokens (starting point / stops)
    ignore_words = {"bus", "buses", "svit", "vasad", "campus", "timings", "timing", "time", "show", "tell", "what", "where", "which", "how", "next", "last", "from", "to", "at", "route", "routes", "schedule", "go", "reach", "take", "available", "morning", "evening", "stop", "stops"}
    query_tokens = [w for w in clean_q.split() if w not in ignore_words and len(w) > 2]

    if not route_id_match and query_tokens:
        found_rows = []
        for idx, row in matched_df.iterrows():
            sp = str(row.get('starting_point', '')).lower()
            rn = str(row.get('route_name', '')).lower()
            stops = str(row.get('stops', '')).lower()
            
            score = 0
            for token in query_tokens:
                if token in sp: score += 6
                elif token in stops: score += 4
                elif token in rn: score += 2
            if score > 0:
                found_rows.append((score, row))

        if found_rows:
            found_rows.sort(key=lambda x: x[0], reverse=True)
            matched_df = pd.DataFrame([r for _, r in found_rows])

    # Next bus resolution
    is_next_bus_tomorrow = False
    if is_next_bus:
        upcoming_rows = []
        for idx, row in df.iterrows():
            dep_min = parse_time_to_minutes(str(row.get('departure_time', '')))
            if dep_min is not None and dep_min >= current_mins:
                upcoming_rows.append((dep_min - current_mins, row))
        if upcoming_rows:
            upcoming_rows.sort(key=lambda x: x[0])
            matched_df = pd.DataFrame([r for _, r in upcoming_rows[:3]])
        else:
            is_next_bus_tomorrow = True
            matched_df = df.head(4)

    cards = []
    for idx, row in matched_df.head(6).iterrows():
        rid = row.get('route_id', f'R{idx+1:02d}')
        rname = row.get('route_name', f'Route {rid}')
        bno = row.get('bus_no', 'GJ06-BUS-XXX')
        sp = row.get('starting_point', 'Vadodara')
        dest = row.get('destination', 'SVIT Vasad Campus')
        dep = row.get('departure_time', 'N/A')
        arr = row.get('arrival_time', 'N/A')
        stops = row.get('stops', '')
        driver = row.get('driver_name', 'Campus Driver')
        contact = row.get('contact_number', 'N/A')
        cap = row.get('capacity', '50')
        status = row.get('status', 'Active')

        card = (
            f"### 🚌 {rname} ({rid})\n"
            f"* 🏷️ **Bus Number:** `{bno}` &nbsp;|&nbsp; 📋 **Status:** `{status}`\n"
            f"* 📍 **Route:** **{sp}** ➔ **{dest}**\n"
            f"* ⏰ **Timings:** Departure **{dep}** | Arrival **{arr}** (at SVIT Campus)\n"
            f"* 🛑 **Stops Sequence:** {stops}\n"
            f"* 👨‍✈️ **Driver:** {driver} | 📞 **Contact:** `{contact}` | 💺 **Capacity:** {cap} Seats"
        )
        cards.append(card)

    header = f"### 🚌 SVIT Campus Transport Schedule & Bus Routes\n\n"
    if is_next_bus:
        if is_next_bus_tomorrow:
            header += f"ℹ️ *All scheduled morning buses for today have completed their runs (Current Time: {current_time_str}). The earliest bus tomorrow departs at 06:30 AM:*\n\n"
        else:
            header += f"*(Live IST Status as of {current_time_str} — Upcoming Bus departures:)*\n\n"

    body = "\n\n---\n\n".join(cards) if cards else "No matching college bus routes were found for the requested location or time. College buses run on all major Vadodara, Anand, and highway arterial routes arriving by 08:00 AM - 08:45 AM at the SVIT Vasad Campus Bus Station."
    map_url = "/static/navigation_maps/Bus stop.png"
    sources = ["transport.csv (Row 1-40)"]

    location_data = {
        "id": "P024",
        "location_id": "P024",
        "name": "SVIT Bus Stop & Transport Hub",
        "latitude": 22.469850,
        "longitude": 73.077500,
        "building": "Main Gate Bus Terminal",
        "landmark": "Near Main Entrance Gate, SVIT Vasad",
        "zone": "Campus Transport",
        "description": "SVIT Central Bus Terminal for all 40 college bus routes from Vadodara, Anand, and highway junctions.",
        "image_url": map_url
    }

    return header + body, map_url, sources, location_data
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
    based on current clock time in Asia/Kolkata (IST) and the logged-in student's schedule.
    """
    now = get_ist_now()
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

            # 1. Day filter (don't restrict to single day if searching for a specific subject, faculty, or room)
            has_subject_or_room_query = any(k in msg for k in ["who teaches", "faculty for", "professor for", "where is", "location", "how to reach", "which room", "what room", "room for", "room is my", "class in", "teaches", "lecture in"])
            if day_col and not has_subject_or_room_query:
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
    """Parses department and faculty details, querying faculty.csv for subject teachers and departments.csv for HODs."""
    cleaned_query = query.replace('"', '').replace("'", "").strip().lower()
    faculty_blocks = []

    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or "Computer Engineering"

    # 1. Search faculty.csv for specific subjects or faculty names
    try:
        df_fac = get_cached_dataframe("faculty.csv")
        if df_fac is not None and not df_fac.empty:
            matched_facs = []
            for idx, row in df_fac.iterrows():
                subj = str(row.get('subject', '')).lower()
                name = str(row.get('full_name', '')).lower()
                desig = str(row.get('designation', ''))
                dept = str(row.get('department', ''))
                cabin = str(row.get('cabin', ''))
                email = str(row.get('email', ''))
                phone = str(row.get('phone', ''))

                is_subj_match = subj and (subj in cleaned_query or any(w in cleaned_query for w in subj.split() if len(w) > 3))
                is_name_match = name and any(part in cleaned_query for part in name.split() if len(part) > 3)

                if is_subj_match or is_name_match:
                    f_str = f"faculty.csv (Row {idx + 2}): Full Name: {row.get('full_name')} | Designation: {desig} | Department: {dept} | Subject: {row.get('subject')} | Cabin: {cabin} | Email: {email} | Phone: {phone}"
                    matched_facs.append(f_str)

            if matched_facs:
                faculty_blocks.extend(matched_facs[:8])
    except Exception as e:
        print(f"[Error] faculty.csv search error: {e}")

    # 2. Search departments.csv for HODs and department details
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
            is_faculty_related = any(k in cleaned_query for k in ["hod", "head", "faculty", "professor", "teacher", "sir", "madam", "cabin", "department", "branch", "dean", "principal"])

            if (is_my_hod_query or has_explicit_dept or name_match or is_faculty_related):
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
            else:
                matched_df = pd.DataFrame()

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

    # 1. Strictly EXCLUDE questions about locations / navigation / buildings
    nav_check_words = [
        "where", "location", "locate", "building", "block", "how to reach", 
        "directions", "direction", "map", "take me", "route", "way to", 
        "find", "visit", "go to", "situated", "kaha", "kahan", "kidhar"
    ]
    if any(re.search(r'\b' + re.escape(k) + r'\b', q) for k in nav_check_words):
        return None

    # 2. Exclude questions about college offerings in general
    if any(k in q for k in [
        "svit offer", "all department", "all course", "list of course", 
        "available course", "available department", "branches in svit", 
        "courses in svit", "departments are available", "courses are available", 
        "what departments are", "what courses are"
    ]):
        return None

    # 3. Whole-word self-reference detection
    has_self_ref = bool(re.search(r'\b(my|i|i am|am i|who am i|mine|profile)\b', q))

    # Precise question intent discriminators
    is_asking_dept_and_course = has_self_ref and bool(re.search(r'\b(department|dept|branch)\b', q)) and bool(re.search(r'\b(course|program|stream)\b', q))
    
    is_asking_course = (
        bool(re.search(r'\b(what is my program|what is my course|which course am i in|which program am i in|what program am i in|what course am i in|my program|my course|my degree|my diploma)\b', q)) or
        (has_self_ref and bool(re.search(r'\b(course name|program name)\b', q)))
    )

    is_asking_dept = (
        bool(re.search(r'\b(what is my department|what is my dept|what is my branch|which department am i in|which dept am i in|what department am i in|tell me my department|show my department)\b', q)) or
        (has_self_ref and bool(re.search(r'\b(my department|my dept|my branch)\b', q)))
    )

    is_asking_sem = (
        bool(re.search(r'\b(what is my semester|what is my sem|which semester am i in|which sem am i in|what semester am i in|my semester|my sem)\b', q))
    )

    is_asking_div = (
        bool(re.search(r'\b(what is my division|what is my div|which division am i in|what division am i in|my division|my div|my section)\b', q))
    )

    is_asking_batch = (
        bool(re.search(r'\b(what is my batch|which batch am i in|what batch am i in|my batch)\b', q))
    )

    is_asking_enrollment = (
        bool(re.search(r'\b(what is my enrollment|what is my roll number|what is my id|my enrollment|my roll number|my id|my student id)\b', q))
    )

    is_asking_full_profile = (
        bool(re.search(r'\b(who am i|my profile|my details|about me|my info|my information|show my profile|what is my name|what are my details|student profile information)\b', q))
    )

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


class NavResult(tuple):
    """
    A 3-element tuple (context, map_url, sources) that also carries .location_data
    and supports both 3-tuple unpacking and location_data attribute access.
    """
    def __new__(cls, context: str, map_url: Optional[str], sources: List[str], location_data: Optional[Dict[str, Any]] = None):
        inst = super().__new__(cls, (context, map_url, sources))
        inst.location_data = location_data
        return inst


def process_campus_navigation_context(query: str):
    """
    Directly resolves campus landmarks, buildings, offices, gates, facilities, and amenities
    from the authoritative campus_info.csv and facilities.csv datasets (backed by MongoDB / CSV).
    Ensures exact entity grounding, anti-collision rank ordering, precise map image attachment,
    and returns authoritative geographic coordinates for Google Maps navigation.
    """
    clean_q = re.sub(r'[\?\.\!,;:]', ' ', str(query or '').strip().lower())
    
    # 1. Load DataFrames
    df_campus = get_cached_dataframe("campus_info.csv")
    df_fac = get_cached_dataframe("facilities.csv")
    
    # Check for general "show all locations" / "campus navigation directory"
    is_list_all = any(k in clean_q for k in [
        "show campus navigation", "all campus navigation", "campus navigation locations",
        "list campus locations", "show all locations", "all locations", "all buildings",
        "campus locations", "navigation locations", "all landmarks",
        # Campus facility overview queries
        "what facilities", "available facilities", "campus facilities", "explore campus",
        "campus facility", "facilities available", "show facilities", "list facilities",
        "explore the campus", "show me the main buildings", "buildings rooms facilities",
        "rooms facilities and landmarks", "campus overview", "show campus"
    ])
    
    if is_list_all:
        context_blocks = ["--- SVIT CAMPUS NAVIGATION DIRECTORY ---"]
        sources = []
        
        # Include campus_info.csv records (buildings, rooms, landmarks, gates, etc.)
        if df_campus is not None and not df_campus.empty:
            for idx, row in df_campus.iterrows():
                pid = row.get('place_id', f'P{idx+1:03d}')
                pname = row.get('place_name', '')
                cat = row.get('category', '')
                zone = row.get('zone', '')
                landmark = row.get('landmark', '')
                desc = row.get('description', '')
                block = (
                    f"* Place ID: {pid} | Place Name: {pname} | Category: {cat} | "
                    f"Zone: {zone} | Landmark: {landmark} | Description: {desc} | "
                    f"[Source: campus_info.csv (Row {idx + 1})]"
                )
                context_blocks.append(block)
                sources.append(f"campus_info.csv (Row {idx + 1})")
        
        # Include facilities.csv records for facility overview queries
        if df_fac is not None and not df_fac.empty:
            for idx, row in df_fac.iterrows():
                fid = row.get('facility_id', f'FAC-{idx+1:03d}')
                fname = row.get('facility_name', '')
                fcat = row.get('category', '')
                fbldg = row.get('building', '')
                ffloor = row.get('floor', '')
                floc = row.get('location', '')
                fdesc = row.get('description', '')
                fcap = row.get('capacity', '')
                famen = row.get('facilities', '')
                block = (
                    f"* Facility ID: {fid} | Facility Name: {fname} | Category: {fcat} | "
                    f"Building: {fbldg} | Floor: {ffloor} | Location: {floc} | "
                    f"Description: {fdesc} | Capacity: {fcap} | Amenities: {famen} | "
                    f"[Source: facilities.csv (Row {idx + 1})]"
                )
                context_blocks.append(block)
                sources.append(f"facilities.csv (Row {idx + 1})")
        
        map_url = "/static/navigation_maps/SVIT with all dep.jpeg"
        return NavResult("\n\n---\n\n".join(context_blocks), map_url, sources[:60], None)
    
    # Check for spatial "near <landmark>"
    near_match = re.search(r'\b(?:near|around|close to|beside|what is near)\s+(?:the\s+)?([a-z0-9\s&]+)', clean_q)
    if near_match:
        target_entity = near_match.group(1).strip()
        if df_campus is not None and not df_campus.empty:
            matching_rows = []
            for idx, row in df_campus.iterrows():
                row_text = f"{row.get('place_name', '')} {row.get('zone', '')} {row.get('landmark', '')}".lower()
                target_tokens = [w for w in target_entity.split() if len(w) > 2 and w not in ["the", "and", "campus", "near", "what", "where", "is"]]
                if target_tokens and any(w in row_text for w in target_tokens):
                    matching_rows.append((idx, row))
            if matching_rows:
                context_blocks = [f"--- CAMPUS LOCATIONS NEAR '{target_entity.title()}' ---"]
                sources = []
                for idx, row in matching_rows:
                    pid = row.get('place_id', f'P{idx+1:03d}')
                    pname = row.get('place_name', '')
                    cat = row.get('category', '')
                    zone = row.get('zone', '')
                    landmark = row.get('landmark', '')
                    desc = row.get('description', '')
                    block = (
                        f"* Place ID: {pid} | Place Name: {pname} | Category: {cat} | "
                        f"Zone: {zone} | Landmark: {landmark} | Description: {desc} | "
                        f"[Source: campus_info.csv (Row {idx + 1})]"
                    )
                    context_blocks.append(block)
                    sources.append(f"campus_info.csv (Row {idx + 1})")
                
                # Resolve map image based on target entity
                top_dict = matching_rows[0][1].to_dict()
                map_file = resolve_entity_map_image(top_dict)
                map_url = f"/static/navigation_maps/{map_file}"

                lat_val = top_dict.get('latitude')
                lng_val = top_dict.get('longitude')
                try:
                    lat_f = float(lat_val) if lat_val is not None and str(lat_val).strip() != '' else None
                except (ValueError, TypeError):
                    lat_f = None
                try:
                    lng_f = float(lng_val) if lng_val is not None and str(lng_val).strip() != '' else None
                except (ValueError, TypeError):
                    lng_f = None

                loc_data = {
                    "id": str(top_dict.get('place_id', '')),
                    "location_id": str(top_dict.get('place_id', '')),
                    "name": str(top_dict.get('place_name', '')),
                    "latitude": lat_f,
                    "longitude": lng_f,
                    "building": str(top_dict.get('zone', '')),
                    "landmark": str(top_dict.get('landmark', '')),
                    "zone": str(top_dict.get('zone', '')),
                    "description": str(top_dict.get('description', '')),
                    "image_url": map_url
                }

                return NavResult("\n\n---\n\n".join(context_blocks), map_url, sources, loc_data)

    # 3. Candidate Scoring & Entity Matching
    candidates = [] # List of tuples: (score, type, idx, row_dict, source_str)

    # A. Score campus_info.csv records
    if df_campus is not None and not df_campus.empty:
        for idx, row in df_campus.iterrows():
            row_dict = row.to_dict()
            pid = str(row_dict.get('place_id', '')).strip().upper()
            pname = str(row_dict.get('place_name', '')).strip()
            pname_lower = pname.lower()

            score = 0

            # 1. Exact Place ID match
            if pid and re.search(r'\b' + re.escape(pid.lower()) + r'\b', clean_q):
                score += 120

            # 2. Exact place name match
            if pname_lower and re.search(r'\b' + re.escape(pname_lower) + r'\b', clean_q):
                score += 100
            elif pname_lower and pname_lower in clean_q:
                score += 80

            # 3. Domain aliases & intent patterns
            if pid == "P001": # Main Gate
                if any(k in clean_q for k in ["main gate", "college gate", "campus gate", "main entrance", "college entrance", "campus entrance", "entrance gate", "entry gate", "front gate", "main entry"]):
                    score = max(score, 95)
                elif "gate" in clean_q or "entrance" in clean_q:
                    score = max(score, 85)

            elif pid == "P027": # Central Canteen
                if any(k in clean_q for k in ["central canteen", "canteen", "cafeteria", "mess", "food court", "college canteen", "snack"]):
                    score = max(score, 95)

            elif pid == "P028": # Diploma Canteen
                if "diploma canteen" in clean_q or ("diploma" in clean_q and "canteen" in clean_q):
                    score = max(score, 100)

            elif pid == "P013": # Central Library
                if any(k in clean_q for k in ["central library", "college library", "campus library", "library", "book issue", "reading hall"]):
                    score = max(score, 95)

            elif pid == "P014": # Seminar Hall
                if any(k in clean_q for k in ["seminar hall", "seminar room", "conference hall"]):
                    score = max(score, 95)

            elif pid == "P015": # Auditorium
                if any(k in clean_q for k in ["auditorium", "audi", "main hall", "annual function hall"]):
                    score = max(score, 95)

            elif pid == "P023": # Sports Complex
                if any(k in clean_q for k in ["sports complex", "sports room", "indoor sports", "gymnasium", "sports ground", "volleyball", "basketball"]):
                    score = max(score, 95)

            elif pid == "P024": # Cricket Ground
                if any(k in clean_q for k in ["cricket ground", "football ground", "ground", "playground"]):
                    score = max(score, 95)

            elif pid == "P025": # Bus Parking
                if any(k in clean_q for k in ["bus parking", "bus stand", "bus stop", "college bus", "transport parking"]):
                    score = max(score, 95)

            elif pid == "P026": # Transport Office
                if any(k in clean_q for k in ["transport office", "bus office", "bus in-charge", "transport department"]):
                    score = max(score, 95)

            elif pid == "P002": # Administration Block
                if any(k in clean_q for k in ["administration block", "admin block", "administration building", "admin building"]):
                    score = max(score, 90)

            elif pid == "P003": # Computer Engineering Block
                if any(k in clean_q for k in ["computer engineering block", "computer engineering department", "computer block", "computer department"]):
                    score = max(score, 95)

            elif pid == "P009": # AI & ML Department
                if any(k in clean_q for k in ["ai & ml department", "ai & ml", "aiml department", "artificial intelligence department", "ai and ml"]):
                    score = max(score, 95)

            elif pid == "P010": # Data Science Department
                if any(k in clean_q for k in ["data science department", "data science block", "data science"]):
                    score = max(score, 95)

            elif pid == "P004": # Information Technology Block
                if any(k in clean_q for k in ["information technology block", "information technology department", "it block", "it department"]):
                    score = max(score, 95)

            elif pid == "P005": # Civil Engineering Block
                if any(k in clean_q for k in ["civil engineering block", "civil engineering department", "civil block", "civil department"]):
                    score = max(score, 95)

            elif pid == "P006": # Mechanical Engineering Block
                if any(k in clean_q for k in ["mechanical engineering block", "mechanical engineering department", "mechanical block", "mechanical department"]):
                    score = max(score, 95)

            elif pid == "P007": # Electrical Engineering Block
                if any(k in clean_q for k in ["electrical engineering block", "electrical engineering department", "electrical block", "electrical department"]):
                    score = max(score, 95)

            elif pid == "P008": # Electronics & Communication Block
                if any(k in clean_q for k in ["electronics & communication block", "electronics & communication department", "ec block", "ec department", "e&c block"]):
                    score = max(score, 95)

            elif pid == "P011": # MCA Department
                if any(k in clean_q for k in ["mca department", "mca block", "master of computer applications"]):
                    score = max(score, 95)

            elif pid == "P012": # BCA Department
                if any(k in clean_q for k in ["bca department", "bca block", "bachelor of computer applications"]):
                    score = max(score, 95)

            elif pid == "P029": # Architecture Block
                if any(k in clean_q for k in ["architecture block", "architecture department", "b.arch block"]):
                    score = max(score, 95)

            elif pid == "P016": # Innovation & AI Lab
                if any(k in clean_q for k in ["innovation & ai lab", "innovation lab", "ai lab", "ai research lab"]):
                    score = max(score, 95)

            elif pid == "P017": # Computer Lab
                if any(k in clean_q for k in ["computer lab", "programming lab", "practical lab"]):
                    score = max(score, 95)

            elif pid == "P018": # Civil Lab
                if any(k in clean_q for k in ["civil lab", "survey lab", "material testing lab"]):
                    score = max(score, 95)

            elif pid == "P019": # Mechanical Workshop
                if any(k in clean_q for k in ["mechanical workshop", "workshop practice", "machine shop", "mechanical lab"]):
                    score = max(score, 95)

            elif pid == "P020": # Electrical Lab
                if any(k in clean_q for k in ["electrical lab", "electrical machines lab"]):
                    score = max(score, 95)

            elif pid == "P021": # EC Lab
                if any(k in clean_q for k in ["ec lab", "electronics lab", "communication lab"]):
                    score = max(score, 95)

            elif pid in ("P030", "P031", "P032", "P033", "P034", "P035", "P036"):
                # Diploma branches
                d_branch = pname_lower.replace("diploma", "").strip()
                if "diploma" in clean_q and d_branch and d_branch in clean_q:
                    score = max(score, 95)

            elif pid == "P038": # Hostel
                if any(k in clean_q for k in ["hostel", "student hostel", "boys hostel", "girls hostel"]):
                    score = max(score, 95)

            if score > 0:
                candidates.append((score, "campus", idx, row_dict, f"campus_info.csv (Row {idx + 1})"))

    # B. Score facilities.csv records
    if df_fac is not None and not df_fac.empty:
        for idx, row in df_fac.iterrows():
            row_dict = row.to_dict()
            fid = str(row_dict.get('facility_id', '')).strip().upper()
            fname = str(row_dict.get('facility_name', '')).strip()
            fname_lower = fname.lower()

            score = 0

            # 1. Exact Facility ID match
            if fid and re.search(r'\b' + re.escape(fid.lower()) + r'\b', clean_q):
                score += 120

            # 2. Exact facility name match
            if fname_lower and re.search(r'\b' + re.escape(fname_lower) + r'\b', clean_q):
                score += 100
            elif fname_lower and fname_lower in clean_q:
                score += 80

            # 3. Domain aliases & intent patterns
            if fid == "FAC-001": # Girls Room
                if any(k in clean_q for k in ["girls room", "girls common room", "ladies room", "ladies common room", "girls rest room", "women common room", "girls resting room"]):
                    score = max(score, 100)

            elif fid == "FAC-002": # Reading Room
                if any(k in clean_q for k in ["reading room", "study room", "quiet study", "place to study", "where can i study", "where to study", "study space", "reading hall"]):
                    score = max(score, 100)

            elif fid == "FAC-003": # Central Library
                if any(k in clean_q for k in ["central library", "college library", "campus library", "library"]):
                    score = max(score, 90)
                elif "study" in clean_q or "reading" in clean_q:
                    score = max(score, 70)

            elif fid == "FAC-004": # College Auditorium
                if any(k in clean_q for k in ["college auditorium", "main auditorium", "auditorium"]):
                    score = max(score, 90)

            elif fid == "FAC-005": # Stationary Shop
                if any(k in clean_q for k in ["stationary shop", "stationery shop", "xerox", "photocopy", "print shop", "stationery", "stationary"]):
                    score = max(score, 95)

            elif fid == "FAC-006": # First Aid & Medical Room
                if any(k in clean_q for k in ["medical room", "first aid", "doctor", "health center", "emergency clinic", "dispensary"]):
                    score = max(score, 95)

            elif fid == "FAC-007": # Boys Hostel
                if any(k in clean_q for k in ["boys hostel", "hostel boys", "male hostel"]):
                    score = max(score, 95)

            elif fid == "FAC-008": # Girls Hostel
                if any(k in clean_q for k in ["girls hostel", "hostel girls", "female hostel"]):
                    score = max(score, 95)

            elif fid == "FAC-009": # Cricket Ground & Pavilion
                if any(k in clean_q for k in ["cricket ground", "pavilion", "sports pavilion", "football field"]):
                    score = max(score, 95)

            elif fid == "FAC-010": # Central Canteen & Dining
                if any(k in clean_q for k in ["central canteen", "canteen", "food court", "mess", "dining"]):
                    if "diploma" not in clean_q:
                        score = max(score, 95)

            elif fid == "FAC-011": # Diploma Canteen & Cafeteria
                if any(k in clean_q for k in ["diploma canteen", "diploma food", "diploma mess"]):
                    score = max(score, 100)
                elif "canteen" in clean_q and "diploma" in clean_q:
                    score = max(score, 100)

            elif fid == "FAC-012": # Campus Main Entrance Gate
                if any(k in clean_q for k in ["campus main entrance gate", "main entrance gate", "main gate", "college gate", "campus gate", "main entrance", "entrance gate", "entry gate"]):
                    score = max(score, 95)

            if score > 0:
                candidates.append((score, "fac", idx, row_dict, f"facilities.csv (Row {idx + 1})"))

    if not candidates:
        map_url = get_navigation_map_url(query)
        return NavResult("", map_url, [], None)

    # Sort candidates by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Filter to qualified candidates (score >= 40)
    top_candidates = [c for c in candidates if c[0] >= 40]
    if not top_candidates:
        top_candidates = [candidates[0]]

    # Take top 1 or 2 distinct candidates
    primary_cand = top_candidates[0]
    selected = [primary_cand]
    if len(top_candidates) > 1:
        sec = top_candidates[1]
        if sec[0] >= 65:
            p_id = primary_cand[3].get('place_id') or primary_cand[3].get('facility_id')
            s_id = sec[3].get('place_id') or sec[3].get('facility_id')
            if p_id != s_id:
                selected.append(sec)

    context_blocks = []
    sources = []

    for cand_score, cand_type, cand_idx, cand_dict, src_str in selected:
        if cand_type == "campus":
            pid = cand_dict.get('place_id', '')
            pname = cand_dict.get('place_name', '')
            cat = cand_dict.get('category', '')
            zone = cand_dict.get('zone', '')
            landmark = cand_dict.get('landmark', '')
            desc = cand_dict.get('description', '')
            block = (
                f"Place ID: {pid}\n"
                f"Place Name: {pname}\n"
                f"Category: {cat}\n"
                f"Campus Zone: {zone}\n"
                f"Landmark Reference: {landmark}\n"
                f"Description: {desc}\n"
                f"[Source: {src_str}]"
            )
            context_blocks.append(block)
            sources.append(src_str)
        else: # facility
            fid = cand_dict.get('facility_id', '')
            fname = cand_dict.get('facility_name', '')
            fcat = cand_dict.get('category', '')
            fbldg = cand_dict.get('building', '')
            ffloor = cand_dict.get('floor', '')
            floc = cand_dict.get('location', '')
            fdesc = cand_dict.get('description', '')
            fcap = cand_dict.get('capacity', '')
            fstatus = cand_dict.get('status', '')
            famen = cand_dict.get('facilities', '')

            bldg_line = f"Building / Block: {fbldg}{' (' + ffloor + ')' if ffloor else ''}\n" if fbldg or ffloor else ""
            cap_line = f"Capacity: {fcap}\n" if fcap else ""
            status_line = f"Status: {fstatus}\n" if fstatus else ""

            block = (
                f"Facility ID: {fid}\n"
                f"Facility Name: {fname}\n"
                f"Category: {fcat}\n"
                f"{bldg_line}"
                f"Location / Landmark: {floc}\n"
                f"Description: {fdesc}\n"
                f"{cap_line}"
                f"{status_line}"
                f"Amenities & Equipment: {famen}\n"
                f"[Source: {src_str}]"
            )
            context_blocks.append(block)
            sources.append(src_str)

    # Authoritative map image resolution based on the top matched entity
    top_dict = primary_cand[3]
    map_filename = resolve_entity_map_image(top_dict)
    map_url = f"/static/navigation_maps/{map_filename}"

    location_data = None
    if primary_cand[1] == "campus":
        lat_val = top_dict.get('latitude')
        lng_val = top_dict.get('longitude')
        try:
            lat_f = float(lat_val) if lat_val is not None and str(lat_val).strip() != '' else None
        except (ValueError, TypeError):
            lat_f = None
        try:
            lng_f = float(lng_val) if lng_val is not None and str(lng_val).strip() != '' else None
        except (ValueError, TypeError):
            lng_f = None

        location_data = {
            "id": str(top_dict.get('place_id', '')),
            "location_id": str(top_dict.get('place_id', '')),
            "name": str(top_dict.get('place_name', '')),
            "latitude": lat_f,
            "longitude": lng_f,
            "building": str(top_dict.get('zone', '')),
            "landmark": str(top_dict.get('landmark', '')),
            "zone": str(top_dict.get('zone', '')),
            "description": str(top_dict.get('description', '')),
            "image_url": map_url
        }
    else: # facility
        fid = str(top_dict.get('facility_id', ''))
        fname = str(top_dict.get('facility_name', ''))
        fbldg = str(top_dict.get('building', ''))
        floc = str(top_dict.get('location', ''))

        lat_f = 22.470850
        lng_f = 73.076780
        if "library" in fname.lower() or "reading room" in fname.lower():
            lat_f = 22.470980
            lng_f = 73.076890
        elif "canteen" in fname.lower():
            lat_f = 22.470720
            lng_f = 73.077150
        elif "sports" in fname.lower():
            lat_f = 22.470120
            lng_f = 73.077850

        location_data = {
            "id": fid,
            "location_id": fid,
            "name": fname,
            "latitude": lat_f,
            "longitude": lng_f,
            "building": fbldg or "Administration Block",
            "landmark": floc or "Central Campus",
            "zone": "Central Campus",
            "description": str(top_dict.get('description', '')),
            "image_url": map_url
        }

    return NavResult("\n\n---\n\n".join(context_blocks), map_url, sources, location_data)


def process_subject_context(query: str, user_profile: dict = None) -> Tuple[str, List[str]]:
    """
    Resolves academic subjects, course codes, and curriculum from subject.csv / subjects.csv.
    """
    clean_q = query.strip().lower()
    user_profile = user_profile or {}
    prof_dept = user_profile.get("department") or ""
    prof_sem = str(user_profile.get("semester") or "")

    df = get_cached_dataframe("subjects.csv")
    if df is None or df.empty:
        df = get_cached_dataframe("subject.csv")
    if df is None or df.empty:
        return "STATUS: NO_SUBJECTS_FOUND", []

    # Extract requested semester from query
    sem_m = re.search(r'\b(?:sem|semester)\s*([1-8])\b', clean_q)
    target_sem = sem_m.group(1) if sem_m else (prof_sem if prof_sem else None)

    # Extract department from query
    dept_keywords = {
        "computer": "Computer Engineering",
        "information technology": "Information Technology",
        "it": "Information Technology",
        "civil": "Civil Engineering",
        "mechanical": "Mechanical Engineering",
        "electrical": "Electrical Engineering",
        "electronics": "Electronics & Communication",
        "ec": "Electronics & Communication",
        "data science": "Data Science",
        "ai & ml": "Artificial Intelligence & Machine Learning",
        "artificial intelligence": "Artificial Intelligence & Machine Learning",
        "mca": "Computer Applications",
        "bca": "Computer Applications",
        "automobile": "Automobile Engineering"
    }

    target_dept = None
    for k, v in dept_keywords.items():
        if re.search(r'\b' + re.escape(k) + r'\b', clean_q):
            target_dept = v
            break
    if not target_dept and prof_dept:
        target_dept = prof_dept

    matched_df = df.copy()
    if target_dept:
        matched_df = matched_df[matched_df['department'].str.lower().str.contains(target_dept.lower(), na=False)]
    if target_sem:
        matched_df = matched_df[matched_df['semester'].astype(str) == str(target_sem)]

    if matched_df.empty:
        matched_df = df.head(10)

    context_lines = [f"--- ACADEMIC SUBJECTS ({target_dept or 'All Departments'}, Sem {target_sem or 'All'}) ---"]
    sources = []
    for idx, row in matched_df.head(15).iterrows():
        s_name = row.get('subject_name', '')
        prog = row.get('program', '')
        dept = row.get('department', '')
        sem = row.get('semester', '')
        yr = row.get('year', '')
        line = f"* Subject: {s_name} | Program: {prog} | Department: {dept} | Semester: {sem} | Year: {yr} | [Source: subject.csv (Row {idx + 1})]"
        context_lines.append(line)
        sources.append(f"subject.csv (Row {idx + 1})")

    return "\n".join(context_lines), sources