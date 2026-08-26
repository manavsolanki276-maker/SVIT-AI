# app/models/student.py
from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Student(UserMixin, db.Model):
    __tablename__ = 'students'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    enrollment_no = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile Info (Completed during first login)
    full_name = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True) 
    semester = db.Column(db.Integer, nullable=True)
    division = db.Column(db.String(10), nullable=True)
    batch = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    
    # Flow Control Flag
    is_profile_complete = db.Column(db.Boolean, default=False)

    # Approval Workflow Fields
    status = db.Column(db.String(20), default='active', nullable=True)
    request_id = db.Column(db.String(100), nullable=True)
    approved_by = db.Column(db.String(100), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.String(100), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"student_{self.id}"

    @property
    def is_admin(self):
        return False