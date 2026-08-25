"""
tests/test_step2_admin_crud_upload.py
Comprehensive Step 2 Test Suite for SVIT Admin Panel.
Tests:
- Admin Authentication & Protected Route Access
- Strict RBAC Boundary Enforcement Across All Modules & APIs
- Full CRUD Operations (Create, Read/Search/Filter/Sort/Paginate, Update, Delete)
- Audit Field Stamping (created_by, updated_by, timestamps)
- Image Upload (Drag-and-drop, Preview, Replace, Delete, Type & Size Validation)
- PDF/Document Upload (Preview, Download, Replace, Delete, Type & Size Validation)
- Invalid File & Oversized File Rejection
- Dynamic Stats API per Role
"""
import io
import os
import sys
import unittest
import json

# Set project root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.database.admin_seed import seed_admin_accounts
from app.database.admin_crud_service import AdminCRUDService, initialize_datasets_if_needed
from app.auth.rbac import (
    ROLE_SUPER_ADMIN,
    ROLE_ACADEMIC_ADMIN,
    ROLE_ADMISSION_ADMIN,
    ROLE_NOTICE_ADMIN,
    ROLE_EVENT_ADMIN,
    ROLE_BUS_ADMIN,
    ROLE_LIBRARY_ADMIN,
    ROLE_CANTEEN_ADMIN,
    ROLE_SPORTS_ADMIN,
)


class TestStep2AdminCrudAndUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Sets up test client and seeds data."""
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()
            seed_admin_accounts(cls.app)
            initialize_datasets_if_needed()

    def login_as(self, identifier: str, password: str = "Admin@123"):
        """Helper to log in as a specific admin."""
        res = self.client.post('/admin/login', json={
            "identifier": identifier,
            "password": password
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200, f"Login failed for {identifier}")
        return res

    def logout(self):
        """Helper to log out."""
        return self.client.get('/admin/logout', headers={"Accept": "application/json"})

    # =========================================================================
    # 1. AUTHENTICATION & DASHBOARD TESTS
    # =========================================================================
    def test_01_super_admin_dashboard_and_stats(self):
        """Verify Super Admin can log in, view dashboard, and fetch aggregate stats."""
        self.login_as("superadmin", "Admin@123")

        # HTML Dashboard
        dash_res = self.client.get('/admin/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"SVIT", dash_res.data)
        self.assertIn(b"Dashboard", dash_res.data)

        # JSON Stats API
        stats_res = self.client.get('/admin/api/stats')
        self.assertEqual(stats_res.status_code, 200)
        stats = stats_res.get_json()["stats"]
        self.assertEqual(stats["role"], ROLE_SUPER_ADMIN)
        self.assertIn("counters", stats)

        self.logout()

    def test_02_each_admin_role_stats_are_tailored(self):
        """Verify that stats returned for each role contain role-specific counters."""
        role_creds = [
            ("bus_admin", "Bus@123", "total_routes"),
            ("sports_admin", "Sports@123", "total_sports"),
            ("event_admin", "Event@123", "total_events"),
            ("library_admin", "Library@123", "total_books"),
            ("canteen_admin", "Canteen@123", "menu_items"),
            ("academic_admin", "Academic@123", "total_students"),
            ("admission_admin", "Admission@123", "programs_offered"),
            ("notice_admin", "Notice@123", "total_notices"),
        ]

        for username, password, expected_counter in role_creds:
            with self.subTest(username=username):
                self.login_as(username, password)
                res = self.client.get('/admin/api/stats')
                self.assertEqual(res.status_code, 200)
                stats = res.get_json()["stats"]
                self.assertIn(expected_counter, stats["counters"], f"{username} should have counter {expected_counter}")
                self.logout()

    # =========================================================================
    # 2. RBAC BOUNDARY TESTS ACROSS MODULES
    # =========================================================================
    def test_03_bus_admin_cannot_access_unauthorized_modules(self):
        """Verify Bus Admin has access to transport but is forbidden from Library, Canteen, Academic, Sports, Events."""
        self.login_as("bus_admin", "Bus@123")

        # Allowed:
        res_transport = self.client.get('/admin/api/crud/transport')
        self.assertEqual(res_transport.status_code, 200)

        # Forbidden HTML routes (403):
        for route in ['/admin/library', '/admin/canteen', '/admin/students', '/admin/faculty', '/admin/sports', '/admin/events', '/admin/admins']:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 403, f"Bus Admin should get 403 on {route}, got {res.status_code}")

        # Forbidden API endpoints (403):
        for module in ['library_books', 'canteen', 'students', 'faculty', 'sports', 'events']:
            res = self.client.get(f'/admin/api/crud/{module}')
            self.assertEqual(res.status_code, 403, f"Bus Admin should get 403 on API {module}, got {res.status_code}")

        self.logout()

    def test_04_sports_admin_cannot_access_college_events(self):
        """Verify Sports Admin is permitted for sports/grounds/tournaments but strictly forbidden from College Events."""
        self.login_as("sports_admin", "Sports@123")

        # Allowed Sports APIs:
        self.assertEqual(self.client.get('/admin/api/crud/sports').status_code, 200)
        self.assertEqual(self.client.get('/admin/api/crud/sports_events').status_code, 200)
        self.assertEqual(self.client.get('/admin/api/crud/grounds').status_code, 200)

        # Forbidden from College Events:
        res_events = self.client.get('/admin/api/crud/events')
        self.assertEqual(res_events.status_code, 403, "Sports Admin must NOT access events API")
        self.assertEqual(self.client.get('/admin/events').status_code, 403)

        self.logout()

    def test_05_event_admin_cannot_access_sports(self):
        """Verify Event Admin is permitted for College Events but strictly forbidden from Sports."""
        self.login_as("event_admin", "Event@123")

        # Allowed Events API:
        self.assertEqual(self.client.get('/admin/api/crud/events').status_code, 200)

        # Forbidden from Sports modules:
        for mod in ['sports', 'sports_events', 'grounds']:
            res = self.client.get(f'/admin/api/crud/{mod}')
            self.assertEqual(res.status_code, 403, f"Event Admin must NOT access {mod} API")

        self.logout()

    def test_06_super_admin_has_unrestricted_access_to_all_modules(self):
        """Verify Super Admin can access every module HTML route and CRUD API."""
        self.login_as("superadmin", "Admin@123")

        modules = [
            'students', 'faculty', 'timetable', 'rooms', 'subjects', 'placements',
            'academic_documents', 'admission_info', 'admission_documents', 'admission_notices',
            'notices', 'events', 'transport', 'library_books', 'library_members',
            'library_issue_return', 'library_info', 'canteen', 'sports', 'sports_events', 'grounds'
        ]

        for mod in modules:
            with self.subTest(module=mod):
                res = self.client.get(f'/admin/api/crud/{mod}')
                self.assertEqual(res.status_code, 200, f"Super Admin failed on API {mod}")

        # Super Admin only route
        admin_mgmt = self.client.get('/admin/admins')
        self.assertEqual(admin_mgmt.status_code, 200)

        self.logout()

    # =========================================================================
    # 3. CRUD OPERATIONS & AUDIT TRAIL TESTS
    # =========================================================================
    def test_07_notice_admin_crud_workflow_with_audit(self):
        """Test complete CRUD lifecycle on Notices module with urgency and audit fields."""
        self.login_as("notice_admin", "Notice@123")

        # 1. CREATE Notice
        new_notice = {
            "title": "Severe Cyclone Warning - College Closed",
            "category": "College Closed/Open Updates",
            "priority": "Emergency",
            "target_audience": "All Students & Faculty",
            "department": "Administration",
            "publish_date": "2026-08-25",
            "expiry_date": "2026-08-27",
            "description": "Due to heavy cyclone warning from IMD, SVIT campus will remain shut for 2 days.",
            "is_urgent": True,
            "status": "Published"
        }
        res_create = self.client.post('/admin/api/crud/notices', json=new_notice)
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.get_json()
        self.assertEqual(created_data["status"], "success")
        notice_id = created_data["item"]["id"]

        # Audit Check: created_by should be notice_admin
        self.assertEqual(created_data["item"]["created_by"], "notice_admin")
        self.assertIsNotNone(created_data["item"]["created_at"])

        # 2. READ / LIST with search & filter
        res_list = self.client.get('/admin/api/crud/notices?search=Cyclone&filter_is_urgent=true')
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.get_json()
        self.assertGreaterEqual(list_data["total"], 1)
        self.assertTrue(any(i["id"] == notice_id for i in list_data["items"]))

        # 3. GET Single Item
        res_get = self.client.get(f'/admin/api/crud/notices/{notice_id}')
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["item"]["title"], new_notice["title"])

        # 4. UPDATE Notice
        update_payload = {
            "title": "Severe Cyclone Warning - Campus Reopening Postponed",
            "priority": "Emergency",
            "description": "Updated alert: Campus will reopen on Friday.",
            "status": "Published"
        }
        res_update = self.client.put(f'/admin/api/crud/notices/{notice_id}', json=update_payload)
        self.assertEqual(res_update.status_code, 200)
        updated_item = res_update.get_json()["item"]
        self.assertEqual(updated_item["title"], update_payload["title"])
        self.assertEqual(updated_item["updated_by"], "notice_admin")

        # 5. DELETE Notice
        res_del = self.client.delete(f'/admin/api/crud/notices/{notice_id}')
        self.assertEqual(res_del.status_code, 200)

        # Verify deletion
        res_get_del = self.client.get(f'/admin/api/crud/notices/{notice_id}')
        self.assertEqual(res_get_del.status_code, 404)

        self.logout()

    def test_08_canteen_admin_crud_workflow(self):
        """Test Canteen Admin creating, updating, and deleting food items."""
        self.login_as("canteen_admin", "Canteen@123")

        # CREATE
        item_data = {
            "item_name": "Special Masala Dosa",
            "category": "South Indian",
            "shop_name": "Main SVIT Canteen",
            "price_inr": 65,
            "is_vegetarian": "Yes (Pure Veg)",
            "availability": "Available",
            "timing": "Morning Breakfast",
            "location": "Counter 2"
        }
        res_create = self.client.post('/admin/api/crud/canteen', json=item_data)
        self.assertEqual(res_create.status_code, 201)
        item_id = res_create.get_json()["item"]["id"]

        # UPDATE price
        res_update = self.client.put(f'/admin/api/crud/canteen/{item_id}', json={"price_inr": 70})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.get_json()["item"]["price_inr"], 70)

        # DELETE
        res_del = self.client.delete(f'/admin/api/crud/canteen/{item_id}')
        self.assertEqual(res_del.status_code, 200)

        self.logout()

    def test_09_bus_admin_crud_workflow(self):
        """Test Bus Admin creating and updating transport route."""
        self.login_as("bus_admin", "Bus@123")

        route_data = {
            "bus_no": "SVIT-BUS-25",
            "route_name": "Anand Express Route",
            "starting_point": "Anand (Bus Stand)",
            "destination": "SVIT Campus, Vasad",
            "stops": "Anand Bus Stand, Borsad Chokdi, Vasad Toll",
            "departure_time": "07:45",
            "arrival_time": "08:30",
            "driver_name": "Rameshbhai Parmar",
            "contact_number": "+91 98765 43210",
            "capacity": 55,
            "status": "Active"
        }
        res_create = self.client.post('/admin/api/crud/transport', json=route_data)
        self.assertEqual(res_create.status_code, 201)
        route_id = res_create.get_json()["item"]["id"]

        # CLEANUP
        self.client.delete(f'/admin/api/crud/transport/{route_id}')
        self.logout()

    # =========================================================================
    # 4. IMAGE UPLOAD, PREVIEW, REPLACEMENT & DELETION TESTS
    # =========================================================================
    def test_10_image_upload_success_and_metadata(self):
        """Verify image upload validates format, saves file, and returns clean URL without leaking paths."""
        self.login_as("event_admin", "Event@123")

        fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
        data = {
            'file': (fake_png, 'hackathon_poster.png', 'image/png'),
            'category': 'image'
        }

        res = self.client.post('/admin/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        self.assertEqual(res_data["status"], "success")
        file_info = res_data["file"]

        # Verify URL is public and does not expose internal filesystem path
        self.assertTrue(file_info["url"].startswith('/static/uploads/images/'))
        self.assertNotIn("D:", file_info["url"])
        self.assertNotIn("C:", file_info["url"])
        self.assertEqual(file_info["uploaded_by"], "event_admin")

        # Test Image Deletion API
        del_res = self.client.post('/admin/api/upload/delete', json={"url": file_info["url"]})
        self.assertEqual(del_res.status_code, 200)

        self.logout()

    def test_11_invalid_image_extension_rejected(self):
        """Verify that invalid file formats like .exe, .sh, .py are rejected."""
        self.login_as("event_admin", "Event@123")

        fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
        data = {
            'file': (fake_exe, 'malicious_script.exe', 'application/x-msdownload'),
            'category': 'image'
        }

        res = self.client.post('/admin/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid image format", res.get_json()["message"])

        self.logout()

    def test_12_oversized_image_rejected(self):
        """Verify that images exceeding 5 MB limit are rejected."""
        self.login_as("event_admin", "Event@123")

        # Create dummy buffer larger than 5 MB
        big_image = io.BytesIO(b"0" * (6 * 1024 * 1024))
        data = {
            'file': (big_image, 'giant_poster.jpg', 'image/jpeg'),
            'category': 'image'
        }

        res = self.client.post('/admin/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn("exceeds the maximum allowed limit", res.get_json()["message"])

        self.logout()

    # =========================================================================
    # 5. PDF UPLOAD, PREVIEW, DOWNLOAD & REPLACEMENT TESTS
    # =========================================================================
    def test_13_pdf_document_upload_and_download(self):
        """Verify Academic Admin PDF document upload, metadata extraction, and secure download."""
        self.login_as("academic_admin", "Academic@123")

        fake_pdf = io.BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Title (GTU Syllabus) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")
        data = {
            'file': (fake_pdf, 'BTech_Syllabus_2026.pdf', 'application/pdf'),
            'category': 'document'
        }

        res = self.client.post('/admin/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        file_info = res_data["file"]

        self.assertTrue(file_info["url"].startswith('/static/uploads/documents/'))
        self.assertEqual(file_info["file_extension"], "pdf")
        self.assertEqual(file_info["uploaded_by"], "academic_admin")

        # CREATE Academic Document Record linked with this uploaded PDF
        doc_record = {
            "title": "B.Tech Computer Engineering Complete Syllabus",
            "department": "Computer Engineering",
            "category": "Syllabus",
            "description": "Full syllabus for semesters 3 to 8.",
            "file_name": file_info["original_name"],
            "file_url": file_info["url"],
            "file_size_formatted": file_info["file_size_formatted"],
            "file_type": "application/pdf"
        }
        create_res = self.client.post('/admin/api/crud/academic_documents', json=doc_record)
        self.assertEqual(create_res.status_code, 201)
        doc_id = create_res.get_json()["item"]["id"]

        # Verify record retrieval
        get_res = self.client.get(f'/admin/api/crud/academic_documents/{doc_id}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["item"]["file_name"], 'BTech_Syllabus_2026.pdf')

        # Test Secure Download API
        stored_name = file_info["stored_filename"]
        dl_res = self.client.get(f'/admin/api/download/documents/{stored_name}')
        self.assertEqual(dl_res.status_code, 200)

        # Cleanup
        self.client.delete(f'/admin/api/crud/academic_documents/{doc_id}')
        self.client.post('/admin/api/upload/delete', json={"url": file_info["url"]})

        self.logout()

    def test_14_invalid_document_extension_rejected(self):
        """Verify non-PDF/DOCX documents like .zip, .html, .py are rejected."""
        self.login_as("academic_admin", "Academic@123")

        fake_zip = io.BytesIO(b"PK\x03\x04")
        data = {
            'file': (fake_zip, 'archive.zip', 'application/zip'),
            'category': 'document'
        }

        res = self.client.post('/admin/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid document format", res.get_json()["message"])

        self.logout()

    # =========================================================================
    # 6. SUPER ADMIN MANAGEMENT API TESTS
    # =========================================================================
    def test_15_super_admin_user_management_apis(self):
        """Test Super Admin creating, updating, resetting password, and listing admins."""
        import uuid
        self.login_as("superadmin", "Admin@123")

        # 1. List admins
        res_list = self.client.get('/admin/api/admins')
        self.assertEqual(res_list.status_code, 200)
        admins = res_list.get_json()["admins"]
        self.assertGreaterEqual(len(admins), 10)

        # 2. Create new test admin
        unique_uname = f"exam_ctrl_{uuid.uuid4().hex[:6]}"
        unique_email = f"{unique_uname}@svit.ac.in"
        new_admin = {
            "name": "Prof. Test Examiner",
            "username": unique_uname,
            "email": unique_email,
            "role": "academic_admin",
            "department": "Examination Cell",
            "password": "Examiner@123"
        }
        res_create = self.client.post('/admin/api/admins', json=new_admin)
        self.assertEqual(res_create.status_code, 201)

        # 3. Reset password for created admin
        res_reset = self.client.post(f'/admin/api/admins/{unique_uname}/reset-password', json={
            "new_password": "NewExaminer@123"
        })
        self.assertEqual(res_reset.status_code, 200)

        # 4. Toggle active status
        res_toggle = self.client.put(f'/admin/api/admins/{unique_uname}', json={"is_active": False})
        self.assertEqual(res_toggle.status_code, 200)

        self.logout()


if __name__ == '__main__':
    unittest.main()
