from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.database.models import Admin

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 1. If already logged in, skip login page and go straight to dashboard
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for('admin.dashboard'))

    # 2. AUTO-BYPASS FOR DEV MODE
    # Automatically log in as 'admin' if AUTO_LOGIN is enabled
    if current_app.config.get('AUTO_LOGIN_DEV'):
        admin = Admin.query.filter_by(username='admin').first()
        if admin:
            login_user(admin, remember=True)
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        from app.database.mongo_models import MongoAdmin
        admin = MongoAdmin.find_by_identifier(identifier)
        if not admin and Admin:
            admin = Admin.query.filter(
                (Admin.username == identifier) | (Admin.email == identifier)
            ).first()

        if admin and admin.check_password(password):
            # remember=True preserves session across browser restarts
            login_user(admin, remember=True)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')

    return render_template('auth/login.html')



@admin_bp.route('/dev-login')
def dev_login():
    """Direct shortcut route to auto-login as admin during development."""
    admin = Admin.query.filter_by(username='admin').first()
    if admin:
        login_user(admin, remember=True)
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))