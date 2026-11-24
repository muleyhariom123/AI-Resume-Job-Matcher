import os
import secrets
import tempfile
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Detect Vercel deployment
IS_VERCEL = (
    os.environ.get("VERCEL") == "1"
    or os.environ.get("VERCEL_ENV") is not None
)


class Config:
    """Base configuration."""

    # Security configuration
    SECRET_KEY = os.environ.get("SECRET_KEY")

    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: SECRET_KEY "
                "environment variable is not set!"
            )

        SECRET_KEY = os.environ.get(
            "DEV_SECRET_KEY",
            "dev-key-fallback-" + secrets.token_hex(16)
        )

    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Use writable temporary storage on Vercel
    if IS_VERCEL:
        INSTANCE_DIR = os.path.join(
            tempfile.gettempdir(), "resume_matcher_instance"
        )
        UPLOAD_FOLDER = os.path.join(
            tempfile.gettempdir(), "resume_matcher_uploads"
        )
    else:
        INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
        UPLOAD_FOLDER = os.environ.get(
            "UPLOAD_FOLDER",
            os.path.join(BASE_DIR, "uploads")
        )

    # Create writable directories
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Database configuration
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        os.path.join(INSTANCE_DIR, "resume_matcher.db")
    )

    ALLOWED_EXTENSIONS = {"pdf", "txt"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
        == "true"
    )

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Login rate limiting
    LOGIN_RATE_LIMIT_ATTEMPTS = int(
        os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", 5)
    )

    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(
        os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 900)
    )

    # Registration rate limiting
    REGISTER_RATE_LIMIT_ATTEMPTS = int(
        os.environ.get("REGISTER_RATE_LIMIT_ATTEMPTS", 10)
    )

    REGISTER_RATE_LIMIT_WINDOW_SECONDS = int(
        os.environ.get("REGISTER_RATE_LIMIT_WINDOW_SECONDS", 3600)
    )

    # Email configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = (
        os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    )
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    @classmethod
    def is_mail_configured(cls):
        """Check whether email configuration is complete."""
        return bool(
            cls.MAIL_SERVER
            and cls.MAIL_USERNAME
            and cls.MAIL_PASSWORD
            and cls.MAIL_DEFAULT_SENDER
        )


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
        == "true"
    )

    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    def __init__(self):
        super().__init__()

        secret = os.environ.get("SECRET_KEY", "")

        if (
            not secret
            or len(secret) < 32
            or "ai-resume-matcher-secret-key" in secret
        ):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: A strong SECRET_KEY "
                "(minimum 32 characters) must be provided!"
            )


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = False

    WTF_CSRF_ENABLED = False

    DATABASE_PATH = ":memory:"

    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False