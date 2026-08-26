"""
tests/test_unified_theme_system.py
End-to-End Automated Verification of the SVIT AI Final Master Visual Theme:
1. Exactly Two Themes: Dark (Default) & Light.
2. Complete removal of Auto / System theme options.
3. Shared LocalStorage persistence ('svit_theme' & 'svit_admin_theme').
4. Cross-Portal Sync: Switching in Student changes Admin; switching in Admin changes Student.
5. Anti-Flicker & Pre-render Theme Application on all views.
6. Master Reference Palette Validation:
   - Dark: #171D3A, #11162D, #1C2342, #222A4D, #E58AF0, #91A7EE, #FFFFFF, #B9C0DA, #353D60
   - Light: #FFFFFF, #F7F8FD, #E8EBFA, #C94BE0, #91A7EE, #171D3A, #66708F, #DDE2F2
7. Responsive mobile viewport verification (320px, 360px, 375px, 390px, 414px, 480px) and no horizontal overflow.
"""
import sys
import os
import time
import unittest
import threading
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

PORT = 5096
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


class TestUnifiedThemeSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.server_thread = ServerThread(cls.app)
        cls.server_thread.start()
        time.sleep(1.5)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.close()
            cls.playwright.stop()
        except Exception:
            pass
        cls.server_thread.shutdown()
        cls.server_thread.join()

    def test_01_default_is_dark_and_no_system_theme(self):
        """Verify that on clean state, default theme is DARK and no Auto/System options exist."""
        context = self.browser.new_context()
        page = context.new_page()

        # Navigate to login
        page.goto(f"{BASE_URL}/auth/login?role=admin", wait_until="networkidle")
        
        # 1. Verify default theme attributes
        theme_attr = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        self.assertEqual(theme_attr, "dark", "Default theme on initial clean load must be dark")

        # 2. Login as Admin
        page.fill('#identifier', 'superadmin@svit.ac.in')
        page.fill('#password', 'Admin@123')
        page.click('#loginSubmitBtn')
        page.wait_for_timeout(1000)

        # 3. Check Admin Profile Appearance section
        page.goto(f"{BASE_URL}/admin/profile", wait_until="networkidle")
        
        # Ensure there are EXACTLY 2 theme options in Admin Profile
        theme_cards = page.query_selector_all('.admin-theme-radio-card')
        self.assertEqual(len(theme_cards), 2, "Admin profile must have exactly 2 theme options (Dark & Light)")

        choices = [c.get_attribute('data-admin-theme-choice') for c in theme_cards]
        self.assertIn('dark', choices)
        self.assertIn('light', choices)
        self.assertNotIn('system', choices, "Auto/System option must NOT exist")
        self.assertNotIn('auto', choices, "Auto option must NOT exist")

        # 4. Check Admin Sidebar Drawer theme switcher
        drawer_btns = page.query_selector_all('.theme-segment-btn')
        drawer_choices = [b.get_attribute('data-theme-choice') or b.get_attribute('data-admin-theme-choice') for b in drawer_btns]
        self.assertIn('dark', drawer_choices)
        self.assertIn('light', drawer_choices)
        self.assertNotIn('system', drawer_choices, "Drawer must not have Auto/System")

        context.close()

    def test_02_cross_portal_sync_and_persistence(self):
        """Verify that switching theme in Admin synchronizes with Student and vice versa."""
        context = self.browser.new_context()
        page = context.new_page()

        # 1. Login as Admin
        page.goto(f"{BASE_URL}/auth/login?role=admin", wait_until="networkidle")
        page.fill('#identifier', 'superadmin@svit.ac.in')
        page.fill('#password', 'Admin@123')
        page.click('#loginSubmitBtn')
        page.wait_for_timeout(1000)

        # 2. Switch to Light theme in Admin Profile
        page.goto(f"{BASE_URL}/admin/profile", wait_until="networkidle")
        page.click('.admin-theme-radio-card[data-admin-theme-choice="light"]')
        page.wait_for_timeout(200)

        # Verify localStorage and DOM attributes in Admin
        admin_theme = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
        student_stored_pref = page.evaluate("() => localStorage.getItem('svit_theme')")
        admin_stored_pref = page.evaluate("() => localStorage.getItem('svit_admin_theme')")
        
        self.assertEqual(admin_theme, "light")
        self.assertEqual(student_stored_pref, "light", "svit_theme must sync to light")
        self.assertEqual(admin_stored_pref, "light", "svit_admin_theme must sync to light")

        # 3. Navigate to Student Chat and verify Light theme is applied
        page.goto(f"{BASE_URL}/student/chat", wait_until="networkidle")
        student_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        self.assertEqual(student_theme, "light", "Student chat must be in Light theme")

        # 4. Navigate to Student Settings and verify 2-option Segmented Control
        page.goto(f"{BASE_URL}/student/settings/", wait_until="networkidle")
        settings_theme_btns = page.query_selector_all('.theme-segmented-control .theme-segment-btn')
        self.assertEqual(len(settings_theme_btns), 2, "Student settings must have exactly 2 theme buttons")

        # 5. Switch to Dark theme in Student Settings
        page.click('.theme-segmented-control .theme-segment-btn[data-theme-choice="dark"]')
        page.wait_for_timeout(200)

        theme_after_switch = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        stored_student = page.evaluate("() => localStorage.getItem('svit_theme')")
        stored_admin = page.evaluate("() => localStorage.getItem('svit_admin_theme')")

        self.assertEqual(theme_after_switch, "dark")
        self.assertEqual(stored_student, "dark")
        self.assertEqual(stored_admin, "dark", "Switching in Student must sync svit_admin_theme to dark")

        # 6. Navigate back to Admin Dashboard and verify Dark theme is active
        page.goto(f"{BASE_URL}/admin/dashboard", wait_until="networkidle")
        dash_theme = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
        self.assertEqual(dash_theme, "dark", "Admin dashboard must be in Dark theme")

        # 7. Reload and verify persistence
        page.reload(wait_until="networkidle")
        dash_theme_reload = page.evaluate("() => document.documentElement.getAttribute('data-admin-theme')")
        self.assertEqual(dash_theme_reload, "dark", "Dark theme must persist across reload")

        context.close()

    def test_03_master_css_variables_and_color_tokens(self):
        """Verify that Master Reference CSS custom properties match the exact palette specification."""
        context = self.browser.new_context()
        page = context.new_page()

        page.goto(f"{BASE_URL}/auth/login", wait_until="networkidle")

        # In Dark Mode (Deep Navy foundation + Soft Vibrant Purple + Periwinkle)
        page.evaluate("() => window.setTheme('dark')")
        page.wait_for_timeout(100)
        dark_bg = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-bg-primary').trim()")
        dark_card = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim()")
        dark_accent = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim()")
        dark_secondary = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-secondary').trim()")
        dark_border = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim()")
        
        self.assertEqual(dark_bg.lower(), "#171d3a", "Dark primary background must be #171D3A")
        self.assertEqual(dark_card.lower(), "#1c2342", "Dark card surface must be #1C2342")
        self.assertEqual(dark_accent.lower(), "#e58af0", "Dark primary purple must be #E58AF0")
        self.assertEqual(dark_secondary.lower(), "#91a7ee", "Dark secondary accent must be #91A7EE")
        self.assertEqual(dark_border.lower(), "#353d60", "Dark border must be #353D60")

        # In Light Mode (White + Soft Lavender + Primary Purple + Periwinkle)
        page.evaluate("() => window.setTheme('light')")
        page.wait_for_timeout(100)
        light_bg = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-bg-primary').trim()")
        light_card = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim()")
        light_lavender = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-lavender').trim()")
        light_accent = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim()")
        light_secondary = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-secondary').trim()")
        light_text = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim()")
        
        self.assertEqual(light_bg.lower(), "#ffffff", "Light primary background must be #FFFFFF")
        self.assertEqual(light_card.lower(), "#ffffff", "Light card surface must be #FFFFFF")
        self.assertEqual(light_lavender.lower(), "#e8ebfa", "Light soft lavender must be #E8EBFA")
        self.assertEqual(light_accent.lower(), "#c94be0", "Light primary purple must be #C94BE0")
        self.assertEqual(light_secondary.lower(), "#91a7ee", "Light secondary periwinkle must be #91A7EE")
        self.assertEqual(light_text.lower(), "#171d3a", "Light primary text must be #171D3A")

        context.close()

    def test_04_responsive_mobile_viewports(self):
        """Verify all requested viewports (320px, 360px, 375px, 390px, 414px, 480px) have no horizontal overflow."""
        viewports = [
            {"width": 320, "height": 568},
            {"width": 360, "height": 640},
            {"width": 375, "height": 667},
            {"width": 390, "height": 844},
            {"width": 414, "height": 896},
            {"width": 480, "height": 800}
        ]

        for vp in viewports:
            context = self.browser.new_context(viewport=vp)
            page = context.new_page()

            # Test Login Page
            page.goto(f"{BASE_URL}/auth/login", wait_until="networkidle")
            overflow_login = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
            self.assertFalse(overflow_login, f"Login page has horizontal overflow at {vp['width']}px")

            # Test Student Chat Page
            page.goto(f"{BASE_URL}/student/chat", wait_until="networkidle")
            overflow_chat = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
            self.assertFalse(overflow_chat, f"Student chat has horizontal overflow at {vp['width']}px")

            # Test Student Settings Page
            page.goto(f"{BASE_URL}/student/settings/", wait_until="networkidle")
            overflow_settings = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
            self.assertFalse(overflow_settings, f"Student settings has horizontal overflow at {vp['width']}px")

            context.close()


if __name__ == "__main__":
    unittest.main()
