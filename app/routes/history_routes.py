"""
history_routes.py
Routes for Chat History HTML Page & APIs with MongoDB Atlas & SQLite Support.
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.database.mongo_models import MongoChatService

history_bp = Blueprint('history', __name__, url_prefix='/chat')


def get_real_student_id():
    """Helper to extract student ID if current_user is authenticated or fallback for dev."""
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user_id_str = str(current_user.id)
        if user_id_str.startswith('student_'):
            return user_id_str.split('_', 1)[1]
        return user_id_str
    return "1"


# =========================================================
# 1. RENDER CHAT HISTORY PAGE
# =========================================================
@history_bp.route('/history-page', methods=['GET'])
def history_page():
    """Renders the dedicated Chat History & Saved Conversations UI."""
    return render_template('student/history.html')


# =========================================================
# 2. STATIC API ENDPOINTS (Must precede dynamic /<id> routes)
# =========================================================
@history_bp.route('/history', methods=['GET'])
def get_chat_history():
    """Retrieves and groups user chat conversations chronologically with pinned chats first."""
    student_id = get_real_student_id()
    search_q = request.args.get('search', '').strip().lower()

    # 1. MongoDB check
    grouped = MongoChatService.get_conversations(student_id, search_q)
    total_found = sum(len(v) for v in grouped.values())
    if total_found > 0:
        return jsonify({"status": "success", "history": grouped})

    # Also check integer student_id for MongoDB if string didn't find anything
    if student_id.isdigit():
        grouped = MongoChatService.get_conversations(int(student_id), search_q)
        if sum(len(v) for v in grouped.values()) > 0:
            return jsonify({"status": "success", "history": grouped})

    # 2. SQLite fallback
    try:
        from app.models.chat_history import ChatConversation, SavedConversation
        int_id = int(student_id) if str(student_id).isdigit() else 1
        query = ChatConversation.query.filter_by(student_id=int_id)
        if search_q:
            query = query.filter(ChatConversation.title.ilike(f"%{search_q}%"))

        conversations = query.order_by(
            ChatConversation.is_pinned.desc(), 
            ChatConversation.updated_at.desc()
        ).all()

        saved_ids = set(
            sc.conversation_id for sc in SavedConversation.query.filter_by(student_id=int_id).all()
        )

        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        grouped = {"today": [], "yesterday": [], "last_7_days": [], "last_month": [], "older": []}

        for c in conversations:
            data = c.to_dict() if hasattr(c, 'to_dict') else {
                "id": c.id, 
                "title": c.title, 
                "is_pinned": bool(getattr(c, 'is_pinned', False)),
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            data["is_saved"] = c.id in saved_ids
            updated = c.updated_at or now

            if updated >= today_start:
                grouped["today"].append(data)
            elif updated >= yesterday_start:
                grouped["yesterday"].append(data)
            elif updated >= week_start:
                grouped["last_7_days"].append(data)
            elif updated >= month_start:
                grouped["last_month"].append(data)
            else:
                grouped["older"].append(data)

        return jsonify({"status": "success", "history": grouped})
    except Exception:
        return jsonify({"status": "success", "history": grouped})


@history_bp.route('/saved', methods=['GET'])
def get_saved_conversations():
    """Retrieves all bookmarked conversations for the student."""
    student_id = get_real_student_id()
    search_q = request.args.get('search', '').strip().lower()

    # 1. MongoDB check
    saved_list = MongoChatService.get_saved_conversations(student_id, search_q)
    if not saved_list and student_id.isdigit():
        saved_list = MongoChatService.get_saved_conversations(int(student_id), search_q)

    if saved_list:
        return jsonify({"status": "success", "saved": saved_list})

    # 2. SQLite fallback
    try:
        from app.models.chat_history import ChatConversation, SavedConversation
        int_id = int(student_id) if str(student_id).isdigit() else 1
        saved_query = db.session.query(ChatConversation)\
            .join(SavedConversation, ChatConversation.id == SavedConversation.conversation_id)\
            .filter(SavedConversation.student_id == int_id)

        if search_q:
            saved_query = saved_query.filter(ChatConversation.title.ilike(f"%{search_q}%"))

        results = saved_query.order_by(SavedConversation.saved_at.desc()).all()
        
        saved_list = []
        for c in results:
            data = c.to_dict() if hasattr(c, 'to_dict') else {"id": c.id, "title": c.title}
            data["is_saved"] = True
            saved_list.append(data)

        return jsonify({"status": "success", "saved": saved_list})
    except Exception:
        return jsonify({"status": "success", "saved": []})


@history_bp.route('/clear-all', methods=['DELETE'])
def clear_all_history():
    """Deletes all conversation threads, messages, and bookmarks for the student."""
    student_id = get_real_student_id()
    # 1. MongoDB
    MongoChatService.clear_history_range(student_id, 'all')
    if student_id.isdigit():
        MongoChatService.clear_history_range(int(student_id), 'all')

    # 2. SQLite
    try:
        from app.models.chat_history import ChatConversation, ChatMessage, SavedConversation
        int_id = int(student_id) if str(student_id).isdigit() else 1
        user_conversations = ChatConversation.query.filter_by(student_id=int_id).all()
        conv_ids = [c.id for c in user_conversations]
        if conv_ids:
            SavedConversation.query.filter(SavedConversation.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
            ChatMessage.query.filter(ChatMessage.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
            ChatConversation.query.filter(ChatConversation.id.in_(conv_ids)).delete(synchronize_session=False)
            db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "All chat history cleared successfully."})


@history_bp.route('/clear-range', methods=['DELETE'])
def clear_history_range():
    """Deletes history based on time range parameter: ?range=1hour | 5hours | today | 24hours | 7days | all"""
    student_id = get_real_student_id()
    range_type = request.args.get('range', 'all').lower()

    MongoChatService.clear_history_range(student_id, range_type)
    if student_id.isdigit():
        MongoChatService.clear_history_range(int(student_id), range_type)

    try:
        from app.models.chat_history import ChatConversation, ChatMessage, SavedConversation
        int_id = int(student_id) if str(student_id).isdigit() else 1
        now = datetime.now()
        query = ChatConversation.query.filter_by(student_id=int_id)
        if range_type == '1hour':
            query = query.filter(ChatConversation.updated_at >= (now - timedelta(hours=1)))
        elif range_type == '5hours':
            query = query.filter(ChatConversation.updated_at >= (now - timedelta(hours=5)))
        elif range_type == 'today':
            query = query.filter(ChatConversation.updated_at >= datetime(now.year, now.month, now.day))
        elif range_type == '24hours':
            query = query.filter(ChatConversation.updated_at >= (now - timedelta(hours=24)))
        elif range_type == '7days':
            query = query.filter(ChatConversation.updated_at >= (now - timedelta(days=7)))

        target_ids = [c.id for c in query.all()]
        if target_ids:
            SavedConversation.query.filter(SavedConversation.conversation_id.in_(target_ids)).delete(synchronize_session=False)
            ChatMessage.query.filter(ChatMessage.conversation_id.in_(target_ids)).delete(synchronize_session=False)
            ChatConversation.query.filter(ChatConversation.id.in_(target_ids)).delete(synchronize_session=False)
            db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success", "message": f"Cleared history for range '{range_type}' successfully."})


# =========================================================
# 3. DYNAMIC / PARAMETERIZED API ENDPOINTS
# =========================================================
@history_bp.route('/<string:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Fetches full message thread for a specific conversation including saved feedback."""
    student_id = get_real_student_id()

    # 1. MongoDB check
    thread = MongoChatService.get_conversation_thread(conversation_id)
    if thread:
        return jsonify({
            "status": "success",
            "conversation": thread["conversation"],
            "messages": thread["messages"]
        })

    # 2. SQLite fallback
    try:
        from app.models.chat_history import ChatConversation, ChatMessage, ChatFeedback
        int_id = int(student_id) if str(student_id).isdigit() else 1
        conv = ChatConversation.query.filter_by(id=conversation_id).first()
        if not conv:
            return jsonify({"status": "error", "message": "Conversation not found"}), 404

        messages = ChatMessage.query.filter_by(conversation_id=conv.id).order_by(ChatMessage.created_at.asc()).all()
        conv_dict = conv.to_dict() if hasattr(conv, 'to_dict') else {"id": conv.id, "title": conv.title}
        
        msg_list = []
        for m in messages:
            m_dict = m.to_dict() if hasattr(m, 'to_dict') else {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "sender": m.sender,
                "content": getattr(m, 'content', getattr(m, 'text', '')),
                "image_path": getattr(m, 'image_path', None),
                "sources": [],
                "feedback": getattr(m, 'feedback', None)
            }
            msg_list.append(m_dict)

        return jsonify({
            "status": "success",
            "conversation": conv_dict,
            "messages": msg_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404


@history_bp.route('/<string:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Deletes a single chat conversation along with its messages and saved bookmarks."""
    student_id = get_real_student_id()
    MongoChatService.delete_conversation(conversation_id, student_id)
    if student_id.isdigit():
        MongoChatService.delete_conversation(conversation_id, int(student_id))

    try:
        from app.models.chat_history import ChatConversation, ChatMessage, SavedConversation
        SavedConversation.query.filter_by(conversation_id=conversation_id).delete()
        ChatMessage.query.filter_by(conversation_id=conversation_id).delete()
        ChatConversation.query.filter_by(id=conversation_id).delete()
        db.session.commit()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Conversation deleted successfully."})


@history_bp.route('/<string:conversation_id>/rename', methods=['PATCH', 'POST'])
def rename_conversation(conversation_id):
    """Renames an existing chat conversation."""
    student_id = get_real_student_id()
    data = request.get_json(silent=True) or request.form or {}
    new_title = str(data.get('title', '')).strip()

    if not new_title:
        return jsonify({"status": "error", "message": "Title cannot be empty."}), 400

    MongoChatService.rename_conversation(conversation_id, student_id, new_title)
    if student_id.isdigit():
        MongoChatService.rename_conversation(conversation_id, int(student_id), new_title)

    try:
        from app.models.chat_history import ChatConversation
        conv = ChatConversation.query.filter_by(id=conversation_id).first()
        if conv:
            conv.title = new_title
            db.session.commit()
    except Exception:
        pass

    return jsonify({
        "status": "success", 
        "message": "Conversation renamed successfully.",
        "conversation": {"id": conversation_id, "title": new_title}
    })


@history_bp.route('/<string:conversation_id>/toggle-save', methods=['POST'])
def toggle_save_conversation(conversation_id):
    """Toggles bookmark status on a chat conversation."""
    student_id = get_real_student_id()
    is_saved = MongoChatService.toggle_save(conversation_id, student_id)

    try:
        from app.models.chat_history import SavedConversation
        int_id = int(student_id) if str(student_id).isdigit() else 1
        existing = SavedConversation.query.filter_by(student_id=int_id, conversation_id=conversation_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        else:
            new_save = SavedConversation(student_id=int_id, conversation_id=conversation_id)
            db.session.add(new_save)
            db.session.commit()
    except Exception:
        pass

    msg = "Conversation bookmarked successfully." if is_saved else "Removed from saved conversations."
    return jsonify({"status": "success", "is_saved": is_saved, "message": msg})


@history_bp.route('/<string:conversation_id>/pin', methods=['POST'])
@history_bp.route('/<string:conversation_id>/toggle-pin', methods=['POST'])
def toggle_pin_conversation(conversation_id):
    """Permanently toggles the pinned status of a conversation in the database."""
    student_id = get_real_student_id()
    new_pinned = MongoChatService.toggle_pin(conversation_id, student_id)
    if new_pinned is None and student_id.isdigit():
        new_pinned = MongoChatService.toggle_pin(conversation_id, int(student_id))

    try:
        from app.models.chat_history import ChatConversation
        conv = ChatConversation.query.filter_by(id=conversation_id).first()
        if conv:
            conv.is_pinned = not bool(conv.is_pinned)
            new_pinned = conv.is_pinned
            db.session.commit()
    except Exception:
        pass

    action_msg = "Conversation pinned to top." if new_pinned else "Conversation unpinned."
    return jsonify({
        "status": "success",
        "is_pinned": bool(new_pinned),
        "message": action_msg,
        "conversation": {"id": conversation_id, "is_pinned": bool(new_pinned)}
    })