# src/app/__init__.py
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

# extensions (singletons)
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()

LOG = logging.getLogger(__name__)

def create_app(config_object=None):
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    if config_object:
        app.config.from_object(config_object)
    else:
        from .config import BaseConfig
        app.config.from_object(BaseConfig)

    # initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.google_login'

    # user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    # logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # ensure upload/output folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    # register blueprints (do this after extensions are configured)
    # Import here to avoid import-time side-effects
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # Configure Celery (init without causing circular import)
    try:
        from .tasks import init_celery
        celery = init_celery(app)
        app.celery = celery
    except Exception as e:
        # don't fail app creation for CLI commands that don't need celery
        app.logger.info("Celery not initialized at create_app: %s", e)

    return app
