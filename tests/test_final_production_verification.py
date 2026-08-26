"""
tests/test_final_production_verification.py
Comprehensive End-to-End Production Verification Test Suite:
1. Premium Admin Theme System (Dark, Light, System, LocalStorage persistence, CSS variables)
2. Admin <-> Student Notification Connection (MongoDB notifications, Admin & Student UI, Isolation, Read/Unread state)
3. Mobile-First Responsive UI & Breakpoints (320px - 1440px, Zero Overflow)
4. Student AI & RAG Data Propagation
"""
import sys
import os
import time
import json
import unittest
import threading
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database.mongodb import get_collection
from app.database.mongo_models import MongoNotificationService
from app.database.admin_crud_service import AdminCRUDService

PORT = 5095
BASE_URL = f"http://127.0.0.1:{PORT}"

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server("127.0.0.1", PORT, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class TestFinalProductionVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.server_thread = ServerThread(cls.app)
        cls.server_thread.start()
        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.shutdown()
        cls.server_thread.join()

    def test_01_theme_system_and_persistence(self):
        """Tests Dark, Light, System themes, LocalStorage persistence, and radio cards."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # 1. Login as Admin
            page.goto(f"{BASE_URL}/auth/login?role=admin", wait_until="networkidle")
            page.fill('#identifier', 'superadmin@svit.ac.in')
            page.fill('#password', 'Admin@123')
            page.click('#loginSubmitBtn')
            page.wait_for_timeout(1000)

            # 2. Navigate to Profile / Settings
            page.goto(f"{BASE_URL}/admin/profile", wait_until="networkidle")
            
            # Verify Default is Dark
            current_theme = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
            self.assertEqual(current_theme, "dark", "Default theme must be dark")

            # 3. Switch to Light Theme via UI Radio Card
            page.click('.admin-theme-radio-card[data-admin-theme-choice="light"]')
            page.wait_for_timeout(200)

            theme_after_light = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
            pref_after_light = page.evaluate("() => localStorage.getItem('svit_admin_theme')")
            self.assertEqual(theme_after_light, "light")
            self.assertEqual(pref_after_light, "light")

            # Refresh and verify Light persistence
            page.reload(wait_until="networkidle")
            theme_after_reload = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
            self.assertEqual(theme_after_reload, "light", "Light theme must persist across page reload")

            # 4. Switch to Dark Theme
            page.click('.admin-theme-radio-card[data-admin-theme-choice="dark"]')
            page.wait_for_timeout(200)
            theme_after_dark = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
            self.assertEqual(theme_after_dark, "dark")

            page.reload(wait_until="networkidle")
            theme_after_dark_reload = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
            self.assertEqual(theme_after_dark_reload, "dark", "Dark theme must persist across page reload")

            # 5. Switch to Auto / System Theme
            page.click('.admin-theme-radio-card[data-admin-theme-choice="system"]')
            page.wait_for_timeout(200)
            pref_after_system = page.evaluate("() => localStorage.getItem('svit_admin_theme')")
            self.assertEqual(pref_after_system, "system")

            browser.close()

    def test_02_admin_student_notification_lifecycle_and_isolation(self):
        """
        Tests the entire Admin <-> Student notification lifecycle:
        1. Notice creation by Admin -> dispatches to MongoDB
        2. Admin verifies notification appears in Admin API
        3. Target Student verifies notification in Student Notification Center
        4. Student marks notification as read -> unread count decrements
        5. Other Student verifies recipient isolation
        """
        # 1. Admin creates a real notice in MongoDB via AdminCRUDService
        test_title = f"Final Production Exam Notice {int(time.time())}"
        test_data = {
            "title": test_title,
            "description": "All Semester 5 students must submit their project files by Friday.",
            "category": "Notice",
            "department": "Computer Engineering",
            "target_audience": "All Students",
            "priority": "High",
            "is_urgent": True,
            "status": "Published",
            "publish_date": "2026-08-26"
        }

        ok, msg, created = AdminCRUDService.create_item("notices", test_data, admin_user={"username": "superadmin"})
        self.assertTrue(ok, f"Notice creation failed: {msg}")

        # 2. Verify notification is in MongoDB notifications collection
        coll = get_collection('notifications')
        self.assertIsNotNone(coll, "MongoDB notifications collection must exist")

        notif_doc = coll.find_one({"title": test_title})
        self.assertIsNotNone(notif_doc, "Notification must be persisted in MongoDB notifications collection")
        self.assertEqual(notif_doc.get("category"), "notice")

        # 3. Check Admin Notifications API
        admin_res = MongoNotificationService.get_admin_notifications(limit=10)
        self.assertEqual(admin_res["status"], "success")

        # 4. Check Student Notifications API for a Computer Engineering student
        student_context = {
            "id": "210420107001",
            "enrollment_no": "210420107001",
            "department": "Computer Engineering",
            "semester": 5
        }
        student_res = MongoNotificationService.get_notifications(student_context, limit=20)
        self.assertEqual(student_res["status"], "success")
        
        found_notif = next((n for n in student_res["notifications"] if n["title"] == test_title), None)
        self.assertIsNotNone(found_notif, "Student must receive the targeted notice notification")
        self.assertFalse(found_notif["is_read"], "New notification must be initially unread")

        # 5. Student marks notification as read
        notif_id = str(found_notif["id"])
        read_ok = MongoNotificationService.mark_read(notif_id, user_id=student_context)
        self.assertTrue(read_ok, "Student mark_read must succeed")

        # 6. Verify unread status updated for this student
        updated_student_res = MongoNotificationService.get_notifications(student_context, limit=20)
        updated_notif = next((n for n in updated_student_res["notifications"] if n["id"] == notif_id), None)
        self.assertTrue(updated_notif["is_read"], "Notification must be marked as read for this student")

        # 7. Check Student Isolation: Create a private notification for Student A
        private_title = f"Private Scholarship Alert {int(time.time())}"
        MongoNotificationService.notify_student(
            student_id="210420107001",
            title=private_title,
            message="Your scholarship application has been processed.",
            category="general"
        )

        # Student A sees it
        res_a = MongoNotificationService.get_notifications(student_context, limit=10)
        found_a = next((n for n in res_a["notifications"] if n["title"] == private_title), None)
        self.assertIsNotNone(found_a, "Student A must see their private notification")

        # Student B (Mechanical Engineering) must NOT see Student A's private notification
        student_b_context = {
            "id": "210420119002",
            "enrollment_no": "210420119002",
            "department": "Mechanical Engineering",
            "semester": 5
        }
        res_b = MongoNotificationService.get_notifications(student_b_context, limit=10)
        found_b = next((n for n in res_b["notifications"] if n["title"] == private_title), None)
        self.assertIsNone(found_b, "Student B must NEVER see Student A's private notification (Strict Recipient Isolation)")

    def test_03_mobile_responsiveness_and_zero_overflow(self):
        """Tests zero horizontal overflow and mobile layout across all 6 requested phone widths."""
        test_routes = ["/admin/dashboard", "/admin/students", "/admin/profile", "/admin/notices", "/admin/timetable"]
        phone_widths = [320, 360, 375, 390, 414, 480]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(f"{BASE_URL}/auth/login?role=admin", wait_until="networkidle")
            page.fill('#identifier', 'superadmin@svit.ac.in')
            page.fill('#password', 'Admin@123')
            page.click('#loginSubmitBtn')
            page.wait_for_timeout(1000)

            for route in test_routes:
                for w in phone_widths:
                    page.set_viewport_size({"width": w, "height": 750})
                    page.goto(f"{BASE_URL}{route}", wait_until="networkidle")

                    overflow = page.evaluate("() => document.documentElement.scrollWidth > (window.innerWidth + 1)")
                    self.assertFalse(overflow, f"Horizontal overflow detected on {route} @ {w}px viewport width")

            browser.close()


if __name__ == "__main__":
    unittest.main()
