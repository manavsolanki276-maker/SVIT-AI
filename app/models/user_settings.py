"""
user_settings.py
SQLAlchemy model for Student Preferences and Chat Settings.
"""
from datetime import datetime
from app.extensions import db


class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Fixed Foreign Key reference to point to 'students.id'
    user_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, unique=True)
    
    # Preferences
    theme = db.Column(db.String(20), default='dark')
    notifications_enabled = db.Column(db.Boolean, default=True)
    email_alerts = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "theme": self.theme,
            "notifications_enabled": self.notifications_enabled,
            "email_alerts": self.email_alerts,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }