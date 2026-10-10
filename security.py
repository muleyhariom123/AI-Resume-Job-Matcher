import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlsplit
from typing import Tuple, Optional, Dict, List
from flask import request, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.utils import secure_filename


# ============================================================================
# Input Validation & Normalization
# ============================================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')


def normalize_email(email: str) -> str:
    """Normalize email address to lowercase and trimmed."""
    return email.strip().lower() if email else ''


def validate_registration_input(full_name: str, email: str, username: str, 
                               password: str, confirm_password: str, terms_accepted: bool) -> Tuple[bool, str]:
    """
    Validate all registration inputs.
    Returns (is_valid, error_message).
    """
    if not full_name or len(full_name.strip()) < 2:
        return False, "Please enter your full name (at least 2 characters)."

    if len(full_name.strip()) > 100:
        return False, "Full name cannot exceed 100 characters."

    if not email or not EMAIL_REGEX.match(email.strip()):
        return False, "Please enter a valid email address."

    if not username or not USERNAME_REGEX.match(username.strip()):
        return False, "Username must be 3-30 characters long and contain only letters, numbers, and underscores."

    if not password:
        return False, "Password is required."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return False, "Password must contain at least one letter and one number."

    if password != confirm_password:
        return False, "Passwords do not match. Please re-enter your password."

    if not terms_accepted:
        return False, "You must agree to the Terms of Service and Privacy Policy."

    return True, ""


# ============================================================================
# In-Memory Rate Limiter (Protects Login and Registration Endpoints)
# ============================================================================

class SlidingWindowRateLimiter:
    """In-memory thread-safe rate limiter based on sliding window timestamps."""
    def __init__(self):
        # Key -> list of float timestamps
        self.records: Dict[str, List[float]] = {}

    def is_rate_limited(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if the key has exceeded max_attempts within window_seconds.
        Returns (is_limited, seconds_remaining).
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Filter out expired attempts
        timestamps = self.records.get(key, [])
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self.records[key] = valid_timestamps

        if len(valid_timestamps) >= max_attempts:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return True, retry_after

        return False, 0

    def record_attempt(self, key: str):
        """Record a single attempt timestamp."""
        now = time.time()
        if key not in self.records:
            self.records[key] = []
        self.records[key].append(now)

    def clear(self, key: str):
        """Clear recorded attempts for a key upon successful authentication."""
        self.records.pop(key, None)


# Singleton rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def get_client_ip() -> str:
    """Extract client IP respecting potential reverse proxy headers safely."""
    # Only trust X-Forwarded-For if configured behind trusted proxy
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


# ============================================================================
# Safe URL Redirection (Prevent Open Redirect / CWE-601)
# ============================================================================

def is_safe_redirect_url(target: Optional[str]) -> bool:
    """
    Ensure redirect target is a safe relative URL on the current host.
    Prevents Open Redirect attacks.
    """
    if not target:
        return False
    parsed = urlsplit(target)
    # Target must be relative (no scheme, no netloc) and must start with / but not //
    return not parsed.scheme and not parsed.netloc and target.startswith('/') and not target.startswith('//')


# ============================================================================
# Password Recovery Token Generation & Dispatch
# ============================================================================

def get_reset_token_serializer() -> URLSafeTimedSerializer:
    """Get serializer for time-limited, signed password reset tokens."""
    secret = current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret, salt='password-reset-salt')


def generate_password_reset_token(user) -> str:
    """
    Generate a cryptographic, time-limited token.
    Includes user ID and a fingerprint of current password hash to guarantee single-use.
    """
    serializer = get_reset_token_serializer()
    fingerprint = user.password_hash[-12:] if user.password_hash else ''
    return serializer.dumps({'user_id': user.id, 'fingerprint': fingerprint})


def verify_password_reset_token(token: str, max_age_seconds: int = 1800) -> Tuple[Optional[int], Optional[str]]:
    """
    Verify reset token within expiration period (default 30 mins).
    Returns (user_id, error_message).
    """
    serializer = get_reset_token_serializer()
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
        from database import get_user_by_id
        user = get_user_by_id(data.get('user_id'))
        if not user:
            return None, "Invalid user token."
        
        # Verify single-use fingerprint against current user password hash
        current_fingerprint = user.password_hash[-12:] if user.password_hash else ''
        if data.get('fingerprint') != current_fingerprint:
            return None, "This password reset token has already been used or has been superseded."

        return user.id, None
    except SignatureExpired:
        return None, "The password reset link has expired. Please request a new one."
    except (BadSignature, Exception):
        return None, "Invalid or malformed password reset link."


def send_password_reset_email(user, reset_url: str) -> Tuple[bool, str]:
    """
    Send real password reset email if SMTP configuration is present.
    If not configured, return False with an explanatory message.
    """
    from config import Config
    if not Config.is_mail_configured():
        return False, "Email service is not configured on this server. Please contact an administrator."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset Request - AI Resume Matcher'
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = user.email

        text_content = f"""Hello {user.full_name},

A password reset was requested for your AI Resume Matcher account.
Click the link below to set a new password (valid for 30 minutes):

{reset_url}

If you did not request this, please ignore this email. Your password will remain unchanged.
"""
        msg.attach(MIMEText(text_content, 'plain'))

        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        if current_app.config['MAIL_USE_TLS']:
            server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.sendmail(msg['From'], [user.email], msg.as_string())
        server.quit()
        return True, "Password reset instructions have been sent to your email."
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


# ============================================================================
# File Upload Security
# ============================================================================

def is_allowed_file(filename: str) -> bool:
    """Validate file extension against allowed whitelist."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    clean = secure_filename(filename)
    return clean if clean else 'uploaded_resume'
