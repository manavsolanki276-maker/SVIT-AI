"""
tests/test_student_erp_chatbot_system.py
Comprehensive Unit, Integration, and Security Test Suite for SVIT Student ERP & Payment System.
"""
import hmac
import hashlib
import json
import unittest
from app import create_app
from app.extensions import db
from app.database.erp_models import StudentERPService
from app.database.payment_service import PaymentService, RAZORPAY_KEY_SECRET
from app.database.erp_sync_service import ERPSyncService
from app.ai.erp_intent import ERPIntentClassifier, format_erp_response_card


from app.database.mongodb import get_collection


class StudentERPSystemTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        # Reset fees collection for test student so each test has fresh pending balance
        coll = get_collection('fees')
        if coll is not None:
            try:
                coll.delete_many({"student_id": "210410107001"})
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # TEST 1: STRICT WORD-BOUNDARY INTENT CLASSIFIER & SYLLABUS SAFETY
    # -------------------------------------------------------------------------
    def test_01_word_boundary_intent_safety(self):
        # CRITICAL TEST: "syllabus" must NEVER be classified as "bus" / "transport"
        self.assertEqual(ERPIntentClassifier.classify("Show my syllabus"), "syllabus")
        self.assertEqual(ERPIntentClassifier.classify("What is the syllabus for sem 3?"), "syllabus")
        self.assertEqual(ERPIntentClassifier.classify("gtu syllabus"), "syllabus")
        self.assertNotEqual(ERPIntentClassifier.classify("syllabus"), "transport")

        # Transport queries
        self.assertEqual(ERPIntentClassifier.classify("What is my bus information?"), "transport")
        self.assertEqual(ERPIntentClassifier.classify("Show my bus pass"), "transport")
        self.assertEqual(ERPIntentClassifier.classify("bus timing"), "transport")

        # Fee & Payment queries
        self.assertEqual(ERPIntentClassifier.classify("How much fee is pending?"), "fees")
        self.assertEqual(ERPIntentClassifier.classify("Check my fee balance"), "fees")
        self.assertEqual(ERPIntentClassifier.classify("Pay my fees"), "payment")
        self.assertEqual(ERPIntentClassifier.classify("I want to pay"), "payment")
        self.assertEqual(ERPIntentClassifier.classify("Show my previous payments"), "payment_history")
        self.assertEqual(ERPIntentClassifier.classify("Give me my fee receipt"), "payment_receipt")

        # Academic queries
        self.assertEqual(ERPIntentClassifier.classify("What is my attendance?"), "attendance")
        self.assertEqual(ERPIntentClassifier.classify("Show my result"), "result")
        self.assertEqual(ERPIntentClassifier.classify("What is my SPI?"), "result")
        self.assertEqual(ERPIntentClassifier.classify("Show my hall ticket"), "hall_ticket")
        self.assertEqual(ERPIntentClassifier.classify("Did I submit exam form?"), "examination")
        self.assertEqual(ERPIntentClassifier.classify("What is my timetable today?"), "timetable")
        self.assertEqual(ERPIntentClassifier.classify("Do I have any pending application?"), "applications")
        self.assertEqual(ERPIntentClassifier.classify("Lodge a complaint"), "grievance")
        self.assertEqual(ERPIntentClassifier.classify("Show my documents"), "documents")
        self.assertEqual(ERPIntentClassifier.classify("Railway concession pass"), "railway_concession")
        self.assertEqual(ERPIntentClassifier.classify("Show my profile"), "student_profile")

    # -------------------------------------------------------------------------
    # TEST 2: STUDENT SCOPING & PRIVACY ISOLATION
    # -------------------------------------------------------------------------
    def test_02_student_scoping_isolation(self):
        student_a = "210410107001"
        student_b = "210410107999"

        # Initialize student A
        fee_a = StudentERPService.get_fee_details(student_a)
        # Initialize student B
        fee_b = StudentERPService.get_fee_details(student_b)

        self.assertEqual(fee_a["student_id"], student_a)
        self.assertEqual(fee_b["student_id"], student_b)

        # Ensure attendance is scoped to student
        att_a = StudentERPService.get_attendance(student_a)
        att_b = StudentERPService.get_attendance(student_b)
        self.assertEqual(att_a["student_id"], student_a)
        self.assertEqual(att_b["student_id"], student_b)

        # Ensure results are scoped
        res_a = StudentERPService.get_results(student_a)
        self.assertEqual(res_a["student_id"], student_a)

    # -------------------------------------------------------------------------
    # TEST 3: PAYMENT AMOUNT TAMPERING RESISTANCE
    # -------------------------------------------------------------------------
    def test_03_payment_amount_tampering_resistance(self):
        student_id = "210410107001"
        fee_details = StudentERPService.get_fee_details(student_id)
        expected_pending = fee_details["pending_fee"]

        # Server-side order creation must enforce actual pending amount
        order_res = PaymentService.create_fee_order(student_id, fee_type="tuition_fee")
        self.assertEqual(order_res["status"], "success")
        self.assertEqual(order_res["amount_inr"], expected_pending)
        self.assertEqual(order_res["amount"], expected_pending * 100)

    # -------------------------------------------------------------------------
    # TEST 4: PAYMENT ORDER CREATION AND HMAC SHA256 VERIFICATION
    # -------------------------------------------------------------------------
    def test_04_payment_order_and_signature_verification(self):
        student_id = "210410107001"
        order_res = PaymentService.create_fee_order(student_id)
        order_id = order_res["order_id"]
        payment_id = f"pay_test_{student_id[-4:]}_valid"

        # Generate authentic HMAC SHA256 signature
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        secret = RAZORPAY_KEY_SECRET.encode('utf-8')
        authentic_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        # Confirm payment
        confirm_res = PaymentService.confirm_payment(
            student_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=authentic_signature,
            payment_method="UPI"
        )

        self.assertEqual(confirm_res["status"], "success")
        self.assertTrue("receipt_number" in confirm_res)
        receipt_no = confirm_res["receipt_number"]

        # Verify idempotency: Repeating with same order_id returns cached receipt
        dup_res = PaymentService.confirm_payment(
            student_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=authentic_signature
        )
        self.assertEqual(dup_res["receipt_number"], receipt_no)

    # -------------------------------------------------------------------------
    # TEST 5: TAMPERED SIGNATURE REJECTION
    # -------------------------------------------------------------------------
    def test_05_tampered_signature_rejection(self):
        student_id = "210410107001"
        order_res = PaymentService.create_fee_order(student_id)
        order_id = order_res["order_id"]
        payment_id = "pay_fake_attacker_id"
        tampered_signature = "invalid_tampered_hex_signature_12345"

        reject_res = PaymentService.confirm_payment(
            student_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=tampered_signature
        )
        self.assertEqual(reject_res["status"], "error")
        self.assertIn("invalid signature", reject_res["message"].lower())

    # -------------------------------------------------------------------------
    # TEST 6: REPORTLAB PDF FEE RECEIPT GENERATION
    # -------------------------------------------------------------------------
    def test_06_pdf_receipt_generation(self):
        student_id = "210410107001"
        # Fetch payment history to get a valid receipt number
        history = PaymentService.get_payment_history(student_id)
        paid_tx = [t for t in history if t.get("status") == "paid" and t.get("receipt_number")]
        if not paid_tx:
            # Create a paid test payment to ensure self-contained test execution
            order_res = PaymentService.create_fee_order(student_id)
            order_id = order_res.get("order_id", "order_test_dummy_06")
            payment_id = "pay_test_06_receipt"
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            sig = hmac.new(secret, f"{order_id}|{payment_id}".encode('utf-8'), hashlib.sha256).hexdigest()
            PaymentService.confirm_payment(
                student_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=sig
            )
            history = PaymentService.get_payment_history(student_id)
            paid_tx = [t for t in history if t.get("status") == "paid" and t.get("receipt_number")]

        self.assertTrue(len(paid_tx) > 0, "At least one paid transaction expected")

        receipt_no = paid_tx[0]["receipt_number"]
        pdf_bytes = PaymentService.generate_receipt_pdf(receipt_no, student_id=student_id)
        self.assertIsNotNone(pdf_bytes)
        # PDF files must start with binary %PDF
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Valid PDF binary header verified")

        # Security check: Unauthorized student cannot access this receipt
        unauthorized_pdf = PaymentService.generate_receipt_pdf(receipt_no, student_id="999999999999")
        self.assertIsNone(unauthorized_pdf, "Cross-student receipt access blocked")

    # -------------------------------------------------------------------------
    # TEST 7: BACKGROUND ERP SYNC SERVICE AND AUDIT LOGS
    # -------------------------------------------------------------------------
    def test_07_erp_sync_resilience_and_logs(self):
        sync_res = ERPSyncService.trigger_sync(admin_user="super_admin")
        self.assertEqual(sync_res["status"], "success")
        self.assertTrue(sync_res["students_synced"] >= 1)

        status = ERPSyncService.get_sync_status()
        self.assertEqual(status["sync_status"], "SUCCESS")
        self.assertIsNotNone(status["last_synced_at"])

        logs = ERPSyncService.get_sync_logs(limit=5)
        self.assertTrue(len(logs) >= 1)

    # -------------------------------------------------------------------------
    # TEST 8: CHATBOT RESPONSE CARDS WITH INLINE PAY & ACTION BUTTONS
    # -------------------------------------------------------------------------
    def test_08_chatbot_response_cards(self):
        student_id = "210410107001"

        # Fee card contains pay button
        fee_card, srcs, sugs = format_erp_response_card("fees", student_id)
        self.assertIn("Student Fee Details", fee_card)
        self.assertTrue(any("pay" in s.lower() or "receipt" in s.lower() for s in sugs))

        # Attendance card contains subject breakdown
        att_card, srcs, sugs = format_erp_response_card("attendance", student_id)
        self.assertIn("Attendance Report", att_card)
        self.assertIn("Data Structures", att_card)

        # Hall ticket card contains seat and room info
        ht_card, srcs, sugs = format_erp_response_card("hall_ticket", student_id)
        self.assertIn("Hall Ticket", ht_card)
        self.assertIn("Seat Number", ht_card)

        # Result card contains SPI / CPI
        res_card, srcs, sugs = format_erp_response_card("result", student_id)
        self.assertIn("SPI", res_card)
        self.assertIn("CPI", res_card)


if __name__ == '__main__':
    unittest.main()
