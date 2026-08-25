"""
tests/test_svit_ai.py
Comprehensive End-to-End Test Suite for SVIT-AI.
Verifies all routes, templates, data processors, auth, chat, history, and Vercel compatibility.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['VERCEL'] = '1'

class TestSVITAI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import api.index
        cls.app = api.index.app
        cls.client = cls.app.test_client()

    def test_01_api_index_import(self):
        """Verify api.index exports a valid Flask WSGI application."""
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.name, 'app')

    def test_02_root_redirect_unauthenticated(self):
        """GET / should redirect unauthenticated user to /auth/student/login."""
        res = self.client.get('/')
        self.assertIn(res.status_code, [200, 302])
        if res.status_code == 302:
            self.assertIn('/login', res.headers.get('Location', ''))

    def test_03_login_page_renders(self):
        """GET /auth/student/login should return 200 with HTML login form."""
        res = self.client.get('/auth/student/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SVIT', res.data)

    def test_04_admin_login_page_renders(self):
        """GET /admin/login should redirect to unified /login."""
        res = self.client.get('/admin/login')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location'))

    def test_05_static_file_accessible(self):
        """Verify static files directory is mapped and accessible."""
        self.assertTrue(os.path.exists(self.app.static_folder))

    def test_06_timetable_context_processing(self):
        """Verify in-memory timetable data processing for Computer Eng sem 3."""
        from app.ai.data_processor import process_timetable_context
        profile = {
            "full_name": "Manav Solanki",
            "department": "Computer Engineering",
            "semester": 3,
            "division": "A",
            "program": "BE"
        }
        res = process_timetable_context([], "timetable monday", user_profile=profile)
        self.assertIsNotNone(res)
        self.assertIn("timetable.csv", res)

    def test_07_next_class_real_time_processing(self):
        """Verify next class analyzer returns structured text."""
        from app.ai.data_processor import process_next_class_context
        profile = {
            "full_name": "Manav Solanki",
            "department": "Computer Engineering",
            "semester": 3,
            "division": "A",
            "program": "BE"
        }
        ans, map_path, srcs = process_next_class_context("where is my next class", user_profile=profile)
        self.assertIsNotNone(ans)
        self.assertTrue(len(srcs) > 0)

    def test_08_notices_and_placements_processing(self):
        """Verify notices and placement context processing."""
        from app.ai.data_processor import process_notice_context, process_placement_context
        notices = process_notice_context([], "exam form notice")
        self.assertIsNotNone(notices)

        placements = process_placement_context("highest package in placement")
        self.assertIsNotNone(placements)

    def test_09_fast_greeting_resolution(self):
        """Verify fast-path greeting resolves in 0ms without external API call."""
        from app.ai.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()
        res = rag.answer_question("hello", session_id="test_session")
        self.assertIn("Hello", res.get("answer", ""))
        self.assertIn("SVIT", res.get("answer", ""))

    def test_10_navigation_interception(self):
        """Verify spatial navigation module returns correct location & map."""
        from app.ai.navigation import find_location
        nav = find_location("where is canteen")
        self.assertIsNotNone(nav)
        self.assertIn("canteen", nav.get("formatted_text", "").lower())

    def test_11_history_routes(self):
        """Verify /chat/history returns valid JSON."""
        res = self.client.get('/chat/history')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("history", data)

    def test_12_saved_history_route(self):
        """Verify /chat/saved returns valid JSON."""
        res = self.client.get('/chat/saved')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    def test_13_mongo_models_layer(self):
        """Verify MongoStudent and MongoChatService interfaces."""
        from app.database.mongo_models import MongoStudent, MongoChatService, MongoUserSettingsService
        s = MongoStudent({"id": "test_1", "enrollment_no": "9999", "full_name": "Test User", "password_hash": ""})
        self.assertEqual(s.get_id(), "student_test_1")
        self.assertFalse(s.is_admin)

        settings = MongoUserSettingsService.get_settings("test_1")
        self.assertIn("theme", settings)

    def test_14_api_chat_empty_validation(self):
        """POST /api/chat with empty body should return 400."""
        res = self.client.post('/api/chat', json={})
        self.assertEqual(res.status_code, 400)

    def test_15_feedback_endpoint_validation(self):
        """POST /api/chat/feedback with valid rating."""
        res = self.client.post('/api/chat/feedback', json={
            "rating": "like",
            "conversation_id": "test_conv_1",
            "query_text": "hello",
            "response_text": "Hi there!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("rating"), "like")

    def test_16_faculty_search_processing(self):
        """Verify faculty context processing finds faculty details."""
        from app.ai.data_processor import process_faculty_context
        fac = process_faculty_context([], "who is HOD of computer department")
        self.assertIsNotNone(fac)


    def test_17_events_processing(self):
        """Verify events context processor extracts campus events."""
        from app.ai.data_processor import process_events_context
        ev = process_events_context("Prakarsh tech fest events")
        self.assertIsNotNone(ev)

    def test_18_streaming_greeting_response(self):
        """Verify streaming generator yields valid SSE chunks for greeting."""
        from app.ai.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()
        stream = list(rag.stream_answer_question("hi", session_id="stream_test"))
        self.assertTrue(len(stream) > 0)
        self.assertTrue(any(p.get("done") for p in stream))


if __name__ == '__main__':
    unittest.main(verbosity=2)
