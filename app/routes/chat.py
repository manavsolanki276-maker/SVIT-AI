"""
app/routes/chat.py
API endpoints for handling student chat queries, AI answer generation via RAGPipeline, 
and persisting conversation history into SQLite/SQLAlchemy.
"""
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from app.extensions import db
from app.models.chat_history import ChatConversation, ChatMessage

chat_bp = Blueprint('chat', __name__)

# ---------------------------------------------------------
# Global RAG Instance Initialization (Runs ONCE at App Startup)
# ---------------------------------------------------------
rag_instance = None
try:
    from app.ai.rag_pipeline import get_rag_pipeline
    rag_instance = get_rag_pipeline()
    print("✅ RAG Pipeline initialized successfully in chat.py")
except Exception as err:
    print(f"⚠️ Could not pre-initialize RAG Pipeline in chat.py: {err}")


def get_real_student_id():
    """Extracts integer ID if current_user.id is formatted like 'student_1'."""
    user_id_str = str(getattr(current_user, 'id', 1))
    if user_id_str.startswith('student_'):
        return int(user_id_str.split('_')[1])
    try:
        return int(user_id_str)
    except ValueError:
        return 1


def generate_campus_response(query_text, session_id="default_user"):
    """
    Response builder for campus queries.
    Routes queries directly through RAGPipeline and validates image existence.
    """
    global rag_instance

    # 1. Attempt Live RAG Pipeline Execution
    if rag_instance is None:
        try:
            from app.ai.rag_pipeline import get_rag_pipeline
            rag_instance = get_rag_pipeline()
        except Exception as e:
            print(f"❌ Failed to load RAG Pipeline instance: {e}")

    if rag_instance is not None:
        try:
            print(f"🚀 Querying RAG Pipeline [{session_id}] with: '{query_text}'")
            
            response_data = rag_instance.answer_question(query_text, session_id=session_id)
            print(f"🔍 RAG Response Data: {response_data}")

            if response_data and isinstance(response_data, dict):
                answer = response_data.get('answer') or response_data.get('response') or ""
                sources = response_data.get('sources') or []
                image = response_data.get('image') or None

                # Clean and validate map image existence on disk
                if image:
                    clean_img = str(image).replace('/static/', '').lstrip('/')
                    full_img_path = os.path.join(current_app.static_folder, clean_img)
                    if not os.path.exists(full_img_path):
                        print(f"⚠️ Map image path '{clean_img}' not found on disk. Hiding image element.")
                        image = None

                if answer and isinstance(answer, str) and answer.strip():
                    return answer, image, sources

        except Exception as e:
            print(f"❌ RAG Execution Error: {type(e).__name__} - {str(e)}")

    # 2. Safety Rule-Based Fallback Matching (Active ONLY if RAG fails completely)
    print("⚠️ Falling back to rule-based fallback response.")
    text_lower = query_text.lower()

    # Timetable / Schedule
    if any(k in text_lower for k in ['timetable', 'time tabel', 'schedule', 'lecture', 'sem 3', 'sem 1', 'sem 5']):
        return (
            "### 📅 Diploma Computer Engineering (Sem 3 - Div A) Timetable\n\n"
            "| Time | Subject | Room / Lab | Faculty |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **09:15 AM - 11:15 AM** | Data Structures Lab | Lab 302 | Prof. Patel |\n"
            "| **11:15 AM - 12:15 PM** | Database Management | Class Room 204 | Prof. Shah |\n"
            "| **01:00 PM - 03:00 PM** | Digital Electronics | Hardware Lab | Prof. Mehta |\n\n"
            "*Note: Please check your department notice board for elective lab batch splits.*",
            None,
            ["timetable.csv"]
        )

    # Canteen / Food
    elif any(k in text_lower for k in ['canteen', 'food', 'mess', 'cafeteria']):
        img_path = "navigation_maps/canteen.png"
        full_img_path = os.path.join(current_app.static_folder, img_path)
        return (
            "### 🍔 Campus Canteen Details\n\n"
            "The Main College Canteen is located behind the **Ground Floor Student Activity Center** near the sports ground.\n\n"
            "* **Operating Hours**: 8:30 AM to 6:00 PM (Monday to Saturday)\n"
            "* **Available Items**: Fresh snacks, full lunch thali meals, cold beverages, and hot tea/coffee.",
            img_path if os.path.exists(full_img_path) else None,
            ["canteen_menu.pdf"]
        )

    # Default Fallback Answer
    else:
        return (
            f"Thank you for asking about **\"{query_text}\"**!\n\n"
            "For specific syllabus details, faculty office hours, or official notices, "
            "please consult the student academic portal or your department coordinator.",
            None,
            ["svit_handbook.pdf"]
        )


@chat_bp.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.get_json() or {}
    user_text = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_text:
        return jsonify({"status": "error", "message": "Message cannot be empty."}), 400

    student_id = get_real_student_id()

    try:
        # 1. Fetch existing conversation or create a new one
        conversation = None
        if conversation_id:
            conversation = ChatConversation.query.filter_by(id=conversation_id, student_id=student_id).first()

        if not conversation:
            title_summary = user_text[:35].strip() + ("..." if len(user_text) > 35 else "")
            conversation = ChatConversation(student_id=student_id, title=title_summary)
            db.session.add(conversation)
            db.session.flush()

        # 2. Save User Message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            sender='user',
            content=user_text
        )
        db.session.add(user_msg)

        # 3. Generate AI Answer with session key
        session_key = f"student_{student_id}_conv_{conversation.id}"
        ai_response_text, image_path, sources_list = generate_campus_response(user_text, session_id=session_key)

        # 4. Save AI Assistant Response
        bot_msg = ChatMessage(
            conversation_id=conversation.id,
            sender='assistant',
            content=ai_response_text,
            image_path=image_path,
            sources=json.dumps(sources_list)
        )
        db.session.add(bot_msg)

        # Update conversation timestamp so it appears under "TODAY" in Chat History
        conversation.updated_at = datetime.now()

        db.session.commit()

        return jsonify({
            "status": "success",
            "conversation_id": conversation.id,
            "answer": ai_response_text,
            "response": ai_response_text,
            "image": image_path,
            "sources": sources_list
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error in /api/chat: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error saving chat."}), 500