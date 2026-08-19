# app/ai/config.py

INTENT_CONFIG = {
    "timetable": {
        "keywords": [
            "timetable", "time table", "timetabel", "time tabel", "tabel",
            "schedule", "class", "lecture", "timing", "slot", "period",
            "today's", "today", "tomorrow", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday"
        ],
        "sources": [("timetable.csv", 1.0), ("academics_faq.csv", 0.5), ("general_faq.csv", 0.2)]
    },
    "placement": {
        "keywords": ["placement", "drive", "package", "salary", "recruiter", "company", "internship", "career", "lpa", "job", "statistics", "stats", "hired"],
        "sources": [("placements.csv", 1.0), ("placement_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "faculty": {
        "keywords": ["faculty", "hod", "teacher", "professor", "sir", "madam", "head", "staff"],
        "sources": [("faculty.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "departments": {
        "keywords": ["department", "branch", "course", "program", "engineering", "diploma", "bca", "mca", "be", "me"],
        "sources": [("departments.csv", 1.0), ("academics_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "subjects": {
        "keywords": ["subject", "syllabus", "subject code", "curriculum", "python", "dbms", "java"],
        "sources": [("subjects.csv", 1.0), ("academics_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "notices": {
        "keywords": ["notice", "notification", "announcement", "circular", "holiday", "news"],
        "sources": [("notices.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "campus_info": {
        "keywords": ["where", "map", "building", "block", "lab", "canteen location", "parking", "gate", "ground"],
        "sources": [("campus_info.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "admissions": {
        "keywords": ["admission", "fees", "fee", "documents", "eligibility", "seat", "cutoff", "quota"],
        "sources": [("admissions_faq.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "transport": {
        "keywords": ["bus", "route", "transport", "commute", "pickup", "driver"],
        "sources": [("transport.csv", 1.0), ("transport_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "canteen": {
        "keywords": ["canteen", "food", "menu", "lunch", "tea", "snack", "breakfast", "price", "samosa", "thali", "coffee"],
        "sources": [("canteen.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "contact": {
        "keywords": ["contact", "phone", "email", "office", "admin", "number", "address", "location"],
        "sources": [("contact.csv", 1.0), ("general_faq.csv", 0.3)]
    },
    "library": {
        "keywords": ["library", "book", "issue", "fine", "author", "reading room", "journal"],
        "sources": [("library_books.csv", 1.0), ("library_faq.csv", 0.8), ("general_faq.csv", 0.3)]
    },
    "events": {
        "keywords": ["event", "workshop", "hackathon", "festival", "symposium", "techfest", "cultural"],
        "sources": [("events.csv", 1.0), ("general_faq.csv", 0.3)]
    }
}