"""
app/routes/chat.py
API endpoints for student chat queries with Student Profile Personalization,
Server-Sent Events (SSE) streaming, and high-speed in-memory cached responses.
"""
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from flask_login import current_user

from app.extensions import db
from app.models.chat_history import ChatConversation, ChatMessage

chat_bp = Blueprint('chat', __name__)

# ---------------------------------------------------------
# Global RAG Instance Placeholder (Lazy-loaded on demand)
# ---------------------------------------------------------
rag_instance = None


def get_real_student_id():
    """Extracts integer ID if current_user.id is formatted like 'student_1'."""
    user_id_str = str(getattr(current_user, 'id', 1))
    if user_id_str.startswith('student_'):
        return int(user_id_str.split('_')[1])
    try:
        return int(user_id_str)
    except ValueError:
        return 1


def get_current_student_profile():
    """Extracts a structured profile dictionary for the active student."""
    if not current_user or not getattr(current_user, 'is_authenticated', False):
        return None

    target = current_user
    real_id = get_real_student_id()

    # Query fresh student DB record if available
    try:
        from app.database.models import Student
        db_student = Student.query.get(real_id)
        if db_student:
            target = db_student
    except Exception:
        pass

    if target == current_user:
        try:
            from app.models.student import Student
            db_student = Student.query.get(real_id)
            if db_student:
                target = db_student
        except Exception:
            pass

    program = getattr(target, 'program', '') or 'BE'
    full_name = getattr(target, 'full_name', getattr(target, 'name', 'Student')) or 'Student'
    department = getattr(target, 'department', '') or 'Computer Engineering'
    semester = getattr(target, 'semester', None) or 3
    division = getattr(target, 'division', '') or ''
    batch = getattr(target, 'batch', '') or ''
    enrollment = getattr(target, 'enrollment_no', getattr(target, 'enrollment_number', ''))

    if not division:
        # Check if batch contains a division letter (e.g. 'A', 'B', 'A1')
        m = re.search(r'\b([A-C])\b|^([A-C])\d*', str(batch), re.IGNORECASE)
        if m:
            division = (m.group(1) or m.group(2)).upper()
        else:
            division = 'A'

    return {
        "full_name": full_name,
        "program": program,
        "department": department,
        "semester": semester,
        "division": division.strip().upper(),
        "batch": batch,
        "enrollment_no": enrollment
    }


def generate_campus_response(query_text, session_id="default_user", user_profile=None):
    """
    Response builder for campus queries with student profile personalization.
    """
    global rag_instance

    if rag_instance is None:
        try:
            from app.ai.rag_pipeline import get_rag_pipeline
            rag_instance = get_rag_pipeline()
        except Exception as e:
            print(f"[Error] Failed to load RAG Pipeline instance: {e}")

    if rag_instance is not None:
        try:
            response_data = rag_instance.answer_question(
                query_text, 
                session_id=session_id,
                user_profile=user_profile
            )

            if response_data and isinstance(response_data, dict):
                answer = response_data.get('answer') or response_data.get('response') or ""
                sources = response_data.get('sources') or []
                image = response_data.get('image') or None
                suggestions = response_data.get('suggestions') or []

                # Clean and validate map image existence on disk
                if image:
                    clean_img = str(image).replace('/static/', '').lstrip('/')
                    full_img_path = os.path.join(current_app.static_folder, clean_img)
                    if not os.path.exists(full_img_path):
                        image = None

                if answer and isinstance(answer, str) and answer.strip():
                    return answer, image, sources, suggestions

        except Exception as e:
            print(f"[Error] RAG Execution Error: {type(e).__name__} - {str(e)}")

    # Fallback response
    text_lower = query_text.lower()
    if any(k in text_lower for k in ['timetable', 'time tabel', 'schedule', 'lecture', 'sem 3', 'sem 1', 'sem 5']):
        dept_title = user_profile.get("department", "Diploma Computer Engineering") if user_profile else "Diploma Computer Engineering"
        sem_title = user_profile.get("semester", "3") if user_profile else "3"
        div_title = user_profile.get("division", "A") if user_profile else "A"
        return (
            f"### 📅 {dept_title} (Sem {sem_title} - Div {div_title}) Timetable\n\n"
            "| Time | Subject | Room / Lab | Faculty |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **09:15 AM - 11:15 AM** | Data Structures Lab | Lab 302 | Prof. Patel |\n"
            "| **11:15 AM - 12:15 PM** | Database Management | Class Room 204 | Prof. Shah |\n"
            "| **01:00 PM - 03:00 PM** | Digital Electronics | Hardware Lab | Prof. Mehta |\n\n"
            "*Note: Please check your department notice board for elective lab batch splits.*",
            None,
            ["timetable.csv"],
            ["Where is my next class right now? 📍", "Show tomorrow's timetable 📅"]
        )
    elif any(k in text_lower for k in ['canteen', 'food', 'mess', 'cafeteria']):
        img_path = "navigation_maps/canteen.png"
        full_img_path = os.path.join(current_app.static_folder, img_path)
        return (
            "### 🍔 Campus Canteen Details\n\n"
            "The Main College Canteen is located behind the **Ground Floor Student Activity Center** near the sports ground.\n\n"
            "* **Operating Hours**: 8:30 AM to 6:00 PM (Monday to Saturday)\n"
            "* **Available Items**: Fresh snacks, full lunch thali meals, cold beverages, and hot tea/coffee.",
            img_path if os.path.exists(full_img_path) else None,
            ["canteen_menu.pdf"],
            ["Where is the sports ground? 📍", "Show bus schedule 🚌"]
        )
    else:
        return (
            f"Thank you for asking about **\"{query_text}\"**!\n\n"
            "For specific syllabus details, faculty office hours, or official notices, "
            "please consult the student academic portal or your department coordinator.",
            None,
            ["svit_handbook.pdf"],
            ["Show today's timetable 📅", "Where is Diploma Room 202? 📍"]
        )


# =========================================================
# 1. STREAMING SSE CHAT ENDPOINT WITH PERSONALIZATION
# =========================================================
@chat_bp.route('/api/chat/stream', methods=['POST'])
def handle_chat_stream():
    """
    Server-Sent Events (SSE) streaming endpoint with student profile personalization.
    """
    data = request.get_json() or {}
    user_text = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_text:
        return jsonify({"status": "error", "message": "Message cannot be empty."}), 400

    student_id = get_real_student_id()
    user_profile = get_current_student_profile()

    # Pre-resolve or create conversation session
    try:
        conversation = None
        if conversation_id:
            conversation = ChatConversation.query.filter_by(id=conversation_id, student_id=student_id).first()

        if not conversation:
            title_summary = user_text[:35].strip() + ("..." if len(user_text) > 35 else "")
            conversation = ChatConversation(student_id=student_id, title=title_summary)
            db.session.add(conversation)
            db.session.flush()

        conv_id = conversation.id

        # Save user message to database
        user_msg = ChatMessage(
            conversation_id=conv_id,
            sender='user',
            content=user_text
        )
        db.session.add(user_msg)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"[Error] Failed to initialize conversation for streaming: {e}")
        conv_id = conversation_id or "temp_conv"

    app_instance = current_app._get_current_object()

    def event_stream():
        session_key = f"student_{student_id}_conv_{conv_id}"
        from app.ai.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()

        full_answer = ""
        final_image = None
        final_sources = []
        final_suggestions = []

        try:
            for packet in rag.stream_answer_question(
                user_text, 
                session_id=session_key,
                user_profile=user_profile
            ):
                if not packet.get("done", False):
                    chunk_str = packet.get("chunk", "")
                    full_answer += chunk_str
                    yield f"data: {json.dumps({'chunk': chunk_str, 'conversation_id': conv_id})}\n\n"
                else:
                    final_image = packet.get("image")
                    final_sources = packet.get("sources", [])
                    final_suggestions = packet.get("suggestions", [])
                    if packet.get("answer"):
                        full_answer = packet.get("answer")

            # Validate map image path
            if final_image:
                clean_img = str(final_image).replace('/static/', '').lstrip('/')
                full_img_path = os.path.join(app_instance.static_folder, clean_img)
                if not os.path.exists(full_img_path):
                    final_image = None

            # Persist assistant response in DB
            with app_instance.app_context():
                bot_msg = ChatMessage(
                    conversation_id=conv_id,
                    sender='assistant',
                    content=full_answer,
                    image_path=final_image,
                    sources=json.dumps(final_sources)
                )
                db.session.add(bot_msg)
                conv_record = ChatConversation.query.get(conv_id)
                if conv_record:
                    conv_record.updated_at = datetime.now()
                db.session.commit()
                saved_msg_id = bot_msg.id

            yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id, 'message_id': saved_msg_id, 'answer': full_answer, 'image': final_image, 'sources': final_sources, 'suggestions': final_suggestions})}\n\n"

        except Exception as err:
            print(f"[Error] Streaming error: {err}")
            yield f"data: {json.dumps({'done': True, 'error': str(err)})}\n\n"

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


# =========================================================
# 2. STANDARD FAST JSON ENDPOINT WITH PERSONALIZATION
# =========================================================
@chat_bp.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.get_json() or {}
    user_text = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_text:
        return jsonify({"status": "error", "message": "Message cannot be empty."}), 400

    student_id = get_real_student_id()
    user_profile = get_current_student_profile()

    try:
        conversation = None
        if conversation_id:
            conversation = ChatConversation.query.filter_by(id=conversation_id, student_id=student_id).first()

        if not conversation:
            title_summary = user_text[:35].strip() + ("..." if len(user_text) > 35 else "")
            conversation = ChatConversation(student_id=student_id, title=title_summary)
            db.session.add(conversation)
            db.session.flush()

        # Save User Message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            sender='user',
            content=user_text
        )
        db.session.add(user_msg)

        # Generate AI Answer with user profile
        session_key = f"student_{student_id}_conv_{conversation.id}"
        ai_response_text, image_path, sources_list, suggestions_list = generate_campus_response(
            user_text, 
            session_id=session_key,
            user_profile=user_profile
        )

        # Save Assistant Message
        bot_msg = ChatMessage(
            conversation_id=conversation.id,
            sender='assistant',
            content=ai_response_text,
            image_path=image_path,
            sources=json.dumps(sources_list)
        )
        db.session.add(bot_msg)
        conversation.updated_at = datetime.now()
        db.session.commit()

        return jsonify({
            "status": "success",
            "conversation_id": conversation.id,
            "message_id": bot_msg.id,
            "answer": ai_response_text,
            "response": ai_response_text,
            "image": image_path,
            "sources": sources_list,
            "suggestions": suggestions_list
        })

    except Exception as e:
        db.session.rollback()
        print(f"[Error] Error in /api/chat: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error saving chat."}), 500


# =========================================================
# 3. USER RESPONSE FEEDBACK ENDPOINT (Thumbs Up / Down)
# =========================================================
@chat_bp.route('/api/chat/feedback', methods=['POST'])
@chat_bp.route('/chat/feedback', methods=['POST'])
@chat_bp.route('/student/api/chat/feedback', methods=['POST'])
def handle_feedback():
    """
    Records student Thumbs Up / Thumbs Down feedback ratings and persists to both
    ChatMessage and ChatFeedback models.
    """
    data = request.get_json(silent=True) or request.form or {}
    raw_rating = str(data.get('rating', '')).strip().lower()
    conversation_id = str(data.get('conversation_id') or '').strip() or None
    message_id = data.get('message_id')
    query_text = str(data.get('query_text') or '').strip()
    response_text = str(data.get('response_text') or '').strip()
    comment = str(data.get('comment') or '').strip()

    if raw_rating not in ['like', 'dislike', 'up', 'down', 'thumbs_up', 'thumbs_down', 'helpful', 'unhelpful']:
        return jsonify({"status": "error", "message": "Rating must be 'like' or 'dislike'."}), 400

    normalized_rating = 'like' if raw_rating in ['like', 'up', 'thumbs_up', 'helpful'] else 'dislike'

    student_id = None
    try:
        if current_user and getattr(current_user, 'is_authenticated', False):
            student_id = get_real_student_id()
    except Exception:
        student_id = None

    try:
        from app.models.chat_history import ChatFeedback, ChatMessage
        
        # 1. Update ChatMessage feedback column if message_id or conversation_id provided
        target_msg = None
        if message_id:
            try:
                target_msg = ChatMessage.query.get(int(message_id))
            except (ValueError, TypeError):
                pass
        
        if not target_msg and conversation_id and response_text:
            target_msg = ChatMessage.query.filter_by(
                conversation_id=conversation_id, 
                sender='assistant'
            ).order_by(ChatMessage.id.desc()).first()

        if target_msg:
            target_msg.feedback = normalized_rating
            message_id = target_msg.id

        # 2. Record in ChatFeedback audit table
        feedback = ChatFeedback(
            message_id=message_id,
            conversation_id=conversation_id,
            student_id=student_id,
            rating=normalized_rating,
            query_text=query_text,
            response_text=response_text,
            comment=comment
        )
        db.session.add(feedback)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"Feedback recorded successfully ({normalized_rating}).",
            "feedback_id": feedback.id,
            "message_id": message_id,
            "rating": normalized_rating
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[Error] Error saving feedback: {e}")
        return jsonify({"status": "error", "message": f"Failed to record feedback: {str(e)}"}), 500


# =========================================================
# 4. HUGGING FACE WHISPER SPEECH-TO-TEXT ENDPOINT
# =========================================================
@chat_bp.route('/api/speech-to-text', methods=['POST'])
@chat_bp.route('/student/api/speech-to-text', methods=['POST'])
def handle_speech_to_text():
    """
    Receives recorded microphone audio (WAV / WebM) and transcribes it to text
    using the lightweight Hugging Face Whisper model (openai/whisper-tiny).
    """
    audio_bytes = None
    filename = "recording.wav"

    if 'audio' in request.files:
        uploaded_file = request.files['audio']
        filename = uploaded_file.filename or "recording.wav"
        audio_bytes = uploaded_file.read()
    elif request.data:
        audio_bytes = request.data
    else:
        return jsonify({"status": "error", "message": "No audio payload received."}), 400

    if not audio_bytes:
        return jsonify({"status": "error", "message": "Empty audio data."}), 400

    try:
        from app.ai.speech_engine import transcribe_audio_bytes
        transcript = transcribe_audio_bytes(audio_bytes, filename=filename)
        return jsonify({
            "status": "success",
            "text": transcript
        }), 200

    except Exception as e:
        print(f"[Error] Speech transcription error: {e}")
        return jsonify({"status": "error", "message": f"Transcription error: {str(e)}"}), 500