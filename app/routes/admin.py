"""
app/routes/admin.py
Admin Authentication, Dashboard, Session Management, RBAC API Endpoints,
Universal CRUD Handlers, File Upload & Download, and Admin Management.
Enforces backend RBAC security on every endpoint.
"""
import os
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, Any

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    current_app,
    send_from_directory,
    abort,
)
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash

from app.database.models import Admin, Student
from app.auth.rbac import (
    admin_required,
    require_role,
    require_permission,
    has_permission,
    has_role,
    normalize_role,
    ROLE_SUPER_ADMIN,
    ROLE_ACADEMIC_ADMIN,
    ROLE_ADMISSION_ADMIN,
    ROLE_NOTICE_ADMIN,
    ROLE_EVENT_ADMIN,
    ROLE_BUS_ADMIN,
    ROLE_LIBRARY_ADMIN,
    ROLE_CANTEEN_ADMIN,
    ROLE_SPORTS_ADMIN,
    ROLE_DISPLAY_NAMES,
)
from app.database.admin_crud_service import AdminCRUDService, MODULE_CONFIGS
from app.utils.file_upload import validate_and_save_file, delete_uploaded_file, get_upload_dir

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def is_safe_url(target: str) -> bool:
    """Validates target URL to prevent Open Redirect vulnerabilities."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('', 'http', 'https') and (ref_url.netloc == test_url.netloc or not test_url.netloc)


# =========================================================================
# 1. ADMIN LOGIN & AUTHENTICATION
# =========================================================================
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Admin Login Endpoint.
    Redirects GET requests directly to unified /login.
    Supports JSON API submissions for backwards-compatible test suites.
    """
    # 1. If already logged in as active admin on GET request, redirect straight to dashboard
    if request.method == 'GET' and current_user.is_authenticated and getattr(current_user, 'is_admin', False) and getattr(current_user, 'is_active', True):
        return redirect(url_for('admin.dashboard'))

    # 2. Redirect all browser GET requests to the unified login page
    if request.method == 'GET':
        next_page = request.args.get('next')
        if next_page:
            return redirect(url_for('auth.login', next=next_page))
        return redirect(url_for('auth.login'))

    # 3. Auto-login shortcut only in explicit dev mode
    if current_app.config.get('AUTO_LOGIN_DEV'):
        admin = Admin.query.filter_by(username='superadmin').first() or Admin.query.filter_by(username='admin').first()
        if admin and admin.is_active:
            login_user(admin, remember=True)
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form or {}

        identifier = str(
            data.get('identifier') or
            data.get('username') or
            data.get('email') or
            ''
        ).strip()
        password = str(data.get('password') or '').strip()
        remember = bool(data.get('remember'))

        is_json_req = request.is_json or request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'

        if not identifier or not password:
            msg = "Please enter both admin username / email and password."
            if is_json_req:
                return jsonify({"status": "error", "error": "Bad Request", "message": msg}), 400
            flash(msg, 'error')
            return redirect(url_for('auth.login'))

        # ----------------------------------------------------
        # FIND ADMIN: Try MongoDB first, fallback to SQLite
        # ----------------------------------------------------
        admin_user = None
        try:
            from app.database.mongo_models import MongoAdmin
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

        if not admin_user:
            # Check if this identifier belongs to a student/faculty with valid password
            student_user = None
            try:
                from app.database.mongo_models import MongoStudent
                student_user = MongoStudent.find_by_identifier(identifier)
            except Exception:
                pass
            if not student_user and Student:
                if '@' in identifier and hasattr(Student, 'email'):
                    student_user = Student.query.filter_by(email=identifier).first()
                if not student_user and hasattr(Student, 'enrollment_no'):
                    student_user = Student.query.filter_by(enrollment_no=identifier).first()
            if student_user and hasattr(student_user, 'check_password') and student_user.check_password(password):
                msg = "Student/Faculty accounts must use the Student / Faculty login."
                if is_json_req:
                    return jsonify({"status": "error", "error": "WrongLoginMode", "message": msg}), 403
                flash(msg, 'error')
                return redirect(url_for('auth.login', tab='student_faculty'))

            msg = "Invalid admin credentials. Username or email not found."
            if is_json_req:
                return jsonify({"status": "error", "error": "Unauthorized", "message": msg}), 401
            flash(msg, 'error')
            return redirect(url_for('auth.login', tab='admin'))

        admin_status = getattr(admin_user, 'status', 'active' if getattr(admin_user, 'is_active', True) else 'inactive')
        if admin_status == 'suspended':
            msg = "Your admin account has been suspended. Please contact the Super Admin."
            if is_json_req:
                return jsonify({
                    "status": "error",
                    "error": "Forbidden",
                    "message": msg,
                    "admin_status": "suspended",
                    "account_status": "suspended"
                }), 403
            flash(msg, 'error')
            return redirect(url_for('auth.login'))
        elif admin_status == 'inactive' or not getattr(admin_user, 'is_active', True):
            msg = "Account is disabled. Your admin account is inactive. Please contact the Super Admin."
            if is_json_req:
                return jsonify({
                    "status": "error",
                    "error": "Forbidden",
                    "message": msg,
                    "admin_status": "inactive",
                    "account_status": "disabled"
                }), 403
            flash(msg, 'error')
            return redirect(url_for('auth.login'))

        if not hasattr(admin_user, 'check_password') or not admin_user.check_password(password):
            msg = "Invalid admin credentials. Incorrect password."
            if is_json_req:
                return jsonify({"status": "error", "error": "Unauthorized", "message": msg}), 401
            flash(msg, 'error')
            return redirect(url_for('auth.login'))

        login_user(admin_user, remember=remember)
        if hasattr(admin_user, 'update_last_login'):
            try:
                admin_user.update_last_login()
            except Exception:
                pass

        if is_json_req:
            admin_payload = admin_user.to_dict() if hasattr(admin_user, 'to_dict') else {
                "username": admin_user.username,
                "role": getattr(admin_user, 'role', 'super_admin')
            }
            return jsonify({
                "status": "success",
                "message": "Login successful.",
                "admin": admin_payload,
                "redirect_url": url_for('admin.dashboard')
            }), 200

        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)

        flash(f"Welcome back, {getattr(admin_user, 'name', 'Admin')}!", "success")
        return redirect(url_for('admin.dashboard'))

    return redirect(url_for('auth.login'))


@admin_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Admin logout endpoint."""
    logout_user()
    session.clear()

    if request.is_json or request.path.startswith('/api/'):
        return jsonify({
            "status": "success",
            "message": "You have been logged out successfully."
        }), 200

    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@admin_bp.route('/dev-login')
def dev_login():
    """Shortcut route for testing in dev environments."""
    if not current_app.debug and not current_app.config.get('AUTO_LOGIN_DEV'):
        flash("Dev login is disabled in production.", "error")
        return redirect(url_for('auth.login'))

    admin = Admin.query.filter_by(username='superadmin').first() or Admin.query.filter_by(username='admin').first()
    if admin and admin.is_active:
        login_user(admin, remember=True)
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))


# =========================================================================
# 2. ADMIN DASHBOARD & PROFILE
# =========================================================================
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Renders the main admin dashboard with role-customized metrics and urgent alerts."""
    stats = AdminCRUDService.get_stats_for_admin(current_user)
    return render_template(
        'admin/dashboard.html',
        admin=current_user,
        stats=stats
    )


@admin_bp.route('/profile')
@admin_required
def profile():
    """Renders the admin profile page."""
    return render_template(
        'admin/profile.html',
        admin=current_user
    )


@admin_bp.route('/api/me', methods=['GET'])
@admin_bp.route('/api/profile', methods=['GET'])
@admin_required
def api_me():
    """
    Returns current authenticated admin profile and permissions.
    CRITICAL: Never exposes password or password_hash.
    """
    if hasattr(current_user, 'to_dict'):
        data = current_user.to_dict()
    else:
        data = {
            "id": getattr(current_user, 'id', None),
            "name": getattr(current_user, 'name', 'Administrator'),
            "username": getattr(current_user, 'username', ''),
            "email": getattr(current_user, 'email', ''),
            "role": getattr(current_user, 'role', 'super_admin'),
            "is_active": getattr(current_user, 'is_active', True)
        }

    return jsonify({
        "status": "success",
        "admin": data
    }), 200


@admin_bp.route('/api/stats', methods=['GET'])
@admin_required
def api_stats():
    """Returns dynamic dashboard counters tailored to the logged-in admin role."""
    from app.database.mongodb import is_mongodb_connected, get_last_error, get_mongodb_uri
    stats = AdminCRUDService.get_stats_for_admin(current_user)
    has_uri = bool(get_mongodb_uri())
    return jsonify({
        "status": "success",
        "stats": stats,
        "mongo_status": {
            "has_uri": has_uri,
            "connected": is_mongodb_connected(),
            "last_error": get_last_error()
        }
    }), 200


# =========================================================================
# 3. UNIVERSAL CRUD HTML VIEWS & ROLE PROTECTION
# =========================================================================
@admin_bp.route('/module/<module_name>')
@admin_required
def render_module(module_name: str, template_name: str = None):
    """
    Universal CRUD page renderer.
    Enforces RBAC permissions before granting access.
    Automatically renders dedicated page template if present.
    """
    config = MODULE_CONFIGS.get(module_name)
    if not config:
        flash(f"Module '{module_name}' does not exist.", "error")
        return redirect(url_for('admin.dashboard'))

    req_perm = config.get("required_permission")
    if not has_permission(current_user, req_perm) and not has_role(current_user, ROLE_SUPER_ADMIN):
        flash(f"Access Denied: You do not have permission to access {config['title']}.", "error")
        abort(403)

    if template_name:
        return render_template(template_name, module_name=module_name, config=config, admin=current_user)

    # Check for dedicated template
    candidate_template = f'admin/{module_name}.html'
    template_file = os.path.join(current_app.root_path, 'templates', candidate_template)
    if os.path.exists(template_file):
        return render_template(candidate_template, module_name=module_name, config=config, admin=current_user)

    return render_template(
        'admin/crud_module.html',
        module_name=module_name,
        config=config,
        admin=current_user
    )


# -------------------------------------------------------------
# Direct Route Handlers for All 28 Admin Pages
# -------------------------------------------------------------

# CORE
@admin_bp.route('/roles-permissions')
@admin_bp.route('/roles')
@admin_bp.route('/roles_permissions')
@require_role(ROLE_SUPER_ADMIN)
def roles_permissions():
    """Renders the Roles & Permissions matrix view for Super Admin."""
    return render_template('admin/roles_permissions.html', admin=current_user)

# ACADEMIC ADMIN
@admin_bp.route('/students')
@admin_required
def students():
    return render_module('students', 'admin/students.html')

@admin_bp.route('/faculty')
@admin_required
def faculty():
    return render_module('faculty', 'admin/faculty.html')

@admin_bp.route('/timetable')
@admin_required
def timetable():
    return render_module('timetable', 'admin/timetable.html')

@admin_bp.route('/rooms')
@admin_bp.route('/rooms-facilities')
@admin_bp.route('/rooms_facilities')
@admin_bp.route('/campus-info')
@admin_bp.route('/facilities')
@admin_required
def rooms():
    return render_module('rooms', 'admin/rooms.html')

@admin_bp.route('/subjects')
@admin_required
def subjects():
    return render_module('subjects', 'admin/subjects.html')

@admin_bp.route('/placements')
@admin_required
def placements():
    return render_module('placements', 'admin/placements.html')

@admin_bp.route('/documents')
@admin_bp.route('/academic-documents')
@admin_bp.route('/academic_documents')
@admin_required
def academic_documents():
    return render_module('academic_documents', 'admin/academic_documents.html')

# ADMISSION ADMIN
@admin_bp.route('/admission')
@admin_bp.route('/admission-info')
@admin_bp.route('/admission-documents')
@admin_bp.route('/admission-notices')
@admin_required
def admission():
    return render_module('admission_info', 'admin/admission.html')

@admin_bp.route('/admission_info')
@admin_required
def admission_info():
    return render_module('admission_info', 'admin/admission.html')

@admin_bp.route('/admission_documents')
@admin_required
def admission_documents():
    return render_module('admission_documents', 'admin/admission.html')

@admin_bp.route('/admission_notices')
@admin_required
def admission_notices():
    return render_module('admission_notices', 'admin/admission.html')

# NOTICE ADMIN
@admin_bp.route('/notices')
@admin_required
def notices():
    return render_module('notices', 'admin/notices.html')

# EVENT ADMIN
@admin_bp.route('/events')
@admin_required
def events():
    return render_module('events', 'admin/events.html')

# BUS ADMIN
@admin_bp.route('/transport')
@admin_bp.route('/buses')
@admin_required
def buses():
    return render_module('transport', 'admin/buses.html')

@admin_bp.route('/bus-routes')
@admin_bp.route('/bus_routes')
@admin_required
def bus_routes():
    return render_module('transport', 'admin/bus_routes.html')

@admin_bp.route('/bus-stops')
@admin_bp.route('/bus_stops')
@admin_required
def bus_stops():
    return render_module('transport', 'admin/bus_stops.html')

@admin_bp.route('/bus-timings')
@admin_bp.route('/bus_timings')
@admin_required
def bus_timings():
    return render_module('transport', 'admin/bus_timings.html')

# LIBRARY ADMIN
@admin_bp.route('/library')
@admin_bp.route('/library-info')
@admin_bp.route('/library_info')
@admin_required
def library():
    return render_module('library_info', 'admin/library.html')

@admin_bp.route('/library-books')
@admin_bp.route('/library_books')
@admin_bp.route('/books')
@admin_required
def library_books():
    return render_module('library_books', 'admin/library_books.html')

@admin_bp.route('/library-members')
@admin_bp.route('/library_members')
@admin_bp.route('/members')
@admin_required
def library_members():
    return render_module('library_members', 'admin/library_members.html')

@admin_bp.route('/issue-return')
@admin_bp.route('/issue_return')
@admin_bp.route('/library-issue-return')
@admin_bp.route('/library_issue_return')
@admin_required
def issue_return():
    return render_module('library_issue_return', 'admin/issue_return.html')

# CANTEEN ADMIN
@admin_bp.route('/canteen')
@admin_required
def canteen():
    return render_module('canteen', 'admin/canteen.html')

@admin_bp.route('/canteen-menu')
@admin_bp.route('/canteen_menu')
@admin_required
def canteen_menu():
    return render_module('canteen', 'admin/canteen_menu.html')

@admin_bp.route('/food-items')
@admin_bp.route('/food_items')
@admin_required
def food_items():
    return render_module('canteen', 'admin/food_items.html')

# SPORTS ADMIN
@admin_bp.route('/sports')
@admin_required
def sports():
    return render_module('sports', 'admin/sports.html')

@admin_bp.route('/sports-events')
@admin_bp.route('/sports_events')
@admin_required
def sports_events():
    return render_module('sports_events', 'admin/sports_events.html')

@admin_bp.route('/grounds')
@admin_required
def grounds():
    return render_module('grounds', 'admin/grounds.html')


# =========================================================================
# 4. SUPER ADMIN USER MANAGEMENT VIEW
# =========================================================================
@admin_bp.route('/admins')
@require_role(ROLE_SUPER_ADMIN)
def admin_management():
    """Renders the Admin Accounts Management view for Super Admin."""
    return render_template(
        'admin/admin_management.html',
        admin=current_user
    )


# =========================================================================
# 5. UNIVERSAL RESTful CRUD API ENDPOINTS
# =========================================================================
def _check_module_permission(module_name: str) -> bool:
    """Helper to verify permission for current admin user on target module."""
    resolved_key = AdminCRUDService.resolve_module_key(module_name)
    config = MODULE_CONFIGS.get(resolved_key)
    if not config:
        return False
    req_perm = config.get("required_permission")
    return has_permission(current_user, req_perm) or has_role(current_user, ROLE_SUPER_ADMIN)


@admin_bp.route('/api/crud/<module_name>', methods=['GET'])
@admin_required
def api_list_items(module_name: str):
    """List, search, filter, sort, and paginate records in a module."""
    if not _check_module_permission(module_name):
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": f"You do not have permission to access module '{module_name}'."
        }), 403

    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by')
    sort_order = int(request.args.get('sort_order', 1))
    page = int(request.args.get('page', 1))

    limit_raw = request.args.get('limit', '50')
    if str(limit_raw).lower() in ('all', '0', '-1'):
        limit = 0
    else:
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 50

    # Extract dynamic filters from query params (e.g. filter_department, filter_category, etc.)
    filters: Dict[str, Any] = {}
    for k, v in request.args.items():
        if k.startswith('filter_') and v:
            actual_key = k.replace('filter_', '', 1)
            filters[actual_key] = v
        elif k in ['department', 'category', 'status', 'priority', 'program', 'semester', 'division', 'day', 'year', 'faculty', 'room', 'is_urgent', 'subject_type', 'credits', 'subject_code'] and v:
            filters[k] = v

    result = AdminCRUDService.list_items(
        module_key=module_name,
        search=search,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )

    return jsonify(result), 200


@admin_bp.route('/api/crud/<module_name>/<item_id>', methods=['GET'])
@admin_required
def api_get_item(module_name: str, item_id: str):
    """Retrieve details of a single record."""
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    item = AdminCRUDService.get_item(module_name, item_id)
    if not item:
        return jsonify({"status": "error", "error": "Not Found", "message": f"Item '{item_id}' not found."}), 404

    return jsonify({"status": "success", "item": item}), 200


@admin_bp.route('/api/crud/<module_name>', methods=['POST'])
@admin_required
def api_create_item(module_name: str):
    """Create a new record in the module."""
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    success, msg, created = AdminCRUDService.create_item(module_name, data, admin_user=current_user)

    if not success:
        return jsonify({"status": "error", "error": "Bad Request", "message": msg}), 400

    return jsonify({"status": "success", "message": msg, "item": created}), 201


@admin_bp.route('/api/crud/<module_name>/<item_id>', methods=['PUT', 'POST'])
@admin_required
def api_update_item(module_name: str, item_id: str):
    """Update an existing record in the module."""
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    success, msg, updated = AdminCRUDService.update_item(module_name, item_id, data, admin_user=current_user)

    if not success:
        status_code = 404 if "not found" in msg.lower() else 400
        return jsonify({"status": "error", "error": "Update Failed", "message": msg}), status_code

    return jsonify({"status": "success", "message": msg, "item": updated}), 200


@admin_bp.route('/api/crud/<module_name>/<item_id>', methods=['DELETE'])
@admin_required
def api_delete_item(module_name: str, item_id: str):
    """Delete a record from the module."""
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    success, msg = AdminCRUDService.delete_item(module_name, item_id)
    if not success:
        return jsonify({"status": "error", "error": "Not Found", "message": msg}), 404

    return jsonify({"status": "success", "message": msg}), 200


# =========================================================================
# 5.1. STUDENT REGISTRATION APPROVAL & NOTIFICATIONS WORKFLOW
# =========================================================================
@admin_bp.route('/api/students/<student_id>/approve', methods=['POST'])
@admin_bp.route('/api/students/<student_id>/accept', methods=['POST'])
@admin_required
@require_permission('academic', 'students')
def api_approve_student(student_id):
    """
    Approves a pending student registration request.
    Enforces RBAC: only Academic Admin and Super Admin can approve.
    Sets status='active', approved_by, approved_at.
    Creates student notification in MongoDB.
    """
    from datetime import datetime
    from bson import ObjectId
    from app.database.mongodb import get_collection
    from app.database.mongo_models import MongoNotificationService

    coll = get_collection('students')
    admin_identifier = getattr(current_user, 'username', getattr(current_user, 'name', 'admin'))
    admin_id_str = getattr(current_user, 'id', admin_identifier)
    now = datetime.utcnow()

    student_doc = None
    if coll is not None:
        query = {
            "$or": [
                {"enrollment_no": str(student_id)},
                {"enrollment_number": str(student_id)},
                {"id": str(student_id)},
                {"id": int(student_id) if str(student_id).isdigit() else -1},
                {"_id": ObjectId(str(student_id)) if ObjectId.is_valid(str(student_id)) else None}
            ]
        }
        student_doc = coll.find_one(query)
        if student_doc:
            coll.update_one(
                {"_id": student_doc["_id"]},
                {"$set": {
                    "status": "active",
                    "approved_by": admin_identifier,
                    "approved_by_id": str(admin_id_str),
                    "approved_at": now.isoformat(),
                    "rejected_by": None,
                    "rejected_at": None,
                    "rejection_reason": None,
                    "updated_at": now.isoformat()
                }}
            )

    # SQLite fallback update
    try:
        from app.database.models import Student
        from app.extensions import db
        s_db = Student.query.filter(
            (Student.enrollment_no == str(student_id)) | (Student.id == int(student_id) if str(student_id).isdigit() else -1)
        ).first()
        if s_db:
            if hasattr(s_db, 'status'):
                s_db.status = 'active'
            if hasattr(s_db, 'approved_by'):
                s_db.approved_by = admin_identifier
            if hasattr(s_db, 'approved_at'):
                s_db.approved_at = now
            db.session.commit()
    except Exception:
        pass

    target_enroll = student_doc.get("enrollment_no") or str(student_id) if student_doc else str(student_id)
    student_name = student_doc.get("full_name") or student_doc.get("name") if student_doc else "Student"

    # Send Student Notification
    # Send Student Notification
    MongoNotificationService.notify_student(
        student_id=target_enroll,
        title="Registration Approved",
        message="Your SVIT student registration has been approved. You can now access SVIT AI.",
        category="approval",
        data={
            "approval_status": "approved",
            "status": "active",
            "approved_at": now.isoformat(),
            "approved_by": admin_identifier,
            "department": student_doc.get("department", "SVIT Vasad") if student_doc else "SVIT Vasad"
        }
    )

    # Dispatch Admin Notification Log
    MongoNotificationService.notify_admins(
        title="Student Registration Approved",
        message=f"Student {student_name} ({target_enroll}) registration was approved by {admin_identifier}.",
        category="registration",
        data={
            "student_name": student_name,
            "enrollment_no": target_enroll,
            "status": "approved",
            "approved_by": admin_identifier,
            "approved_at": now.isoformat()
        },
        link="/admin/students"
    )

    return jsonify({
        "status": "success",
        "message": "Student registration approved successfully.",
        "student": {
            "id": target_enroll,
            "name": student_name,
            "status": "active",
            "approved_by": admin_identifier,
            "approved_at": now.isoformat()
        }
    }), 200


@admin_bp.route('/api/students/<student_id>/reject', methods=['POST'])
@admin_required
@require_permission('academic', 'students')
def api_reject_student(student_id):
    """
    Rejects a student registration request with an optional reason.
    Enforces RBAC: only Academic Admin and Super Admin can reject.
    Sets status='rejected', rejected_by, rejected_at, rejection_reason.
    Creates student notification in MongoDB.
    """
    from datetime import datetime
    from bson import ObjectId
    from app.database.mongodb import get_collection
    from app.database.mongo_models import MongoNotificationService

    data = request.get_json(silent=True) or request.form or {}
    reason = str(data.get('reason') or data.get('rejection_reason') or '').strip()

    coll = get_collection('students')
    admin_identifier = getattr(current_user, 'username', getattr(current_user, 'name', 'admin'))
    admin_id_str = getattr(current_user, 'id', admin_identifier)
    now = datetime.utcnow()

    student_doc = None
    if coll is not None:
        query = {
            "$or": [
                {"enrollment_no": str(student_id)},
                {"enrollment_number": str(student_id)},
                {"id": str(student_id)},
                {"id": int(student_id) if str(student_id).isdigit() else -1},
                {"_id": ObjectId(str(student_id)) if ObjectId.is_valid(str(student_id)) else None}
            ]
        }
        student_doc = coll.find_one(query)
        if student_doc:
            coll.update_one(
                {"_id": student_doc["_id"]},
                {"$set": {
                    "status": "rejected",
                    "rejected_by": admin_identifier,
                    "rejected_by_id": str(admin_id_str),
                    "rejected_at": now.isoformat(),
                    "rejection_reason": reason,
                    "updated_at": now.isoformat()
                }}
            )

    # SQLite fallback update
    try:
        from app.database.models import Student
        from app.extensions import db
        s_db = Student.query.filter(
            (Student.enrollment_no == str(student_id)) | (Student.id == int(student_id) if str(student_id).isdigit() else -1)
        ).first()
        if s_db:
            if hasattr(s_db, 'status'):
                s_db.status = 'rejected'
            if hasattr(s_db, 'rejected_by'):
                s_db.rejected_by = admin_identifier
            if hasattr(s_db, 'rejected_at'):
                s_db.rejected_at = now
            if hasattr(s_db, 'rejection_reason'):
                s_db.rejection_reason = reason
            db.session.commit()
    except Exception:
        pass

    target_enroll = student_doc.get("enrollment_no") or str(student_id) if student_doc else str(student_id)
    student_name = student_doc.get("full_name") or student_doc.get("name") if student_doc else "Student"

    notif_msg = "Your SVIT registration request was rejected."
    if reason:
        notif_msg += f" Reason: {reason}"

    # Send Student Notification
    MongoNotificationService.notify_student(
        student_id=target_enroll,
        title="Registration Request Rejected",
        message=notif_msg,
        category="rejection",
        data={
            "approval_status": "rejected",
            "status": "rejected",
            "rejected_at": now.isoformat(),
            "rejected_by": admin_identifier,
            "rejection_reason": reason
        }
    )

    # Dispatch Admin Notification Log
    MongoNotificationService.notify_admins(
        title="Student Registration Rejected",
        message=f"Student {student_name} ({target_enroll}) registration was rejected by {admin_identifier}." + (f" Reason: {reason}" if reason else ""),
        category="registration",
        data={
            "student_name": student_name,
            "enrollment_no": target_enroll,
            "status": "rejected",
            "rejected_by": admin_identifier,
            "rejection_reason": reason,
            "rejected_at": now.isoformat()
        },
        link="/admin/students?status=rejected"
    )

    return jsonify({
        "status": "success",
        "message": "Student registration rejected.",
        "student": {
            "id": target_enroll,
            "name": student_name,
            "status": "rejected",
            "rejected_by": admin_identifier,
            "rejected_at": now.isoformat(),
            "rejection_reason": reason
        }
    }), 200


@admin_bp.route('/api/notifications', methods=['GET'])
@admin_required
def api_admin_notifications():
    """Returns real-time notifications for the Admin Header UI."""
    from app.database.mongo_models import MongoNotificationService
    res = MongoNotificationService.get_admin_notifications(limit=30)
    return jsonify(res), 200


@admin_bp.route('/api/notifications/<notification_id>/read', methods=['PATCH', 'POST'])
@admin_required
def api_admin_notification_mark_read(notification_id):
    """Marks a single admin notification as read."""
    from app.database.mongo_models import MongoNotificationService
    MongoNotificationService.mark_admin_notification_read(notification_id)
    return jsonify({"status": "success"}), 200


@admin_bp.route('/api/notifications/read-all', methods=['POST'])
@admin_required
def api_admin_notifications_mark_all_read():
    """Marks all admin notifications as read."""
    from app.database.mongo_models import MongoNotificationService
    MongoNotificationService.mark_all_admin_notifications_read()
    return jsonify({"status": "success"}), 200


# =========================================================================
# 6. FILE UPLOAD, DELETE & SECURE DOWNLOAD APIS
# =========================================================================
@admin_bp.route('/api/upload', methods=['POST'])
@admin_required
def api_upload_file():
    """
    Secure file upload API for images and PDF/DOCX documents.
    Validates extension, size limits, and sanitizes filenames.
    Never exposes internal filesystem paths.
    """
    if 'file' not in request.files:
        return jsonify({"status": "error", "error": "Bad Request", "message": "No file uploaded in request."}), 400

    file_obj = request.files['file']
    category = request.form.get('category', 'image').strip().lower()

    success, msg, file_info = validate_and_save_file(
        file_storage=file_obj,
        category=category,
        uploaded_by=getattr(current_user, 'username', 'admin')
    )

    if not success:
        return jsonify({"status": "error", "error": "Upload Failed", "message": msg}), 400

    return jsonify({
        "status": "success",
        "message": msg,
        "file": file_info
    }), 200


@admin_bp.route('/api/upload/delete', methods=['POST', 'DELETE'])
@admin_required
def api_delete_file():
    """Safely deletes an uploaded asset given its URL or filename."""
    data = request.get_json(silent=True) or request.form or {}
    file_url = data.get('url') or data.get('file_url') or data.get('filename') or ''

    if not file_url:
        return jsonify({"status": "error", "error": "Bad Request", "message": "Missing file URL or filename."}), 400

    deleted = delete_uploaded_file(file_url)
    if deleted:
        return jsonify({"status": "success", "message": "File removed successfully."}), 200
    else:
        return jsonify({"status": "error", "message": "File not found or could not be removed."}), 404


@admin_bp.route('/api/download/<subfolder>/<filename>')
@admin_required
def api_download_file(subfolder: str, filename: str):
    """Securely serves/downloads uploaded files without exposing server path."""
    if subfolder not in ('images', 'documents'):
        abort(404)

    upload_dir = get_upload_dir(subfolder)
    return send_from_directory(upload_dir, filename, as_attachment=True)


# =========================================================================
# 6.1 RAG DOCUMENT INDEXING & RE-INDEXING APIS
# =========================================================================
@admin_bp.route('/api/rag/reindex/<module_name>/<item_id>', methods=['POST'])
@admin_required
def api_rag_reindex(module_name: str, item_id: str):
    """
    Triggers re-indexing of an uploaded document into the RAG vector store.
    Flushes old chunks, extracts text again, chunks, generates embeddings,
    and updates metadata.
    """
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    success, msg, updated = AdminCRUDService.reindex_document(module_name, item_id, admin_user=current_user)
    if not success:
        status_code = 404 if "not found" in msg.lower() else 400
        return jsonify({"status": "error", "error": "Re-index Failed", "message": msg, "item": updated}), status_code

    return jsonify({"status": "success", "message": msg, "item": updated}), 200


@admin_bp.route('/api/rag/status/<module_name>/<item_id>', methods=['GET'])
@admin_required
def api_rag_status(module_name: str, item_id: str):
    """Fetches real-time RAG processing/indexing status for a document."""
    if not _check_module_permission(module_name):
        return jsonify({"status": "error", "error": "Forbidden", "message": "Permission denied."}), 403

    item = AdminCRUDService.get_item(module_name, item_id)
    if not item:
        return jsonify({"status": "error", "error": "Not Found", "message": "Document not found."}), 404

    return jsonify({
        "status": "success",
        "document_id": item_id,
        "rag_status": item.get("rag_status", "UNKNOWN"),
        "chunk_count": item.get("chunk_count", 0),
        "page_count": item.get("page_count", 0),
        "version": item.get("version", 1),
        "indexed_at": item.get("indexed_at"),
        "error_message": item.get("error_message", "")
    }), 200


# =========================================================================
# 7. SUPER ADMIN USER MANAGEMENT APIS
# =========================================================================
@admin_bp.route('/api/admins', methods=['GET'])
@require_role(ROLE_SUPER_ADMIN)
def api_list_admins():
    """Returns list of all admin accounts (Super Admin only)."""
    admin_list = []
    try:
        from app.database.mongo_models import MongoAdmin
        mongo_admins = MongoAdmin.get_all()
        for a in mongo_admins:
            admin_list.append(a.to_dict())
    except Exception:
        pass

    if not admin_list and Admin:
        sqlite_admins = Admin.query.all()
        for a in sqlite_admins:
            admin_list.append(a.to_dict())

    return jsonify({
        "status": "success",
        "admins": admin_list
    }), 200


@admin_bp.route('/api/admins', methods=['POST'])
@require_role(ROLE_SUPER_ADMIN)
def api_create_admin():
    """Create a new administrator account (Super Admin only)."""
    data = request.get_json(silent=True) or request.form or {}
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    name = str(data.get('name', '')).strip() or username
    role = normalize_role(str(data.get('role', 'academic_admin')).strip())
    department = str(data.get('department', '')).strip()
    password = str(data.get('password', '')).strip()

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Username, email, and password are required."}), 400

    from app.database.mongo_models import MongoAdmin
    existing = None
    try:
        existing = MongoAdmin.find_by_identifier(username) or MongoAdmin.find_by_identifier(email)
    except Exception:
        pass

    if not existing and Admin:
        existing = Admin.query.filter((Admin.username == username) | (Admin.email == email)).first()

    if existing:
        return jsonify({"status": "error", "message": f"Admin with username or email already exists."}), 400

    admin_doc = {
        "username": username,
        "email": email,
        "name": name,
        "role": role,
        "department": department,
        "password": password,
        "is_active": True,
        "created_at": datetime.utcnow()
    }

    created = None
    try:
        created = MongoAdmin.save_or_update(admin_doc)
    except Exception:
        pass

    if Admin:
        try:
            from app.extensions import db
            existing_sql = Admin.query.filter_by(username=username).first()
            if not existing_sql:
                new_sql = Admin(
                    username=username,
                    email=email,
                    name=name,
                    role=role,
                    department=department,
                    is_active=True
                )
                new_sql.set_password(password)
                db.session.add(new_sql)
                db.session.commit()
                if not created:
                    created = new_sql
        except Exception:
            pass

    return jsonify({
        "status": "success",
        "message": f"Admin '{username}' created successfully.",
        "admin": created.to_dict() if hasattr(created, 'to_dict') else {"username": username}
    }), 201


@admin_bp.route('/api/admins/<admin_id>', methods=['PUT'])
@require_role(ROLE_SUPER_ADMIN)
def api_update_admin(admin_id: str):
    """Updates admin account details or active status (Super Admin only)."""
    data = request.get_json(silent=True) or request.form or {}
    from app.database.mongo_models import MongoAdmin
    admin_obj = None
    try:
        admin_obj = MongoAdmin.get_by_id(admin_id) or MongoAdmin.find_by_identifier(admin_id)
    except Exception:
        pass

    if not admin_obj and Admin:
        from sqlalchemy import or_
        conds = [(Admin.username == str(admin_id)), (Admin.email == str(admin_id).lower())]
        if str(admin_id).isdigit():
            conds.append(Admin.id == int(admin_id))
        admin_obj = Admin.query.filter(or_(*conds)).first()

    if not admin_obj:
        return jsonify({"status": "error", "message": "Admin account not found."}), 404

    # Superadmin cannot deactivate themselves
    if admin_obj.username == current_user.username and 'is_active' in data and not data['is_active']:
        return jsonify({"status": "error", "message": "You cannot deactivate your own active Super Admin account."}), 400

    update_payload = dict(data)
    if 'role' in update_payload:
        update_payload['role'] = normalize_role(update_payload['role'])

    updated_dict = {}
    if hasattr(admin_obj, '_doc'):
        update_payload['id'] = admin_obj.id
        update_payload['username'] = admin_obj.username
        updated = MongoAdmin.save_or_update(update_payload)
        updated_dict = updated.to_dict() if updated else {}
    elif Admin:
        from app.extensions import db
        for k, v in update_payload.items():
            if hasattr(admin_obj, k) and k not in ('id', 'password_hash'):
                setattr(admin_obj, k, v)
        admin_obj.updated_at = datetime.utcnow()
        db.session.commit()
        updated_dict = admin_obj.to_dict()

    return jsonify({
        "status": "success",
        "message": "Admin updated successfully.",
        "admin": updated_dict
    }), 200


@admin_bp.route('/api/admins/<admin_id>/reset-password', methods=['POST'])
@admin_required
def api_reset_admin_password(admin_id: str):
    """Resets password for an admin account (Own account or Super Admin only)."""
    is_self = (admin_id in ("me", str(getattr(current_user, 'id', '')), getattr(current_user, 'username', '')))
    if not is_self and not has_role(current_user, ROLE_SUPER_ADMIN):
        return jsonify({"status": "error", "message": "Super Admin role required to reset other administrators' passwords."}), 403

    if admin_id == "me":
        admin_id = getattr(current_user, 'username', str(getattr(current_user, 'id', '')))

    data = request.get_json(silent=True) or request.form or {}
    new_password = str(data.get('new_password', '')).strip()

    if not new_password or len(new_password) < 6:
        return jsonify({"status": "error", "message": "New password must be at least 6 characters."}), 400

    from app.database.mongo_models import MongoAdmin
    admin_obj = None
    try:
        admin_obj = MongoAdmin.get_by_id(admin_id) or MongoAdmin.find_by_identifier(admin_id)
    except Exception:
        pass

    if not admin_obj and Admin:
        from sqlalchemy import or_
        conds = [(Admin.username == str(admin_id)), (Admin.email == str(admin_id).lower())]
        if str(admin_id).isdigit():
            conds.append(Admin.id == int(admin_id))
        admin_obj = Admin.query.filter(or_(*conds)).first()

    if not admin_obj:
        return jsonify({"status": "error", "message": "Admin account not found."}), 404

    if hasattr(admin_obj, '_doc'):
        MongoAdmin.save_or_update({"id": admin_obj.id, "username": admin_obj.username, "password": new_password})
    elif Admin:
        from app.extensions import db
        admin_obj.set_password(new_password)
        admin_obj.updated_at = datetime.utcnow()
        db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Password for {admin_obj.username} reset successfully."
    }), 200


# =========================================================================
# 8. RBAC VERIFICATION TEST ENDPOINTS (PRESERVED FROM STEP 1)
# =========================================================================
@admin_bp.route('/api/test/super-admin-only', methods=['GET', 'POST'])
@require_role(ROLE_SUPER_ADMIN)
def test_super_admin():
    """Test endpoint restricted strictly to Super Admin."""
    return jsonify({
        "status": "success",
        "message": "Super Admin access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/academic', methods=['GET', 'POST'])
@require_permission("academic")
def test_academic_access():
    """Test endpoint restricted to Academic Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Academic module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/admission', methods=['GET', 'POST'])
@require_permission("admission")
def test_admission_access():
    """Test endpoint restricted to Admission Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Admission module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/notices', methods=['GET', 'POST'])
@require_permission("notices")
def test_notices_access():
    """Test endpoint restricted to Notice Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Notice module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/events', methods=['GET', 'POST'])
@require_permission("events")
def test_events_access():
    """
    Test endpoint restricted to College Event Admin (and Super Admin).
    Sports Admin must NOT be allowed.
    """
    return jsonify({
        "status": "success",
        "message": "Events module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/bus', methods=['GET', 'POST'])
@require_permission("bus")
def test_bus_access():
    """Test endpoint restricted to Bus Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Bus module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/library', methods=['GET', 'POST'])
@require_permission("library")
def test_library_access():
    """Test endpoint restricted to Library Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Library module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/canteen', methods=['GET', 'POST'])
@require_permission("canteen")
def test_canteen_access():
    """Test endpoint restricted to Canteen Admin (and Super Admin)."""
    return jsonify({
        "status": "success",
        "message": "Canteen module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200


@admin_bp.route('/api/test/sports', methods=['GET', 'POST'])
@require_permission("sports")
def test_sports_access():
    """
    Test endpoint restricted to Sports Admin (and Super Admin).
    Event Admin must NOT be allowed.
    """
    return jsonify({
        "status": "success",
        "message": "Sports module access granted.",
        "admin": current_user.username,
        "role": current_user.role
    }), 200
