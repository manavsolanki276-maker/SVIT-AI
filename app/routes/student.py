import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.chat_history import ChatConversation, ChatMessage

student_bp = Blueprint('student', __name__, url_prefix='/student')


# =========================================================
# 1. FIRST-TIME PROFILE ONBOARDING & VIEW REDIRECTS
# =========================================================
@student_bp.route('/complete-profile', methods=['GET', 'POST'])
@student_bp.route('/complete_profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    return redirect('/student/profile/complete')


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return redirect('/student/profile/')


# =========================================================
# 2. AI CHAT DASHBOARD
# =========================================================
@student_bp.route('/chat')
@login_required
def chat():
    """ Renders the main student chat dashboard UI """
    is_complete = getattr(current_user, 'is_profile_complete', getattr(current_user, 'is_profile_completed', True))
    if not is_complete:
        return redirect('/student/profile/complete')

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

        # 3. Extract fresh user profile and call the RAG pipeline
        from app.routes.chat import get_current_student_profile
        user_profile = get_current_student_profile() or {
            "full_name": getattr(current_user, 'full_name', getattr(current_user, 'name', 'Student')),
            "program": getattr(current_user, 'program', 'BE'),
            "department": getattr(current_user, 'department', 'Computer Engineering'),
            "semester": getattr(current_user, 'semester', 3),
            "division": getattr(current_user, 'division', 'A'),
            "batch": getattr(current_user, 'batch', 'A1'),
            "enrollment_no": getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', ''))
        }
        session_id = f"user_{current_user.id}"
        from app.ai.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()
        result = rag.answer_question(
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