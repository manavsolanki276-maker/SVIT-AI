# app/models/student.py
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Student(UserMixin, db.Model):
    __tablename__ = 'students'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    enrollment_no = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile Info (Completed during first login)
    full_name = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(50), nullable=True) 
    semester = db.Column(db.Integer, nullable=True)
    batch = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    
    # Flow Control Flag
    is_profile_complete = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    # Safely handle string prefixes (e.g., 'student_1' -> '1')
    if isinstance(user_id, str) and user_id.startswith('student_'):
        user_id = user_id.replace('student_', '')
        
    try:
        return Student.query.get(int(user_id))
    except (ValueError, TypeError):
        return None