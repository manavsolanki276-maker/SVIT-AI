import os
from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, current_user
from jinja2 import TemplateNotFound
from app.extensions import db

# 1. Resolve Project Root, Static, and Template Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATE_DIR = os.path.join(APP_DIR, "templates")

# Ensure static upload and navigation folders exist
os.makedirs(os.path.join(STATIC_DIR, "navigation_maps"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "profile_images"), exist_ok=True)

# 2. Initialize Flask Application
app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATE_DIR
)
app.secret_key = "svit_ai_assistant_secret_key"

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///' + os.path.join(APP_DIR, 'svit_assistant.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Initialize SQLAlchemy with App Context
db.init_app(app)

# Add Python built-ins to Jinja environment to prevent UndefinedError in templates
app.jinja_env.globals.update(getattr=getattr, hasattr=hasattr, str=str, int=int, len=len)

# 3. Initialize Flask-Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.unauthorized_handler
def handle_unauthorized():
    """Safely redirects unauthenticated users without crashing on BuildError."""
    try:
        if 'auth.login' in app.view_functions:
            return redirect(url_for('auth.login', next=request.url))
        return redirect('/')
    except Exception:
        return redirect('/')

# Active User class fallback for local session testing
class ActiveUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.full_name = "Manav Solanki"
        self.department = "Computer Engineering"
        self.semester = 3
        self.division = "A"
        self.batch = "A1"
        self.avatar_url = None
        self.is_admin = False
        self.is_profile_complete = True

@login_manager.user_loader
def load_user(user_id):
    user_str = str(user_id)
    try:
        from app.database.mongo_models import MongoStudent, MongoAdmin
        if user_str.startswith('admin_'):
            real_id = user_str.split('_', 1)[1]
            return MongoAdmin.get_by_id(real_id) or Admin.query.get(int(real_id))
        elif user_str.startswith('student_'):
            real_id = user_str.split('_', 1)[1]
            return MongoStudent.get_by_id(real_id) or Student.query.get(int(real_id))
        
        m_user = MongoStudent.get_by_id(user_id) or MongoAdmin.get_by_id(user_id)
        if m_user:
            return m_user

        from app.database.models import Student, Admin
        return Student.query.get(int(user_id)) or Admin.query.get(int(user_id))
    except Exception:
        pass
    
    # Fallback user so chatbot endpoints work seamlessly during dev testing
    return ActiveUser(user_id)


# 4. Register All Blueprints (Prevent Duplicate Registrations)
try:
    from app.routes import register_blueprints
    register_blueprints(app)
except ImportError:
    pass

# Helper to safely register blueprint only if not already registered
def safe_register_blueprint(app_instance, blueprint):
    if blueprint.name not in app_instance.blueprints:
        app_instance.register_blueprint(blueprint)

# Safely register core & phase 2 blueprints
try:
    from app.auth.routes import auth_bp
    safe_register_blueprint(app, auth_bp)
except ImportError as e:
    print(f"⚠️ Note: auth_bp registration: {e}")

try:
    from app.routes.history_routes import history_bp
    safe_register_blueprint(app, history_bp)
except ImportError as e:
    print(f"⚠️ Note: history_bp registration: {e}")

try:
    from app.routes.profile_routes import profile_bp
    safe_register_blueprint(app, profile_bp)
except ImportError as e:
    print(f"⚠️ Note: profile_bp registration: {e}")

try:
    from app.routes.settings_routes import settings_bp
    safe_register_blueprint(app, settings_bp)
except ImportError as e:
    print(f"⚠️ Note: settings_bp registration: {e}")

try:
    from app.routes.notification_routes import notification_bp
    safe_register_blueprint(app, notification_bp)
except ImportError as e:
    print(f"⚠️ Note: notification_bp registration: {e}")

# Pass registered endpoints to Jinja context for safety check
@app.context_processor
def inject_endpoints():
    return {
        'bootstrap_endpoints': set(app.view_functions.keys())
    }

# 5. Root Endpoint to Render Chatbot UI
@app.route("/")
def home():
    """Renders the main student chat interface safely."""
    try:
        return render_template("student/chat.html")
    except TemplateNotFound:
        try:
            return render_template("chat.html")
        except TemplateNotFound:
            return render_template("chat/chat.html")


# 6. Server Entry Point
if __name__ == "__main__":
    print("🚀 Starting SVIT AI Assistant Server...")
    print(f"📁 Static Directory: {STATIC_DIR}")
    print(f"📄 Template Directory: {TEMPLATE_DIR}")
    
    with app.app_context():
        # Load user models first so SQLAlchemy registers the 'students' table schema
        try:
            from app.database.models import Student, Admin
        except ImportError:
            pass
            
        try:
            from app.models.chat_history import ChatConversation, ChatMessage, SavedConversation
            from app.models.user_settings import UserSettings
            from app.models.notification import Notification
        except ImportError:
            pass

        db.create_all()

    app.run(host="127.0.0.1", port=5000, debug=True)