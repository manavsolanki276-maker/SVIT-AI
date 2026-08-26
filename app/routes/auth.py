"""
app/routes/auth.py
Unified authentication routes for Students and Administrators.
Supports Email, Enrollment ID, and Admin Username lookup with password verification.
Routes authenticated users based on backend RBAC role.
"""
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_user, logout_user, current_user

try:
    from app.extensions import db
except ImportError:
    from app import db

# Safe model imports for both Student and Admin
try:
    from app.database.models import Student, Admin
except ImportError:
    Student = None
    Admin = None


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def is_safe_url(target: str) -> bool:
    """Validates target URL to prevent Open Redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('', 'http', 'https') and (ref_url.netloc == test_url.netloc or not test_url.netloc)


# =========================================================
# 1. UNIFIED LOGIN ROUTE (Handles Student / Faculty & Admin)
# =========================================================
@auth_bp.route('/student/login', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def student_login():
    """Handles unified authentication for Students and Admins via identifier and password."""
    # 1. If already logged in, route immediately based on role
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        is_completed = getattr(current_user, 'is_profile_completed', getattr(current_user, 'is_profile_complete', True))
        if not is_completed:
            return redirect('/student/profile/complete')
        return redirect('/')

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form or {}
        is_json_req = request.is_json or request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'

        identifier = (
            data.get('identifier') or
            data.get('email') or
            data.get('enrollment_no') or
            data.get('username') or
            ''
        ).strip()

        password = str(data.get('password') or '').strip()
        remember = bool(data.get('remember'))
        next_page = request.args.get('next')

        if not identifier or not password:
            msg = 'Please enter both username/email/enrollment ID and password.'
            if is_json_req:
                return jsonify({"status": "error", "message": msg}), 400
            flash(msg, 'error')
            return render_template('auth/login.html')

        from app.database.mongo_models import MongoAdmin, MongoStudent

        # ----------------------------------------------------
        # 1. ATTEMPT ADMIN AUTHENTICATION
        # ----------------------------------------------------
        admin_user = None
        try:
            admin_user = MongoAdmin.find_by_identifier(identifier)
        except Exception:
            pass

        if not admin_user and Admin:
            ident_lower = identifier.lower()
            admin_user = Admin.query.filter(
                (Admin.username == identifier) |
                (Admin.email == ident_lower) |
                (Admin.email == identifier)
            ).first()

        if admin_user and hasattr(admin_user, 'check_password') and admin_user.check_password(password):
            if not getattr(admin_user, 'is_active', True):
                msg = 'Account is disabled. Please contact the Super Administrator.'
                if is_json_req:
                    return jsonify({"status": "error", "message": msg}), 403
                flash(msg, 'error')
                return render_template('auth/login.html')

            login_user(admin_user, remember=remember)
            if hasattr(admin_user, 'update_last_login'):
                try:
                    admin_user.update_last_login()
                except Exception:
                    pass

            if is_json_req:
                return jsonify({
                    "status": "success",
                    "message": "Admin login successful.",
                    "role": getattr(admin_user, 'role', 'admin'),
                    "redirect_url": "/admin/dashboard"
                }), 200

            if next_page and is_safe_url(next_page) and '/admin' in next_page:
                return redirect(next_page)

            return redirect(url_for('admin.dashboard'))

        # ----------------------------------------------------
        # 2. ATTEMPT STUDENT AUTHENTICATION
        # ----------------------------------------------------
        student_user = None
        try:
            student_user = MongoStudent.find_by_identifier(identifier)
        except Exception:
            pass

        if not student_user and Student:
            if '@' in identifier and hasattr(Student, 'email'):
                student_user = Student.query.filter_by(email=identifier).first()
            if not student_user and hasattr(Student, 'enrollment_no'):
                student_user = Student.query.filter_by(enrollment_no=identifier).first()
            if not student_user and hasattr(Student, 'enrollment_number'):
                student_user = Student.query.filter_by(enrollment_number=identifier).first()

        if student_user and hasattr(student_user, 'check_password') and student_user.check_password(password):
            status = getattr(student_user, 'status', 'active')

            if status == 'pending':
                msg = 'Your registration is pending admin approval.'
                if is_json_req:
                    return jsonify({
                        "status": "error",
                        "error": "PendingApproval",
                        "message": msg,
                        "student_status": "pending"
                    }), 403
                flash(msg, 'warning')
                return render_template('auth/login.html')

            if status == 'rejected':
                reason = getattr(student_user, 'rejection_reason', '')
                msg = 'Your registration request was rejected.'
                if reason:
                    msg += f' Reason: {reason}'
                if is_json_req:
                    return jsonify({
                        "status": "error",
                        "error": "Rejected",
                        "message": msg,
                        "student_status": "rejected",
                        "rejection_reason": reason
                    }), 403
                flash(msg, 'error')
                return render_template('auth/login.html')

            # Approved active student
            login_user(student_user, remember=remember)

            if is_json_req:
                student_payload = student_user.to_dict() if hasattr(student_user, 'to_dict') else {
                    "enrollment_no": getattr(student_user, 'enrollment_no', ''),
                    "name": getattr(student_user, 'full_name', getattr(student_user, 'name', 'Student'))
                }
                return jsonify({
                    "status": "success",
                    "message": "Login successful.",
                    "student": student_payload,
                    "redirect_url": "/"
                }), 200

            if next_page and is_safe_url(next_page) and not next_page.startswith('/admin'):
                return redirect(next_page)

            is_completed = getattr(student_user, 'is_profile_completed', getattr(student_user, 'is_profile_complete', True))
            if not is_completed:
                return redirect('/student/profile/complete')
            return redirect('/')

        if is_json_req:
            return jsonify({"status": "error", "message": "Invalid credentials. Please check your username/email and password."}), 401

        flash('Invalid credentials. Please check your username/email and password.', 'error')

    return render_template('auth/login.html')


# =========================================================
# 2. STUDENT REGISTRATION ROUTE
# =========================================================
@auth_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
@auth_bp.route('/student/register', methods=['GET', 'POST'])
def register():
    """
    Handles new student self-registration into the pending approval workflow.
    Validates duplicate enrollment/email and dispatches notifications.
    """
    import time
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    from app.database.mongodb import get_collection
    from app.database.mongo_models import MongoNotificationService

    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect('/')

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form or {}
        is_json_req = request.is_json or request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'

        full_name = str(data.get('full_name') or data.get('name') or '').strip()
        enrollment_no = str(data.get('enrollment_no') or data.get('enrollment_number') or '').strip()
        email = str(data.get('email') or '').strip().lower()
        password = str(data.get('password') or '').strip()
        phone = str(data.get('phone') or data.get('contact_number') or '').strip()
        department = str(data.get('department') or 'Computer Engineering').strip()
        program = str(data.get('program') or 'BE').strip()
        try:
            semester = int(data.get('semester') or 1)
        except (ValueError, TypeError):
            semester = 1
        division = str(data.get('division') or 'A').strip()
        batch = str(data.get('batch') or 'A1').strip()

        # 1. Validation
        if not full_name or not enrollment_no or not email or not password:
            msg = "Please fill in all required fields (Full Name, Enrollment No, Email, and Password)."
            if is_json_req:
                return jsonify({"status": "error", "message": msg}), 400
            flash(msg, 'error')
            return render_template('auth/register.html', form_data=data)

        # 2. Duplicate prevention in MongoDB
        coll = get_collection('students')
        if coll is not None:
            existing_enroll = coll.find_one({
                "$or": [
                    {"enrollment_no": enrollment_no},
                    {"enrollment_number": enrollment_no},
                    {"id": enrollment_no}
                ]
            })
            if existing_enroll:
                st = existing_enroll.get('status', 'active')
                msg = "Registration request already pending." if st == 'pending' else "Student already registered."
                if is_json_req:
                    return jsonify({"status": "error", "message": msg, "student_status": st}), 409
                flash(msg, 'warning' if st == 'pending' else 'error')
                return render_template('auth/register.html', form_data=data)

            existing_email = coll.find_one({"email": email})
            if existing_email:
                st = existing_email.get('status', 'active')
                msg = "Registration request already pending." if st == 'pending' else "Student already registered."
                if is_json_req:
                    return jsonify({"status": "error", "message": msg, "student_status": st}), 409
                flash(msg, 'warning' if st == 'pending' else 'error')
                return render_template('auth/register.html', form_data=data)

        # 3. Duplicate prevention in SQLite
        try:
            from app.database.models import Student
            if Student:
                if Student.query.filter_by(enrollment_no=enrollment_no).first() or Student.query.filter_by(email=email).first():
                    msg = "Student already registered."
                    if is_json_req:
                        return jsonify({"status": "error", "message": msg}), 409
                    flash(msg, 'error')
                    return render_template('auth/register.html', form_data=data)
        except Exception:
            pass

        # 4. Create Registration Document with status="pending"
        request_id = f"REQ_{enrollment_no}_{int(time.time())}"
        now = datetime.utcnow()
        hashed_pw = generate_password_hash(password)

        student_doc = {
            "id": enrollment_no,
            "enrollment_no": enrollment_no,
            "full_name": full_name,
            "name": full_name,
            "email": email,
            "password_hash": hashed_pw,
            "phone": phone,
            "department": department,
            "program": program,
            "semester": semester,
            "division": division,
            "batch": batch,
            "status": "pending",
            "request_id": request_id,
            "is_profile_complete": True,
            "is_profile_completed": True,
            "approved_by": None,
            "approved_at": None,
            "rejected_by": None,
            "rejected_at": None,
            "rejection_reason": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        if coll is not None:
            coll.update_one({"enrollment_no": enrollment_no}, {"$set": student_doc}, upsert=True)

        # Save in SQLite fallback
        try:
            from app.database.models import Student
            from app.extensions import db
            s_obj = Student(
                enrollment_no=enrollment_no,
                email=email,
                password_hash=hashed_pw,
                full_name=full_name,
                program=program,
                department=department,
                semester=semester,
                division=division,
                batch=batch,
                phone=phone,
                is_profile_complete=True
            )
            if hasattr(s_obj, 'status'):
                s_obj.status = 'pending'
            if hasattr(s_obj, 'request_id'):
                s_obj.request_id = request_id
            db.session.add(s_obj)
            db.session.commit()
        except Exception:
            try:
                from app.extensions import db
                db.session.rollback()
            except Exception:
                pass

        # 5. Dispatch Admin Notification
        MongoNotificationService.notify_admins(
            title="New student registration request",
            message=f"{full_name} submitted a registration request.",
            category="registration",
            data={
                "student_name": full_name,
                "enrollment_no": enrollment_no,
                "email": email,
                "department": department,
                "program": program,
                "semester": semester,
                "status": "pending",
                "request_id": request_id,
                "registered_at": now.isoformat(),
                "link": "/admin/students?status=pending"
            }
        )

        # 6. Dispatch Student Notification
        MongoNotificationService.notify_student(
            student_id=enrollment_no,
            title="Registration Submitted",
            message="Your SVIT student registration request has been submitted and is pending admin approval.",
            category="registration",
            data={
                "request_id": request_id,
                "registered_at": now.isoformat()
            }
        )

        success_msg = "Your registration request has been submitted successfully and is pending admin approval."
        if is_json_req:
            return jsonify({
                "status": "success",
                "message": success_msg,
                "request_id": request_id,
                "student_status": "pending"
            }), 201

        flash(success_msg, "info")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# =========================================================
# 3. LOGOUT ROUTE
# =========================================================
@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logs out the active user, clears session, and redirects to login."""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# =========================================================
# 4. FORGOT PASSWORD ROUTE
# =========================================================
@auth_bp.route('/forgot-password', methods=['GET', 'POST'], endpoint='forgot_password')
def forgot_password():
    """Provides instructions for account recovery."""
    if request.method == 'POST':
        flash('Password reset instructions have been forwarded to the college administrator.', 'info')
        return redirect(url_for('auth.login'))
    flash('To reset your credentials, please contact the SVIT Examination / Admin Section or your department coordinator.', 'info')
    return render_template('auth/login.html')
