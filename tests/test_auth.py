import pytest
from database import get_user_by_email, get_user_by_username, get_db, create_user
from security import rate_limiter

def test_registration_succeeds_with_valid_details(client, app):
    """1. Registration succeeds with valid, unique details."""
    response = client.post('/register', data={
        'full_name': 'Alice Candidate',
        'email': 'alice@example.com',
        'username': 'alice_c',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!',
        'terms': '1'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    with app.app_context():
        user = get_user_by_email('alice@example.com')
        assert user is not None
        assert user.full_name == 'Alice Candidate'
        assert user.username == 'alice_c'


def test_registration_rejects_invalid_input(client):
    """2. Registration rejects invalid input (e.g. invalid email, short password, no terms)."""
    # Bad email
    res1 = client.post('/register', data={
        'full_name': 'Alice Candidate',
        'email': 'not-an-email',
        'username': 'alice_bad1',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!',
        'terms': '1'
    })
    assert res1.status_code == 400
    assert b"valid email address" in res1.data

    # Short password
    res2 = client.post('/register', data={
        'full_name': 'Alice Candidate',
        'email': 'alice2@example.com',
        'username': 'alice_bad2',
        'password': 'short',
        'confirm_password': 'short',
        'terms': '1'
    })
    assert res2.status_code == 400
    assert b"at least 8 characters" in res2.data

    # Password without digits
    res3 = client.post('/register', data={
        'full_name': 'Alice Candidate',
        'email': 'alice3@example.com',
        'username': 'alice_bad3',
        'password': 'OnlyLettersHere',
        'confirm_password': 'OnlyLettersHere',
        'terms': '1'
    })
    assert res3.status_code == 400
    assert b"at least one letter and one number" in res3.data

    # Terms not accepted
    res4 = client.post('/register', data={
        'full_name': 'Alice Candidate',
        'email': 'alice4@example.com',
        'username': 'alice_bad4',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!'
    })
    assert res4.status_code == 400
    assert b"Terms of Service" in res4.data


def test_registration_rejects_mismatched_passwords(client):
    """3. Registration rejects mismatched passwords."""
    response = client.post('/register', data={
        'full_name': 'Bob Tester',
        'email': 'bob@example.com',
        'username': 'bob_t',
        'password': 'Password123!',
        'confirm_password': 'DifferentPassword456!',
        'terms': '1'
    })
    assert response.status_code == 400
    assert b"Passwords do not match" in response.data


def test_duplicate_email_and_username_handled(client):
    """4. Duplicate email addresses and usernames are handled correctly."""
    # Register first user
    client.post('/register', data={
        'full_name': 'Charlie First',
        'email': 'charlie@example.com',
        'username': 'charlie1',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'terms': '1'
    })

    # Attempt duplicate email with different username
    res_dup_email = client.post('/register', data={
        'full_name': 'Charlie Second',
        'email': 'charlie@example.com',
        'username': 'charlie2',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'terms': '1'
    })
    assert res_dup_email.status_code == 400
    assert b"account with this email address already exists" in res_dup_email.data

    # Attempt duplicate username with different email
    res_dup_user = client.post('/register', data={
        'full_name': 'Charlie Third',
        'email': 'different_charlie@example.com',
        'username': 'charlie1',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'terms': '1'
    })
    assert res_dup_user.status_code == 400
    assert b"username is already taken" in res_dup_user.data


def test_passwords_stored_as_hashes_not_plaintext(app):
    """5. Passwords are stored as hashes, not plaintext."""
    with app.app_context():
        user = create_user(
            full_name='Diana Prince',
            email='diana@example.com',
            username='diana',
            password='MySecretPassword99!'
        )

        # Check raw database entry
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,))
        raw_row = cursor.fetchone()
        raw_hash = raw_row['password_hash']

        # Ensure raw string in DB is NOT the plaintext
        assert raw_hash != 'MySecretPassword99!'
        # Ensure it starts with scrypt identifier
        assert raw_hash.startswith('scrypt:')
        # Check that user object verifies correctly
        assert user.check_password('MySecretPassword99!') is True
        assert user.check_password('WrongPassword') is False


def test_login_succeeds_with_valid_credentials(client, app):
    """6. Login succeeds with valid credentials (by username or email)."""
    with app.app_context():
        create_user('Evan Stone', 'evan@example.com', 'evan_s', 'Pass1234!')

    # Login via username
    res1 = client.post('/login', data={
        'identifier': 'evan_s',
        'password': 'Pass1234!'
    }, follow_redirects=True)
    assert res1.status_code == 200
    assert b"Welcome back, Evan Stone!" in res1.data

    # Logout
    client.get('/logout')

    # Login via email
    res2 = client.post('/login', data={
        'identifier': 'evan@example.com',
        'password': 'Pass1234!'
    }, follow_redirects=True)
    assert res2.status_code == 200
    assert b"Welcome back, Evan Stone!" in res2.data


def test_login_fails_with_invalid_credentials(client, app):
    """7. Login fails with invalid credentials."""
    with app.app_context():
        create_user('Fiona Gallagher', 'fiona@example.com', 'fiona', 'Pass1234!')

    # Wrong password
    res1 = client.post('/login', data={
        'identifier': 'fiona',
        'password': 'WrongPassword123'
    })
    assert res1.status_code == 401
    assert b"Invalid credentials" in res1.data

    # Non-existent user
    res2 = client.post('/login', data={
        'identifier': 'nonexistent_user',
        'password': 'Pass1234!'
    })
    assert res2.status_code == 401
    assert b"Invalid credentials" in res2.data


def test_logout_invalidates_session(client, app):
    """8. Logout invalidates the authenticated session."""
    with app.app_context():
        create_user('George Clark', 'george@example.com', 'george', 'Pass1234!')

    # Login
    client.post('/login', data={'identifier': 'george', 'password': 'Pass1234!'})

    # Access protected dashboard
    home_res = client.get('/')
    assert home_res.status_code == 200
    assert b"AI Resume &amp; Job Matching Engine" in home_res.data or b"AI Resume & Job Matching Engine" in home_res.data

    # Logout
    logout_res = client.get('/logout', follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"successfully logged out" in logout_res.data

    # Attempt to access protected dashboard after logout
    after_res = client.get('/', follow_redirects=False)
    assert after_res.status_code == 302
    assert '/login' in after_res.headers['Location']


def test_csrf_protection_enforcement(app):
    """12. CSRF protection works where applicable."""
    # Enable CSRF in a dedicated test client
    app.config['WTF_CSRF_ENABLED'] = True
    csrf_client = app.test_client()

    # POST to login without CSRF token should be rejected (400 or redirected with CSRF error)
    response = csrf_client.post('/login', data={
        'identifier': 'someone',
        'password': 'somepassword'
    }, follow_redirects=True)

    assert b"security session has expired or the form submission was invalid" in response.data or response.status_code == 400
