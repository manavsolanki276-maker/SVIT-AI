"""
chat_history.py
SQLAlchemy models for Chat Sessions, Messages, Saved/Bookmarked Conversations,
and User Thumbs Up/Down Response Feedback.
"""
import json
import uuid
from datetime import datetime
from app.extensions import db


class ChatConversation(db.Model):
    __tablename__ = 'chat_conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="New Conversation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = db.relationship('ChatMessage', backref='conversation', cascade='all, delete-orphan', lazy=True)
    saved_ref = db.relationship('SavedConversation', backref='conversation', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_saved": self.saved_ref is not None,
            "message_count": len(self.messages) if self.messages else 0
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('chat_conversations.id'), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    sources = db.Column(db.Text, nullable=True)  # JSON string array
    feedback = db.Column(db.String(10), nullable=True)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        parsed_sources = []
        if self.sources:
            try:
                parsed_sources = json.loads(self.sources)
            except (json.JSONDecodeError, TypeError):
                parsed_sources = [self.sources]

        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "content": self.content,
            "text": self.content,  # Compatibility alias
            "image_path": self.image_path,
            "sources": parsed_sources,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SavedConversation(db.Model):
    __tablename__ = 'saved_conversations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    conversation_id = db.Column(db.String(36), db.ForeignKey('chat_conversations.id'), nullable=False, index=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_id', 'conversation_id', name='_user_conv_uc'),)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "conversation_id": self.conversation_id,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None
        }


class ChatFeedback(db.Model):
    __tablename__ = 'chat_feedbacks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.Integer, nullable=True)
    conversation_id = db.Column(db.String(36), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    rating = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    query_text = db.Column(db.Text, nullable=True)
    response_text = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "student_id": self.student_id,
            "rating": self.rating,
            "query_text": self.query_text,
            "response_text": self.response_text,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }