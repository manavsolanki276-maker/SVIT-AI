"""
settings_routes.py
User Preferences and Settings Management Blueprint.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user_settings import UserSettings

settings_bp = Blueprint('settings', __name__, url_prefix='/student/settings')

@settings_bp.route('/', methods=['GET'])
@login_required
def settings_page():
    user_setting = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_setting:
        user_setting = UserSettings(user_id=current_user.id)
        db.session.add(user_setting)
        db.session.commit()

    return render_template('student/settings.html', settings=user_setting.to_dict())


@settings_bp.route('/save', methods=['POST'])
@login_required
def save_settings():
    data = request.get_json() or {}
    user_setting = UserSettings.query.filter_by(user_id=current_user.id).first()

    if not user_setting:
        user_setting = UserSettings(user_id=current_user.id)
        db.session.add(user_setting)

    if 'theme' in data: user_setting.theme = data['theme']
    if 'language' in data: user_setting.language = data['language']
    if 'font_size' in data: user_setting.font_size = data['font_size']
    if 'voice_output' in data: user_setting.voice_output = bool(data['voice_output'])
    if 'auto_read_response' in data: user_setting.auto_read_response = bool(data['auto_read_response'])

    db.session.commit()
    return jsonify({"status": "success", "message": "Settings saved.", "settings": user_setting.to_dict()})