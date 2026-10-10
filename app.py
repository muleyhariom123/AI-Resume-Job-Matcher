import os
import uuid
import logging
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    session, flash, abort, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user, 
    login_required, current_user
)
from flask_wtf.csrf import CSRFProtect, CSRFError
import json
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from analyzer import analyze_compatibility

from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from database import (
    init_db, close_db, get_db,
    get_user_by_id, get_user_by_username, get_user_by_email,
    get_user_by_username_or_email, create_user, update_user_password,
    save_match_result, get_user_matches, get_match_by_id_and_user, delete_match
)
from security import (
    normalize_email, validate_registration_input,
    rate_limiter, get_client_ip, is_safe_redirect_url,
    generate_password_reset_token, verify_password_reset_token,
    send_password_reset_email, is_allowed_file, sanitize_filename
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize Extensions
csrf = CSRFProtect()
login_manager = LoginManager()


def create_app(config_class=None):
    """Application factory for AI Resume Matcher."""
    app = Flask(__name__)

    # Determine configuration class
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development').lower()
        if env == 'production':
            config_class = ProductionConfig
        elif env == 'testing':
            config_class = TestingConfig
        else:
            config_class = DevelopmentConfig

    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please sign in to access this page.'
    login_manager.login_message_category = 'error'
    login_manager.session_protection = 'strong'

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Initialize database tables
    with app.app_context():
        init_db()

    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return get_user_by_id(int(user_id))
        except (ValueError, TypeError):
            return None

    # Error Handlers
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        logger.warning(f"CSRF validation failed for IP {get_client_ip()}: {e.description}")
        flash("Your security session has expired or the form submission was invalid. Please try again.", "error")
        return redirect(request.referrer or url_for('login'))

    @app.errorhandler(413)
    def request_entity_too_large(e):
        flash("The uploaded file exceeds the 16MB maximum file size limit.", "error")
        return redirect(url_for('home'))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('login.html', not_found=True), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error: {e}", exc_info=True)
        flash("An unexpected server error occurred. Please try again later.", "error")
        return render_template('login.html'), 500

    # =========================================================================
    # Core Resume Processing Algorithms (Preserved)
    # =========================================================================

    def extract_text_from_file(file_path: str) -> str:
        """Extract text from PDF or TXT files."""
        text = ""
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        return text

    def calculate_match_score(resume_text: str, job_description: str) -> float:
        """Calculate TF-IDF Cosine Similarity score between resume and job description."""
        if not resume_text.strip() or not job_description.strip():
            return 0.0
        documents = [resume_text, job_description]
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(documents)
        match_percentage = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100
        return round(float(match_percentage), 2)

    # =========================================================================
    # Authentication Routes
    # =========================================================================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # Prevent authenticated users from entering an unnecessary login loop
        if current_user.is_authenticated:
            return redirect(url_for('home'))

        client_ip = get_client_ip()
        rate_key = f"login:{client_ip}"

        if request.method == 'POST':
            # Check rate limiting for brute force protection
            is_limited, retry_after = rate_limiter.is_rate_limited(
                rate_key, 
                app.config['LOGIN_RATE_LIMIT_ATTEMPTS'], 
                app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS']
            )
            if is_limited:
                flash(f"Too many failed login attempts. For security, please wait {retry_after} seconds before trying again.", "error")
                return render_template('login.html'), 429

            identifier = request.form.get('identifier', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))

            if not identifier or not password:
                flash("Please provide both your username/email and password.", "error")
                return render_template('login.html'), 400

            user = get_user_by_username_or_email(identifier)

            if user and user.check_password(password):
                if not user.is_active:
                    flash("This account has been deactivated. Please contact support.", "error")
                    return render_template('login.html'), 403

                # Successful authentication: clear rate limiting tracking
                rate_limiter.clear(rate_key)

                # Prevent session fixation by resetting the session cookie
                session.clear()

                # Establish authenticated session via Flask-Login
                login_user(user, remember=remember)
                session.permanent = remember

                logger.info(f"User '{user.username}' (ID: {user.id}) logged in successfully from {client_ip}.")
                flash(f"Welcome back, {user.full_name}!", "success")

                # Validate safe redirection target
                next_page = request.args.get('next')
                if next_page and is_safe_redirect_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('home'))
            else:
                # Record failed attempt for rate limiting
                rate_limiter.record_attempt(rate_key)
                logger.warning(f"Failed login attempt for identifier '{identifier}' from {client_ip}.")
                # Generic error message to prevent user enumeration
                flash("Invalid credentials. Please verify your details and try again.", "error")
                return render_template('login.html'), 401

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        # Prevent authenticated users from visiting registration
        if current_user.is_authenticated:
            return redirect(url_for('home'))

        client_ip = get_client_ip()
        rate_key = f"register:{client_ip}"

        if request.method == 'POST':
            # Rate limiting for registration to prevent automated bot spam
            is_limited, retry_after = rate_limiter.is_rate_limited(
                rate_key,
                app.config['REGISTER_RATE_LIMIT_ATTEMPTS'],
                app.config['REGISTER_RATE_LIMIT_WINDOW_SECONDS']
            )
            if is_limited:
                flash(f"Too many account creation attempts. Please wait {retry_after} seconds before trying again.", "error")
                return render_template('register.html'), 429

            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            terms_accepted = bool(request.form.get('terms'))

            # Server-side validation
            is_valid, error_msg = validate_registration_input(
                full_name, email, username, password, confirm_password, terms_accepted
            )
            if not is_valid:
                flash(error_msg, "error")
                return render_template('register.html', 
                                       full_name=full_name, 
                                       email=email, 
                                       username=username), 400

            norm_email = normalize_email(email)

            # Check for existing email or username
            if get_user_by_email(norm_email):
                rate_limiter.record_attempt(rate_key)
                flash("An account with this email address already exists. Please sign in or use a different email.", "error")
                return render_template('register.html', full_name=full_name, username=username), 400

            if get_user_by_username(username):
                rate_limiter.record_attempt(rate_key)
                flash("This username is already taken. Please choose another username.", "error")
                return render_template('register.html', full_name=full_name, email=email), 400

            # Create user in database with modern scrypt hash
            try:
                new_user = create_user(
                    full_name=full_name,
                    email=norm_email,
                    username=username,
                    password=password
                )
                logger.info(f"New user registered: '{new_user.username}' (ID: {new_user.id}) from {client_ip}.")
                rate_limiter.clear(rate_key)
                flash("Account created successfully! Please sign in with your new credentials.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                logger.error(f"Error creating user: {e}", exc_info=True)
                flash("An error occurred while creating your account. Please try again.", "error")
                return render_template('register.html', full_name=full_name, email=email, username=username), 500

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logger.info(f"User '{current_user.username}' (ID: {current_user.id}) logged out.")
        logout_user()
        session.clear()
        flash("You have been successfully logged out.", "success")
        return redirect(url_for('login'))

    # =========================================================================
    # Password Recovery Routes
    # =========================================================================

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if current_user.is_authenticated:
            return redirect(url_for('home'))

        mail_configured = Config.is_mail_configured()

        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            norm_email = normalize_email(email)

            if not norm_email:
                flash("Please enter your registered email address.", "error")
                return render_template('forgot_password.html', mail_configured=mail_configured), 400

            user = get_user_by_email(norm_email)
            if not mail_configured:
                # Do NOT pretend email was sent if service is not configured!
                flash("Password recovery via email is currently unconfigured by the administrator. Please contact your system administrator for assistance.", "error")
                return render_template('forgot_password.html', mail_configured=False), 503

            if user:
                token = generate_password_reset_token(user)
                reset_url = url_for('reset_password', token=token, _external=True)
                success, msg = send_password_reset_email(user, reset_url)
                if success:
                    flash("If an account exists for that email, a password reset link has been dispatched.", "success")
                    return redirect(url_for('login'))
                else:
                    flash(f"Error dispatching reset email: {msg}", "error")
            else:
                # Ambiguous message to prevent user enumeration
                flash("If an account exists for that email, a password reset link has been dispatched.", "success")
                return redirect(url_for('login'))

        return render_template('forgot_password.html', mail_configured=mail_configured)

    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        if current_user.is_authenticated:
            return redirect(url_for('home'))

        user_id, error = verify_password_reset_token(token)
        if error or not user_id:
            flash(error or "Invalid or expired password reset link.", "error")
            return redirect(url_for('forgot_password'))

        user = get_user_by_id(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not password or len(password) < 8:
                flash("Password must be at least 8 characters long.", "error")
                return render_template('reset_password.html', token=token), 400

            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return render_template('reset_password.html', token=token), 400

            update_user_password(user.id, password)
            logger.info(f"Password reset successfully completed for user ID {user.id}.")
            flash("Your password has been successfully reset. Please sign in with your new password.", "success")
            return redirect(url_for('login'))

        return render_template('reset_password.html', token=token)

    # =========================================================================
    # Protected Application Dashboard & Resume Processing
    # =========================================================================

    @app.route('/')
    @login_required
    def home():
        # Retrieve match history strictly owned by the authenticated user
        matches = get_user_matches(current_user.id)
        return render_template('index.html', score=None, matches=matches, user=current_user)

    @app.route('/upload', methods=['POST'])
    @login_required
    def match_resume():
        job_description = request.form.get('job_description', '').strip()
        file = request.files.get('resume')
        matches = get_user_matches(current_user.id)

        if not job_description:
            flash("Please enter or paste the target job description.", "error")
            return render_template('index.html', score=None, job_description=job_description, matches=matches, user=current_user), 400

        if not file or not file.filename:
            flash("Please select a valid resume file to upload.", "error")
            return render_template('index.html', score=None, job_description=job_description, matches=matches, user=current_user), 400

        if not is_allowed_file(file.filename):
            flash("Unsupported file format. Please upload a PDF (.pdf) or Text (.txt) file.", "error")
            return render_template('index.html', score=None, job_description=job_description, matches=matches, user=current_user), 400

        # Isolated directory per user: uploads/<user_id>/
        user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)

        original_name = sanitize_filename(file.filename)
        # Unique file storage prefix to prevent overwriting and directory traversal
        stored_name = f"{uuid.uuid4().hex[:12]}_{original_name}"
        filepath = os.path.join(user_upload_dir, stored_name)

        try:
            file.save(filepath)
            resume_text = extract_text_from_file(filepath)
            score = calculate_match_score(resume_text, job_description)

            # Generate explainable compatibility analysis
            analysis = analyze_compatibility(resume_text, job_description, score)
            analysis_json = json.dumps(analysis)

            # Persist match linked strictly to current_user.id
            save_match_result(
                user_id=current_user.id,
                original_filename=original_name,
                stored_filename=stored_name,
                job_description=job_description,
                match_score=score,
                analysis_json=analysis_json
            )

            # Refresh user's match history
            updated_matches = get_user_matches(current_user.id)
            flash("Resume compatibility analyzed with full breakdown!", "success")
            return render_template(
                'index.html',
                score=score,
                job_description=job_description,
                uploaded_filename=original_name,
                analysis=analysis,
                matches=updated_matches,
                user=current_user
            )

        except Exception as e:
            logger.error(f"Error processing resume upload for user {current_user.id}: {e}", exc_info=True)
            flash("An error occurred while parsing the resume file. Please ensure the file is not corrupted.", "error")
            return render_template('index.html', score=None, job_description=job_description, matches=matches, user=current_user), 500

    @app.route('/match/<int:match_id>')
    @login_required
    def view_match_details(match_id):
        match = get_match_by_id_and_user(match_id, current_user.id)
        if not match:
            flash("Analysis record not found or access denied.", "error")
            return redirect(url_for('home'))

        analysis = None
        if match.get('analysis_json'):
            try:
                analysis = json.loads(match['analysis_json'])
            except Exception as e:
                logger.warning(f"Failed to deserialize analysis_json for match {match_id}: {e}")

        if not analysis:
            user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            filepath = os.path.join(user_upload_dir, match['stored_filename'])
            resume_text = ""
            if os.path.exists(filepath):
                try:
                    resume_text = extract_text_from_file(filepath)
                except Exception:
                    pass
            analysis = analyze_compatibility(resume_text, match['job_description'], match['match_score'])

        matches = get_user_matches(current_user.id)
        return render_template(
            'index.html',
            score=match['match_score'],
            job_description=match['job_description'],
            uploaded_filename=match['original_filename'],
            analysis=analysis,
            matches=matches,
            user=current_user,
            selected_match_id=match_id
        )

    @app.route('/delete-match/<int:match_id>', methods=['POST'])
    @login_required
    def remove_match(match_id):
        # Strict user authorization check enforced by query
        success = delete_match(match_id, current_user.id)
        if success:
            flash("Analysis record deleted successfully.", "success")
        else:
            flash("Record not found or you do not have permission to delete it.", "error")
        return redirect(url_for('home'))

    return app


# Create default application instance
app = create_app()

if __name__ == '__main__':
    # When executed directly, run server safely
    env = os.environ.get('FLASK_ENV', 'development').lower()
    if env == 'production':
        from waitress import serve
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Waitress production WSGI server on port {port}...")
        serve(app, host='0.0.0.0', port=port)
    else:
        app.run(host='127.0.0.1', port=5000, debug=True)