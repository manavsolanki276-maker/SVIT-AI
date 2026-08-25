"""
tests/test_step1_rbac.py
Comprehensive Step 1 RBAC Acceptance Test Suite for SVIT Admin System.
Tests all roles, authentication paths, hashing security, disabled account handling,
and backend permission boundaries.
"""
import unittest
import json
import sys
import os

# Set project root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.database.models.admin import Admin
from app.database.admin_seed import seed_admin_accounts, DEFAULT_ADMIN_ACCOUNTS
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
    has_permission,
    has_role,
    get_role_permissions,
)


class TestStep1AdminRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initializes test application context and database."""
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()
            seed_admin_accounts(cls.app)

    def test_01_password_hashing_in_database(self):
        """Verify that passwords are securely hashed and plaintext is never stored."""
        with self.app.app_context():
            admins = Admin.query.all()
            self.assertGreaterEqual(len(admins), 10, "Should have at least 10 seeded admins")

            for admin in admins:
                # Password hash must exist and not be empty
                self.assertTrue(admin.password_hash, f"Admin {admin.username} must have a password_hash")
                # Must not equal any common plaintext passwords
                for plain in ["Admin@123", "Academic@123", "Admission@123", "Notice@123", "Event@123", "Bus@123", "Library@123", "Canteen@123", "Sports@123", "Disabled@123", "admin123", "password"]:
                    self.assertNotEqual(admin.password_hash, plain, f"Password for {admin.username} is stored in plaintext!")
                # Must be a salted hash format (e.g. pbkdf2:sha256, scrypt, argon2)
                self.assertTrue(
                    admin.password_hash.startswith(('pbkdf2:', 'scrypt:', '$argon2', '$2b$', '$2a$')),
                    f"Hash for {admin.username} does not use standard secure algorithm: {admin.password_hash[:15]}"
                )

    def test_02_password_hash_never_exposed_in_api_or_to_dict(self):
        """Verify that password and password_hash are NEVER exposed in to_dict() or API endpoints."""
        with self.app.app_context():
            admin = Admin.query.filter_by(username='superadmin').first()
            d = admin.to_dict()
            self.assertNotIn("password", d)
            self.assertNotIn("password_hash", d)
            self.assertEqual(d["username"], "superadmin")
            self.assertEqual(d["role"], "super_admin")
            self.assertTrue(isinstance(d["permissions"], list))

        # Test via login API response
        res = self.client.post('/admin/login', json={
            "identifier": "superadmin",
            "password": "Admin@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("admin", data)
        self.assertNotIn("password", data["admin"])
        self.assertNotIn("password_hash", data["admin"])

    def test_03_super_admin_login_works(self):
        """Verify that Super Admin can log in successfully."""
        res = self.client.post('/admin/login', json={
            "identifier": "superadmin",
            "password": "Admin@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["admin"]["role"], "super_admin")

    def test_04_each_admin_role_can_login(self):
        """Verify that each configured admin role can log in successfully."""
        role_accounts = [
            ("superadmin", "Admin@123", ROLE_SUPER_ADMIN),
            ("academic_admin", "Academic@123", ROLE_ACADEMIC_ADMIN),
            ("admission_admin", "Admission@123", ROLE_ADMISSION_ADMIN),
            ("notice_admin", "Notice@123", ROLE_NOTICE_ADMIN),
            ("event_admin", "Event@123", ROLE_EVENT_ADMIN),
            ("bus_admin", "Bus@123", ROLE_BUS_ADMIN),
            ("library_admin", "Library@123", ROLE_LIBRARY_ADMIN),
            ("canteen_admin", "Canteen@123", ROLE_CANTEEN_ADMIN),
            ("sports_admin", "Sports@123", ROLE_SPORTS_ADMIN),
        ]

        for username, password, expected_role in role_accounts:
            with self.subTest(username=username, role=expected_role):
                res = self.client.post('/admin/login', json={
                    "identifier": username,
                    "password": password
                }, headers={"Accept": "application/json"})
                self.assertEqual(res.status_code, 200, f"Failed login for {username}")
                data = res.get_json()
                self.assertEqual(data["admin"]["role"], expected_role)
                self.assertEqual(data["admin"]["username"], username)
                # Logout to clean session
                self.client.get('/admin/logout')

    def test_05_username_login_works(self):
        """Verify login via username."""
        res = self.client.post('/admin/login', json={
            "identifier": "academic_admin",
            "password": "Academic@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["admin"]["username"], "academic_admin")
        self.client.get('/admin/logout')

    def test_06_email_login_works(self):
        """Verify login via email address (case-insensitive)."""
        res = self.client.post('/admin/login', json={
            "identifier": "ACADEMIC@SVIT.AC.IN",
            "password": "Academic@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["admin"]["username"], "academic_admin")
        self.client.get('/admin/logout')

    def test_07_wrong_password_rejected(self):
        """Verify that incorrect passwords return 401 Unauthorized."""
        res = self.client.post('/admin/login', json={
            "identifier": "superadmin",
            "password": "WrongPassword!999"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Invalid admin credentials", data["message"])

    def test_08_nonexistent_admin_rejected(self):
        """Verify that non-existent username/email returns 401 Unauthorized."""
        res = self.client.post('/admin/login', json={
            "identifier": "ghost_admin_9999",
            "password": "SomePassword@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 401)

    def test_09_disabled_admin_cannot_login(self):
        """Verify that a deactivated admin account cannot log in and returns 403 Forbidden."""
        res = self.client.post('/admin/login', json={
            "identifier": "disabled_admin",
            "password": "Disabled@123"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data["error"], "Forbidden")
        self.assertIn("Account is disabled", data["message"])

    def test_10_last_login_tracking(self):
        """Verify that last_login timestamp updates on successful login."""
        with self.app.app_context():
            admin = Admin.query.filter_by(username='canteen_admin').first()
            old_login = admin.last_login

        self.client.post('/admin/login', json={
            "identifier": "canteen_admin",
            "password": "Canteen@123"
        }, headers={"Accept": "application/json"})

        with self.app.app_context():
            admin = Admin.query.filter_by(username='canteen_admin').first()
            self.assertIsNotNone(admin.last_login)
            if old_login:
                self.assertGreaterEqual(admin.last_login, old_login)
        self.client.get('/admin/logout')

    def test_11_super_admin_has_full_access(self):
        """Verify Super Admin can access every module API."""
        # Login as superadmin
        self.client.post('/admin/login', json={
            "identifier": "superadmin",
            "password": "Admin@123"
        }, headers={"Accept": "application/json"})

        endpoints = [
            '/admin/api/test/super-admin-only',
            '/admin/api/test/academic',
            '/admin/api/test/admission',
            '/admin/api/test/notices',
            '/admin/api/test/events',
            '/admin/api/test/bus',
            '/admin/api/test/library',
            '/admin/api/test/canteen',
            '/admin/api/test/sports',
        ]

        for ep in endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep, headers={"Accept": "application/json"})
                self.assertEqual(res.status_code, 200, f"Super Admin failed access to {ep}")

        self.client.get('/admin/logout')

    def test_12_bus_admin_cannot_access_unauthorized_apis(self):
        """Verify Bus Admin can access Bus APIs but is denied (403) from Library, Canteen, Academic, etc."""
        # Login as bus_admin
        self.client.post('/admin/login', json={
            "identifier": "bus_admin",
            "password": "Bus@123"
        }, headers={"Accept": "application/json"})

        # Bus Admin ALLOWED:
        res_bus = self.client.get('/admin/api/test/bus', headers={"Accept": "application/json"})
        self.assertEqual(res_bus.status_code, 200)

        # Bus Admin DENIED (403 Forbidden):
        unauthorized_endpoints = [
            '/admin/api/test/super-admin-only',
            '/admin/api/test/library',
            '/admin/api/test/canteen',
            '/admin/api/test/academic',
            '/admin/api/test/admission',
            '/admin/api/test/notices',
            '/admin/api/test/events',
            '/admin/api/test/sports',
        ]

        for ep in unauthorized_endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep, headers={"Accept": "application/json"})
                self.assertEqual(res.status_code, 403, f"Bus Admin should be denied 403 from {ep}, got {res.status_code}")

        self.client.get('/admin/logout')

    def test_13_sports_admin_cannot_access_college_events(self):
        """Verify Sports Admin can access Sports APIs but is strictly denied (403) from College Events."""
        # Login as sports_admin
        self.client.post('/admin/login', json={
            "identifier": "sports_admin",
            "password": "Sports@123"
        }, headers={"Accept": "application/json"})

        # Sports Admin ALLOWED:
        res_sports = self.client.get('/admin/api/test/sports', headers={"Accept": "application/json"})
        self.assertEqual(res_sports.status_code, 200)

        # Sports Admin DENIED from College Events:
        res_events = self.client.get('/admin/api/test/events', headers={"Accept": "application/json"})
        self.assertEqual(res_events.status_code, 403, "Sports Admin must NOT have access to general College Events API")

        # Sports Admin DENIED from Library, Canteen, Academic:
        self.assertEqual(self.client.get('/admin/api/test/library', headers={"Accept": "application/json"}).status_code, 403)
        self.assertEqual(self.client.get('/admin/api/test/canteen', headers={"Accept": "application/json"}).status_code, 403)
        self.assertEqual(self.client.get('/admin/api/test/academic', headers={"Accept": "application/json"}).status_code, 403)

        self.client.get('/admin/logout')

    def test_14_event_admin_cannot_access_sports_events(self):
        """Verify Event Admin can access College Events but is strictly denied (403) from Sports."""
        # Login as event_admin
        self.client.post('/admin/login', json={
            "identifier": "event_admin",
            "password": "Event@123"
        }, headers={"Accept": "application/json"})

        # Event Admin ALLOWED for Events:
        res_events = self.client.get('/admin/api/test/events', headers={"Accept": "application/json"})
        self.assertEqual(res_events.status_code, 200)

        # Event Admin DENIED for Sports:
        res_sports = self.client.get('/admin/api/test/sports', headers={"Accept": "application/json"})
        self.assertEqual(res_sports.status_code, 403, "Event Admin must NOT have access to Sports API")

        self.client.get('/admin/logout')

    def test_15_api_me_returns_profile_without_secret_leak(self):
        """Verify /admin/api/me returns active admin profile and permissions without secrets."""
        # Login as library_admin
        self.client.post('/admin/login', json={
            "identifier": "library_admin",
            "password": "Library@123"
        }, headers={"Accept": "application/json"})

        res = self.client.get('/admin/api/me', headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        admin_data = data["admin"]
        self.assertEqual(admin_data["role"], "library_admin")
        self.assertIn("library", admin_data["permissions"])
        self.assertNotIn("password", admin_data)
        self.assertNotIn("password_hash", admin_data)

        self.client.get('/admin/logout')


if __name__ == '__main__':
    unittest.main()
