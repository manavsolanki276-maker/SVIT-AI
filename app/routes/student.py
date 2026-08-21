import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.chat_history import ChatConversation, ChatMessage
from app.ai.rag_pipeline import RAGPipeline

student_bp = Blueprint('student', __name__, url_prefix='/student')

# Initialize RAG Pipeline Instance
rag_pipeline = RAGPipeline()


# =========================================================
# 1. FIRST-TIME PROFILE ONBOARDING
# =========================================================
@student_bp.route('/complete-profile', methods=['GET', 'POST'])
@student_bp.route('/complete_profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    # If the student already completed their profile, send them to chat
    is_complete = getattr(current_user, 'is_profile_complete', getattr(current_user, 'is_profile_completed', True))
    if is_complete:
        return redirect(url_for('student.chat'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        department = request.form.get('department')
        semester = request.form.get('semester')
        batch = request.form.get('batch')
        phone = request.form.get('phone') or request.form.get('mobile_no')
        gender = request.form.get('gender')

        if full_name:
            if hasattr(current_user, 'full_name'):
                current_user.full_name = full_name
            elif hasattr(current_user, 'name'):
                current_user.name = full_name
                
        if department and hasattr(current_user, 'department'):
            current_user.department = department
            
        if semester and hasattr(current_user, 'semester'):
            try:
                current_user.semester = int(semester)
            except ValueError:
                current_user.semester = semester

        if batch and hasattr(current_user, 'batch'):
            current_user.batch = batch

        if phone:
            if hasattr(current_user, 'phone'):
                current_user.phone = phone
            elif hasattr(current_user, 'contact'):
                current_user.contact = phone

        if gender and hasattr(current_user, 'gender'):
            current_user.gender = gender

        # Mark onboarding as complete
        if hasattr(current_user, 'is_profile_complete'):
            current_user.is_profile_complete = True
        if hasattr(current_user, 'is_profile_completed'):
            current_user.is_profile_completed = True

        db.session.commit()
        flash('Profile setup completed successfully!', 'success')

        return redirect(url_for('student.chat'))

    return render_template('student/complete_profile.html', user=current_user)


# =========================================================
# 2. STUDENT PROFILE VIEW & EDIT
# =========================================================
@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """ Dedicated view/edit profile route """
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        department = request.form.get('department')
        semester = request.form.get('semester')
        phone = request.form.get('phone')
        gender = request.form.get('gender')

        if full_name:
            if hasattr(current_user, 'full_name'):
                current_user.full_name = full_name
            elif hasattr(current_user, 'name'):
                current_user.name = full_name

        if department and hasattr(current_user, 'department'):
            current_user.department = department

        if semester and hasattr(current_user, 'semester'):
            try:
                current_user.semester = int(semester)
            except ValueError:
                current_user.semester = semester

        if phone:
            if hasattr(current_user, 'phone'):
                current_user.phone = phone
            elif hasattr(current_user, 'contact'):
                current_user.contact = phone

        if gender and hasattr(current_user, 'gender'):
            current_user.gender = gender

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))

    # ✅ FIXED: Now correctly renders profile.html
    return render_template('student/profile.html', user=current_user)


# =========================================================
# 3. AI CHAT DASHBOARD
# =========================================================
@student_bp.route('/chat')
@login_required
def chat():
    """ Renders the main student chat dashboard UI """
    is_complete = getattr(current_user, 'is_profile_complete', getattr(current_user, 'is_profile_completed', True))
    if not is_complete:
        return redirect(url_for('student.complete_profile'))

    return render_template('student/chat.html')


# =========================================================
# 4. CHAT API ENDPOINT
# =========================================================
@student_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """ API endpoint receiving fetch requests from chat UI """
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    try:
        # 1. Fetch or create conversation session
        if conversation_id:
            conv = ChatConversation.query.filter_by(
                id=conversation_id, 
                student_id=current_user.id
            ).first()
        else:
            conv = None

        if not conv:
            title_snippet = user_message[:30] + "..." if len(user_message) > 30 else user_message
            conv = ChatConversation(
                id=str(uuid.uuid4()), 
                student_id=current_user.id, 
                title=title_snippet
            )
            db.session.add(conv)
            db.session.commit()

        # 2. Log user message
        user_msg_db = ChatMessage(
            conversation_id=conv.id, 
            sender='user', 
            content=user_message
        )
        db.session.add(user_msg_db)

        # 3. Extract user profile and call the RAG pipeline
        user_profile = {
            "full_name": getattr(current_user, 'full_name', getattr(current_user, 'name', 'Student')),
            "department": getattr(current_user, 'department', ''),
            "semester": getattr(current_user, 'semester', None),
            "division": getattr(current_user, 'division', ''),
            "batch": getattr(current_user, 'batch', ''),
            "enrollment_no": getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', ''))
        }
        session_id = f"user_{current_user.id}"
        result = rag_pipeline.answer_question(
            question=user_message,
            session_id=session_id,
            user_profile=user_profile
        )

        bot_answer = result.get('answer', '')
        map_image = result.get('image')
        sources = result.get('sources', [])

        # 4. Log assistant message & metadata
        bot_msg_db = ChatMessage(
            conversation_id=conv.id,
            sender='assistant',
            content=bot_answer,
            image_path=map_image,
            sources=json.dumps(sources)
        )
        db.session.add(bot_msg_db)
        db.session.commit()

        return jsonify({
            'conversation_id': conv.id,
            'answer': bot_answer,
            'image': map_image,
            'sources': sources
        }), 200

    except Exception as e:
        print(f"[Error] Error in RAG Pipeline route: {e}")
        return jsonify({'error': 'Failed to process response. Please try again.'}), 500