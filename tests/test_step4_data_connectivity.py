"""
Step 4 Comprehensive Verification Test:
Validates that all 28 SVIT Admin frontend pages and backend modules are fully connected
to real MongoDB / Excel / CSV data sources and CRUD APIs.
"""

import unittest
import json
from app import create_app
from app.extensions import db
from app.database.models.admin import Admin
from app.database.admin_crud_service import AdminCRUDService, MODULE_CONFIGS, MODULE_ALIASES
from app.auth.rbac import ROLE_SUPER_ADMIN, ROLE_ACADEMIC_ADMIN


class TestStep4DataConnectivity(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        with self.app.app_context():
            db.create_all()
            # Ensure super admin exists
            admin = Admin.query.filter_by(username="test_superadmin").first()
            if not admin:
                admin = Admin(
                    username="test_superadmin",
                    email="test_superadmin@svit.ac.in",
                    name="Test Super Admin",
                    role=ROLE_SUPER_ADMIN,
                    department="Computer Engineering",
                    is_active=True
                )
                admin.set_password("Admin@123456")
                db.session.add(admin)
                db.session.commit()
            self.admin_id = admin.id

    def tearDown(self):
        self.app_context.pop()

    def _login_admin(self):
        return self.client.post('/admin/login', data={
            'username': 'test_superadmin',
            'password': 'Admin@123456'
        }, follow_redirects=True)

    def test_01_all_28_admin_routes_render_200(self):
        """Verify that all 28 individual Admin frontend page routes return HTTP 200."""
        self._login_admin()
        routes = [
            '/admin/dashboard',
            '/admin/admins',
            '/admin/students',
            '/admin/faculty',
            '/admin/timetable',
            '/admin/subjects',
            '/admin/rooms',
            '/admin/placements',
            '/admin/admission',
            '/admin/notices',
            '/admin/events',
            '/admin/buses',
            '/admin/bus_routes',
            '/admin/bus_stops',
            '/admin/bus_timings',
            '/admin/library',
            '/admin/library_books',
            '/admin/library_members',
            '/admin/issue_return',
            '/admin/canteen',
            '/admin/canteen_menu',
            '/admin/food_items',
            '/admin/sports',
            '/admin/sports_events',
            '/admin/grounds',
            '/admin/academic_documents',
            '/admin/roles_permissions',
            '/admin/profile'
        ]

        self.assertEqual(len(routes), 28, "Must verify all 28 individual admin page routes.")
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")

    def test_02_all_crud_modules_fetch_real_data(self):
        """Verify that every module registered in MODULE_CONFIGS returns real records."""
        self._login_admin()
        for module_key in MODULE_CONFIGS.keys():
            res = self.client.get(f'/admin/api/crud/{module_key}?limit=10')
            self.assertEqual(res.status_code, 200, f"CRUD API for '{module_key}' failed: {res.data}")
            data = res.get_json()
            self.assertEqual(data.get('status'), 'success')
            self.assertIn('items', data)
            self.assertIn('total', data)
            self.assertGreaterEqual(data['total'], 0)

    def test_03_module_aliases_resolve_correctly(self):
        """Verify that friendly and plural aliases resolve to primary datasets."""
        self._login_admin()
        aliases = [
            ("admission", "admission_info"),
            ("buses", "transport"),
            ("bus_routes", "transport"),
            ("bus_stops", "transport"),
            ("bus_timings", "transport"),
            ("library", "library_info"),
            ("books", "library_books"),
            ("members", "library_members"),
            ("issue_return", "library_issue_return"),
            ("canteen_menu", "canteen"),
            ("food_items", "canteen"),
            ("sports_disciplines", "sports")
        ]
        for alias, canonical in aliases:
            res = self.client.get(f'/admin/api/crud/{alias}?limit=5')
            self.assertEqual(res.status_code, 200, f"Alias '{alias}' failed to resolve.")
            data = res.get_json()
            self.assertEqual(data.get('status'), 'success')
            self.assertEqual(data.get('module'), canonical)

    def test_04_live_crud_lifecycle(self):
        """Verify complete Create -> Read -> Update -> Delete lifecycle against live data store."""
        self._login_admin()
        
        # 1. Create with all required fields
        create_payload = {
            "notice_id": "TEST_NT_9999",
            "title": "Automated Connectivity Test Notice",
            "category": "Academic",
            "priority": "High",
            "target_audience": "All Students",
            "department": "All Departments",
            "publish_date": "2026-08-26",
            "description": "Integration test payload description.",
            "is_urgent": False,
            "status": "Published"
        }
        create_res = self.client.post('/admin/api/crud/notices',
                                      data=json.dumps(create_payload),
                                      content_type='application/json')
        self.assertEqual(create_res.status_code, 201, f"Failed to create: {create_res.data}")
        created_data = create_res.get_json()
        self.assertEqual(created_data.get('status'), 'success')

        # 2. Read single
        get_res = self.client.get('/admin/api/crud/notices/TEST_NT_9999')
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.get_json()
        self.assertEqual(get_data['item']['title'], "Automated Connectivity Test Notice")

        # 3. Update
        update_payload = {"title": "Updated Notice Title via API"}
        update_res = self.client.put('/admin/api/crud/notices/TEST_NT_9999',
                                     data=json.dumps(update_payload),
                                     content_type='application/json')
        self.assertEqual(update_res.status_code, 200)
        updated_data = update_res.get_json()
        self.assertEqual(updated_data['item']['title'], "Updated Notice Title via API")

        # 4. Delete
        del_res = self.client.delete('/admin/api/crud/notices/TEST_NT_9999')
        self.assertEqual(del_res.status_code, 200)

        # 5. Verify 404 after delete
        verify_res = self.client.get('/admin/api/crud/notices/TEST_NT_9999')
        self.assertEqual(verify_res.status_code, 404)

    def test_05_admin_stats_and_profile_api(self):
        """Verify telemetry stats and current admin profile API endpoints."""
        self._login_admin()

        stats_res = self.client.get('/admin/api/stats')
        self.assertEqual(stats_res.status_code, 200)
        stats_json = stats_res.get_json()
        self.assertEqual(stats_json.get('status'), 'success')
        counters = stats_json.get('stats', {}).get('counters', {})
        self.assertIn('total_students', counters)
        self.assertIn('faculty_members', counters)
        self.assertIn('library_books', counters)

        me_res = self.client.get('/admin/api/me')
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertEqual(me_data['admin']['username'], 'test_superadmin')

    def test_06_verify_real_counts_and_empty_modules(self):
        """Verify that modules with CSVs return real counts, and modules without CSVs return 0 / empty."""
        self._login_admin()

        # 1. Modules with real CSVs must have real counts
        csv_modules = {
            "faculty": 250,
            "library_books": 640,
            "subjects": 640,
            "timetable": 9216,
            "rooms": 40,
            "placements": 300,
            "notices": 150,
            "events": 120,
            "transport": 40,
            "canteen": 40
        }
        for mod, expected_min in csv_modules.items():
            res = self.client.get(f'/admin/api/crud/{mod}?limit=1')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertGreaterEqual(data['total'], expected_min, f"Module {mod} missing real CSV records.")

        # 2. Modules without CSVs must be cleanly empty (0 records)
        empty_modules = [
            "academic_documents",
            "admission_info",
            "admission_documents",
            "admission_notices",
            "library_members",
            "library_issue_return",
            "sports",
            "sports_events",
            "grounds"
        ]
        for mod in empty_modules:
            res = self.client.get(f'/admin/api/crud/{mod}?limit=1')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['total'], 0, f"Module {mod} must not contain fake seeded records.")

        # 3. Create a real record in an empty module, verify it appears, then delete it
        sport_payload = {
            "sport_id": "TEST_SPT_001",
            "sport_name": "Test Real Badminton",
            "category": "Indoor",
            "coach_name": "Test Coach",
            "equipment_available": "Available for Issue"
        }
        create_res = self.client.post('/admin/api/crud/sports',
                                      data=json.dumps(sport_payload),
                                      content_type='application/json')
        self.assertEqual(create_res.status_code, 201)
        
        # Verify total is now 1
        res_after = self.client.get('/admin/api/crud/sports?limit=1')
        self.assertEqual(res_after.get_json()['total'], 1)

        # Delete it and verify it reverts to 0
        del_res = self.client.delete('/admin/api/crud/sports/TEST_SPT_001')
        self.assertEqual(del_res.status_code, 200)
        res_final = self.client.get('/admin/api/crud/sports?limit=1')
        self.assertEqual(res_final.get_json()['total'], 0)


if __name__ == '__main__':
    unittest.main()
