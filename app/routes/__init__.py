from app.routes.admin import admin_bp
from app.routes.student import student_bp
from app.routes.auth import auth_bp
from app.routes.chat import chat_bp  # <-- Add chat blueprint import


def register_blueprints(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)   # <-- Register chat blueprint