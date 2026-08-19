from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Where to redirect users if they try accessing a @login_required route
login_manager.login_view = 'admin.login'
login_manager.login_message_category = 'warning'