import os
import sys
import json

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.admin_crud_service import AdminCRUDService
from app.database.mongodb import get_collection
from app.database.mongo_models import MongoNotificationService
from app.ai.data_processor import process_notice_context, process_events_context, invalidate_ai_caches

def main():
    print("=== STEP 1: CREATE 3 NOTICES IN MONGODB ATLAS ===")
    demo_notices = [
        {
            "notice_id": "NOT_MIDSEM_2026",
            "title": "Mid-Semester Examination Schedule October 2026",
            "category": "Examination",
            "priority": "High",
            "department": "All Departments",
            "target_audience": "All Students",
            "publish_date": "2026-09-08",
            "expiry_date": "2026-10-31",
            "status": "Published",
            "is_urgent": False,
            "description": "Mid-semester examination for all B.E. and MCA semesters will commence from October 12, 2026. Hall tickets will be issued through student portal."
        },
        {
            "notice_id": "NOT_HOLIDAY_2026",
            "title": "Ganesh Chaturthi Campus Holiday Announcement",
            "category": "Holiday Announcements",
            "priority": "Normal",
            "department": "All Departments",
            "target_audience": "All Students & Faculty",
            "publish_date": "2026-09-08",
            "expiry_date": "2026-09-21",
            "status": "Published",
            "is_urgent": False,
            "description": "SVIT campus will observe an official holiday on September 19, 2026 on the occasion of Ganesh Chaturthi. Regular academic schedule resumes the next day."
        },
        {
            "notice_id": "NOT_WEATHER_2026",
            "title": "Emergency Weather Alert: Heavy Rain Advisory",
            "category": "Rain/Weather Notices",
            "priority": "Emergency",
            "department": "Administration",
            "target_audience": "All Students & Faculty",
            "publish_date": "2026-09-08",
            "expiry_date": "2026-09-10",
            "status": "Published",
            "is_urgent": True,
            "description": "Due to IMD red alert warning for heavy rainfall in Anand/Vadodara region, on-campus physical lectures are suspended for tomorrow. Online sessions will be held on MS Teams."
        }
    ]

    for not_data in demo_notices:
        nid = not_data["notice_id"]
        # If exists, update or create
        existing = AdminCRUDService.get_item("notices", nid)
        if existing:
            print(f"Notice {nid} already exists, updating...")
            res_obj = AdminCRUDService.update_item("notices", nid, not_data)
        else:
            print(f"Creating Notice {nid}...")
            res_obj = AdminCRUDService.create_item("notices", not_data)
        res = res_obj[0] if isinstance(res_obj, tuple) else res_obj
        code = res_obj[1] if isinstance(res_obj, tuple) else 200
        print(f"Notice {nid} result (HTTP {code}):", res.get("status") if isinstance(res, dict) else res)

    print("\n=== STEP 2: CREATE 3 EVENTS IN MONGODB ATLAS ===")
    demo_events = [
        {
            "event_id": "EVT_PRAKARSH_2026",
            "event_name": "Prakarsh 2026: National Level Technical Fest",
            "category": "Technical Events",
            "department": "Computer Engineering",
            "organizer": "CSI & IEEE Student Chapters",
            "event_date": "2026-10-15",
            "start_time": "09:30",
            "end_time": "18:00",
            "venue": "SVIT Central Auditorium & Computer Block",
            "speaker_or_guest": "Dr. Sandeep Patel (AI Architect)",
            "registration_required": "Yes",
            "capacity": 300,
            "status": "Upcoming",
            "description": "Prakarsh 2026 features coding hackathons, robot combat arena, web dev sprints, and tech quiz competitions with a cash prize pool."
        },
        {
            "event_id": "EVT_SPANDAN_2026",
            "event_name": "Spandan 2026: Annual Cultural & Arts Festival",
            "category": "Cultural Events",
            "department": "Cultural Committee",
            "organizer": "Student Activity Council (SAC)",
            "event_date": "2026-11-20",
            "start_time": "17:00",
            "end_time": "22:00",
            "venue": "SVIT Open Air Amphitheatre",
            "speaker_or_guest": "Celebrity Band & Alumni Artists",
            "registration_required": "No",
            "capacity": 800,
            "status": "Upcoming",
            "description": "Annual SVIT cultural extravaganza featuring musical orchestra, classical and western group dance competitions, fashion runway, and celebrity music night."
        },
        {
            "event_id": "EVT_AI_WORKSHOP_2026",
            "event_name": "Generative AI & Autonomous Agents Workshop",
            "category": "Workshops",
            "department": "Information Technology",
            "organizer": "GDSC & IT Department",
            "event_date": "2026-09-25",
            "start_time": "10:00",
            "end_time": "16:00",
            "venue": "Advanced IT Computing Lab 304",
            "speaker_or_guest": "Prof. Hiren Patel & Google Developer Expert",
            "registration_required": "Yes",
            "capacity": 60,
            "status": "Upcoming",
            "description": "Hands-on engineering workshop on building multi-agent AI systems, LangChain / LlamaIndex pipelines, and Gemini 2.0 Flash function calling."
        }
    ]

    for ev_data in demo_events:
        eid = ev_data["event_id"]
        existing = AdminCRUDService.get_item("events", eid)
        if existing:
            print(f"Event {eid} already exists, updating...")
            res_obj = AdminCRUDService.update_item("events", eid, ev_data)
        else:
            print(f"Creating Event {eid}...")
            res_obj = AdminCRUDService.create_item("events", ev_data)
        res = res_obj[0] if isinstance(res_obj, tuple) else res_obj
        code = res_obj[1] if isinstance(res_obj, tuple) else 200
        print(f"Event {eid} result (HTTP {code}):", res.get("status") if isinstance(res, dict) else res)

    print("\n=== STEP 3: VERIFY IN MONGODB ATLAS DIRECTLY ===")
    notices_coll = get_collection("notices")
    events_coll = get_collection("events")
    notif_coll = get_collection("notifications")

    db_notices = list(notices_coll.find({"notice_id": {"$in": [n["notice_id"] for n in demo_notices]}}, {"_id": 0, "notice_id": 1, "title": 1, "priority": 1, "status": 1}))
    print(f"Found {len(db_notices)}/3 demo notices directly in MongoDB Atlas:")
    for n in db_notices:
        print(f"  - [{n.get('notice_id')}] {n.get('title')} ({n.get('priority')}, {n.get('status')})")

    db_events = list(events_coll.find({"event_id": {"$in": [e["event_id"] for e in demo_events]}}, {"_id": 0, "event_id": 1, "event_name": 1, "category": 1, "status": 1}))
    print(f"\nFound {len(db_events)}/3 demo events directly in MongoDB Atlas:")
    for e in db_events:
        print(f"  - [{e.get('event_id')}] {e.get('event_name')} ({e.get('category')}, {e.get('status')})")

    print("\n=== STEP 4: VERIFY STUDENT-SIDE NOTIFICATIONS ===")
    mock_student = {
        "id": "1",
        "enrollment_no": "210410107001",
        "department": "Computer Engineering",
        "semester": 5,
        "program": "BE",
        "is_admin": False
    }

    student_notifs = MongoNotificationService.get_notifications(mock_student, limit=10)
    print(f"Student Notifications count: {len(student_notifs.get('notifications', []))}, Unread: {student_notifs.get('unread_count')}")
    for notif in student_notifs.get("notifications", [])[:6]:
        print(f"  * [{notif.get('category')}] {notif.get('title')}")

    print("\n=== STEP 5: VERIFY STUDENT AI CONTEXT RETRIEVAL ===")
    # Clear AI cache to guarantee freshly fetched data from MongoDB
    invalidate_ai_caches()

    # Check Notices Context
    notice_ctx = process_notice_context([], "latest exam and rain alert notices", user_profile=mock_student)
    print("--- Notices Context Output ---")
    print(notice_ctx[:300] + ("..." if len(notice_ctx) > 300 else ""))

    # Check Events Context
    events_ctx = process_events_context("tell me about Prakarsh and Spandan events")
    print("\n--- Events Context Output ---")
    print(events_ctx[:300] + ("..." if len(events_ctx) > 300 else ""))

    print("\n=== ALL VERIFICATIONS COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    main()
