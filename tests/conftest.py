import os
import tempfile
import pytest
from app import create_app
from database import init_db
from config import TestingConfig

@pytest.fixture
def app():
    """Create and configure a new app instance for each test with isolated DB."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    upload_dir = tempfile.mkdtemp()

    class TestConfig(TestingConfig):
        DATABASE_PATH = db_path
        UPLOAD_FOLDER = upload_dir
        WTF_CSRF_ENABLED = False  # Disabled by default in tests for convenience, can be enabled per-test
        LOGIN_RATE_LIMIT_ATTEMPTS = 5
        LOGIN_RATE_LIMIT_WINDOW_SECONDS = 900
        REGISTER_RATE_LIMIT_ATTEMPTS = 10
        REGISTER_RATE_LIMIT_WINDOW_SECONDS = 3600

    test_app = create_app(TestConfig)

    with test_app.app_context():
        init_db(db_path)

    yield test_app

    # Cleanup temporary resources
    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
