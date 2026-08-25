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
_run_db_url = os.environ.get('DATABASE_URL', '').strip()
if _run_db_url and not _run_db_url.startswith(('mongodb://', 'mongodb+srv://')):
    if _run_db_url.startswith('postgres://'):
        _run_db_url = _run_db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = _run_db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(APP_DIR, 'svit_assistant.db')
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

@login_manager.user_loader
def load_user(user_id):
    user_str = str(user_id)
    try:
        from app.database.mongo_models import MongoStudent, MongoAdmin
        from app.database.models import Student, Admin
        if user_str.startswith('admin_'):
            real_id = user_str.split('_', 1)[1]
            admin = MongoAdmin.get_by_id(real_id)
            if admin:
                return admin
            try:
                return Admin.query.get(int(real_id))
            except Exception:
                return None
        elif user_str.startswith('student_'):
            real_id = user_str.split('_', 1)[1]
            student = MongoStudent.get_by_id(real_id)
            if student:
                return student
            try:
                return Student.query.get(int(real_id))
            except Exception:
                return None
        
        m_user = MongoStudent.get_by_id(user_id) or MongoAdmin.get_by_id(user_id)
        if m_user:
            return m_user

        return Student.query.get(int(user_id)) or Admin.query.get(int(user_id))
    except Exception:
        return None


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

from app.auth.rbac import has_permission, has_role, ROLE_DISPLAY_NAMES, normalize_role

# Pass registered endpoints to Jinja context for safety check
@app.context_processor
def inject_endpoints():
    return {
        'bootstrap_endpoints': set(app.view_functions.keys()),
        'has_permission': has_permission,
        'has_role': has_role,
        'ROLE_DISPLAY_NAMES': ROLE_DISPLAY_NAMES,
        'normalize_role': normalize_role,
    }

app.jinja_env.globals.update(
    has_permission=has_permission,
    has_role=has_role,
    ROLE_DISPLAY_NAMES=ROLE_DISPLAY_NAMES,
    normalize_role=normalize_role,
)

# 5. Root Endpoint & Global Error Handlers
@app.route("/")
def home():
    """Renders the main student chat interface safely or routes admin to dashboard."""
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin.dashboard'))
    try:
        return render_template("student/chat.html")
    except TemplateNotFound:
        try:
            return render_template("chat.html")
        except TemplateNotFound:
            return render_template("chat/chat.html")

@app.errorhandler(403)
def handle_403(e):
    """Clean 403 access denied handler without template variable dependencies."""
    return render_template('errors/403.html', error_message=getattr(e, 'description', 'Access Denied: You do not have permission to view this resource.')), 403


# 6. Server Entry Point
if __name__ == "__main__":
    print("[START] Starting SVIT AI Assistant Server...")
    print(f"[STATIC] Static Directory: {STATIC_DIR}")
    print(f"[TEMPLATE] Template Directory: {TEMPLATE_DIR}")
    
    with app.app_context():
        # Load user models first so SQLAlchemy registers the 'students' and 'admins' table schema
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

        try:
            from app.database.admin_seed import seed_admin_accounts
            seed_admin_accounts(app)
        except Exception as seed_err:
            print(f"⚠️ Note: Admin seeding: {seed_err}")

    app.run(host="127.0.0.1", port=5000, debug=True)