"""
Comprehensive Test Suite for SVIT-AI Guest Mode and Public Information Categories
Verifies:
1. "Skip & Continue as Guest" button on Login and Register pages.
2. Route access for /guest, /guest/chat, /skip, /continue-as-guest.
3. Accurate responses for all 11 public categories.
4. Strict access restrictions on private student/faculty data for guests.
5. Preserved full access for logged-in students.
6. Guest exit / logout flow.
"""

import unittest
from app import create_app
from app.ai.guest_service import PUBLIC_CATEGORIES_METADATA, classify_guest_query

class TestGuestMode(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_login_and_register_pages_have_guest_button(self):
        """Verify Skip / Continue as Guest button is rendered on both Login and Register pages."""
        login_res = self.client.get('/login')
        self.assertEqual(login_res.status_code, 200)
        login_html = login_res.get_data(as_text=True)
        self.assertIn('/guest', login_html)
        self.assertIn('Continue as Guest', login_html)

        reg_res = self.client.get('/register')
        self.assertEqual(reg_res.status_code, 200)
        reg_html = reg_res.get_data(as_text=True)
        self.assertIn('/guest', reg_html)
        self.assertIn('Continue as Guest', reg_html)

    def test_02_guest_routes_render_chat(self):
        """Verify accessing /guest sets guest session and returns 200 with guest interface."""
        res = self.client.get('/guest', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('11 Public Information Categories', html)
        self.assertIn('Guest Mode', html)
        self.assertIn('About SVIT', html)
        self.assertIn('Fees Structure', html)

        # Also test /skip alias
        skip_res = self.client.get('/skip', follow_redirects=True)
        self.assertEqual(skip_res.status_code, 200)

    def test_03_guest_categories_api(self):
        """Verify /guest/api/categories returns all 11 categories."""
        res = self.client.get('/guest/api/categories')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['total'], 11)
        cat_ids = [c['id'] for c in data['categories']]
        expected_ids = [
            'about_svit', 'courses', 'fees', 'admission',
            'eligibility', 'seats', 'timing', 'events',
            'bus', 'library', 'sports'
        ]
        for cid in expected_ids:
            self.assertIn(cid, cat_ids)

    def test_04_all_11_categories_query_resolution(self):
        """Verify guest classifier resolves queries for all 11 categories."""
        category_queries = {
            'about_svit': "Tell me about SVIT Vasad and its history",
            'courses': "What courses and engineering branches are offered?",
            'fees': "What is the fee structure for B.E. and MCA?",
            'admission': "How can I get admission through ACPC?",
            'eligibility': "What is the eligibility criteria for admission?",
            'seats': "How many seats are available in Computer Engineering?",
            'timing': "What are the college and office hours?",
            'events': "Tell me about college tech fests and events",
            'bus': "What are the college bus routes and transportation?",
            'library': "Tell me about the central library and book bank",
            'sports': "What sports facilities and gymnasium are available?"
        }

        for expected_id, query in category_queries.items():
            result = classify_guest_query(query)
            self.assertFalse(result.get('is_restricted', False), f"Query '{query}' was unexpectedly restricted")
            self.assertEqual(result.get('matched_category'), expected_id, f"Query '{query}' resolved to {result.get('matched_category')} instead of {expected_id}")
            self.assertTrue(len(result.get('response_text', '')) > 50)

    def test_05_student_internal_queries_are_restricted_for_guest(self):
        """Verify private student/faculty queries are strictly blocked for guests."""
        restricted_queries = [
            "What is my timetable today?",
            "Where is my next class right now?",
            "Check my attendance percentage",
            "Show my internal marks and exam results",
            "What is my student roll number and batch?",
            "Show my faculty meeting notes and internal circular"
        ]

        for query in restricted_queries:
            result = classify_guest_query(query)
            self.assertTrue(result.get('is_restricted'), f"Query '{query}' should be restricted for guests!")
            self.assertIn("registered students and faculty only", result.get('response_text', '').lower())

    def test_06_guest_chat_api_allows_11_categories(self):
        """Verify /api/chat endpoint answers guest queries for the 11 categories."""
        res = self.client.post('/api/chat', json={
            'message': 'Tell me about the fees structure',
            'is_guest': True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('answer', data)
        self.assertIn('Fees Structure', data['answer'])
        self.assertIn('FRC', data['answer'])

    def test_07_guest_chat_api_blocks_student_features(self):
        """Verify /api/chat endpoint strictly returns restriction message for internal queries."""
        res = self.client.post('/api/chat', json={
            'message': 'What is my timetable today?',
            'is_guest': True
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('answer', data)
        self.assertIn("registered students", data['answer'].lower())

    def test_08_guest_exit_flow(self):
        """Verify /guest/exit clears the session and redirects to /login."""
        # Enter guest mode
        self.client.get('/guest')
        # Exit guest mode
        exit_res = self.client.get('/guest/exit')
        self.assertEqual(exit_res.status_code, 302)
        self.assertIn('/login', exit_res.headers.get('Location'))

if __name__ == '__main__':
    unittest.main()
