"""
app/auth/routes.py
Unified authentication routes for Students and Admins.
"""
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user

from app.database.models import Student, Admin

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target: str) -> bool:
    """Validates target URL to prevent Open Redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('', 'http', 'https') and (ref_url.netloc == test_url.netloc or not test_url.netloc)


# =========================================================
# 1. UNIFIED LOGIN ROUTE
# =========================================================
@auth_bp.route('/student/login', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect them directly
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            if 'admin.dashboard' in current_app.view_functions:
                return redirect(url_for('admin.dashboard'))
            return redirect('/admin/dashboard')
        
        is_completed = getattr(current_user, 'is_profile_completed', getattr(current_user, 'is_profile_complete', True))
        if not is_completed:
            return redirect('/student/profile/complete')
        
        if 'student.chat' in current_app.view_functions:
            return redirect(url_for('student.chat'))
        return redirect('/')

    if request.method == 'POST':
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
            flash('Please enter both username/email/enrollment ID and password.', 'danger')
            return render_template('auth/login.html')

        from app.database.mongo_models import MongoAdmin, MongoStudent

        # --- ATTEMPT ADMIN LOGIN ---
        admin = MongoAdmin.find_by_identifier(identifier)
        if not admin and Admin:
            ident_lower = identifier.lower()
            admin = Admin.query.filter(
                (Admin.username == identifier) | 
                (Admin.email == ident_lower) | 
                (Admin.email == identifier)
            ).first()

        if admin and hasattr(admin, 'check_password') and admin.check_password(password):
            if not getattr(admin, 'is_active', True):
                flash('Account is disabled. Please contact the Super Administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(admin, remember=remember)
            if hasattr(admin, 'update_last_login'):
                try:
                    admin.update_last_login()
                except Exception:
                    pass

            if next_page and is_safe_url(next_page) and '/admin' in next_page:
                return redirect(next_page)

            if 'admin.dashboard' in current_app.view_functions:
                return redirect(url_for('admin.dashboard'))
            return redirect('/admin/dashboard')

        # --- ATTEMPT STUDENT LOGIN ---
        student = MongoStudent.find_by_identifier(identifier)
        if not student and Student:
            if '@' in identifier and hasattr(Student, 'email'):
                student = Student.query.filter_by(email=identifier).first()
            if not student and hasattr(Student, 'enrollment_no'):
                student = Student.query.filter_by(enrollment_no=identifier).first()
            if not student and hasattr(Student, 'enrollment_number'):
                student = Student.query.filter_by(enrollment_number=identifier).first()

        if student and hasattr(student, 'check_password') and student.check_password(password):
            login_user(student, remember=remember)

            if next_page and is_safe_url(next_page) and not next_page.startswith('/admin'):
                return redirect(next_page)

            is_completed = getattr(student, 'is_profile_completed', getattr(student, 'is_profile_complete', True))
            if not is_completed:
                return redirect('/student/profile/complete')

            if 'student.chat' in current_app.view_functions:
                return redirect(url_for('student.chat'))
            return redirect('/')

        flash('Invalid credentials. Please check your username/email and password.', 'danger')

    return render_template('auth/login.html')


# =========================================================
# 2. LOGOUT ROUTE
# =========================================================
@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    
    if 'auth.login' in current_app.view_functions:
        return redirect(url_for('auth.login'))
    return redirect('/auth/login')


# =========================================================
# 3. FORGOT PASSWORD ROUTE
# =========================================================
@auth_bp.route('/forgot-password', methods=['GET', 'POST'], endpoint='forgot_password')
def forgot_password():
    if request.method == 'POST':
        flash('Password reset instructions have been forwarded to the college administrator.', 'info')
        return redirect(url_for('auth.login'))
    flash('To reset your credentials, please contact the SVIT Examination / Admin Section or your department coordinator.', 'info')
    return render_template('auth/login.html')