"""
settings_routes.py
User Preferences and Settings Management Blueprint with MongoDB & SQLite support.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.database.mongo_models import MongoUserSettingsService

settings_bp = Blueprint('settings', __name__, url_prefix='/student/settings')


def get_real_user_id():
    uid = getattr(current_user, 'id', 1)
    if str(uid).startswith('student_'):
        return str(uid).split('_', 1)[1]
    return uid


@settings_bp.route('/', methods=['GET'])
@login_required
def settings_page():
    uid = get_real_user_id()
    # 1. MongoDB check
    settings_dict = MongoUserSettingsService.get_settings(uid)

    # 2. SQLite sync/fallback
    try:
        from app.models.user_settings import UserSettings
        user_setting = UserSettings.query.filter_by(user_id=int(uid) if str(uid).isdigit() else 1).first()
        if user_setting:
            settings_dict.update(user_setting.to_dict())
    except Exception:
        pass

    return render_template('student/settings.html', settings=settings_dict)


@settings_bp.route('/save', methods=['POST'])
@login_required
def save_settings():
    data = request.get_json() or {}
    uid = get_real_user_id()

    # 1. Save to MongoDB
    saved = MongoUserSettingsService.save_settings(uid, data)

    # 2. Save to SQLite if available
    try:
        from app.models.user_settings import UserSettings
        int_id = int(uid) if str(uid).isdigit() else 1
        user_setting = UserSettings.query.filter_by(user_id=int_id).first()
        if not user_setting:
            user_setting = UserSettings(user_id=int_id)
            db.session.add(user_setting)

        if 'theme' in data: user_setting.theme = data['theme']
        if 'language' in data: user_setting.language = data.get('language')
        if 'font_size' in data: user_setting.font_size = data.get('font_size')
        if 'voice_output' in data: user_setting.voice_output = bool(data['voice_output'])
        if 'auto_read_response' in data: user_setting.auto_read_response = bool(data['auto_read_response'])

        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    return jsonify({"status": "success", "message": "Settings saved.", "settings": saved})