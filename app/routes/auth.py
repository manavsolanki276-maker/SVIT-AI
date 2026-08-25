"""
app/routes/auth.py
Unified authentication routes for Students and Administrators.
Supports Email, Enrollment ID, and Admin Username lookup with password verification.
Routes authenticated users based on backend RBAC role.
"""
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
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
        # Read the identifier: supports name="identifier", "email", "enrollment_no", or "username"
        identifier = (
            request.form.get('identifier') or 
            request.form.get('email') or 
            request.form.get('enrollment_no') or 
            request.form.get('username') or 
            ''
        ).strip()

        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))
        next_page = request.args.get('next')

        if not identifier or not password:
            flash('Please enter both username/email/enrollment ID and password.', 'error')
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
                flash('Account is disabled. Please contact the Super Administrator.', 'error')
                return render_template('auth/login.html')

            login_user(admin_user, remember=remember)
            if hasattr(admin_user, 'update_last_login'):
                try:
                    admin_user.update_last_login()
                except Exception:
                    pass

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
            login_user(student_user, remember=remember)

            if next_page and is_safe_url(next_page) and not next_page.startswith('/admin'):
                return redirect(next_page)

            is_completed = getattr(student_user, 'is_profile_completed', getattr(student_user, 'is_profile_complete', True))
            if not is_completed:
                return redirect('/student/profile/complete')
            return redirect('/')

        flash('Invalid credentials. Please check your username/email and password.', 'error')

    return render_template('auth/login.html')


# =========================================================
# 2. LOGOUT ROUTE
# =========================================================
@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logs out the active user, clears session, and redirects to login."""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# =========================================================
# 3. FORGOT PASSWORD ROUTE
# =========================================================
@auth_bp.route('/forgot-password', methods=['GET', 'POST'], endpoint='forgot_password')
def forgot_password():
    """Provides instructions for account recovery."""
    if request.method == 'POST':
        flash('Password reset instructions have been forwarded to the college administrator.', 'info')
        return redirect(url_for('auth.login'))
    flash('To reset your credentials, please contact the SVIT Examination / Admin Section or your department coordinator.', 'info')
    return render_template('auth/login.html')