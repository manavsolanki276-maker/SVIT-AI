from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Student

student_bp = Blueprint('student', __name__, url_prefix='/student')

# 1. Complete Profile Route
@student_bp.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    # If student already completed profile, send straight to Chatbot
    if getattr(current_user, 'is_profile_complete', False):
        return redirect(url_for('student.chat'))

    if request.method == 'POST':
        # Safely assign fields
        if hasattr(current_user, 'full_name'):
            current_user.full_name = request.form.get('full_name')
        
        current_user.department = request.form.get('department')
        
        # Safely parse integer semester to avoid ValueError crashes
        sem_val = request.form.get('semester')
        if sem_val and sem_val.isdigit():
            current_user.semester = int(sem_val)
            
        current_user.batch = request.form.get('batch')
        
        # Mark profile complete
        current_user.is_profile_complete = True
        
        db.session.commit()
        flash('Profile completed successfully! Welcome to SVIT AI Assistant.', 'success')
        return redirect(url_for('student.chat'))

    return render_template('student/complete_profile.html')


# 2. Main AI Chatbot Route
@student_bp.route('/chat')
@login_required
def chat():
    # Gatekeeper: Force profile completion before allowing chat access
    if not getattr(current_user, 'is_profile_complete', False):
        return redirect(url_for('student.complete_profile'))

    return render_template('student/chat.html')