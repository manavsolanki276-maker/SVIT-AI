import unittest
import json
from app import create_app
from app.database.admin_crud_service import AdminCRUDService
from app.database.mongo_models import MongoNotificationService
from app.ai.data_processor import process_notice_context, process_events_context, invalidate_ai_caches

class TestStudentNoticeEventSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_create_notice_and_verify_student_notification(self):
        """Test notice creation by admin and instant delivery to student notifications."""
        test_nid = "SYNC_TEST_NOT_999"
        notice_data = {
            "notice_id": test_nid,
            "title": "Semester 5 Endsem Lab Exam Timetable Released",
            "category": "Examination",
            "priority": "High",
            "department": "All Departments",
            "target_audience": "All Students",
            "publish_date": "2026-09-08",
            "expiry_date": "2026-10-20",
            "status": "Published",
            "description": "The official lab exam schedule for 5th semester BE is now published."
        }

        # Create notice via Admin CRUD Service
        success, msg, item = AdminCRUDService.create_item("notices", notice_data)
        self.assertTrue(success, f"Failed to create notice: {msg}")

        # Check student notification retrieval for mock student
        mock_student = {
            "id": "1",
            "enrollment_no": "210410107001",
            "department": "Computer Engineering",
            "semester": 5,
            "program": "BE",
            "is_admin": False
        }

        notifs = MongoNotificationService.get_notifications(mock_student, limit=20)
        found = any(n.get("title") == "Semester 5 Endsem Lab Exam Timetable Released" for n in notifs.get("notifications", []))
        self.assertTrue(found, "Notice was not found in student notifications list")

        # Invalidate AI caches and test AI context retrieval
        invalidate_ai_caches()
        notice_ctx = process_notice_context([], "timetable and lab exam notice", user_profile=mock_student)
        self.assertIn("Semester 5 Endsem Lab Exam Timetable", notice_ctx)

        # Cleanup
        AdminCRUDService.delete_item("notices", test_nid)

    def test_02_create_event_and_verify_student_notification(self):
        """Test event creation by admin and instant delivery to student notifications."""
        test_eid = "SYNC_TEST_EVT_999"
        event_data = {
            "event_id": test_eid,
            "event_name": "SVIT Mega Roborace Championship 2026",
            "category": "Technical Events",
            "department": "Mechanical Engineering",
            "organizer": "Robotics Club SVIT",
            "event_date": "2026-10-28",
            "start_time": "10:00",
            "venue": "SVIT Campus Ground",
            "registration_required": "Yes",
            "status": "Upcoming",
            "description": "High-speed autonomous and RC roborace competition across obstacles."
        }

        # Create event via Admin CRUD Service
        success, msg, item = AdminCRUDService.create_item("events", event_data)
        self.assertTrue(success, f"Failed to create event: {msg}")

        # Check student notification
        mock_student = {
            "id": "1",
            "enrollment_no": "210410107001",
            "department": "Computer Engineering",
            "semester": 5,
            "program": "BE",
            "is_admin": False
        }

        notifs = MongoNotificationService.get_notifications(mock_student, limit=20)
        found = any("SVIT Mega Roborace" in n.get("title", "") for n in notifs.get("notifications", []))
        self.assertTrue(found, "Event was not found in student notifications list")

        # Invalidate AI caches and test events AI context retrieval
        invalidate_ai_caches()
        event_ctx = process_events_context("tell me about roborace competition event")
        self.assertIn("Roborace", event_ctx)

        # Cleanup
        AdminCRUDService.delete_item("events", test_eid)

if __name__ == '__main__':
    unittest.main()
