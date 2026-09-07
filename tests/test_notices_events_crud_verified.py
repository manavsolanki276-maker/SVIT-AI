import unittest
import json
from app import create_app
from app.database.admin_crud_service import AdminCRUDService

class TestNoticesAndEventsCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def login_as(self, identifier: str = "superadmin", password: str = "Admin@123"):
        """Helper to log in as admin."""
        res = self.client.post('/admin/login', json={
            "identifier": identifier,
            "password": password
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 200, f"Login failed for {identifier}")
        return res

    def logout(self):
        """Helper to log out."""
        return self.client.get('/admin/logout', headers={"Accept": "application/json"})

    def test_01_page_routes_render_200(self):
        """Verify Notice Admin and Event Admin HTML views return HTTP 200."""
        self.login_as("superadmin", "Admin@123")
        res_notices = self.client.get('/admin/notices')
        self.assertEqual(res_notices.status_code, 200, "Notice Admin page /admin/notices failed to render 200")
        self.assertIn(b"Campus Notices", res_notices.data)

        res_events = self.client.get('/admin/events')
        self.assertEqual(res_events.status_code, 200, "Event Admin page /admin/events failed to render 200")
        self.assertIn(b"College Cultural", res_events.data)
        self.logout()

    def test_02_notice_admin_full_crud_workflow(self):
        """Verify full CRUD lifecycle on /admin/api/crud/notices."""
        self.login_as("superadmin", "Admin@123")

        test_notice_id = "VERIFIED_NOT_001"
        # 1. CREATE Notice
        payload = {
            "notice_id": test_notice_id,
            "title": "Automated Verification Cyclone Notice",
            "category": "Emergency Announcements",
            "priority": "Emergency",
            "department": "Administration",
            "target_audience": "All Students & Faculty",
            "publish_date": "2026-09-08",
            "expiry_date": "2026-09-10",
            "status": "Published",
            "is_urgent": True,
            "description": "Due to weather alert, classes are suspended tomorrow."
        }
        res_create = self.client.post('/admin/api/crud/notices', json=payload)
        self.assertEqual(res_create.status_code, 201, f"Notice creation failed: {res_create.get_data(as_text=True)}")
        data_create = res_create.get_json()
        self.assertEqual(data_create["status"], "success")
        self.assertEqual(data_create["item"]["id"], test_notice_id)
        self.assertTrue(data_create["item"]["is_urgent"])

        # 2. LIST & FILTER Notices
        res_list = self.client.get(f'/admin/api/crud/notices?search=Verification&filter_priority=Emergency')
        self.assertEqual(res_list.status_code, 200)
        data_list = res_list.get_json()
        self.assertGreaterEqual(data_list["total"], 1)
        self.assertTrue(any(item["id"] == test_notice_id for item in data_list["items"]))

        # 3. GET Single Notice
        res_get = self.client.get(f'/admin/api/crud/notices/{test_notice_id}')
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.get_json()
        self.assertEqual(data_get["item"]["title"], payload["title"])
        self.assertEqual(data_get["item"]["category"], payload["category"])

        # 4. UPDATE Notice
        update_payload = {
            "title": "Automated Verification Cyclone Notice - REOPENING",
            "priority": "Normal",
            "description": "Weather cleared. Campus reopens on Friday."
        }
        res_update = self.client.put(f'/admin/api/crud/notices/{test_notice_id}', json=update_payload)
        self.assertEqual(res_update.status_code, 200)
        data_update = res_update.get_json()
        self.assertEqual(data_update["item"]["title"], update_payload["title"])

        # 5. DELETE Notice
        res_del = self.client.delete(f'/admin/api/crud/notices/{test_notice_id}')
        self.assertEqual(res_del.status_code, 200)

        # 6. Verify Deletion
        res_get_deleted = self.client.get(f'/admin/api/crud/notices/{test_notice_id}')
        self.assertEqual(res_get_deleted.status_code, 404)
        self.logout()

    def test_03_event_admin_full_crud_workflow(self):
        """Verify full CRUD lifecycle on /admin/api/crud/events."""
        self.login_as("superadmin", "Admin@123")

        test_event_id = "VERIFIED_EVT_001"
        # 1. CREATE Event
        payload = {
            "event_id": test_event_id,
            "event_name": "SVIT National Hackathon 2026",
            "category": "Hackathons",
            "department": "Computer Engineering",
            "organizer": "CSI & IEEE Student Branch",
            "event_date": "2026-10-15",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "start_time": "09:00",
            "end_time": "18:00",
            "venue": "SVIT Central Auditorium",
            "speaker_or_guest": "Dr. Tech Speaker",
            "registration_required": "Yes",
            "registration_link": "https://svitvasad.ac.in/hackathon2026",
            "capacity": 250,
            "status": "Upcoming",
            "description": "36-hour code sprint for students with cash prize pool."
        }
        res_create = self.client.post('/admin/api/crud/events', json=payload)
        self.assertEqual(res_create.status_code, 201, f"Event creation failed: {res_create.get_data(as_text=True)}")
        data_create = res_create.get_json()
        self.assertEqual(data_create["status"], "success")
        self.assertEqual(data_create["item"]["id"], test_event_id)

        # 2. LIST & FILTER Events
        res_list = self.client.get('/admin/api/crud/events?search=Hackathon&filter_department=Computer+Engineering')
        self.assertEqual(res_list.status_code, 200)
        data_list = res_list.get_json()
        self.assertGreaterEqual(data_list["total"], 1)
        self.assertTrue(any(item["id"] == test_event_id for item in data_list["items"]))

        # 3. GET Single Event
        res_get = self.client.get(f'/admin/api/crud/events/{test_event_id}')
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.get_json()
        self.assertEqual(data_get["item"]["event_name"], payload["event_name"])
        self.assertEqual(data_get["item"]["venue"], payload["venue"])

        # 4. UPDATE Event
        update_payload = {
            "event_name": "SVIT National Hackathon 2026 (Grand Finale)",
            "venue": "SVIT Computer Engineering Block",
            "status": "Ongoing"
        }
        res_update = self.client.put(f'/admin/api/crud/events/{test_event_id}', json=update_payload)
        self.assertEqual(res_update.status_code, 200)
        data_update = res_update.get_json()
        self.assertEqual(data_update["item"]["event_name"], update_payload["event_name"])
        self.assertEqual(data_update["item"]["venue"], update_payload["venue"])

        # 5. DELETE Event
        res_del = self.client.delete(f'/admin/api/crud/events/{test_event_id}')
        self.assertEqual(res_del.status_code, 200)

        # 6. Verify Deletion
        res_get_deleted = self.client.get(f'/admin/api/crud/events/{test_event_id}')
        self.assertEqual(res_get_deleted.status_code, 404)
        self.logout()

if __name__ == '__main__':
    unittest.main()
