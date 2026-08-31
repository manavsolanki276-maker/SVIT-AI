"""
navigation.py
Location Resolution Engine for SVIT AI Assistant.
Integrates real campus landmark records from campus_info.csv with departmental floor maps.
"""

import re
from typing import Optional, Dict, Any
from app.ai.navigation_config import NAVIGATION, FLOOR_NAMES

def find_location(query: str) -> Optional[Dict[str, Any]]:
    """
    Parses a user natural language query and resolves specific spatial locations.
    Returns structured location metadata or None if no location is resolved.
    """
    clean_query = query.lower().strip()

    # Define explicit navigation intent keywords (English + Hinglish)
    nav_intent_keywords = [
        # English Intent Keywords
        "where", "location", "reach", "map", "direction", "directions", 
        "way", "route", "locate", "find", "building", "block", "take me",
        "how to go", "how to reach", "navigate", "visit", "go to", "situated",
        
        # Hinglish / Hindi Intent Keywords
        "kaha", "kahan", "kidhar", "kaha hai", "kahan hai", "kidhar hai", 
        "kaha pe hai", "kaise jaye", "kaise jau", "rasta", "kaha par hai"
    ]

    has_nav_intent = any(re.search(r'\b' + re.escape(k) + r'\b', clean_query) for k in nav_intent_keywords)

    # -------------------------------------------------------------
    # STEP 0: Check Admin Sub-Facilities (Library, Reading Room, Offices, etc.)
    # -------------------------------------------------------------
    admin_info = NAVIGATION.get("admin", {})
    admin_facilities = admin_info.get("facilities", {})
    for fac_key, fac_data in admin_facilities.items():
        for alias in fac_data.get("aliases", []):
            if re.search(r'\b' + re.escape(alias) + r'\b', clean_query):
                fac_name = fac_key.title()
                fac_lat = fac_data.get("latitude", admin_info.get("latitude"))
                fac_lng = fac_data.get("longitude", admin_info.get("longitude"))
                fac_floor = fac_data.get("floor", "Administration Building")
                return {
                    "id": admin_info.get("id", "P002"),
                    "location_id": admin_info.get("id", "P002"),
                    "name": fac_name,
                    "latitude": fac_lat,
                    "longitude": fac_lng,
                    "building": "Administration Building",
                    "zone": "Center Campus",
                    "floor": fac_floor,
                    "room": fac_name,
                    "image": admin_info.get("image", "Admin dep.jpeg"),
                    "formatted_text": (
                        f"📍 **{fac_name}**\n\n"
                        f"🏢 **Building:** Administration Building\n"
                        f"📌 **Floor / Location:** {fac_floor} (Center Campus)\n\n"
                        f"Please follow the highlighted building location on the map below."
                    )
                }

    # -------------------------------------------------------------
    # STEP 1: Check Standalone Amenities (Canteen, Sports Ground, Bus Stop, etc.)
    # -------------------------------------------------------------
    standalone_keys = ["canteen", "sports court", "stationary", "bus stop", "admin"]
    for key in standalone_keys:
        item_data = NAVIGATION.get(key)
        if not item_data:
            continue
        for alias in item_data.get("aliases", []):
            if re.search(r'\b' + re.escape(alias) + r'\b', clean_query):
                item_name = item_data.get("display_name", key.title())
                item_lat = item_data.get("latitude")
                item_lng = item_data.get("longitude")
                item_img = item_data.get("image")
                item_id = item_data.get("id", "CAMPUS_LOC")
                return {
                    "id": item_id,
                    "location_id": item_id,
                    "name": item_name,
                    "latitude": item_lat,
                    "longitude": item_lng,
                    "building": item_name,
                    "zone": "Campus Landmark",
                    "floor": "Ground Level",
                    "room": item_name,
                    "image": item_img,
                    "formatted_text": (
                        f"📍 **{item_name}**\n\n"
                        f"🏢 **Location:** SVIT Vasad Campus\n\n"
                        f"Please follow the highlighted location on the map below."
                    )
                }

    # -------------------------------------------------------------
    # STEP 2: Check Department Context from Query
    # -------------------------------------------------------------
    matched_dept_key = None
    for dept_key, dept_data in NAVIGATION.items():
        if "floors" not in dept_data:
            continue
        for alias in dept_data["aliases"]:
            if re.search(r'\b' + re.escape(alias) + r'\b', clean_query):
                matched_dept_key = dept_key
                break
        if matched_dept_key:
            break

    # -------------------------------------------------------------
    # STEP 3: Extract Room / Lab Identifier using Pattern Matching
    # -------------------------------------------------------------
    lab_match = re.search(r'\b(?:lab\s*)?l([1-5])\b', clean_query)
    room_match = re.search(r'\b(?:room\s*)?([2-4]0[1-5])\b', clean_query)

    # -------------------------------------------------------------
    # STEP 4: Resolve Location via Department & Identified Room
    # -------------------------------------------------------------
    if matched_dept_key:
        dept_info = NAVIGATION[matched_dept_key]
        dept_name = dept_info["display_name"]
        dept_image = dept_info["image"]
        dept_building = dept_info.get("building", dept_name)
        dept_zone = dept_info.get("zone", "Main Academic Block")
        dept_id = dept_info.get("id", "CAMPUS_LOC")
        dept_lat = dept_info.get("latitude")
        dept_lng = dept_info.get("longitude")
        floors = dept_info.get("floors", {})

        # Case A: Underground Lab
        if lab_match:
            lab_code = f"L{lab_match.group(1)}"
            return {
                "id": dept_id,
                "location_id": dept_id,
                "name": f"{dept_name} - Lab {lab_code}",
                "latitude": dept_lat,
                "longitude": dept_lng,
                "building": dept_building,
                "zone": dept_zone,
                "department": dept_name,
                "floor": FLOOR_NAMES["underground"],
                "room": f"Lab {lab_code}",
                "image": dept_image,
                "formatted_text": (
                    f"📍 **{dept_name}**\n\n"
                    f"🏢 **Building:** {dept_building}\n"
                    f"📌 **Room / Lab:** Lab {lab_code} (Located on the **{FLOOR_NAMES['underground']}**)\n\n"
                    f"Please follow the highlighted building location on the map below."
                )
            }

        # Case B: Classroom (200, 300, 400 series)
        if room_match:
            room_num = int(room_match.group(1))
            floor_key = "first" if 201 <= room_num <= 205 else ("second" if 301 <= room_num <= 305 else "third")
            return {
                "id": dept_id,
                "location_id": dept_id,
                "name": f"{dept_name} - Room {room_num}",
                "latitude": dept_lat,
                "longitude": dept_lng,
                "building": dept_building,
                "zone": dept_zone,
                "department": dept_name,
                "floor": FLOOR_NAMES[floor_key],
                "room": f"Room {room_num}",
                "image": dept_image,
                "formatted_text": (
                    f"📍 **{dept_name}**\n\n"
                    f"🏢 **Building:** {dept_building}\n"
                    f"📌 **Classroom:** Room {room_num} (Located on the **{FLOOR_NAMES[floor_key]}**)\n\n"
                    f"Please follow the highlighted building location on the map below."
                )
            }

        # Case C: Ground Floor Offices / Cabins
        for ground_term in floors.get("ground", []):
            if re.search(r'\b' + re.escape(ground_term) + r'\b', clean_query):
                return {
                    "id": dept_id,
                    "location_id": dept_id,
                    "name": f"{dept_name} - {ground_term.title()}",
                    "latitude": dept_lat,
                    "longitude": dept_lng,
                    "building": dept_building,
                    "zone": dept_zone,
                    "department": dept_name,
                    "floor": FLOOR_NAMES["ground"],
                    "room": ground_term.title(),
                    "image": dept_image,
                    "formatted_text": (
                        f"📍 **{dept_name}**\n\n"
                        f"🏢 **Building:** {dept_building}\n"
                        f"📌 **Location:** The **{ground_term.title()}** is located on the **{FLOOR_NAMES['ground']}** ({dept_zone}).\n\n"
                        f"Please follow the highlighted building location on the map below."
                    )
                }

        # Case D: Department Building Query (matches if nav intent exists or question asks about the department/block)
        if has_nav_intent or any(k in clean_query for k in ["block", "building", "dept", "department", "where is", "location of"]):
            return {
                "id": dept_id,
                "location_id": dept_id,
                "name": dept_name,
                "latitude": dept_lat,
                "longitude": dept_lng,
                "building": dept_building,
                "zone": dept_zone,
                "department": dept_name,
                "floor": "Entire Building",
                "room": dept_name,
                "image": dept_image,
                "formatted_text": (
                    f"📍 **{dept_name}**\n\n"
                    f"🏢 **Building:** {dept_building}\n"
                    f"📌 **Location:** {dept_zone}\n\n"
                    f"Please follow the highlighted building location on the map below."
                )
            }

    # -------------------------------------------------------------
    # STEP 5: Unattached Room Number Fallback (e.g., "Where is 202?")
    # -------------------------------------------------------------
    if room_match:
        room_num = int(room_match.group(1))
        floor_key = "first" if 201 <= room_num <= 205 else ("second" if 301 <= room_num <= 305 else "third")
        return {
            "id": "CAMPUS_ROOM",
            "location_id": "CAMPUS_ROOM",
            "name": f"Room {room_num}",
            "latitude": 22.471410,
            "longitude": 73.077220,
            "department": "Academic Block",
            "floor": FLOOR_NAMES[floor_key],
            "room": f"Room {room_num}",
            "image": "SVIT with all dep.jpeg",
            "formatted_text": f"📍 **Room {room_num}** is located on the **{FLOOR_NAMES[floor_key]}** of the respective academic department block."
        }

    # -------------------------------------------------------------
    # STEP 5.5: Room Code Pattern Match (e.g., "AR-101", "CO-203", "ME-105")
    # -------------------------------------------------------------
    room_code_match = re.search(r'\b([a-z]{2,4})[-.]?(\d{2,3})\b', clean_query)
    if room_code_match:
        code_prefix = room_code_match.group(1).upper()
        code_number = room_code_match.group(2)
        room_code_full = f"{code_prefix}-{code_number}"
        room_result = _query_room_code_fallback(room_code_full, clean_query)
        if room_result:
            return room_result

    # -------------------------------------------------------------
    # STEP 6: Data-Driven Fallback from campus_info.csv & facilities.csv
    # -------------------------------------------------------------
    if has_nav_intent:
        campus_result = _query_campus_data_fallback(clean_query)
        if campus_result:
            return campus_result

    return None


def _query_room_code_fallback(room_code: str, clean_query: str) -> Optional[Dict[str, Any]]:
    """
    Resolves specific room codes (e.g., "AR-101", "CO-203") against
    rooms_facilities.csv (admin-managed dataset). Returns structured
    navigation result with department info, or None.
    """
    try:
        from app.ai.data_processor import get_cached_dataframe
    except ImportError:
        return None

    try:
        df_rooms = get_cached_dataframe("rooms_facilities.csv")
        if df_rooms is None or df_rooms.empty:
            return None

        # Find the exact room code in the dataset
        room_col = 'room_name' if 'room_name' in df_rooms.columns else None
        if not room_col:
            return None

        matched = df_rooms[df_rooms[room_col].str.upper() == room_code.upper()]
        if matched.empty:
            # Try partial match (e.g., user typed "AR101" without dash)
            clean_code = room_code.replace('-', '').replace('.', '').upper()
            matched = df_rooms[
                df_rooms[room_col].str.replace('-', '').str.replace('.', '').str.upper() == clean_code
            ]

        if matched.empty:
            return None

        row = matched.iloc[0]
        dept = str(row.get('department', '')).strip() or 'SVIT Campus'
        building = str(row.get('building', '')).strip() or ''
        floor = str(row.get('floor', '')).strip() or ''
        room_type = str(row.get('room_type', '')).strip() or ''
        room_status = str(row.get('status', '')).strip() or 'Active'
        display_name = str(row.get('room_name', '')).strip() or room_code

        # Determine map image based on department prefix
        dept_lower = dept.lower()
        code_lower = room_code[:2].lower()
        map_images = {
            'ar': 'Computer dep.jpeg',   # AI & Robotics / AI & ML
            'au': 'Computer dep.jpeg',   # Automobile Engineering
            'ci': 'Civil dep.jpeg',      # Civil Engineering
            'co': 'Computer dep.jpeg',   # Computer Engineering
            'ee': 'Electrical dep.jpeg', # Electrical Engineering
            'ec': 'E&C dep.jpeg',        # Electronics & Communication
            'it': 'IT dep.jpeg',         # Information Technology
            'me': 'Mechanical dep.jpeg', # Mechanical Engineering
            'in': 'IT dep.jpeg',         # Information Technology
            'mc': 'MCA&BCA.jpeg',        # MCA / BCA
            'bc': 'MCA&BCA.jpeg',        # BCA
        }
        image = map_images.get(code_lower, 'SVIT with all dep.jpeg')

        # Also resolve from department name for robustness
        if 'artificial intelligence' in dept_lower or 'machine learning' in dept_lower:
            image = 'Computer dep.jpeg'
        elif 'civil' in dept_lower:
            image = 'Civil dep.jpeg'
        elif 'mechanical' in dept_lower:
            image = 'Mechanical dep.jpeg'
        elif 'electrical' in dept_lower:
            image = 'Electrical dep.jpeg'
        elif 'electronics' in dept_lower or 'communication' in dept_lower:
            image = 'E&C dep.jpeg'
        elif 'computer' in dept_lower:
            image = 'Computer dep.jpeg'
        elif 'information technology' in dept_lower or 'it' == dept_lower.strip():
            image = 'IT dep.jpeg'
        elif 'automobile' in dept_lower:
            image = 'Computer dep.jpeg'

        # Build location text
        loc_text = f"**{display_name}**"
        loc_text += f" belongs to the **{dept}" 
        if building:
            loc_text += f", located in the **{building}**"
        loc_text += "."

        if floor:
            loc_text += f"\n\n🏢 **Floor:** {floor}"

        if room_type:
            loc_text += f"\n📋 **Type:** {room_type}"

        loc_text += f"\n✅ **Status:** {room_status}"
        loc_text += "\n\nPlease follow the highlighted building location on the map below."

        return {
            "department": dept,
            "floor": floor or "Campus Level",
            "room": display_name,
            "image": image,
            "formatted_text": f"📍 **{display_name}**\n\n{loc_text}"
        }

    except Exception as e:
        print(f"[Navigation] rooms_facilities.csv room code lookup error: {e}")

    return None


def _query_campus_data_fallback(clean_query: str) -> Optional[Dict[str, Any]]:
    """
    Queries campus_info.csv and facilities.csv (admin-managed datasets) as a
    fallback when the hardcoded NAVIGATION dictionary has no match.
    Returns a structured navigation result or None.
    """
    try:
        from app.ai.data_processor import get_cached_dataframe
    except ImportError:
        return None

    # --- Query facilities.csv first (higher specificity for named rooms/cells) ---
    try:
        df_fac = get_cached_dataframe("facilities.csv")
        if df_fac is not None and not df_fac.empty:
            best_facility = None
            best_match_count = 0
            best_total_words = 0
            for idx, row in df_fac.iterrows():
                fname = str(row.get('facility_name', '')).strip().lower()
                fname_words = [w for w in fname.split() if len(w) > 2]
                matching_words = [w for w in fname_words if re.search(r'\b' + re.escape(w) + r'\b', clean_query)]
                # Require at least half of significant words to match
                if fname_words and len(matching_words) >= max(1, (len(fname_words) + 1) // 2):
                    # Select the best match: more matching words is better;
                    # tie-break by higher match ratio (precision over recall)
                    if (len(matching_words) > best_match_count or
                        (len(matching_words) == best_match_count and
                         len(matching_words) / len(fname_words) > best_match_count / max(best_total_words, 1))):
                        best_facility = row
                        best_match_count = len(matching_words)
                        best_total_words = len(fname_words)

            if best_facility is not None:
                row = best_facility
                building = str(row.get('building', '')).strip() or "SVIT Campus"
                floor_info = str(row.get('floor', '')).strip() or "Campus Level"
                location = str(row.get('location', '')).strip()
                description = str(row.get('description', '')).strip()
                display_name = str(row.get('facility_name', '')).strip()

                building_lower = building.lower()
                if any(k in building_lower for k in ["admin", "administration"]):
                    image = "Admin dep.jpeg"
                elif any(k in building_lower for k in ["computer", "academic block"]):
                    image = "Computer dep.jpeg"
                elif "sports" in building_lower or "gym" in building_lower:
                    image = "Sports court.png"
                elif "food" in building_lower or "canteen" in building_lower:
                    image = "SVIT Canteen loc.png"
                elif "entry" in building_lower or "gate" in building_lower:
                    image = "SVIT with all dep.jpeg"
                elif "central" in building_lower:
                    image = "Admin dep.jpeg"
                else:
                    image = "SVIT with all dep.jpeg"

                loc_text = f"**{display_name}**"
                if floor_info and floor_info.lower() not in ("campus level", ""):
                    loc_text += f" is located on the **{floor_info}" 
                    if building and building.lower() not in ("svit campus", ""):
                        loc_text += f" of **{building}**"
                    loc_text += "."
                else:
                    if building and building.lower() not in ("svit campus", ""):
                        loc_text += f" is located in **{building}**."
                    else:
                        loc_text += " is located on the campus."

                if location and location.lower() not in ("svit campus", ""):
                    loc_text += f"\n\n📌 **Nearest Landmark:** {location}"

                if description and len(description) > 10:
                    loc_text += f"\n\n{description}"

                loc_text += "\n\nPlease follow the highlighted location on the map below."

                return {
                    "department": display_name,
                    "floor": floor_info,
                    "room": display_name,
                    "image": image,
                    "formatted_text": f"📍 **{display_name}**\n\n{loc_text}"
                }
    except Exception as e:
        print(f"[Navigation] facilities.csv fallback error: {e}")

    # --- Query campus_info.csv for broader campus landmarks ---
    try:
        df_campus = get_cached_dataframe("campus_info.csv")
        if df_campus is not None and not df_campus.empty:
            for idx, row in df_campus.iterrows():
                pname = str(row.get('place_name', '')).strip().lower()
                pname_words = [w for w in pname.split() if len(w) > 2]
                if pname_words and sum(1 for w in pname_words if w in clean_query) >= max(1, len(pname_words) // 2):
                    category = str(row.get('category', '')).strip()
                    zone = str(row.get('zone', '')).strip()
                    landmark = str(row.get('landmark', '')).strip()
                    description = str(row.get('description', '')).strip()
                    display_name = str(row.get('place_name', '')).strip()

                    # Determine best map image
                    zone_lower = zone.lower()
                    cat_lower = category.lower()
                    if any(k in zone_lower for k in ["admin", "center", "academic"]):
                        image = "Admin dep.jpeg"
                    elif "north" in zone_lower or "computer" in zone_lower:
                        image = "Computer dep.jpeg"
                    elif "south" in zone_lower or "sport" in cat_lower:
                        image = "Sports court.png"
                    elif "transport" in cat_lower or "bus" in pname.lower():
                        image = "Bus stop.png"
                    elif "entrance" in cat_lower or "gate" in pname.lower() or "entry" in pname.lower():
                        image = "SVIT with all dep.jpeg"
                    else:
                        image = "SVIT with all dep.jpeg"

                    loc_text = f"**{display_name}**"
                    if zone:
                        loc_text += f" is located in the **{zone}" 
                        if landmark:
                            loc_text += f", {landmark}"
                        loc_text += "."

                    if description:
                        loc_text += f"\n\n{description}"

                    loc_text += "\n\nPlease follow the highlighted location on the map below."

                    return {
                        "department": display_name,
                        "floor": zone or "Campus Level",
                        "room": display_name,
                        "image": image,
                        "formatted_text": f"📍 **{display_name}**\n\n{loc_text}"
                    }
    except Exception as e:
        print(f"[Navigation] campus_info.csv fallback error: {e}")

    return None