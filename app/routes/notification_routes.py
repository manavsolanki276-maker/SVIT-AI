"""
notification_routes.py
Campus Notification Center API Endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification

notification_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notification_bp.route('/', methods=['GET'])
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(30).all()

    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return jsonify({
        "status": "success",
        "unread_count": unread_count,
        "notifications": [n.to_dict() for n in notifications]
    })


@notification_bp.route('/<int:notification_id>/read', methods=['PATCH'])
@login_required
def mark_read(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"status": "success"})


@notification_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"status": "success"})


@notification_bp.route('/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    return jsonify({"status": "success"})