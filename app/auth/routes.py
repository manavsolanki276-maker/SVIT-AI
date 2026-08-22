"""
app/auth/routes.py
Authentication routes for Students and Admins.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.database.models import Student, Admin

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    """Validates target URL to prevent Open Redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('', 'http', 'https') and ref_url.netloc == test_url.netloc or not test_url.netloc


# =========================================================
# 1. LOGIN ROUTE
# =========================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect them directly
    if current_user.is_authenticated:
        if getattr(current_user, 'is_admin', False):
            if 'admin.dashboard' in current_app.view_functions:
                return redirect(url_for('admin.dashboard'))
            return redirect('/')
        
        if not getattr(current_user, 'is_profile_complete', True):
            if 'student.complete_profile' in current_app.view_functions:
                return redirect(url_for('student.complete_profile'))
        
        if 'student.chat' in current_app.view_functions:
            return redirect(url_for('student.chat'))
        return redirect('/')

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student').lower()

        print(f"--> LOGIN ATTEMPT: role={role}, identifier={identifier}")

        # --- STUDENT LOGIN PATH ---
        if role == 'student':
            from app.database.mongo_models import MongoStudent
            student = MongoStudent.find_by_identifier(identifier)
            if not student and Student:
                student = Student.query.filter(
                    (Student.enrollment_no == identifier) | (Student.email == identifier)
                ).first()

            if student and student.check_password(password):
                login_user(student, remember=True)

                # Handle redirected URL target
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)

                if not getattr(student, 'is_profile_complete', True):
                    if 'student.complete_profile' in current_app.view_functions:
                        return redirect(url_for('student.complete_profile'))

                if 'student.chat' in current_app.view_functions:
                    return redirect(url_for('student.chat'))
                return redirect('/')

            flash('Invalid enrollment number/email or password.', 'danger')

        # --- ADMIN LOGIN PATH ---
        elif role == 'admin':
            from app.database.mongo_models import MongoAdmin
            admin = MongoAdmin.find_by_identifier(identifier)
            if not admin and Admin:
                admin = Admin.query.filter(
                    (Admin.username == identifier) | (Admin.email == identifier)
                ).first()

            if admin and admin.check_password(password):
                login_user(admin, remember=True)

                next_page = request.args.get('next')

                if next_page and is_safe_url(next_page):
                    return redirect(next_page)

                if 'admin.dashboard' in current_app.view_functions:
                    return redirect(url_for('admin.dashboard'))
                return redirect('/')

            flash('Invalid admin username or password.', 'danger')

    return render_template('auth/login.html')


# =========================================================
# 2. LOGOUT ROUTE
# =========================================================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    
    if 'auth.login' in current_app.view_functions:
        return redirect(url_for('auth.login'))
    return redirect('/')