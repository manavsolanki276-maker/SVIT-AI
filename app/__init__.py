import os
import logging
from datetime import timedelta
from flask import Flask, redirect, url_for, render_template
from flask_login import current_user
from app.extensions import db, login_manager

# Configure logging to monitor application context events
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # =========================================================
    # 1. BASE CONFIGURATIONS
    # =========================================================
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-svit-ai-assistant')
    
    # Enable automatic login during local development
    app.config['AUTO_LOGIN_DEV'] = False  # Set to False when deploying to production
    
    # Keep session active for 30 days
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    # Database setup
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url and not db_url.startswith(('mongodb://', 'mongodb+srv://')):
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    elif os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        import tempfile
        tmp_dir = tempfile.gettempdir()
        tmp_db = os.path.join(tmp_dir, 'svit_assistant.db')
        src_db = os.path.join(base_dir, 'svit_assistant.db')
        if not os.path.exists(tmp_db) and os.path.exists(src_db):
            try:
                import shutil
                shutil.copy2(src_db, tmp_db)
            except Exception:
                pass
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_db}'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'svit_assistant.db')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Ensure static upload folders exist safely
    profile_upload_path = os.path.join(app.root_path, 'static', 'profile_images')
    images_upload_path = os.path.join(app.root_path, 'static', 'uploads', 'images')
    docs_upload_path = os.path.join(app.root_path, 'static', 'uploads', 'documents')
    for p in [profile_upload_path, images_upload_path, docs_upload_path]:
        try:
            os.makedirs(p, exist_ok=True)
        except OSError:
            pass

    # =========================================================
    # 2. EXTENSION INITIALIZATION
    # =========================================================
    db.init_app(app)
    login_manager.init_app(app)
    
    # Set default login view to student login
    login_manager.login_view = 'auth.student_login'

    # Import User models for login loader
    from app.database.models import Admin, Student
    from app.database.mongo_models import MongoStudent, MongoAdmin

    # =========================================================
    # 3. FLASK-LOGIN USER LOADER Callback
    # =========================================================
    @login_manager.user_loader
    def load_user(user_id):
        user_str = str(user_id)
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
        
        # Fallback for legacy raw IDs
        mongo_user = MongoStudent.get_by_id(user_id) or MongoAdmin.get_by_id(user_id)
        if mongo_user:
            return mongo_user
        try:
            return Student.query.get(int(user_id)) or Admin.query.get(int(user_id))
        except (ValueError, TypeError):
            return None


    # =========================================================
    # 4. BLUEPRINT REGISTRATIONS
    # =========================================================
    # Auth Blueprint
    try:
        from app.routes.auth import auth_bp
    except ImportError:
        from app.auth.routes import auth_bp

    # Student Blueprint
    try:
        from app.routes.student import student_bp
    except ImportError:
        from app.student.routes import student_bp

    # Admin Blueprint
    try:
        from app.routes.admin import admin_bp
    except ImportError:
        admin_bp = None

    # Chat API Blueprint
    from app.routes.chat import chat_bp

    # Feature Blueprints
    from app.routes.history_routes import history_bp
    from app.routes.profile_routes import profile_bp
    
    try:
        from app.routes.settings_routes import settings_bp
    except ImportError:
        settings_bp = None

    try:
        from app.routes.notification_routes import notification_bp
    except ImportError:
        notification_bp = None

    # Register Blueprints
    app.register_blueprint(auth_bp)        # Handles /auth/...
    app.register_blueprint(student_bp)     # Handles /student/...
    app.register_blueprint(chat_bp)        # Handles /api/chat
    app.register_blueprint(history_bp)     # Handles /chat/history-page, /chat/clear-range
    app.register_blueprint(profile_bp)     # Handles /student/profile/

    if admin_bp:
        app.register_blueprint(admin_bp)
    if settings_bp:
        app.register_blueprint(settings_bp)
    if notification_bp:
        app.register_blueprint(notification_bp)

    # =========================================================
    # 5. JINJA CONTEXT PROCESSORS & UTILITIES
    # =========================================================
    from app.auth.rbac import has_permission, has_role, ROLE_DISPLAY_NAMES, normalize_role

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
        getattr=getattr,
        hasattr=hasattr,
        str=str,
        int=int,
        len=len,
        has_permission=has_permission,
        has_role=has_role,
        ROLE_DISPLAY_NAMES=ROLE_DISPLAY_NAMES,
        normalize_role=normalize_role,
    )

    # Register CLI commands
    try:
        from app.commands import admin_cli
        app.cli.add_command(admin_cli)
    except Exception as e:
        logger.warning(f"CLI command registration notice: {e}")

    # =========================================================
    # 6. DEFAULT APPLICATION ROOT ROUTE
    # =========================================================
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if getattr(current_user, 'is_admin', False):
                return redirect(url_for('admin.dashboard'))
            
            # Check student approval status
            status = getattr(current_user, 'status', 'active')
            if status != 'active':
                if status == 'pending':
                    return redirect(url_for('auth.pending_view'))
                elif status == 'rejected':
                    return redirect(url_for('auth.rejected_view'))
                logout_user()
                return redirect(url_for('auth.login'))

            # Check profile completion status
            is_complete = getattr(current_user, 'is_profile_completed', getattr(current_user, 'is_profile_complete', True))
            if not is_complete:
                return redirect('/student/profile/complete')
            
            # Render chat page directly without an intermediate 302 bounce
            return render_template('student/chat.html')

        return redirect(url_for('auth.login'))

    @app.route('/login', methods=['GET', 'POST'])
    def root_login():
        from app.routes.auth import student_login
        return student_login()

    @app.route('/admin/login', methods=['GET', 'POST'])
    def root_admin_login():
        return redirect('/login', code=302)

    @app.route('/register', methods=['GET', 'POST'])
    def root_register():
        from app.routes.auth import register
        return register()

    @app.route('/logout', methods=['GET', 'POST'])
    def root_logout():
        from app.routes.auth import logout
        return logout()

    @app.errorhandler(403)
    def handle_403(e):
        return render_template('errors/403.html', error_message=getattr(e, 'description', 'Access Denied: You do not have permission to view this resource.')), 403

    # =========================================================
    # 7. MODEL METADATA REGISTRATION, MIGRATION & SEEDING
    # =========================================================
    with app.app_context():
        try:
            from app.models.chat_history import ChatConversation, ChatMessage, SavedConversation
            from app.models.user_settings import UserSettings
            from app.models.notification import Notification
        except ImportError as e:
            logger.warning(f"Secondary models registration notice: {e}")

        try:
            db.create_all()
            with db.engine.connect() as conn:
                res = conn.execute(db.text("PRAGMA table_info(students)")).fetchall()
                cols = [r[1] for r in res]
                if cols:
                    if 'status' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
                    if 'request_id' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN request_id VARCHAR(50)"))
                    if 'approved_by' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN approved_by VARCHAR(50)"))
                    if 'approved_at' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN approved_at DATETIME"))
                    if 'rejected_by' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN rejected_by VARCHAR(50)"))
                    if 'rejected_at' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN rejected_at DATETIME"))
                    if 'rejection_reason' not in cols:
                        conn.execute(db.text("ALTER TABLE students ADD COLUMN rejection_reason TEXT"))
                    conn.commit()
        except Exception as db_err:
            logger.warning(f"Database table initialization notice: {db_err}")

        # Seed admin accounts for RBAC system
        try:
            from app.database.admin_seed import seed_admin_accounts
            seed_admin_accounts(app)
        except Exception as seed_err:
            logger.warning(f"Admin seeding notice: {seed_err}")

        # Initialize and seed datasets from CSV knowledge base
        try:
            from app.database.admin_crud_service import initialize_datasets_if_needed
            initialize_datasets_if_needed(os.path.abspath(os.path.join(base_dir, '..')))
        except Exception as data_err:
            logger.warning(f"Dataset initialization notice: {data_err}")

    return app