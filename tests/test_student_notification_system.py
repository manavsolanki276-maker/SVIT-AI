"""
tests/test_student_notification_system.py
Comprehensive test suite for the SVIT AI Student Notification System and Mobile Sidebar Layout.
Validates:
1. MongoDB notification schema & MongoNotificationService operations
2. Student isolation & security (students only see their own / audience notifications)
3. Authenticated REST API endpoints:
   - GET /api/notifications
   - POST /api/notifications/<id>/read
   - POST /api/notifications/read-all
   - DELETE /api/notifications/<id>
4. Admin -> Student notification generation (Notice, Event, Approval, Rejection)
5. HTML view routing (/notifications, /student/notifications)
6. Mobile sidebar DOM structure and UI elements
"""
import os
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import login_user

# Set test environment
os.environ['TESTING'] = 'True'

from app import create_app
from app.extensions import db
from app.database.mongo_models import MongoNotificationService
from app.database.admin_crud_service import AdminCRUDService


class DummyStudentUser:
    """Mock student user object simulating Flask-Login current_user."""
    def __init__(self, id="student_101", name="Manav Solanki", enrollment_no="220101", department="Computer Engineering", semester=4, is_admin=False, status="active"):
        self.id = id
        self.name = name
        self.full_name = name
        self.enrollment_no = enrollment_no
        self.department = department
        self.semester = semester
        self.program = "Diploma"
        self.batch = "A1"
        self.is_admin = is_admin
        self.status = status
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)


class DummyAdminUser:
    """Mock admin user object simulating Flask-Login current_user."""
    def __init__(self):
        self.id = "admin_1"
        self.name = "Campus Admin"
        self.full_name = "Campus Administrator"
        self.is_admin = True
        self.status = "active"
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return "admin_1"


class MockMongoCollection:
    """In-memory MongoDB collection mock for notifications."""
    def __init__(self):
        self.docs = []
        self._counter = 1

    def insert_one(self, doc):
        doc = dict(doc)
        if "_id" not in doc:
            doc["_id"] = f"notif_{self._counter}"
            self._counter += 1
        self.docs.append(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result

    def find(self, query=None):
        docs = list(self.docs)
        if query:
            filtered = []
            for d in docs:
                if self._matches(d, query):
                    filtered.append(d)
            docs = filtered
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = docs
        cursor.__iter__.return_value = iter(docs)
        return cursor

    def find_one(self, query=None):
        for d in self.docs:
            if self._matches(d, query):
                return d
        return None

    def update_one(self, query, update):
        for d in self.docs:
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$addToSet" in update:
                    for k, v in update["$addToSet"].items():
                        if k not in d:
                            d[k] = []
                        if v not in d[k]:
                            d[k].append(v)
                return True
        return False

    def update_many(self, query, update):
        count = 0
        for d in self.docs:
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$addToSet" in update:
                    for k, v in update["$addToSet"].items():
                        if k not in d:
                            d[k] = []
                        if v not in d[k]:
                            d[k].append(v)
                count += 1
        return count

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                self.docs.pop(i)
                return True
        return False

    def _matches(self, doc, query):
        if not query:
            return True
        if "$and" in query:
            return all(self._matches(doc, q) for q in query["$and"])
        if "$or" in query:
            return any(self._matches(doc, q) for q in query["$or"])
        for k, v in query.items():
            if k == "_id":
                if str(doc.get("_id")) != str(v):
                    return False
            elif isinstance(v, dict):
                if "$in" in v:
                    doc_val = doc.get(k)
                    str_in = [str(x) for x in v["$in"]]
                    if str(doc_val) not in str_in and doc_val not in v["$in"]:
                        return False
                if "$nin" in v:
                    doc_val = doc.get(k, [])
                    if isinstance(doc_val, list):
                        if any(x in doc_val for x in v["$nin"]):
                            return False
                    elif doc_val in v["$nin"]:
                        return False
                if "$ne" in v:
                    if doc.get(k) == v["$ne"]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True


class TestStudentNotificationSystem(unittest.TestCase):
    """Unit and Integration tests for Student Notifications & Mobile Sidebar UI."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.mock_mongo_notifs = MockMongoCollection()
        self.student_user_1 = DummyStudentUser(id="student_101", enrollment_no="220101", department="Computer Engineering")
        self.student_user_2 = DummyStudentUser(id="student_202", enrollment_no="220202", department="Mechanical Engineering")
        self.admin_user = DummyAdminUser()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.database.mongo_models.get_collection')
    def test_01_mongo_notification_creation_and_schema(self, mock_get_coll):
        """Test MongoDB notification creation conforms to the complete unified schema."""
        mock_get_coll.side_effect = lambda name: self.mock_mongo_notifs if name == 'notifications' else None

        notif_id = MongoNotificationService.create_notification(
            user_id="101",
            recipient_id="101",
            recipient_type="student",
            title="Registration Approved",
            message="Your SVIT AI student portal registration has been verified.",
            category="approval",
            target_audience="Student",
            department="Computer Engineering",
            semester=4,
            link="/student/chat",
            data={"status": "active"}
        )

        self.assertIsNotNone(notif_id)
        doc = self.mock_mongo_notifs.find_one({"_id": notif_id})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["title"], "Registration Approved")
        self.assertEqual(doc["recipient_id"], "101")
        self.assertEqual(doc["category"], "approval")
        self.assertEqual(doc["is_read"], False)
        self.assertEqual(doc["read_by"], [])
        self.assertEqual(doc["deleted_by"], [])
        self.assertIn("created_at", doc)
        self.assertIn("updated_at", doc)

    @patch('app.database.mongo_models.get_collection')
    def test_02_student_isolation_security(self, mock_get_coll):
        """Verify Student A can NEVER fetch or see Student B's private notifications."""
        mock_get_coll.side_effect = lambda name: self.mock_mongo_notifs if name == 'notifications' else None

        # Student A private notification
        MongoNotificationService.notify_student(
            student_id="101",
            title="Private Notice for Student A",
            message="Your lab assignment is submitted.",
            category="academic"
        )

        # Student B private notification
        MongoNotificationService.notify_student(
            student_id="202",
            title="Private Notice for Student B",
            message="Your fee receipt is generated.",
            category="academic"
        )

        # General broadcast notification
        MongoNotificationService.notify_audience(
            title="Campus Fest 2026",
            message="Annual technical fest registrations are open.",
            category="events",
            target_audience="All Students"
        )

        # Fetch for Student A
        res_a = MongoNotificationService.get_notifications(self.student_user_1)
        titles_a = [n["title"] for n in res_a["notifications"]]
        self.assertIn("Private Notice for Student A", titles_a)
        self.assertIn("Campus Fest 2026", titles_a)
        self.assertNotIn("Private Notice for Student B", titles_a)

        # Fetch for Student B
        res_b = MongoNotificationService.get_notifications(self.student_user_2)
        titles_b = [n["title"] for n in res_b["notifications"]]
        self.assertIn("Private Notice for Student B", titles_b)
        self.assertIn("Campus Fest 2026", titles_b)
        self.assertNotIn("Private Notice for Student A", titles_b)

    @patch('app.database.mongo_models.get_collection')
    def test_03_unread_count_and_mark_read(self, mock_get_coll):
        """Test unread counting and marking single notification as read."""
        mock_get_coll.side_effect = lambda name: self.mock_mongo_notifs if name == 'notifications' else None

        id1 = MongoNotificationService.notify_student(
            student_id="101",
            title="Exam Schedule",
            message="Mid-sem timetable published.",
            category="timetable"
        )
        id2 = MongoNotificationService.notify_student(
            student_id="101",
            title="Workshop Alert",
            message="AI workshop tomorrow at Seminar Hall.",
            category="events"
        )

        res = MongoNotificationService.get_notifications(self.student_user_1)
        self.assertEqual(res["unread_count"], 2)

        # Mark id1 as read
        ok = MongoNotificationService.mark_read(id1, self.student_user_1)
        self.assertTrue(ok)

        res_after = MongoNotificationService.get_notifications(self.student_user_1)
        self.assertEqual(res_after["unread_count"], 1)

    @patch('app.database.mongo_models.get_collection')
    def test_04_mark_all_read(self, mock_get_coll):
        """Test mark all notifications as read for current student."""
        mock_get_coll.side_effect = lambda name: self.mock_mongo_notifs if name == 'notifications' else None

        MongoNotificationService.notify_student(student_id="101", title="Notice 1", message="Msg 1")
        MongoNotificationService.notify_student(student_id="101", title="Notice 2", message="Msg 2")
        MongoNotificationService.notify_audience(title="Broadcast 1", message="All students msg")

        res_before = MongoNotificationService.get_notifications(self.student_user_1)
        self.assertEqual(res_before["unread_count"], 3)

        # Mark all read
        ok = MongoNotificationService.mark_all_read(self.student_user_1)
        self.assertTrue(ok)

        res_after = MongoNotificationService.get_notifications(self.student_user_1)
        self.assertEqual(res_after["unread_count"], 0)

    @patch('app.routes.notification_routes.MongoNotificationService.get_notifications')
    def test_05_authenticated_api_get_notifications(self, mock_get_notifs):
        """Test GET /api/notifications returns student notifications with unread count."""
        mock_get_notifs.return_value = {
            "status": "success",
            "unread_count": 1,
            "notifications": [
                {
                    "id": "notif_1",
                    "title": "Welcome to SVIT AI",
                    "message": "Your profile is active.",
                    "category": "general",
                    "is_read": False,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        }

        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.get('/api/notifications')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["unread_count"], 1)
            self.assertEqual(len(data["notifications"]), 1)
            self.assertEqual(data["notifications"][0]["title"], "Welcome to SVIT AI")

    @patch('app.routes.notification_routes.MongoNotificationService.mark_read')
    def test_06_authenticated_api_mark_read(self, mock_mark_read):
        """Test POST /api/notifications/<id>/read marks notification read."""
        mock_mark_read.return_value = True

        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.post('/api/notifications/notif_1/read')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["status"], "success")

    @patch('app.routes.notification_routes.MongoNotificationService.mark_all_read')
    def test_07_authenticated_api_mark_all_read(self, mock_mark_all_read):
        """Test POST /api/notifications/read-all marks all notifications read."""
        mock_mark_all_read.return_value = True

        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.post('/api/notifications/read-all')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["status"], "success")

    @patch('app.routes.notification_routes.MongoNotificationService.delete_notification')
    def test_08_authenticated_api_delete_notification(self, mock_delete_notif):
        """Test DELETE /api/notifications/<id> deletes or dismisses notification."""
        mock_delete_notif.return_value = True

        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.delete('/api/notifications/notif_1')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["status"], "success")

    @patch('app.database.mongo_models.MongoNotificationService.notify_audience')
    def test_09_admin_notice_and_event_publishing_dispatches_notification(self, mock_notify_aud):
        """Test AdminCRUDService creates real notifications when publishing notices or events."""
        mock_notify_aud.return_value = "notif_admin_dispatched"

        clean_data = {
            "title": "Semester 4 Timetable Released",
            "description": "The revised mid-semester exam timetable is available.",
            "target_audience": "All Students",
            "department": "Computer Engineering"
        }

        AdminCRUDService._dispatch_admin_action_notification(
            module_key="notices",
            item_id="notice_55",
            clean_data=clean_data,
            is_update=False
        )

        mock_notify_aud.assert_called_once()
        args, kwargs = mock_notify_aud.call_args
        self.assertIn("Semester 4 Timetable Released", kwargs.get("title", ""))
        self.assertEqual(kwargs.get("department"), "Computer Engineering")

    def test_10_student_notification_html_view_route(self):
        """Test GET /notifications and GET /student/notifications render the HTML template."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.get('/notifications')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Notifications', response.data)
            self.assertIn(b'Mark all as read', response.data)
            self.assertIn(b'notifications-container', response.data)

            response2 = self.client.get('/student/notifications')
            self.assertEqual(response2.status_code, 200)
            self.assertIn(b'Notifications', response2.data)

    def test_11_unauthenticated_request_blocked(self):
        """Test unauthenticated requests are redirected or denied."""
        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 302)

        response_api = self.client.get('/api/notifications')
        self.assertEqual(response_api.status_code, 302)

    def test_12_mobile_sidebar_html_structure_verification(self):
        """Verify chat.html contains required mobile sidebar elements without awkward whitespace."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = 'student_101'

        with patch('flask_login.utils._get_user', return_value=self.student_user_1):
            response = self.client.get('/student/chat')
            self.assertEqual(response.status_code, 200)
            html = response.data.decode('utf-8')

            # 1. Branding & Header
            self.assertIn('sidebar-brand', html)
            self.assertIn('SVIT AI', html)

            # 2. Drawer Profile Card
            self.assertIn('drawer-profile-card', html)

            # 3. New Chat Button
            self.assertIn('new-chat-btn', html)
            self.assertIn('+ New Chat', html)

            # 4. Recents section
            self.assertIn('sidebar-recents-section', html)
            self.assertIn('RECENTS', html)
            self.assertIn('sidebarRecentList', html)

            # 5. Fixed Anchored Bottom Actions
            self.assertIn('drawer-bottom-actions', html)
            self.assertIn('drawer-view-all-chats-btn', html)
            self.assertIn('drawer-exit-chat-btn', html)
            self.assertIn('View All Chats', html)

            # 6. Notification Bell & Mobile Drawer
            self.assertIn('mobileNotifBellBtn', html)
            self.assertIn('mobileNotifDrawer', html)
            self.assertIn('mobileNotifBackdrop', html)
            self.assertIn('View all notifications', html)


if __name__ == '__main__':
    unittest.main()
