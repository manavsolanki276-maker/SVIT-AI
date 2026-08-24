"""
navigation_config.py
Master configuration for SVIT Campus Navigation Hierarchy.
"""

# Floor name mapping
FLOOR_NAMES = {
    "underground": "Underground Floor (Labs)",
    "ground": "Ground Floor",
    "first": "First Floor",
    "second": "Second Floor",
    "third": "Third Floor"
}

# Standard 5-Floor Academic Building Layout Template
STANDARD_ACADEMIC_FLOORS = {
    "underground": ["L1", "L2", "L3", "L4", "L5"],
    "ground": [
        "department office", "office", "faculty staff room", "faculty room", 
        "faculty cabin", "staff room", "hod cabin", "hod room", "lab"
    ],
    "first": [201, 202, 203, 204, 205],
    "second": [301, 302, 303, 304, 305],
    "third": [401, 402, 403, 404, 405]
}

# Master Department and Building Configuration
NAVIGATION = {
    "diploma": {
        "display_name": "Diploma Building",
        "building": "Diploma Building (Blocks A–G)",
        "zone": "Near Diploma Canteen and Architecture Block",
        "image": "diploma dep.jpeg",
        "aliases": ["diploma", "diploma department", "diploma block", "diploma building", "polytechnic"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "computer engineering": {
        "display_name": "Computer Engineering Department",
        "building": "Computer Engineering Block",
        "zone": "North Wing, Near Central Garden",
        "image": "Computer dep.jpeg",
        "aliases": ["computer engineering", "computer department", "computer", "ce", "comp"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "information technology": {
        "display_name": "Information Technology Department",
        "building": "Information Technology Block",
        "zone": "North-East Wing, Adjacent to Computer Block",
        "image": "IT dep.jpeg",
        "aliases": ["information technology", "it department", "it block", "it"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "mechanical engineering": {
        "display_name": "Mechanical Engineering Department",
        "building": "Mechanical Engineering Block",
        "zone": "West Wing, Near Workshop",
        "image": "Mechanical dep.jpeg",
        "aliases": ["mechanical engineering", "mechanical department", "mechanical", "mech"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "civil engineering": {
        "display_name": "Civil Engineering Department",
        "building": "Civil Engineering Block",
        "zone": "North-West Wing, Opposite Computer Block",
        "image": "Civil dep.jpeg",
        "aliases": ["civil engineering", "civil department", "civil"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "electrical engineering": {
        "display_name": "Electrical Engineering Department",
        "building": "Electrical Engineering Block",
        "zone": "South-West Wing, Near Mechanical Block",
        "image": "Electrical dep.jpeg",
        "aliases": ["electrical engineering", "electrical department", "electrical", "ee"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "electronics & communication": {
        "display_name": "Electronics & Communication Department",
        "building": "Electronics & Communication Block",
        "zone": "East Wing, Near IT Block",
        "image": "E&C dep.jpeg",
        "aliases": ["electronics & communication", "electronics and communication", "e&c", "ec", "electronics", "electronics engineering"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "aeronautical engineering": {
        "display_name": "Aeronautical Engineering Department",
        "building": "Aeronautical Engineering Block",
        "zone": "Engineering Complex",
        "image": "Aero dep.jpeg",
        "aliases": ["aeronautical engineering", "aeronautical department", "aero department", "aero", "aeronautical"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "mca & bca": {
        "display_name": "MCA & BCA Department",
        "building": "LCMCA Block",
        "zone": "Academic Complex",
        "image": "MCA&BCA.jpeg",
        "aliases": ["mca & bca", "mca and bca", "mca", "bca", "computer applications"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "architecture": {
        "display_name": "Architecture Department",
        "building": "Architecture Block",
        "zone": "South-East Wing, Near Diploma Canteen",
        "image": "SVIT with all dep.jpeg",
        "aliases": ["architecture", "b.arch", "arch"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "admin": {
        "display_name": "Administration Building",
        "image": "Admin dep.jpeg",
        "aliases": ["admin", "administration", "admin block", "admin building"],
        "facilities": {
            "central library": {"floor": "Ground / First Floor", "aliases": ["library", "central library", "librari"]},
            "reading room": {"floor": "First Floor", "aliases": ["reading room", "study room"]},
            "book bank": {"floor": "Ground Floor", "aliases": ["book bank"]},
            "indoor sports": {"floor": "Ground Floor", "aliases": ["indoor sports", "indoor sports room", "sports room"]},
            "girls common room": {"floor": "Ground Floor", "aliases": ["girls room", "girls common room", "girls rest room"]},
            "principal office": {"floor": "Ground Floor", "aliases": ["principal office", "principal cabin"]},
            "accounts office": {"floor": "Ground Floor", "aliases": ["accounts office", "accounts section", "fee counter"]},
            "examination cell": {"floor": "Ground Floor", "aliases": ["examination cell", "exam cell", "exam section"]}
        }
    },
    "sports court": {
        "display_name": "Outdoor Sports Complex & Pavilion",
        "image": "Sports court.png",
        "aliases": [
            "sports court", "sports ground", "outdoor sports", "pavilion", 
            "pavellion", "pavelion", "pavillion", "pavellinon", "playground", 
            "cricket ground", "basketball court", "volleyball court", "ground"
        ]
    },
    "canteen": {
        "display_name": "Central Canteen",
        "image": "SVIT Canteen loc.png",
        "aliases": ["canteen", "central canteen", "food court", "mess"]
    },
    "stationary": {
        "display_name": "Stationary Shop",
        "image": "Stationarys.png",
        "aliases": ["stationary", "stationery", "xerox shop", "print shop"]
    },
    "bus stop": {
        "display_name": "Campus Bus Stop",
        "image": "Bus stop.png",
        "aliases": ["bus stop", "bus stand", "transport hub", "bus parking"]
    }
}

# Flat Key-to-Image Mapping Dictionary for RAG Pipeline Fallback Resolvers
MAP_LOOKUP = {
    # Pavilion & Sports Ground Variants
    "pavilion": "Sports court.png",
    "pavellion": "Sports court.png",
    "pavelion": "Sports court.png",
    "pavillion": "Sports court.png",
    "pavellinon": "Sports court.png",
    "sports court": "Sports court.png",
    "sports ground": "Sports court.png",
    "outdoor sports": "Sports court.png",
    "cricket ground": "Sports court.png",
    "basketball court": "Sports court.png",
    "volleyball court": "Sports court.png",
    
    # Department Buildings
    "diploma": "diploma dep.jpeg",
    "computer": "Computer dep.jpeg",
    "computer engineering": "Computer dep.jpeg",
    "it": "IT dep.jpeg",
    "information technology": "IT dep.jpeg",
    "mechanical": "Mechanical dep.jpeg",
    "civil": "Civil dep.jpeg",
    "electrical": "Electrical dep.jpeg",
    "e&c": "E&C dep.jpeg",
    "ec": "E&C dep.jpeg",
    "aero": "Aero dep.jpeg",
    "aeronautical": "Aero dep.jpeg",
    "mca": "MCA&BCA.jpeg",
    "bca": "MCA&BCA.jpeg",
    "architecture": "SVIT with all dep.jpeg",
    
    # Campus Facilities
    "admin": "Admin dep.jpeg",
    "library": "Admin dep.jpeg",
    "canteen": "SVIT Canteen loc.png",
    "stationary": "Stationarys.png",
    "stationery": "Stationarys.png",
    "bus stop": "Bus stop.png"
}