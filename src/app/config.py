import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///ai_job_scraper.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB upload limit

    # Celery / Redis
    # For local dev without Redis, use memory broker; in production, use Redis
    _broker = os.getenv('CELERY_BROKER_URL')
    CELERY_BROKER_URL = _broker if _broker else 'memory://'
    _backend = os.getenv('CELERY_RESULT_BACKEND')
    CELERY_RESULT_BACKEND = _backend if _backend else 'cache+memory://'
    
    # For testing without a worker, set to True to run tasks synchronously
    CELERY_ALWAYS_EAGER = os.getenv('CELERY_ALWAYS_EAGER', 'true').lower() in ('true', '1')

    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'redis://redis:6379/2')
    RATELIMIT_DEFAULT = "60 per minute"

    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ('true', '1')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    # Encryption
    FERNET_KEY = os.getenv('FERNET_KEY')  # generate via utils.generate_fernet_key()

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRETS_FILE')

    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')

    # App limits
    FREE_JOB_MONTHLY = int(os.getenv('FREE_JOB_MONTHLY', '100'))
    CELERY_RESULT_EXPIRES = int(os.getenv('CELERY_RESULT_EXPIRES', 3600))

    JSON_SORT_KEYS = False
