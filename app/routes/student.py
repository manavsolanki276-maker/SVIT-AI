import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.chat_history import ChatConversation, ChatMessage

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.before_request
def verify_student_status():
    if current_user.is_authenticated and not getattr(current_user, 'is_admin', False):
        status = getattr(current_user, 'status', 'active')
        if status != 'active':
            if status == 'pending':
                return redirect(url_for('auth.pending_view'))
            elif status == 'rejected':
                return redirect(url_for('auth.rejected_view'))
            from flask_login import logout_user
            logout_user()
            return redirect(url_for('auth.login'))


# =========================================================
# 1. FIRST-TIME PROFILE ONBOARDING & VIEW REDIRECTS
# =========================================================
@student_bp.route('/complete-profile', methods=['GET', 'POST'])
@student_bp.route('/complete_profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    return redirect('/student/profile/complete')


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return redirect('/student/profile/')


# =========================================================
# 2. AI CHAT DASHBOARD
# =========================================================
@student_bp.route('/chat')
@login_required
def chat():
    """ Renders the main student chat dashboard UI """
    is_complete = getattr(current_user, 'is_profile_complete', getattr(current_user, 'is_profile_completed', True))
    if not is_complete:
        return redirect('/student/profile/complete')

    return render_template('student/chat.html')


# =========================================================
# 4. CHAT API ENDPOINT
# =========================================================
@student_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """ API endpoint receiving fetch requests from chat UI """
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    try:
        # 1. Fetch or create conversation session
        raw_uid = getattr(current_user, 'id', 1)
        uid_str = str(raw_uid).split('_', 1)[1] if str(raw_uid).startswith('student_') else str(raw_uid)
        conv_id = conversation_id or str(uuid.uuid4())
        title_snippet = user_message[:30] + "..." if len(user_message) > 30 else user_message

        # MongoDB persistence
        try:
            from app.database.mongo_models import MongoChatService
            MongoChatService.save_or_update_conversation(conv_id, uid_str, title_snippet)
            MongoChatService.save_message(conv_id, 'user', user_message)
        except Exception:
            pass

        # SQLite persistence
        try:
            conv = None
            if conversation_id:
                conv = ChatConversation.query.filter_by(id=conversation_id).first()
            if not conv:
                conv = ChatConversation(
                    id=conv_id, 
                    student_id=int(uid_str) if str(uid_str).isdigit() else 1, 
                    title=title_snippet
                )
                db.session.add(conv)
                db.session.commit()

            user_msg_db = ChatMessage(
                conversation_id=conv.id, 
                sender='user', 
                content=user_message
            )
            db.session.add(user_msg_db)
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        # 3. Extract fresh user profile and call the RAG pipeline
        from app.routes.chat import get_current_student_profile
        user_profile = get_current_student_profile() or {
            "full_name": getattr(current_user, 'full_name', getattr(current_user, 'name', 'Student')),
            "program": getattr(current_user, 'program', 'BE'),
            "department": getattr(current_user, 'department', 'Computer Engineering'),
            "semester": getattr(current_user, 'semester', 3),
            "division": getattr(current_user, 'division', 'A'),
            "batch": getattr(current_user, 'batch', 'A1'),
            "enrollment_no": getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', ''))
        }
        session_id = f"user_{uid_str}"
        from app.ai.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()
        result = rag.answer_question(
            question=user_message,
            session_id=session_id,
            user_profile=user_profile
        )

        bot_answer = result.get('answer', '')
        map_image = result.get('image')
        sources = result.get('sources', [])

        # 4. Log assistant message & metadata in MongoDB
        try:
            from app.database.mongo_models import MongoChatService
            MongoChatService.save_message(conv_id, 'assistant', bot_answer, image_path=map_image, sources=sources)
        except Exception:
            pass

        # Log in SQLite
        try:
            bot_msg_db = ChatMessage(
                conversation_id=conv_id,
                sender='assistant',
                content=bot_answer,
                image_path=map_image,
                sources=json.dumps(sources)
            )
            db.session.add(bot_msg_db)
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            'conversation_id': conv_id,
            'answer': bot_answer,
            'image': map_image,
            'sources': sources
        }), 200

    except Exception as e:
        print(f"[Error] Error in RAG Pipeline route: {e}")
        return jsonify({'error': 'Failed to process response. Please try again.'}), 500


# =========================================================
# 5. AUTHENTICATED STUDENT SCOPING HELPER
# =========================================================
def get_auth_student_id() -> str:
    """
    Extracts strictly validated student identity from active user session.
    Prevents cross-student data leakage.
    """
    if not current_user or not current_user.is_authenticated:
        return "210410107001"
    raw_uid = getattr(current_user, 'id', None)
    enrollment = getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', None))
    if enrollment:
        return str(enrollment).strip()
    uid_str = str(raw_uid)
    if uid_str.startswith('student_'):
        return uid_str.split('_', 1)[1]
    return uid_str


# =========================================================
# 6. STUDENT ERP DASHBOARD VIEW
# =========================================================
@student_bp.route('/dashboard')
@login_required
def dashboard():
    """ Renders the modern Student ERP Dashboard """
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    profile = StudentERPService.get_student_profile(sid) or {
        "full_name": getattr(current_user, 'full_name', getattr(current_user, 'name', 'Student')),
        "enrollment_no": sid,
        "program": getattr(current_user, 'program', 'BE'),
        "department": getattr(current_user, 'department', 'Computer Engineering'),
        "semester": getattr(current_user, 'semester', 3),
        "division": getattr(current_user, 'division', 'A'),
        "batch": getattr(current_user, 'batch', 'A1'),
        "roll_no": f"{sid[-3:] if len(sid) >= 3 else '001'}"
    }
    attendance = StudentERPService.get_attendance(sid)
    fees = StudentERPService.get_fee_details(sid)
    results = StudentERPService.get_results(sid)
    applications = StudentERPService.get_applications(sid)
    transport = StudentERPService.get_transport_info(sid)

    return render_template(
        'student/dashboard.html',
        profile=profile,
        attendance=attendance,
        fees=fees,
        results=results,
        applications=applications,
        transport=transport
    )


# =========================================================
# 7. SCOPED STUDENT ERP REST APIS
# =========================================================
@student_bp.route('/api/erp/profile', methods=['GET'])
@login_required
def api_erp_profile():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    p = StudentERPService.get_student_profile(sid)
    return jsonify({"status": "success", "profile": p or {}}), 200


@student_bp.route('/api/erp/attendance', methods=['GET'])
@login_required
def api_erp_attendance():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    att = StudentERPService.get_attendance(sid)
    return jsonify({"status": "success", "attendance": att}), 200


@student_bp.route('/api/erp/fees', methods=['GET'])
@login_required
def api_erp_fees():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    f = StudentERPService.get_fee_details(sid)
    return jsonify({"status": "success", "fees": f}), 200


@student_bp.route('/api/erp/results', methods=['GET'])
@login_required
def api_erp_results():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    r = StudentERPService.get_results(sid)
    return jsonify({"status": "success", "results": r}), 200


@student_bp.route('/api/erp/hall-ticket', methods=['GET'])
@login_required
def api_erp_hall_ticket():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    ht = StudentERPService.get_hall_ticket(sid)
    return jsonify({"status": "success", "hall_ticket": ht}), 200


@student_bp.route('/api/erp/exam-form', methods=['GET'])
@login_required
def api_erp_exam_form():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    ef = StudentERPService.get_exam_form(sid)
    return jsonify({"status": "success", "exam_form": ef}), 200


@student_bp.route('/api/erp/applications', methods=['GET', 'POST'])
@login_required
def api_erp_applications():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    if request.method == 'POST':
        data = request.get_json() or {}
        app_type = data.get('type', 'Bonafide Certificate')
        purpose = data.get('purpose', 'General Academic Requirement')
        details = data.get('details', '')
        res = StudentERPService.submit_application(sid, app_type, purpose, details)
        return jsonify({"status": "success", "application": res}), 201
    apps = StudentERPService.get_applications(sid)
    return jsonify({"status": "success", "applications": apps}), 200


@student_bp.route('/api/erp/grievances', methods=['GET', 'POST'])
@login_required
def api_erp_grievances():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    if request.method == 'POST':
        data = request.get_json() or {}
        cat = data.get('category', 'Academics')
        sub = data.get('subject', 'General Inquiry')
        desc = data.get('description', '')
        res = StudentERPService.submit_grievance(sid, cat, sub, desc)
        return jsonify({"status": "success", "grievance": res}), 201
    grvs = StudentERPService.get_grievances(sid)
    return jsonify({"status": "success", "grievances": grvs}), 200


@student_bp.route('/api/erp/documents', methods=['GET'])
@login_required
def api_erp_documents():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    docs = StudentERPService.get_documents(sid)
    return jsonify({"status": "success", "documents": docs}), 200


@student_bp.route('/api/erp/transport', methods=['GET'])
@login_required
def api_erp_transport():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    tr = StudentERPService.get_transport_info(sid)
    return jsonify({"status": "success", "transport": tr}), 200


@student_bp.route('/api/erp/railway-concession', methods=['GET'])
@login_required
def api_erp_railway_concession():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    rc = StudentERPService.get_railway_concession(sid)
    return jsonify({"status": "success", "railway_concession": rc}), 200


@student_bp.route('/api/erp/homework', methods=['GET'])
@login_required
def api_erp_homework():
    sid = get_auth_student_id()
    from app.database.erp_models import StudentERPService
    hw = StudentERPService.get_homework_and_notes(sid)
    return jsonify({"status": "success", "homework": hw}), 200


# =========================================================
# 8. ONLINE FEE PAYMENT APIS (RAZORPAY)
# =========================================================
@student_bp.route('/api/payment/create-order', methods=['POST'])
@login_required
def api_create_payment_order():
    """
    Creates Razorpay order. Amount is strictly enforced server-side.
    Client-sent amount parameters are ignored for security.
    """
    sid = get_auth_student_id()
    data = request.get_json() or {}
    fee_type = data.get('fee_type', 'tuition_fee')

    from app.database.payment_service import PaymentService
    res = PaymentService.create_fee_order(sid, fee_type=fee_type)
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res), 200


@student_bp.route('/api/payment/verify', methods=['POST'])
@login_required
def api_verify_payment():
    """
    Cryptographically verifies Razorpay payment signature before updating ledger.
    """
    sid = get_auth_student_id()
    data = request.get_json() or {}

    order_id = data.get('razorpay_order_id', '').strip()
    payment_id = data.get('razorpay_payment_id', '').strip()
    signature = data.get('razorpay_signature', '').strip()
    payment_method = data.get('payment_method', 'UPI')

    if not order_id or not payment_id or not signature:
        return jsonify({"status": "error", "message": "Missing payment signature parameters."}), 400

    from app.database.payment_service import PaymentService
    res = PaymentService.confirm_payment(
        sid,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
        payment_method=payment_method
    )

    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res), 200


@student_bp.route('/api/payment/failure', methods=['POST'])
@login_required
def api_payment_failure():
    """ Marks order as failed to allow clean user retry """
    sid = get_auth_student_id()
    data = request.get_json() or {}
    order_id = data.get('razorpay_order_id', '')
    desc = data.get('error_description', 'User cancelled or failed checkout.')

    from app.database.payment_service import PaymentService
    res = PaymentService.mark_payment_failed(sid, order_id, desc)
    return jsonify(res), 200


@student_bp.route('/api/payment/history', methods=['GET'])
@login_required
def api_payment_history():
    """ Returns payment transactions strictly scoped to current student """
    sid = get_auth_student_id()
    from app.database.payment_service import PaymentService
    history = PaymentService.get_payment_history(sid)
    return jsonify({"status": "success", "payments": history}), 200


@student_bp.route('/api/payment/receipt/<receipt_no>', methods=['GET'])
@login_required
def api_download_receipt(receipt_no):
    """
    Streams official SVIT fee payment receipt PDF.
    Enforces authorization check: student can only download their own receipts.
    """
    sid = get_auth_student_id()
    from app.database.payment_service import PaymentService
    pdf_bytes = PaymentService.generate_receipt_pdf(receipt_no, student_id=sid)

    if not pdf_bytes:
        return jsonify({"status": "error", "message": "Receipt not found or unauthorized access."}), 404

    from flask import make_response
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={receipt_no}.pdf'
    return response


@student_bp.route('/api/payment/webhook', methods=['POST'])
def api_payment_webhook():
    """
    Razorpay Webhook endpoint for async payment confirmations.
    Validates HMAC SHA256 webhook signature.
    """
    signature = request.headers.get('X-Razorpay-Signature', '')
    raw_body = request.get_data()

    from app.database.payment_service import PaymentService
    if not PaymentService.verify_webhook_signature(raw_body, signature):
        return jsonify({"status": "error", "message": "Invalid webhook signature"}), 400

    payload = request.get_json() or {}
    event = payload.get('event')

    # Handle payment.captured event
    if event == 'payment.captured':
        payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        notes = payment_entity.get('notes', {})
        student_id = notes.get('student_id')
        method = payment_entity.get('method', 'online')

        if order_id and student_id:
            # Complete payment idempotently
            PaymentService.confirm_payment(
                student_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature="webhook_verified",
                payment_method=method
            )

    return jsonify({"status": "received"}), 200