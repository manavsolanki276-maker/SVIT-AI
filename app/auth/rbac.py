"""
app/auth/rbac.py
Role-Based Access Control (RBAC) definitions, permissions matrix,
and authorization decorators for the SVIT Admin System.
"""
from functools import wraps
from typing import Set, List, Dict, Any, Optional
from flask import request, jsonify, abort, render_template, redirect, url_for, flash, current_app
from flask_login import current_user

# =========================================================================
# 1. ADMIN ROLE DEFINITIONS & CANONICAL NAMES
# =========================================================================
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ACADEMIC_ADMIN = "academic_admin"
ROLE_ADMISSION_ADMIN = "admission_admin"
ROLE_NOTICE_ADMIN = "notice_admin"
ROLE_EVENT_ADMIN = "event_admin"
ROLE_BUS_ADMIN = "bus_admin"
ROLE_LIBRARY_ADMIN = "library_admin"
ROLE_CANTEEN_ADMIN = "canteen_admin"
ROLE_SPORTS_ADMIN = "sports_admin"

# Normalized role name lookup with common aliases
ROLE_ALIASES: Dict[str, str] = {
    "super_admin": ROLE_SUPER_ADMIN,
    "superadmin": ROLE_SUPER_ADMIN,
    "admin": ROLE_SUPER_ADMIN,
    "super": ROLE_SUPER_ADMIN,

    "academic_admin": ROLE_ACADEMIC_ADMIN,
    "academic": ROLE_ACADEMIC_ADMIN,
    "academics": ROLE_ACADEMIC_ADMIN,

    "admission_admin": ROLE_ADMISSION_ADMIN,
    "admission": ROLE_ADMISSION_ADMIN,
    "admissions": ROLE_ADMISSION_ADMIN,

    "notice_admin": ROLE_NOTICE_ADMIN,
    "notices_admin": ROLE_NOTICE_ADMIN,
    "notice_announcement_admin": ROLE_NOTICE_ADMIN,
    "notice": ROLE_NOTICE_ADMIN,
    "announcement_admin": ROLE_NOTICE_ADMIN,

    "event_admin": ROLE_EVENT_ADMIN,
    "events_admin": ROLE_EVENT_ADMIN,
    "event": ROLE_EVENT_ADMIN,
    "events": ROLE_EVENT_ADMIN,

    "bus_admin": ROLE_BUS_ADMIN,
    "transport_admin": ROLE_BUS_ADMIN,
    "bus": ROLE_BUS_ADMIN,
    "transport": ROLE_BUS_ADMIN,

    "library_admin": ROLE_LIBRARY_ADMIN,
    "library": ROLE_LIBRARY_ADMIN,

    "canteen_admin": ROLE_CANTEEN_ADMIN,
    "canteen": ROLE_CANTEEN_ADMIN,

    "sports_admin": ROLE_SPORTS_ADMIN,
    "sport_admin": ROLE_SPORTS_ADMIN,
    "sports": ROLE_SPORTS_ADMIN,
}

ALL_ADMIN_ROLES = [
    ROLE_SUPER_ADMIN,
    ROLE_ACADEMIC_ADMIN,
    ROLE_ADMISSION_ADMIN,
    ROLE_NOTICE_ADMIN,
    ROLE_EVENT_ADMIN,
    ROLE_BUS_ADMIN,
    ROLE_LIBRARY_ADMIN,
    ROLE_CANTEEN_ADMIN,
    ROLE_SPORTS_ADMIN,
]

ROLE_DISPLAY_NAMES = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_ACADEMIC_ADMIN: "Academic Admin",
    ROLE_ADMISSION_ADMIN: "Admission Admin",
    ROLE_NOTICE_ADMIN: "Notice / Announcement Admin",
    ROLE_EVENT_ADMIN: "Event Admin",
    ROLE_BUS_ADMIN: "Bus Admin",
    ROLE_LIBRARY_ADMIN: "Library Admin",
    ROLE_CANTEEN_ADMIN: "Canteen Admin",
    ROLE_SPORTS_ADMIN: "Sports Admin",
}

# =========================================================================
# 2. PERMISSIONS MATRIX
# =========================================================================
# Module permissions map
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_SUPER_ADMIN: {"*"},  # Full access to everything
    ROLE_ACADEMIC_ADMIN: {
        "academic",
        "students",
        "faculty",
        "timetable",
        "rooms",
        "subjects",
        "placements",
        "academic_documents",
        "rag",
    },
    ROLE_ADMISSION_ADMIN: {
        "admission",
        "admission_info",
        "admission_documents",
        "admission_notices",
    },
    ROLE_NOTICE_ADMIN: {
        "notices",
        "urgent_notices",
        "general_updates",
        "emergency_announcements",
        "holiday_announcements",
        "college_status",
        "rain_weather",
        "class_cancellations",
        "alerts",
    },
    ROLE_EVENT_ADMIN: {
        "events",
        "cultural_events",
        "technical_events",
        "hackathons",
        "seminars",
        "workshops",
        "festivals",
        "college_programs",
        # EXPLICITLY NOT: sports, sports_events
    },
    ROLE_BUS_ADMIN: {
        "bus",
        "buses",
        "routes",
        "stops",
        "timings",
        "transport",
    },
    ROLE_LIBRARY_ADMIN: {
        "library",
        "books",
        "members",
        "issue_return",
        "library_info",
    },
    ROLE_CANTEEN_ADMIN: {
        "canteen",
        "menu",
        "food_items",
        "prices",
        "timings",
    },
    ROLE_SPORTS_ADMIN: {
        "sports",
        "sports_events",
        "grounds",
        # EXPLICITLY NOT: cultural_events, technical_events, general college events
    },
}


def normalize_role(role_name: Optional[str]) -> str:
    """Normalizes role name or returns 'guest' if unknown."""
    if not role_name:
        return ""
    clean = str(role_name).strip().lower().replace("-", "_").replace(" ", "_")
    return ROLE_ALIASES.get(clean, clean)


def get_role_permissions(role: str) -> Set[str]:
    """Returns the set of permissions associated with a given role."""
    norm = normalize_role(role)
    return ROLE_PERMISSIONS.get(norm, set())


def has_permission(user: Any, permission: str) -> bool:
    """
    Checks whether the user has the specified permission.
    Returns True if user is super_admin or has explicit permission.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if not getattr(user, 'is_active', True):
        return False

    role = normalize_role(getattr(user, 'role', ''))
    if role == ROLE_SUPER_ADMIN:
        return True

    perms = get_role_permissions(role)
    if "*" in perms:
        return True

    perm_norm = permission.strip().lower()
    return perm_norm in perms


def has_role(user: Any, *roles: str) -> bool:
    """
    Checks whether the user matches any of the given roles.
    Super admin automatically matches all role requirements.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if not getattr(user, 'is_active', True):
        return False

    user_role = normalize_role(getattr(user, 'role', ''))
    if user_role == ROLE_SUPER_ADMIN:
        return True

    normalized_target_roles = [normalize_role(r) for r in roles]
    return user_role in normalized_target_roles


# =========================================================================
# 3. AUTHORIZATION DECORATORS
# =========================================================================

def _is_api_request() -> bool:
    """Determines whether current request expects JSON response."""
    return (
        request.path.startswith('/api/') or
        request.is_json or
        request.headers.get('Accept') == 'application/json' or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )


def _unauthorized_response(message: str = "Authentication required.", status_code: int = 401):
    """Returns JSON 401 or redirects to login."""
    if _is_api_request():
        return jsonify({
            "status": "error",
            "error": "Unauthorized",
            "message": message
        }), status_code
    flash(message, "warning")
    try:
        if 'auth.login' in getattr(current_app, 'view_functions', {}):
            return redirect(url_for('auth.login', next=request.url))
    except Exception:
        pass
    return redirect('/login')


def _forbidden_response(message: str = "403 Forbidden: You do not have permission to access this resource."):
    """Returns JSON 403 or renders dedicated 403 access denied page."""
    if _is_api_request():
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": message,
            "required_role": "Insufficient permissions"
        }), 403
    flash(message, "error")
    try:
        return render_template(
            'errors/403.html',
            error_message=message,
            user=current_user
        ), 403
    except Exception:
        abort(403)


def admin_required(f):
    """Decorator requiring an active, authenticated Admin user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return _unauthorized_response("Please log in to access the Admin Panel.")

        if not getattr(current_user, 'is_admin', False):
            return _forbidden_response("Student accounts cannot access admin resources.")

        if not getattr(current_user, 'is_active', True):
            return _forbidden_response("Your admin account is disabled. Please contact Super Admin.")

        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator enforcing that the current admin belongs to one of `allowed_roles`.
    Super Admin always passes this check.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return _unauthorized_response("Please log in to continue.")

            if not getattr(current_user, 'is_admin', False):
                return _forbidden_response("Access restricted to administrators.")

            if not getattr(current_user, 'is_active', True):
                return _forbidden_response("Your admin account is disabled.")

            user_role = normalize_role(getattr(current_user, 'role', ''))
            if user_role == ROLE_SUPER_ADMIN:
                return f(*args, **kwargs)

            norm_allowed = [normalize_role(r) for r in allowed_roles]
            if user_role not in norm_allowed:
                role_names = ", ".join([ROLE_DISPLAY_NAMES.get(r, r) for r in norm_allowed])
                return _forbidden_response(f"Access Denied: Requires one of [{role_names}]. Your role is [{ROLE_DISPLAY_NAMES.get(user_role, user_role)}].")

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(*required_permissions):
    """
    Decorator enforcing that the current admin has at least one of `required_permissions`.
    Super Admin always passes this check.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return _unauthorized_response("Please log in to continue.")

            if not getattr(current_user, 'is_admin', False):
                return _forbidden_response("Access restricted to administrators.")

            if not getattr(current_user, 'is_active', True):
                return _forbidden_response("Your admin account is disabled.")

            user_role = normalize_role(getattr(current_user, 'role', ''))
            if user_role == ROLE_SUPER_ADMIN:
                return f(*args, **kwargs)

            user_perms = get_role_permissions(user_role)
            if "*" in user_perms:
                return f(*args, **kwargs)

            has_any = any(p.strip().lower() in user_perms for p in required_permissions)
            if not has_any:
                perms_str = ", ".join(required_permissions)
                return _forbidden_response(f"Access Denied: Requires permission [{perms_str}].")

            return f(*args, **kwargs)
        return decorated_function
    return decorator
