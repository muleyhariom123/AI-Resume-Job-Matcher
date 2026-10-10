import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Config:
    """Base configuration."""
    # Ensure SECRET_KEY is securely sourced
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # Fallback only for non-production environments
        if os.environ.get('FLASK_ENV') == 'production':
            raise RuntimeError("CRITICAL SECURITY ERROR: SECRET_KEY environment variable is not set in production!")
        # Ephemeral secure random key for development if unset
        SECRET_KEY = os.environ.get('DEV_SECRET_KEY', 'dev-key-fallback-' + secrets.token_hex(16))

    # Database configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(INSTANCE_DIR, 'resume_matcher.db'))

    # Uploads configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ALLOWED_EXTENSIONS = {'pdf', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload size

    # Security & Cookie configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token lifetime

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get('LOGIN_RATE_LIMIT_ATTEMPTS', 5))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 900))  # 15 mins
    REGISTER_RATE_LIMIT_ATTEMPTS = int(os.environ.get('REGISTER_RATE_LIMIT_ATTEMPTS', 10))
    REGISTER_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('REGISTER_RATE_LIMIT_WINDOW_SECONDS', 3600))  # 1 hour

    # SMTP / Email Configuration for Genuine Password Recovery
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    @classmethod
    def is_mail_configured(cls) -> bool:
        """Check if production-grade email infrastructure is configured."""
        return bool(cls.MAIL_SERVER and cls.MAIL_USERNAME and cls.MAIL_PASSWORD and cls.MAIL_DEFAULT_SENDER)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Enforce strict HTTPS cookie flag in production unless explicitly overridden
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    REMEMBER_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'

    def __init__(self):
        super().__init__()
        # Validate that the secret key is not a weak default
        secret = os.environ.get('SECRET_KEY', '')
        if not secret or len(secret) < 32 or 'ai-resume-matcher-secret-key' in secret:
            raise RuntimeError("CRITICAL SECURITY ERROR: A strong SECRET_KEY (min 32 chars) must be provided in production!")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # Allows unit testing form endpoints without extracting tokens unless explicitly tested
    DATABASE_PATH = ':memory:'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
