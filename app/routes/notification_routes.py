"""
notification_routes.py
Campus Notification Center API Endpoints with MongoDB & SQLite support.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.database.mongo_models import MongoNotificationService

notification_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


def get_real_user_id():
    uid = getattr(current_user, 'id', 1)
    if str(uid).startswith('student_'):
        return str(uid).split('_', 1)[1]
    return uid


@notification_bp.route('/', methods=['GET'])
@login_required
def get_notifications():
    uid = get_real_user_id()

    # 1. MongoDB check
    res = MongoNotificationService.get_notifications(uid, limit=30)
    if res.get("notifications"):
        return jsonify(res)

    # 2. SQLite fallback
    try:
        from app.models.notification import Notification
        int_id = int(uid) if str(uid).isdigit() else 1
        notifications = Notification.query.filter_by(user_id=int_id)\
            .order_by(Notification.created_at.desc()).limit(30).all()
        unread_count = Notification.query.filter_by(user_id=int_id, is_read=False).count()

        return jsonify({
            "status": "success",
            "unread_count": unread_count,
            "notifications": [n.to_dict() for n in notifications]
        })
    except Exception:
        return jsonify({"status": "success", "unread_count": 0, "notifications": []})


@notification_bp.route('/<string:notification_id>/read', methods=['PATCH'])
@login_required
def mark_read(notification_id):
    uid = get_real_user_id()
    MongoNotificationService.mark_read(notification_id, uid)

    try:
        from app.models.notification import Notification
        if notification_id.isdigit():
            notif = Notification.query.filter_by(id=int(notification_id)).first()
            if notif:
                notif.is_read = True
                db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success"})


@notification_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    uid = get_real_user_id()
    MongoNotificationService.mark_all_read(uid)

    try:
        from app.models.notification import Notification
        int_id = int(uid) if str(uid).isdigit() else 1
        Notification.query.filter_by(user_id=int_id, is_read=False).update({"is_read": True})
        db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success"})


@notification_bp.route('/<string:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    uid = get_real_user_id()
    MongoNotificationService.delete_notification(notification_id, uid)

    try:
        from app.models.notification import Notification
        if notification_id.isdigit():
            notif = Notification.query.filter_by(id=int(notification_id)).first()
            if notif:
                db.session.delete(notif)
                db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success"})