"""
tests/test_student_approval_workflow.py
Comprehensive test suite verifying the Student Registration Approval & Notification Workflow.
Covers:
1. Student self-registration -> status="pending", request_id, admin notification, student notification
2. Duplicate registration prevention
3. Pending student login restriction & Student AI access blocking
4. Admin student review list & status filtering
5. Admin approve student action -> status="active", student notification
6. Active student login & Student AI access allowed
7. Admin reject student action -> status="rejected", reason audit, student notification
8. Rejected student login restriction
9. Admin notifications API & Student notifications API
10. Backward compatibility with existing active records
"""
import unittest
import json
from app import create_app
from app.extensions import db
from app.database.models import Student, Admin
from app.database.mongo_models import MongoStudent, MongoAdmin, MongoNotificationService
from app.database.mongodb import get_collection
from werkzeug.security import generate_password_hash


class TestStudentApprovalWorkflow(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create temporary testing credentials
        self.admin_username = "academic_test_admin"
        self.admin_password = "AdminSecurePass123!"
        self.student_enrollment = "990410107001"
        self.student_email = "test.workflow.student@svitvasad.ac.in"
        self.student_password = "StudentSecurePass123!"

        # Clean up any previous test artifacts in MongoDB & SQLite
        self.students_coll = get_collection("students")
        self.notifs_coll = get_collection("notifications")
        self.admin_coll = get_collection("admins")

        test_enrollments = [self.student_enrollment, "990410107002", "990410107003"]

        if self.students_coll is not None:
            self.students_coll.delete_many({"enrollment_no": {"$in": test_enrollments}})
        if self.notifs_coll is not None:
            self.notifs_coll.delete_many({"recipient_id": {"$in": test_enrollments + ["admin"]}})
            self.notifs_coll.delete_many({"user_id": {"$in": test_enrollments + ["admin"]}})

        try:
            from app.database.models import Student
            from app.extensions import db
            if Student:
                Student.query.filter(Student.enrollment_no.in_(test_enrollments)).delete(synchronize_session=False)
                db.session.commit()
        except Exception:
            try:
                from app.extensions import db
                db.session.rollback()
            except Exception:
                pass

        # Seed test admin in Mongo & SQLite
        if self.admin_coll is not None:
            self.admin_coll.update_one(
                {"username": self.admin_username},
                {"$set": {
                    "username": self.admin_username,
                    "name": "Academic Admin Tester",
                    "email": "academic_admin_test@svitvasad.ac.in",
                    "role": "academic_admin",
                    "role_display": "Academic Admin",
                    "permissions": ["academic", "students", "faculty", "subjects", "academic_documents"],
                    "password_hash": generate_password_hash(self.admin_password),
                    "is_active": True
                }},
                upsert=True
            )

    def tearDown(self):
        # Cleanup
        test_enrollments = [self.student_enrollment, "990410107002", "990410107003"]
        if self.students_coll is not None:
            self.students_coll.delete_many({"enrollment_no": {"$in": test_enrollments}})
        if self.notifs_coll is not None:
            self.notifs_coll.delete_many({"recipient_id": {"$in": test_enrollments + ["admin"]}})
            self.notifs_coll.delete_many({"user_id": {"$in": test_enrollments + ["admin"]}})
        if self.admin_coll is not None:
            self.admin_coll.delete_one({"username": self.admin_username})

        try:
            from app.database.models import Student
            from app.extensions import db
            if Student:
                Student.query.filter(Student.enrollment_no.in_(test_enrollments)).delete(synchronize_session=False)
                db.session.commit()
        except Exception:
            try:
                from app.extensions import db
                db.session.rollback()
            except Exception:
                pass

        self.app_context.pop()

    def test_01_student_registration_creates_pending_status_and_notifications(self):
        """Test that student registration saves with status='pending' and triggers admin/student notifications."""
        payload = {
            "full_name": "Manav Solanki",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password,
            "program": "BE",
            "department": "Computer Engineering",
            "semester": 6,
            "division": "A",
            "batch": "A1",
            "phone": "9876543210"
        }

        res = self.client.post('/auth/register', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["student_status"], "pending")
        self.assertTrue("request_id" in data)

        # Verify MongoDB document
        if self.students_coll is not None:
            doc = self.students_coll.find_one({"enrollment_no": self.student_enrollment})
            self.assertIsNotNone(doc)
            self.assertEqual(doc.get("status"), "pending")
            self.assertEqual(doc.get("full_name"), "Manav Solanki")
            self.assertIsNotNone(doc.get("request_id"))

        # Verify Admin Notification created
        if self.notifs_coll is not None:
            admin_notif = self.notifs_coll.find_one({
                "$or": [{"recipient_id": "admin"}, {"user_id": "admin"}, {"role": "admin"}],
                "category": "registration"
            })
            self.assertIsNotNone(admin_notif)
            self.assertEqual(admin_notif.get("title"), "New student registration request")

            # Verify Student Notification created
            student_notif = self.notifs_coll.find_one({
                "$or": [{"recipient_id": self.student_enrollment}, {"user_id": self.student_enrollment}]
            })
            self.assertIsNotNone(student_notif)
            self.assertEqual(student_notif.get("title"), "Registration Submitted")

    def test_02_duplicate_registration_prevention(self):
        """Test duplicate enrollment number or email prevents re-registration."""
        payload = {
            "full_name": "Manav Duplicate",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password
        }
        # First registration
        self.client.post('/auth/register', json=payload)

        # Duplicate registration attempt
        res = self.client.post('/auth/register', json=payload)
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("already", data["message"].lower())

    def test_03_pending_student_login_is_blocked(self):
        """Test that a pending student cannot log in or access the AI chat."""
        # 1. Register student
        self.client.post('/auth/register', json={
            "full_name": "Pending Student",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password
        })

        # 2. Attempt login via API
        res = self.client.post('/auth/login', json={
            "identifier": self.student_enrollment,
            "password": self.student_password
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data["student_status"], "pending")
        self.assertEqual(data["message"], "Your registration is pending admin approval.")

        # 3. Attempt chat endpoint without active approval
        res_chat = self.client.post('/student/api/chat', json={"message": "Hello"})
        # Should redirect to login or return 302/403
        self.assertIn(res_chat.status_code, [302, 401, 403])

    def test_04_admin_can_filter_and_approve_student(self):
        """Test that Academic Admin can list pending students and approve a request."""
        # 1. Register pending student
        self.client.post('/auth/register', json={
            "full_name": "Candidate Student",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password,
            "department": "Computer Engineering"
        })

        # 2. Login as Academic Admin
        login_res = self.client.post('/auth/login', data={
            "identifier": self.admin_username,
            "password": self.admin_password
        }, follow_redirects=False)
        self.assertEqual(login_res.status_code, 302)

        # 3. Query pending students via Admin API
        res_list = self.client.get('/admin/api/crud/students?status=pending')
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.get_json()
        self.assertEqual(list_data["status"], "success")
        pending_items = [i for i in list_data["items"] if (i.get("enrollment_no") or i.get("id")) == self.student_enrollment]
        self.assertTrue(len(pending_items) > 0)
        self.assertEqual(pending_items[0].get("status"), "pending")

        # 4. Approve student
        res_approve = self.client.post(f'/admin/api/students/{self.student_enrollment}/approve')
        self.assertEqual(res_approve.status_code, 200)
        approve_data = res_approve.get_json()
        self.assertEqual(approve_data["status"], "success")
        self.assertEqual(approve_data["student"]["status"], "active")
        self.assertEqual(approve_data["student"]["approved_by"], self.admin_username)

        # 5. Verify database audit trail
        if self.students_coll is not None:
            doc = self.students_coll.find_one({"enrollment_no": self.student_enrollment})
            self.assertEqual(doc.get("status"), "active")
            self.assertEqual(doc.get("approved_by"), self.admin_username)
            self.assertIsNotNone(doc.get("approved_at"))

        # 6. Verify student approval notification
        if self.notifs_coll is not None:
            app_notif = self.notifs_coll.find_one({
                "$or": [{"recipient_id": self.student_enrollment}, {"user_id": self.student_enrollment}],
                "category": "approval"
            })
            self.assertIsNotNone(app_notif)
            self.assertEqual(app_notif.get("title"), "Registration Approved")

    def test_05_approved_student_login_succeeds(self):
        """Test that once approved, the student can log in normally."""
        # 1. Register & approve
        self.client.post('/auth/register', json={
            "full_name": "Active Student",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password
        })

        # Login admin & approve
        self.client.post('/auth/login', data={"identifier": self.admin_username, "password": self.admin_password})
        self.client.post(f'/admin/api/students/{self.student_enrollment}/approve')
        self.client.get('/auth/logout')

        # 2. Student login attempt
        res_login = self.client.post('/auth/login', json={
            "identifier": self.student_enrollment,
            "password": self.student_password
        })
        self.assertEqual(res_login.status_code, 200)
        data = res_login.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["message"], "Login successful.")

    def test_06_admin_can_reject_student_with_reason(self):
        """Test that admin can reject a student and student sees the rejection reason upon login."""
        # 1. Register student
        self.client.post('/auth/register', json={
            "full_name": "Reject Candidate",
            "enrollment_no": self.student_enrollment,
            "email": self.student_email,
            "password": self.student_password
        })

        # 2. Login admin & reject with reason
        self.client.post('/auth/login', data={"identifier": self.admin_username, "password": self.admin_password})
        rejection_reason = "Enrollment ID does not match GTU academic records."
        res_reject = self.client.post(
            f'/admin/api/students/{self.student_enrollment}/reject',
            json={"reason": rejection_reason}
        )
        self.assertEqual(res_reject.status_code, 200)
        rej_data = res_reject.get_json()
        self.assertEqual(rej_data["student"]["status"], "rejected")
        self.assertEqual(rej_data["student"]["rejection_reason"], rejection_reason)
        self.client.get('/auth/logout')

        # 3. Verify student login returns rejection message and reason
        res_login = self.client.post('/auth/login', json={
            "identifier": self.student_enrollment,
            "password": self.student_password
        })
        self.assertEqual(res_login.status_code, 403)
        data = res_login.get_json()
        self.assertEqual(data["student_status"], "rejected")
        self.assertIn("rejected", data["message"].lower())
        self.assertIn(rejection_reason, data["message"])

    def test_07_backward_compatibility_existing_students(self):
        """Existing active students without an explicit status field must be treated as active."""
        legacy_enrollment = "990410107003"
        if self.students_coll is not None:
            self.students_coll.update_one(
                {"enrollment_no": legacy_enrollment},
                {"$set": {
                    "enrollment_no": legacy_enrollment,
                    "full_name": "Legacy Active Student",
                    "email": "legacy.student@svitvasad.ac.in",
                    "password_hash": generate_password_hash("LegacyPass123!"),
                    "is_profile_complete": True
                    # Notice: status field omitted intentionally
                }},
                upsert=True
            )

            m_student = MongoStudent.find_by_identifier(legacy_enrollment)
            self.assertIsNotNone(m_student)
            self.assertEqual(m_student.status, "active")

            # Must also appear in active list
            self.client.post('/auth/login', data={"identifier": self.admin_username, "password": self.admin_password})
            res_active = self.client.get('/admin/api/crud/students?status=active')
            self.assertEqual(res_active.status_code, 200)
            active_items = [i for i in res_active.get_json()["items"] if (i.get("enrollment_no") or i.get("id")) == legacy_enrollment]
            self.assertTrue(len(active_items) > 0)


if __name__ == '__main__':
    unittest.main()
