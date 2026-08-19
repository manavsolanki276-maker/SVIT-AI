"""
notification.py
SQLAlchemy model for Student Alerts and System Notifications.
"""
from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Fixed Foreign Key reference to point to 'students.id'
    user_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')  # e.g., 'event', 'placement', 'academic'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }