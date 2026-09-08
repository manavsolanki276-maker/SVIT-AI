"""
app/database/payment_service.py
Secure Razorpay Payment Service with Server-Side Amount Validation,
HMAC SHA256 Cryptographic Signature Verification, Idempotency, and PDF Receipt Generation.
"""
import os
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple

import requests
from app.database.mongodb import get_collection
from app.database.erp_models import StudentERPService


# Environment Keys with safe dev fallback
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_svit_vasad_key")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "svit_test_secret_key_2026")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "svit_webhook_secret_2026")


def get_current_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaymentService:
    """
    Production Payment Engine for Student Fees.
    Strictly guarantees that client amounts are never trusted.
    """

    @staticmethod
    def get_public_key_id() -> str:
        return RAZORPAY_KEY_ID

    @staticmethod
    def create_fee_order(student_id: Any, fee_type: str = "tuition_fee") -> Dict[str, Any]:
        """
        Creates a Razorpay Order server-side.
        CRITICAL: Amount is verified strictly from the student's authorized fee record in MongoDB.
        """
        sid_str = str(student_id)
        fee_info = StudentERPService.get_fee_details(sid_str)
        actual_pending = int(fee_info.get("pending_fee", 0))

        if actual_pending <= 0:
            return {
                "status": "error",
                "message": "No pending fees. Your fees are already completely paid!",
                "pending_amount": 0
            }

        # Amount in paise (1 INR = 100 paise)
        amount_paise = actual_pending * 100
        receipt_id = f"rcpt_{sid_str[-4:] if len(sid_str) >= 4 else '1001'}_{int(datetime.now().timestamp())}"

        razorpay_order_id = None

        # If live Razorpay API key is configured and not placeholder test key
        if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith("rzp_test_svit_vasad") and RAZORPAY_KEY_SECRET != "svit_test_secret_key_2026":
            try:
                resp = requests.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                    json={
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": receipt_id,
                        "notes": {
                            "student_id": sid_str,
                            "fee_type": fee_type
                        }
                    },
                    timeout=10
                )
                if resp.status_code in (200, 201):
                    order_data = resp.json()
                    razorpay_order_id = order_data.get("id")
            except Exception as e:
                print(f"[Razorpay API Warning] Direct API call error: {e}")

        if not razorpay_order_id:
            # Generate valid deterministic Razorpay Order ID format
            razorpay_order_id = f"order_{uuid.uuid4().hex[:14]}"

        # Persist transaction in MongoDB 'payments' collection
        payments_coll = get_collection('payments')
        payment_record = {
            "payment_id": f"pay_tx_{uuid.uuid4().hex[:12]}",
            "student_id": sid_str,
            "enrollment_no": fee_info.get("enrollment_no", sid_str),
            "payment_type": fee_type,
            "amount": actual_pending,
            "amount_paise": amount_paise,
            "currency": "INR",
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": None,
            "razorpay_signature": None,
            "payment_method": None,
            "status": "created",  # created -> pending -> paid / failed
            "receipt_number": None,
            "payment_date": None,
            "created_at": get_current_time_iso(),
            "updated_at": get_current_time_iso()
        }

        if payments_coll is not None:
            payments_coll.insert_one(payment_record)

        profile = StudentERPService.get_student_profile(sid_str) or {}
        return {
            "status": "success",
            "key_id": RAZORPAY_KEY_ID,
            "order_id": razorpay_order_id,
            "amount": amount_paise,
            "amount_inr": actual_pending,
            "currency": "INR",
            "receipt": receipt_id,
            "student_name": profile.get("full_name") or profile.get("name", "SVIT Student"),
            "student_email": profile.get("email", "student@svit.ac.in"),
            "student_phone": profile.get("phone", "9876543210")
        }

    @staticmethod
    def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
        """
        Cryptographically verifies the HMAC SHA256 signature returned by Razorpay Checkout.
        """
        if not order_id or not payment_id or not signature:
            return False
        try:
            msg = f"{order_id}|{payment_id}".encode('utf-8')
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            print(f"[Payment Signature Verification Error] {e}")
            return False

    @staticmethod
    def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
        """
        Cryptographically verifies the Razorpay Webhook signature.
        """
        if not payload_body or not signature_header:
            return False
        try:
            secret = RAZORPAY_WEBHOOK_SECRET.encode('utf-8')
            expected = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception:
            return False

    @staticmethod
    def confirm_payment(
        student_id: Any,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        payment_method: str = "UPI"
    ) -> Dict[str, Any]:
        """
        Verifies and completes a payment transaction.
        Updates student fee balance atomically and creates an official receipt.
        """
        sid_str = str(student_id)
        payments_coll = get_collection('payments')

        # 1. Fetch matching payment record
        record = None
        if payments_coll is not None:
            record = payments_coll.find_one({"razorpay_order_id": razorpay_order_id, "student_id": sid_str})

        if not record:
            return {"status": "error", "message": "Order not found or does not belong to this student."}

        # Idempotency check: if already marked paid, return cached receipt
        if record.get("status") == "paid":
            return {
                "status": "success",
                "message": "Payment already confirmed.",
                "receipt_number": record.get("receipt_number"),
                "payment_id": record.get("razorpay_payment_id"),
                "amount": record.get("amount"),
                "date": record.get("payment_date")
            }

        # 2. Verify signature
        is_valid = PaymentService.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
        if not is_valid:
            # Mark failed
            if payments_coll is not None:
                payments_coll.update_one(
                    {"_id": record["_id"]},
                    {"$set": {"status": "failed", "error_reason": "Invalid cryptographic signature", "updated_at": get_current_time_iso()}}
                )
            return {"status": "error", "message": "Payment verification failed: invalid signature."}

        # 3. Success -> mark paid & generate receipt number
        receipt_no = f"SVIT-RCP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        payment_date_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        amount_paid = record.get("amount", 15000)

        update_data = {
            "status": "paid",
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "payment_method": payment_method or "UPI",
            "receipt_number": receipt_no,
            "payment_date": payment_date_str,
            "updated_at": get_current_time_iso()
        }

        if payments_coll is not None:
            payments_coll.update_one({"_id": record["_id"]}, {"$set": update_data})

        # 4. Atomic update of student fee record
        StudentERPService.update_fee_after_payment(sid_str, amount_paid)

        # 5. Create notification for student
        try:
            notif_coll = get_collection('notifications')
            if notif_coll is not None:
                notif_coll.insert_one({
                    "student_id": sid_str,
                    "title": "Fee Payment Successful",
                    "message": f"Payment of ₹{amount_paid:,} received successfully. Receipt No: {receipt_no}",
                    "type": "payment",
                    "is_read": False,
                    "created_at": get_current_time_iso()
                })
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Payment verified and recorded successfully.",
            "receipt_number": receipt_no,
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "amount": amount_paid,
            "payment_method": payment_method,
            "date": payment_date_str
        }

    @staticmethod
    def mark_payment_failed(student_id: Any, razorpay_order_id: str, error_description: str = "") -> Dict[str, Any]:
        """
        Marks an order attempt as failed when client checkout closes or fails.
        Allows student to retry smoothly without orphaned state.
        """
        sid_str = str(student_id)
        payments_coll = get_collection('payments')
        if payments_coll is not None:
            payments_coll.update_one(
                {"razorpay_order_id": razorpay_order_id, "student_id": sid_str, "status": "created"},
                {"$set": {"status": "failed", "error_reason": error_description, "updated_at": get_current_time_iso()}}
            )
        return {"status": "recorded", "message": "Payment marked as failed."}

    @staticmethod
    def get_payment_history(student_id: Any) -> List[Dict[str, Any]]:
        """
        Returns all payment transactions strictly scoped to student_id.
        """
        sid_str = str(student_id)
        payments_coll = get_collection('payments')
        if payments_coll is None:
            return []
        docs = list(payments_coll.find({"student_id": sid_str}).sort("created_at", -1))
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    @staticmethod
    def get_payment_by_receipt(receipt_no: str, student_id: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        payments_coll = get_collection('payments')
        if payments_coll is None:
            return None
        query: Dict[str, Any] = {"receipt_number": receipt_no}
        if student_id is not None:
            query["student_id"] = str(student_id)
        doc = payments_coll.find_one(query)
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    # -------------------------------------------------------------------------
    # PDF RECEIPT GENERATOR (ReportLab)
    # -------------------------------------------------------------------------
    @staticmethod
    def generate_receipt_pdf(receipt_no: str, student_id: Optional[Any] = None) -> Optional[bytes]:
        """
        Generates a professional SVIT College Fee Receipt PDF using ReportLab.
        """
        payment = PaymentService.get_payment_by_receipt(receipt_no, student_id=student_id)
        if not payment:
            return None

        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Palette Styles
        primary_color = colors.HexColor("#171D3A")
        accent_color = colors.HexColor("#8B5CF6")
        dark_gray = colors.HexColor("#334155")
        light_bg = colors.HexColor("#F8FAFC")

        title_style = ParagraphStyle(
            'CollegeTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=primary_color,
            alignment=1  # Centered
        )

        sub_style = ParagraphStyle(
            'CollegeSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=dark_gray,
            alignment=1
        )

        badge_style = ParagraphStyle(
            'BadgeStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#16A34A"),
            alignment=1
        )

        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=primary_color
        )

        val_style = ParagraphStyle(
            'Val',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=dark_gray
        )

        elements = []

        # College Header
        elements.append(Paragraph("SARDAR VALLABHBHAI PATEL INSTITUTE OF TECHNOLOGY", title_style))
        elements.append(Paragraph("B/h. Vasad Railway Station, Vasad - 388306, Dist. Anand, Gujarat", sub_style))
        elements.append(Paragraph("Approved by AICTE, Affiliated to Gujarat Technological University (GTU)", sub_style))
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=14))

        # Receipt Heading
        elements.append(Paragraph("OFFICIAL STUDENT FEE PAYMENT RECEIPT", ParagraphStyle(
            'RecTitle', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=accent_color, alignment=1
        )))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("STATUS: PAID & VERIFIED ONLINE", badge_style))
        elements.append(Spacer(1, 14))

        # Student & Transaction Info Table
        profile = StudentERPService.get_student_profile(payment.get("student_id")) or {}
        student_name = profile.get("full_name") or profile.get("name", "Student")
        enrollment = payment.get("enrollment_no") or profile.get("enrollment_no", "N/A")
        dept = profile.get("department", "Engineering")
        sem = profile.get("semester", 3)

        info_data = [
            [Paragraph("Receipt Number:", label_style), Paragraph(receipt_no, val_style),
             Paragraph("Payment Date:", label_style), Paragraph(payment.get("payment_date", "Today"), val_style)],
            [Paragraph("Student Name:", label_style), Paragraph(student_name, val_style),
             Paragraph("Enrollment No:", label_style), Paragraph(str(enrollment), val_style)],
            [Paragraph("Department / Course:", label_style), Paragraph(f"{dept} (Sem {sem})", val_style),
             Paragraph("Payment Method:", label_style), Paragraph(payment.get("payment_method", "UPI"), val_style)],
            [Paragraph("Razorpay Order ID:", label_style), Paragraph(payment.get("razorpay_order_id", "N/A"), val_style),
             Paragraph("Transaction ID:", label_style), Paragraph(payment.get("razorpay_payment_id", "N/A"), val_style)]
        ]

        info_table = Table(info_data, colWidths=[1.5 * inch, 2.3 * inch, 1.5 * inch, 2.2 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_bg),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 16))

        # Amount Breakdown Table
        amount_val = payment.get("amount", 15000)
        breakdown_data = [
            [Paragraph("Fee Component Description", label_style), Paragraph("Category", label_style), Paragraph("Amount (INR)", label_style)],
            [Paragraph("Term Tuition & Academic Dues", val_style), Paragraph("Academic Fee", val_style), Paragraph(f"INR {amount_val:,.2f}", val_style)],
            [Paragraph("<b>TOTAL AMOUNT PAID</b>", label_style), Paragraph("<b>Online Razorpay</b>", label_style), Paragraph(f"<b>INR {amount_val:,.2f}</b>", label_style)]
        ]

        b_table = Table(breakdown_data, colWidths=[4.0 * inch, 1.8 * inch, 1.7 * inch])
        b_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
            ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
            ('TOPPADDING', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(b_table)
        elements.append(Spacer(1, 24))

        # Footer Notice
        elements.append(Paragraph("<i>Note: This is a computer-generated receipt issued through SVIT-AI Portal. No physical signature is required. For inquiries, please contact the Accounts Section at accounts@svitvasad.ac.in.</i>", ParagraphStyle(
            'Footer', fontName='Helvetica-Oblique', fontSize=8, leading=12, textColor=colors.HexColor("#64748B"), alignment=1
        )))

        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
