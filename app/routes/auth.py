"""
auth.py
Authentication routes for student and admin login, profile completion routing, and session logout.
Supports form submission with name="identifier" (Email, Enrollment ID, or Username).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
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
        

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# =========================================================
# 1. LOGIN ROUTES (Handles Student / Faculty & Admin)
# =========================================================
@auth_bp.route('/student/login', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def student_login():
    """Handles authentication for Students and Admins via identifier and password."""
    # If already logged in, route immediately
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            return redirect('/admin/dashboard')
        is_completed = getattr(current_user, 'is_profile_completed', getattr(current_user, 'is_profile_complete', True))
        if not is_completed:
            return redirect('/student/profile/complete')
        return redirect('/')

    if request.method == 'POST':
        role = request.form.get('role', 'student').strip()

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

        if not identifier or not password:
            flash('Please enter both enrollment number / email and password.', 'error')
            return render_template('auth/login.html')

        # ----------------------------------------------------
        # ADMIN LOGIN FLOW
        # ----------------------------------------------------
        if role == 'admin' and Admin:
            admin_user = None
            if hasattr(Admin, 'username'):
                admin_user = Admin.query.filter_by(username=identifier).first()
            if not admin_user and hasattr(Admin, 'email'):
                admin_user = Admin.query.filter_by(email=identifier).first()

            if admin_user and hasattr(admin_user, 'check_password') and admin_user.check_password(password):
                login_user(admin_user, remember=remember)
                return redirect('/admin/dashboard')

        # ----------------------------------------------------
        # STUDENT LOGIN FLOW
        # ----------------------------------------------------
        student_user = None
        if Student:
            # Query by Email
            if '@' in identifier and hasattr(Student, 'email'):
                student_user = Student.query.filter_by(email=identifier).first()

            # Query by Enrollment Number
            if not student_user and hasattr(Student, 'enrollment_no'):
                student_user = Student.query.filter_by(enrollment_no=identifier).first()

            if not student_user and hasattr(Student, 'enrollment_number'):
                student_user = Student.query.filter_by(enrollment_number=identifier).first()

        # Check student password
        if student_user and hasattr(student_user, 'check_password') and student_user.check_password(password):
            login_user(student_user, remember=remember)

            # Check profile completion status
            is_completed = getattr(student_user, 'is_profile_completed', getattr(student_user, 'is_profile_complete', False))
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
    return redirect(url_for('auth.student_login'))