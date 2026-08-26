"""
notification_routes.py
Dedicated Student Notification Center & API Endpoints for SVIT AI Assistant.
Provides both rich HTML views (/notifications, /student/notifications)
and authenticated REST APIs (/api/notifications, /api/notifications/<id>/read, etc.)
backed by MongoDB Atlas (svit_ai.notifications).
"""
import logging
from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.database.mongo_models import MongoNotificationService

logger = logging.getLogger(__name__)

notification_bp = Blueprint('notifications', __name__)


def get_real_user_id():
    """
    Extracts authenticated user's ID candidate.
    Backend session is the absolute source of truth.
    """
    if not current_user.is_authenticated:
        return None
    uid = getattr(current_user, 'id', None)
    if str(uid).startswith('student_'):
        return str(uid).split('_', 1)[1]
    return uid


# =========================================================================
# 1. DEDICATED STUDENT NOTIFICATION HTML VIEW
# =========================================================================
@notification_bp.route('/notifications', methods=['GET'])
@notification_bp.route('/notifications/', methods=['GET'])
@notification_bp.route('/student/notifications', methods=['GET'])
@login_required
def student_notifications_view():
    """
    Renders the dedicated Student Notification Center HTML page.
    If requested with application/json, returns JSON notifications for compatibility.
    """
    # Check if client explicitly expects JSON
    if request.is_json or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept', '') and 'text/html' not in request.headers.get('Accept', '')):
        return api_get_notifications()

    # Block non-active students from accessing notification center
    if not getattr(current_user, 'is_admin', False):
        status = getattr(current_user, 'status', 'active')
        if status == 'pending':
            return redirect(url_for('auth.pending_view'))
        elif status == 'rejected':
            return redirect(url_for('auth.rejected_view'))

    return render_template(
        'student/notifications.html',
        current_user=current_user,
        student=current_user
    )


# =========================================================================
# 2. AUTHENTICATED NOTIFICATION REST APIS
# =========================================================================
@notification_bp.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    """
    Returns only notifications belonging to the currently authenticated student
    or admin, along with the dynamic unread_count.
    Enforces strict isolation: never trusts frontend user IDs.
    """
    if getattr(current_user, 'is_admin', False):
        res = MongoNotificationService.get_admin_notifications(limit=50)
        return jsonify(res)

    # 1. Fetch from MongoDB Atlas
    res = MongoNotificationService.get_notifications(current_user, limit=50)
    if res and res.get("status") == "success" and "notifications" in res:
        # If MongoDB returned records or empty list successfully
        if len(res.get("notifications", [])) > 0 or not getattr(db, 'engine', None):
            return jsonify(res)

    # 2. SQLite Fallback if MongoDB is empty / offline
    try:
        from app.models.notification import Notification
        uid = get_real_user_id()
        int_id = int(uid) if str(uid).isdigit() else 1
        notifications = Notification.query.filter_by(user_id=int_id)\
            .order_by(Notification.created_at.desc()).limit(50).all()
        unread_count = Notification.query.filter_by(user_id=int_id, is_read=False).count()

        return jsonify({
            "status": "success",
            "unread_count": unread_count,
            "notifications": [n.to_dict() for n in notifications]
        })
    except Exception as sqle:
        logger.warning(f"SQLite notification fallback note: {sqle}")
        return jsonify(res or {"status": "success", "unread_count": 0, "notifications": []})


@notification_bp.route('/api/notifications/<string:notification_id>/read', methods=['POST', 'PATCH'])
@notification_bp.route('/notifications/<string:notification_id>/read', methods=['POST', 'PATCH'])
@login_required
def api_mark_read(notification_id):
    """
    Marks a single notification as read for the authenticated student.
    Prevents marking another student's private notification as read.
    """
    # 1. Update in MongoDB
    user_context = "admin" if getattr(current_user, 'is_admin', False) else current_user
    ok = MongoNotificationService.mark_read(notification_id, user_context)

    # 2. SQLite Fallback
    try:
        from app.models.notification import Notification
        if str(notification_id).isdigit():
            uid = get_real_user_id()
            int_id = int(uid) if str(uid).isdigit() else None
            q = Notification.query.filter_by(id=int(notification_id))
            if int_id and not getattr(current_user, 'is_admin', False):
                q = q.filter_by(user_id=int_id)
            notif = q.first()
            if notif:
                notif.is_read = True
                db.session.commit()
                ok = True
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Notification marked as read"})


@notification_bp.route('/api/notifications/read-all', methods=['POST'])
@notification_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_read():
    """
    Marks all notifications for the authenticated student as read.
    """
    # 1. Update in MongoDB
    user_context = "admin" if getattr(current_user, 'is_admin', False) else current_user
    MongoNotificationService.mark_all_read(user_context)

    # 2. SQLite Fallback
    try:
        from app.models.notification import Notification
        uid = get_real_user_id()
        int_id = int(uid) if str(uid).isdigit() else 1
        Notification.query.filter_by(user_id=int_id, is_read=False).update({"is_read": True})
        db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "All notifications marked as read"})


@notification_bp.route('/api/notifications/<string:notification_id>', methods=['DELETE'])
@notification_bp.route('/notifications/<string:notification_id>', methods=['DELETE'])
@login_required
def api_delete_notification(notification_id):
    """
    Deletes or dismisses a notification for the authenticated student.
    """
    # 1. Delete in MongoDB
    user_context = "admin" if getattr(current_user, 'is_admin', False) else current_user
    MongoNotificationService.delete_notification(notification_id, user_context)

    # 2. SQLite Fallback
    try:
        from app.models.notification import Notification
        if str(notification_id).isdigit():
            uid = get_real_user_id()
            int_id = int(uid) if str(uid).isdigit() else None
            q = Notification.query.filter_by(id=int(notification_id))
            if int_id and not getattr(current_user, 'is_admin', False):
                q = q.filter_by(user_id=int_id)
            notif = q.first()
            if notif:
                db.session.delete(notif)
                db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Notification deleted"})