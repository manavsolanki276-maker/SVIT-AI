"""
app/routes/guest.py
Public Guest Mode Routes for SVIT-AI Assistant.
Enables guest access without login or signup, restricted to 11 public categories.
"""

from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.ai.guest_service import PUBLIC_CATEGORIES_METADATA, CATEGORY_RESPONSES

guest_bp = Blueprint('guest', __name__, url_prefix='/guest')


@guest_bp.route('/')
@guest_bp.route('/chat')
def guest_chat():
    """Renders the SVIT AI Assistant in Guest Mode without requiring authentication."""
    session['is_guest'] = True
    return render_template(
        'student/chat.html',
        is_guest=True,
        guest_categories=PUBLIC_CATEGORIES_METADATA
    )


@guest_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Returns the list of 11 permitted public categories for guests."""
    return jsonify({
        "status": "success",
        "official_website": "https://svitvasad.ac.in/",
        "total": len(PUBLIC_CATEGORIES_METADATA),
        "categories_count": len(PUBLIC_CATEGORIES_METADATA),
        "categories": PUBLIC_CATEGORIES_METADATA
    }), 200


@guest_bp.route('/exit')
def exit_guest():
    """Clears guest session and navigates to the login screen."""
    session.pop('is_guest', None)
    return redirect(url_for('auth.login'))
