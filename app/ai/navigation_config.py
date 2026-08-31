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
        "id": "P030",
        "display_name": "Diploma Building",
        "building": "Diploma Building (Blocks A–G)",
        "zone": "Near Diploma Canteen and Architecture Block",
        "latitude": 22.472250,
        "longitude": 73.078450,
        "image": "diploma dep.jpeg",
        "aliases": ["diploma", "diploma department", "diploma block", "diploma building", "polytechnic"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "computer engineering": {
        "id": "P003",
        "display_name": "Computer Engineering Department",
        "building": "Computer Engineering Block",
        "zone": "North Wing, Near Central Garden",
        "latitude": 22.471410,
        "longitude": 73.077220,
        "image": "Computer dep.jpeg",
        "aliases": ["computer engineering", "computer department", "computer", "ce", "comp"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "information technology": {
        "id": "P004",
        "display_name": "Information Technology Department",
        "building": "Information Technology Block",
        "zone": "North-East Wing, Adjacent to Computer Block",
        "latitude": 22.471550,
        "longitude": 73.077480,
        "image": "IT dep.jpeg",
        "aliases": ["information technology", "it department", "it block", "it"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "mechanical engineering": {
        "id": "P006",
        "display_name": "Mechanical Engineering Department",
        "building": "Mechanical Engineering Block",
        "zone": "West Wing, Near Workshop",
        "latitude": 22.470920,
        "longitude": 73.076350,
        "image": "Mechanical dep.jpeg",
        "aliases": ["mechanical engineering", "mechanical department", "mechanical", "mech"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "civil engineering": {
        "id": "P005",
        "display_name": "Civil Engineering Department",
        "building": "Civil Engineering Block",
        "zone": "North-West Wing, Opposite Computer Block",
        "latitude": 22.471280,
        "longitude": 73.076950,
        "image": "Civil dep.jpeg",
        "aliases": ["civil engineering", "civil department", "civil"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "electrical engineering": {
        "id": "P007",
        "display_name": "Electrical Engineering Department",
        "building": "Electrical Engineering Block",
        "zone": "South-West Wing, Near Mechanical Block",
        "latitude": 22.470650,
        "longitude": 73.076550,
        "image": "Electrical dep.jpeg",
        "aliases": ["electrical engineering", "electrical department", "electrical", "ee"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "electronics & communication": {
        "id": "P008",
        "display_name": "Electronics & Communication Department",
        "building": "Electronics & Communication Block",
        "zone": "East Wing, Near IT Block",
        "latitude": 22.471350,
        "longitude": 73.077650,
        "image": "E&C dep.jpeg",
        "aliases": ["electronics & communication", "electronics and communication", "e&c", "ec", "electronics", "electronics engineering"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "aeronautical engineering": {
        "id": "P008",
        "display_name": "Aeronautical Engineering Department",
        "building": "Aeronautical Engineering Block",
        "zone": "Engineering Complex",
        "latitude": 22.471150,
        "longitude": 73.076750,
        "image": "Aero dep.jpeg",
        "aliases": ["aeronautical engineering", "aeronautical department", "aero department", "aero", "aeronautical"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "mca & bca": {
        "id": "P011",
        "display_name": "MCA & BCA Department",
        "building": "LCMCA Block",
        "zone": "Academic Complex",
        "latitude": 22.471680,
        "longitude": 73.077110,
        "image": "MCA&BCA.jpeg",
        "aliases": ["mca & bca", "mca and bca", "mca", "bca", "computer applications"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "architecture": {
        "id": "P029",
        "display_name": "Architecture Department",
        "building": "Architecture Block",
        "zone": "South-East Wing, Near Diploma Canteen",
        "latitude": 22.471950,
        "longitude": 73.077920,
        "image": "SVIT with all dep.jpeg",
        "aliases": ["architecture", "b.arch", "arch"],
        "floors": STANDARD_ACADEMIC_FLOORS
    },
    "admin": {
        "id": "P002",
        "display_name": "Administration Building",
        "latitude": 22.470850,
        "longitude": 73.076780,
        "image": "Admin dep.jpeg",
        "aliases": ["admin", "administration", "admin block", "admin building"],
        "facilities": {
            "central library": {"floor": "Ground / First Floor", "latitude": 22.470980, "longitude": 73.076890, "aliases": ["library", "central library", "librari"]},
            "reading room": {"floor": "First Floor", "latitude": 22.470980, "longitude": 73.076890, "aliases": ["reading room", "study room"]},
            "book bank": {"floor": "Ground Floor", "latitude": 22.470980, "longitude": 73.076890, "aliases": ["book bank"]},
            "indoor sports": {"floor": "Ground Floor", "latitude": 22.470850, "longitude": 73.076780, "aliases": ["indoor sports", "indoor sports room", "sports room"]},
            "girls common room": {"floor": "Ground Floor", "latitude": 22.470850, "longitude": 73.076780, "aliases": ["girls room", "girls common room", "girls rest room"]},
            "principal office": {"floor": "Ground Floor", "latitude": 22.470850, "longitude": 73.076780, "aliases": ["principal office", "principal cabin"]},
            "accounts office": {"floor": "Ground Floor", "latitude": 22.470850, "longitude": 73.076780, "aliases": ["accounts office", "accounts section", "fee counter"]},
            "examination cell": {"floor": "Ground Floor", "latitude": 22.470850, "longitude": 73.076780, "aliases": ["examination cell", "exam cell", "exam section"]}
        }
    },
    "sports court": {
        "id": "P023",
        "display_name": "Outdoor Sports Complex & Pavilion",
        "latitude": 22.470120,
        "longitude": 73.077850,
        "image": "Sports court.png",
        "aliases": [
            "sports court", "sports ground", "outdoor sports", "pavilion", 
            "pavellion", "pavelion", "pavillion", "pavellinon", "playground", 
            "cricket ground", "basketball court", "volleyball court", "ground"
        ]
    },
    "canteen": {
        "id": "P027",
        "display_name": "Central Canteen",
        "latitude": 22.470720,
        "longitude": 73.077150,
        "image": "SVIT Canteen loc.png",
        "aliases": ["canteen", "central canteen", "food court", "mess"]
    },
    "stationary": {
        "id": "P039",
        "display_name": "Stationary Shop",
        "latitude": 22.471620,
        "longitude": 73.076450,
        "image": "Stationarys.png",
        "aliases": ["stationary", "stationery", "xerox shop", "print shop"]
    },
    "bus stop": {
        "id": "P025",
        "display_name": "Campus Bus Stop",
        "latitude": 22.471850,
        "longitude": 73.076320,
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