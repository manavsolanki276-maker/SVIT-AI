import unittest
import json
from app import create_app
from app.database.admin_crud_service import AdminCRUDService

class TestAdminLibrarySystem(unittest.TestCase):
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
        self.assertEqual(res.status_code, 200, f"Login failed for {identifier}: {res.get_data(as_text=True)}")
        return res

    def logout(self):
        """Helper to log out."""
        return self.client.get('/admin/logout', headers={"Accept": "application/json"})

    def test_01_library_routes_render_200(self):
        """Verify Library Admin HTML routes render 200 for authenticated admin."""
        self.login_as("superadmin", "Admin@123")

        for path in ['/admin/library', '/admin/library-books', '/admin/library-issue-return', '/admin/library-members']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Route {path} failed to render 200")
            self.assertIn(b"SVIT Central Library Management", res.data, f"Route {path} missing header title")
            self.assertIn(b"Books Catalog", res.data, f"Route {path} missing Books Catalog tab")

        self.logout()

    def test_02_rbac_authorization(self):
        """Verify unauthenticated access is rejected and Super Admin / Library Admin are authorized."""
        # Unauthenticated access
        res = self.client.get('/admin/library', headers={"Accept": "application/json"})
        self.assertIn(res.status_code, [302, 401], "Unauthenticated user should be redirected or unauthorized")

        # Super Admin access
        self.login_as("superadmin", "Admin@123")
        res = self.client.get('/admin/library')
        self.assertEqual(res.status_code, 200)
        self.logout()

    def test_03_book_crud_lifecycle(self):
        """Verify full CREATE, READ, UPDATE, DELETE lifecycle on library_books."""
        self.login_as("superadmin", "Admin@123")
        test_book_id = "TEST_BK_AUTOMATED_999"

        # 1. CREATE Book
        payload = {
            "id": test_book_id,
            "title": "Automated Testing and Systems Verification",
            "author": "Dr. Manav Solanki",
            "department": "Computer Engineering",
            "subject": "Software Engineering",
            "isbn": "978-0132350884",
            "shelf_location": "Rack A-01 / Shelf 4",
            "total_copies": 3,
            "available_copies": 3,
            "issued_copies": 0,
            "status": "Available"
        }
        res_create = self.client.post('/admin/api/crud/library_books', json=payload)
        self.assertEqual(res_create.status_code, 201, f"Book creation failed: {res_create.get_data(as_text=True)}")
        data_create = res_create.get_json()
        self.assertEqual(data_create["status"], "success")
        self.assertEqual(data_create["item"]["id"], test_book_id)
        self.assertEqual(data_create["item"]["total_copies"], 3)
        self.assertEqual(data_create["item"]["available_copies"], 3)

        # 2. READ / GET Single Book
        res_get = self.client.get(f'/admin/api/crud/library_books/{test_book_id}')
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.get_json()
        self.assertEqual(data_get["item"]["title"], "Automated Testing and Systems Verification")
        self.assertEqual(data_get["item"]["author"], "Dr. Manav Solanki")

        # 3. UPDATE Book
        update_payload = {
            "title": "Automated Testing and Systems Verification (2nd Edition)",
            "total_copies": 4,
            "available_copies": 4
        }
        res_update = self.client.put(f'/admin/api/crud/library_books/{test_book_id}', json=update_payload)
        self.assertEqual(res_update.status_code, 200)
        data_update = res_update.get_json()
        self.assertIn("2nd Edition", data_update["item"]["title"])
        self.assertEqual(data_update["item"]["total_copies"], 4)

        # 4. DELETE Book
        res_delete = self.client.delete(f'/admin/api/crud/library_books/{test_book_id}')
        self.assertEqual(res_delete.status_code, 200)

        # Verify Deleted
        res_verify = self.client.get(f'/admin/api/crud/library_books/{test_book_id}')
        self.assertEqual(res_verify.status_code, 404)
        self.logout()

    def test_04_dataset_pagination_20_and_50(self):
        """Verify pagination with 20 and 50 records per page on the library catalog."""
        self.login_as("superadmin", "Admin@123")

        # Page size 20
        res_20 = self.client.get('/admin/api/crud/library_books?limit=20&page=1')
        self.assertEqual(res_20.status_code, 200)
        data_20 = res_20.get_json()
        self.assertEqual(data_20["status"], "success")
        self.assertLessEqual(len(data_20["items"]), 20)
        self.assertGreaterEqual(data_20["total"], 20, "Library catalog should contain realistic dataset (>20 books)")

        # Page size 50
        res_50 = self.client.get('/admin/api/crud/library_books?limit=50&page=1')
        self.assertEqual(res_50.status_code, 200)
        data_50 = res_50.get_json()
        self.assertEqual(data_50["status"], "success")
        self.assertLessEqual(len(data_50["items"]), 50)
        self.assertGreaterEqual(data_50["total"], 50, "Library catalog should contain realistic dataset (>50 books)")

        # Verify page 2 is different from page 1
        res_page2 = self.client.get('/admin/api/crud/library_books?limit=20&page=2')
        self.assertEqual(res_page2.status_code, 200)
        data_page2 = res_page2.get_json()
        ids_p1 = [b["id"] for b in data_20["items"]]
        ids_p2 = [b["id"] for b in data_page2["items"]]
        self.assertNotEqual(ids_p1, ids_p2, "Page 2 records should differ from Page 1 records")

        self.logout()

    def test_05_issue_and_return_workflow_and_consistency(self):
        """Verify issue and return workflow, stock decrement/increment, and transaction records."""
        self.login_as("superadmin", "Admin@123")
        test_book_id = "TEST_CIRCULATION_BOOK_101"

        # Create book with 2 copies available
        create_res = self.client.post('/admin/api/crud/library_books', json={
            "id": test_book_id,
            "title": "Circulation Testing Essentials",
            "author": "SVIT Library QA",
            "department": "Information Technology",
            "total_copies": 2,
            "available_copies": 2,
            "issued_copies": 0,
            "status": "Available"
        })
        self.assertEqual(create_res.status_code, 201)

        # 1. Issue Book
        issue_res = self.client.post('/admin/api/library/issue', json={
            "book_id": test_book_id,
            "enrollment_no": "210410107001",
            "student_name": "Test Student Borrower",
            "due_date": "2026-09-22",
            "notes": "Automated verification checkout"
        })
        self.assertEqual(issue_res.status_code, 201, f"Issue failed: {issue_res.get_data(as_text=True)}")
        data_issue = issue_res.get_json()
        self.assertEqual(data_issue["status"], "success")
        issue_id = data_issue["issue"]["id"]

        # Verify book stock decremented: available=1, issued=1
        book_res1 = self.client.get(f'/admin/api/crud/library_books/{test_book_id}')
        book1 = book_res1.get_json()["item"]
        self.assertEqual(int(book1["available_copies"]), 1)
        self.assertEqual(int(book1["issued_copies"]), 1)

        # 2. Return Book
        return_res = self.client.post(f'/admin/api/library/return/{issue_id}')
        self.assertEqual(return_res.status_code, 200, f"Return failed: {return_res.get_data(as_text=True)}")
        data_return = return_res.get_json()
        self.assertEqual(data_return["status"], "success")
        self.assertEqual(data_return["issue"]["status"], "Returned")

        # Verify book stock restored: available=2, issued=0
        book_res2 = self.client.get(f'/admin/api/crud/library_books/{test_book_id}')
        book2 = book_res2.get_json()["item"]
        self.assertEqual(int(book2["available_copies"]), 2)
        self.assertEqual(int(book2["issued_copies"]), 0)

        # Clean up
        self.client.delete(f'/admin/api/crud/library_books/{test_book_id}')
        self.logout()

    def test_06_prevent_issue_when_unavailable(self):
        """Verify that trying to issue a book with 0 available copies is blocked."""
        self.login_as("superadmin", "Admin@123")
        test_book_id = "TEST_OUT_OF_STOCK_BOOK_102"

        # Create book with 0 available copies
        self.client.post('/admin/api/crud/library_books', json={
            "id": test_book_id,
            "title": "Rare Out of Stock Manuscript",
            "author": "Archivist",
            "department": "General Library",
            "total_copies": 1,
            "available_copies": 0,
            "issued_copies": 1,
            "status": "Out of Stock"
        })

        # Attempt to issue
        issue_res = self.client.post('/admin/api/library/issue', json={
            "book_id": test_book_id,
            "enrollment_no": "210410107002",
            "student_name": "Second Borrower",
            "due_date": "2026-09-22"
        })
        self.assertEqual(issue_res.status_code, 400, "Should block issuing an out of stock book")
        data = issue_res.get_json()
        self.assertIn("No available copies", data.get("message", ""))

        # Clean up
        self.client.delete(f'/admin/api/crud/library_books/{test_book_id}')
        self.logout()

    def test_07_prevent_delete_when_issued(self):
        """Verify that deleting a book with actively issued copies is prevented."""
        self.login_as("superadmin", "Admin@123")
        import uuid
        test_book_id = f"TEST_LOCKED_BOOK_{uuid.uuid4().hex[:6].upper()}"

        # Create book
        create_res = self.client.post('/admin/api/crud/library_books', json={
            "id": test_book_id,
            "title": "Active Lending Book",
            "author": "SVIT Library QA",
            "department": "Computer Engineering",
            "total_copies": 1,
            "available_copies": 1,
            "issued_copies": 0,
            "status": "Available"
        })
        self.assertEqual(create_res.status_code, 201, f"Create failed: {create_res.get_data(as_text=True)}")

        # Issue copy
        issue_res = self.client.post('/admin/api/library/issue', json={
            "book_id": test_book_id,
            "enrollment_no": "210410107003",
            "student_name": "Third Borrower",
            "due_date": "2026-09-22"
        })
        self.assertEqual(issue_res.status_code, 201, f"Issue failed: {issue_res.get_data(as_text=True)}")
        issue_id = issue_res.get_json()["issue"]["id"]

        # Attempt to delete book while issued
        del_res = self.client.delete(f'/admin/api/crud/library_books/{test_book_id}')
        self.assertEqual(del_res.status_code, 400, "Should reject deleting book with issued copies")
        self.assertIn("Cannot delete", del_res.get_json().get("message", ""))

        # Return book then delete
        ret_res = self.client.post(f'/admin/api/library/return/{issue_id}')
        self.assertEqual(ret_res.status_code, 200)

        del_res_success = self.client.delete(f'/admin/api/crud/library_books/{test_book_id}')
        self.assertEqual(del_res_success.status_code, 200)
        self.logout()

    def test_08_library_stats_and_members_endpoints(self):
        """Verify library stats endpoint and member search endpoint."""
        self.login_as("superadmin", "Admin@123")

        # Stats endpoint
        res_stats = self.client.get('/admin/api/library/stats')
        self.assertEqual(res_stats.status_code, 200)
        data_stats = res_stats.get_json()
        self.assertEqual(data_stats["status"], "success")
        stats = data_stats["stats"]
        self.assertIn("total_books", stats)
        self.assertIn("available_books", stats)
        self.assertIn("issued_books", stats)
        self.assertIn("total_members", stats)
        self.assertGreaterEqual(stats["total_books"], 1)

        # Members endpoint
        res_members = self.client.get('/admin/api/library/members?q=')
        self.assertEqual(res_members.status_code, 200)
        data_members = res_members.get_json()
        self.assertEqual(data_members["status"], "success")
        self.assertIsInstance(data_members["members"], list)

        self.logout()

if __name__ == '__main__':
    unittest.main()
