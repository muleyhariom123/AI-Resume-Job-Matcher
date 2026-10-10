import io
import os
import pytest
from database import create_user, save_match_result, get_match_by_id_and_user, delete_match
from config import ProductionConfig, DevelopmentConfig

def test_protected_pages_reject_unauthenticated_requests(client):
    """9. Protected pages reject unauthenticated requests."""
    # Attempt to view dashboard without logging in
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.headers['Location']

    # Attempt to upload resume without logging in
    upload_res = client.post('/upload', data={}, follow_redirects=False)
    assert upload_res.status_code == 302
    assert '/login' in upload_res.headers['Location']


def test_authenticated_users_can_access_authorized_pages(client, app):
    """10. Authenticated users can access authorized pages."""
    with app.app_context():
        user = create_user('Helen Hunt', 'helen@example.com', 'helen_h', 'Pass1234!')

    # Login
    client.post('/login', data={'identifier': 'helen_h', 'password': 'Pass1234!'})

    # Access authorized dashboard
    res = client.get('/')
    assert res.status_code == 200
    assert b"AI Resume &amp; Job Matching Engine" in res.data or b"AI Resume & Job Matching Engine" in res.data
    assert b"Helen Hunt" in res.data
    assert b"@helen_h" in res.data


def test_user_data_isolation_between_accounts(client, app):
    """11. Users cannot access or delete another user's private resume data or results."""
    with app.app_context():
        user_a = create_user('User A', 'user_a@example.com', 'user_a', 'Pass1234!')
        user_b = create_user('User B', 'user_b@example.com', 'user_b', 'Pass1234!')

        # Create a match record belonging to User A
        match_a_id = save_match_result(
            user_id=user_a.id,
            original_filename='user_a_resume.pdf',
            stored_filename='stored_a.pdf',
            job_description='Software Engineer with Python and ML',
            match_score=88.5
        )

        # Create a match record belonging to User B
        match_b_id = save_match_result(
            user_id=user_b.id,
            original_filename='user_b_resume.pdf',
            stored_filename='stored_b.pdf',
            job_description='Product Manager with Agile',
            match_score=72.0
        )

    # Login as User B
    client.post('/login', data={'identifier': 'user_b', 'password': 'Pass1234!'})

    # User B views dashboard: should see their own resume, but NOT User A's resume
    dashboard_res = client.get('/')
    assert dashboard_res.status_code == 200
    assert b"user_b_resume.pdf" in dashboard_res.data
    assert b"user_a_resume.pdf" not in dashboard_res.data

    # User B attempts to delete User A's match record
    del_res = client.post(f'/delete-match/{match_a_id}', follow_redirects=True)
    assert b"Record not found or you do not have permission" in del_res.data

    # Verify in DB that User A's match still exists intact
    with app.app_context():
        match_a = get_match_by_id_and_user(match_a_id, user_a.id)
        assert match_a is not None
        assert match_a['original_filename'] == 'user_a_resume.pdf'


def test_resume_upload_and_job_matching_flow(client, app):
    """13. Existing resume-upload and job-matching features continue working."""
    with app.app_context():
        create_user('Candidate Ian', 'ian@example.com', 'ian_dev', 'Pass1234!')

    # Login
    client.post('/login', data={'identifier': 'ian_dev', 'password': 'Pass1234!'})

    # Sample resume text content matching the job description
    resume_content = b"Senior Python developer experienced in machine learning, scikit-learn, natural language processing and Flask web development."
    job_desc = "Looking for a Senior Python Developer with machine learning, scikit-learn, and Flask experience."

    data = {
        'job_description': job_desc,
        'resume': (io.BytesIO(resume_content), 'ian_resume.txt')
    }

    res = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"Compatibility Analysis Result" in res.data
    assert b"Compatibility" in res.data
    assert b"ian_resume.txt" in res.data
    assert b"%" in res.data


def test_login_page_no_longer_displays_demo_credentials(client):
    """14. The login page no longer displays demo credentials."""
    res = client.get('/login')
    assert res.status_code == 200

    # Ensure demo credentials text and pills are absent
    assert b"Demo Credentials" not in res.data
    assert b"admin123" not in res.data
    assert b"recruiter2026" not in res.data
    assert b"demo-pill" not in res.data


def test_no_hardcoded_default_passwords_in_source_code():
    """15. No hardcoded default password or secret remains in application code."""
    # List all relevant project files
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    source_files = ['app.py', 'config.py', 'database.py', 'security.py', 'streamlit_app.py']

    demo_passwords = ['admin123', 'recruiter2026', 'ai-resume-matcher-secret-key-2026']

    for fname in source_files:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                for bad_str in demo_passwords:
                    assert bad_str not in content, f"Hardcoded credential '{bad_str}' found in {fname}"


def test_production_configuration_debug_and_security():
    """16. Production configuration does not enable debug mode and requires strong secret key."""
    # ProductionConfig must have DEBUG = False
    assert ProductionConfig.DEBUG is False

    # In production without a strong key, an error should be raised
    old_env = os.environ.get('FLASK_ENV')
    old_sec = os.environ.get('SECRET_KEY')
    try:
        os.environ['FLASK_ENV'] = 'production'
        os.environ['SECRET_KEY'] = 'short'
        with pytest.raises(RuntimeError):
            ProductionConfig()

        # With a strong secret key, it succeeds with debug=False
        os.environ['SECRET_KEY'] = 'a' * 32
        prod_cfg = ProductionConfig()
        assert prod_cfg.DEBUG is False
    finally:
        if old_env is not None:
            os.environ['FLASK_ENV'] = old_env
        else:
            os.environ.pop('FLASK_ENV', None)

        if old_sec is not None:
            os.environ['SECRET_KEY'] = old_sec
        else:
            os.environ.pop('SECRET_KEY', None)
