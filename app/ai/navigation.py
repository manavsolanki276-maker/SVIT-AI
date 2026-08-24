"""
navigation.py
Location Resolution Engine for SVIT AI Assistant.
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
    # STEP 1: Check Admin Facilities & Standalone Amenities First
    # -------------------------------------------------------------
    # Admin Block Facilities
    admin_facilities = NAVIGATION["admin"].get("facilities", {})
    for facility_name, meta in admin_facilities.items():
        for alias in meta["aliases"]:
            if re.search(r'\b' + re.escape(alias) + r'\b', clean_query):
                return {
                    "department": NAVIGATION["admin"]["display_name"],
                    "floor": meta["floor"],
                    "room": facility_name.title(),
                    "image": NAVIGATION["admin"]["image"],
                    "formatted_text": (
                        f"📍 **{NAVIGATION['admin']['display_name']}**\n\n"
                        f"**{facility_name.title()}** is located on the **{meta['floor']}** inside the Administration Building.\n\n"
                        f"Please follow the highlighted location on the map below."
                    )
                }

    # Standalone Campus Amenities (Sports, Canteen, Stationary, Bus Stop, etc.)
    # Trigger if user explicitly asks for location OR uses a clear amenity keyword
    for key, data in NAVIGATION.items():
        if key in ["admin"] or "floors" in data:
            continue
        for alias in data.get("aliases", []):
            if re.search(r'\b' + re.escape(alias) + r'\b', clean_query):
                # If query is about sports/pavilion/bus stop/stationary OR has general navigation intent
                if key != "canteen" or has_nav_intent:
                    return {
                        "department": data["display_name"],
                        "floor": "Campus Level",
                        "room": data["display_name"],
                        "image": data["image"],
                        "formatted_text": (
                            f"📍 **{data['display_name']}**\n\n"
                            f"🏢 **Area:** {data['display_name']}\n"
                            f"📌 **Location:** Main Campus Facilities Area\n\n"
                            f"Please follow the highlighted location on the map below."
                        )
                    }

    # -------------------------------------------------------------
    # STEP 2: Extract Department Context from Query
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
        floors = dept_info["floors"]

        # Case A: Underground Lab
        if lab_match:
            lab_code = f"L{lab_match.group(1)}"
            return {
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
        for ground_term in floors["ground"]:
            if re.search(r'\b' + re.escape(ground_term) + r'\b', clean_query):
                return {
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
        if has_nav_intent or any(k in clean_query for k in ["block", "building", "dept", "department", "office", "find", "where"]):
            return {
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
            "department": "Academic Block",
            "floor": FLOOR_NAMES[floor_key],
            "room": f"Room {room_num}",
            "image": "SVIT with all dep.jpeg",
            "formatted_text": f"📍 **Room {room_num}** is located on the **{FLOOR_NAMES[floor_key]}** of the respective academic department block."
        }

    return None