# app/ai/config.py
"""
Configuration for Query Routing, Intent Recognition, and Page-Specific RAG Namespaces.
"""

INTENT_CONFIG = {
    "svit_info": {
        "keywords": [
            "svit", "vasad", "about svit", "patel kelavani mandal", "pkm", "trust",
            "established", "establishment", "affiliation", "affiliated", "aicte", "gtu",
            "history of svit", "campus overview", "principal", "dr d p soni", "governance",
            "accreditation", "dte", "infrastructure", "campus area", "mahisagar", "anand"
        ],
        "sources": [
            ("campus_info.csv", 1.0),
            ("contact.csv", 0.9),
            ("facilities.csv", 0.8),
            ("departments.csv", 0.7),
            ("general_faq.csv", 0.4)
        ]
    },
    "campus_info": {
        "keywords": [
            "where", "map", "building", "block", "lab", "location", "locate", "directions",
            "how to go", "how to reach", "navigate", "gate", "main gate", "entrance", "parking",
            "ground", "court", "auditorium", "seminar hall", "canteen location", "food court",
            "hostel", "landmark", "zone", "amphitheatre", "room", "cabin"
        ],
        "sources": [
            ("campus_info.csv", 1.0),
            ("facilities.csv", 0.95),
            ("departments.csv", 0.8),
            ("contact.csv", 0.7),
            ("general_faq.csv", 0.3)
        ]
    },
    "transport": {
        "keywords": [
            "bus", "route", "transport", "commute", "pickup", "driver", "bus pass", 
            "bus stop", "bus parking", "transport office", "transport coordinator", "bus timing"
        ],
        "sources": [
            ("transport.csv", 1.0),
            ("transport_faq.csv", 0.9),
            ("campus_info.csv", 0.7),
            ("general_faq.csv", 0.3)
        ]
    },
    "placement": {
        "keywords": [
            "placement", "drive", "package", "salary", "recruiter", "company", "internship",
            "career", "lpa", "job", "statistics", "stats", "hired", "t&p", "training & placement",
            "training and placement", "placement cell", "placement office"
        ],
        "sources": [
            ("placements.csv", 1.0),
            ("placement_faq.csv", 0.8),
            ("facilities.csv", 0.7),
            ("campus_info.csv", 0.6),
            ("general_faq.csv", 0.3)
        ]
    },
    "faculty": {
        "keywords": [
            "faculty", "hod", "teacher", "professor", "sir", "madam", "head", "staff",
            "who teaches", "faculty for", "professor for", "cabin", "faculty detail",
            "registrar", "student section"
        ],
        "sources": [
            ("faculty.csv", 1.0),
            ("departments.csv", 0.9),
            ("contact.csv", 0.7),
            ("general_faq.csv", 0.3)
        ]
    },
    "departments": {
        "keywords": [
            "department", "branch", "course", "program", "engineering", "diploma",
            "bca", "mca", "be", "me", "civil", "mechanical", "electrical", "computer",
            "information technology", "electronics", "aero", "automobile"
        ],
        "sources": [
            ("departments.csv", 1.0),
            ("campus_info.csv", 0.9),
            ("academics_faq.csv", 0.8),
            ("general_faq.csv", 0.3)
        ]
    },
    "subjects": {
        "keywords": [
            "subject", "syllabus", "subject code", "curriculum", "python", "dbms", "java",
            "subjects", "course code", "study material", "teaching scheme", "gtu syllabus",
            "credits", "academic scheme"
        ],
        "sources": [
            ("subject.csv", 1.0),
            ("subjects.csv", 1.0),
            ("academics_faq.csv", 0.8),
            ("general_faq.csv", 0.3)
        ]
    },
    "facilities": {
        "keywords": [
            "facility", "facilities", "amenity", "amenities", "medical", "first aid", "medical & first aid",
            "medical room", "first aid room", "health center", "dispensary", "gym", "gymnasium", 
            "girls room", "reading room", "amphitheatre", "food court", "water cooler", "atm"
        ],
        "sources": [
            ("facilities.csv", 1.0),
            ("campus_info.csv", 0.95),
            ("general_faq.csv", 0.3)
        ]
    },
    "rooms": {
        "keywords": [
            "room", "classroom", "lab room", "hall", "seminar hall", "tutorial room",
            "workshop", "ar-", "co-", "me-", "ci-", "el-", "in-"
        ],
        "sources": [
            ("rooms_facilities.csv", 1.0),
            ("campus_info.csv", 0.9),
            ("facilities.csv", 0.8),
            ("general_faq.csv", 0.3)
        ]
    },
    "notices": {
        "keywords": ["notice", "notification", "announcement", "circular", "holiday", "news", "exam form", "mid-term", "deadline", "fee date"],
        "sources": [("notices.csv", 1.0), ("notices_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "admissions": {
        "keywords": ["admission", "fees", "fee", "documents", "eligibility", "seat", "cutoff", "quota", "scholarship", "intake", "acpc", "merit"],
        "sources": [("admissions_faq.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "canteen": {
        "keywords": ["canteen", "food", "menu", "lunch", "tea", "snack", "breakfast", "price", "samosa", "thali", "coffee", "cafeteria", "diploma canteen"],
        "sources": [("canteen.csv", 1.0), ("canteen_faq.csv", 0.8), ("campus_info.csv", 0.7), ("general_faq.csv", 0.3)]
    },
    "contact": {
        "keywords": ["contact", "phone", "email", "office", "admin", "number", "address", "principal office", "accounts", "student section"],
        "sources": [("contact.csv", 1.0), ("campus_info.csv", 0.9), ("contact_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "events": {
        "keywords": ["event", "workshop", "hackathon", "festival", "symposium", "techfest", "cultural", "competition", "webinar"],
        "sources": [("events.csv", 1.0), ("events_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "timetable": {
        "keywords": [
            "timetable", "time table", "timetabel", "time tabel", "tabel",
            "schedule", "class", "lecture", "timing", "slot", "period",
            "today's", "today", "tomorrow", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday"
        ],
        "sources": [("timetable.csv", 1.0), ("academics_faq.csv", 0.5), ("general_faq.csv", 0.2)]
    }
}

# Module-to-Namespace Map for Page-Specific RAG Isolation
INTENT_TO_MODULE_MAP = {
    "svit_info": "svit_info",
    "campus_info": "svit_info",
    "admissions": "admission",
    "admission": "admission",
    "notices": "notices",
    "events": "events",
    "transport": "bus",
    "bus": "bus",
    "canteen": "canteen",
    "subjects": "syllabus",
    "syllabus": "syllabus",
    "faculty": "faculty",
}