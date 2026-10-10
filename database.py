import sqlite3
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from flask import g, current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """User representation compliant with Flask-Login."""
    def __init__(self, id: int, full_name: str, email: str, username: str, 
                 password_hash: str, is_active: int = 1, is_admin: int = 0,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self._is_active = bool(is_active)
        self.is_admin = bool(is_admin)
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def is_active(self) -> bool:
        return self._is_active

    def get_id(self) -> str:
        return str(self.id)

    def check_password(self, password: str) -> bool:
        """Verify candidate password against securely stored scrypt/pbkdf2 hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Obtain database connection, utilizing Flask g context when available."""
    target_path = db_path
    if not target_path:
        if current_app:
            target_path = current_app.config.get('DATABASE_PATH')
        else:
            from config import Config
            target_path = Config.DATABASE_PATH

    # If within Flask app context and using the app's configured DB, store on g
    try:
        if current_app and target_path == current_app.config.get('DATABASE_PATH'):
            if 'db' not in g:
                conn = sqlite3.connect(target_path)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                g.db = conn
            return g.db
    except RuntimeError:
        # Working outside of application context
        pass

    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def close_db(e=None):
    """Close connection at the end of Flask request context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(db_path: Optional[str] = None):
    """Initialize database tables with constraints and indexes."""
    conn = get_db(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE,
                username TEXT NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS resume_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                job_description TEXT NOT NULL,
                match_score REAL NOT NULL,
                analysis_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_resume_matches_user_id ON resume_matches(user_id);")

        # Safe schema migration: check if analysis_json column exists
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(resume_matches);")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'analysis_json' not in columns:
            conn.execute("ALTER TABLE resume_matches ADD COLUMN analysis_json TEXT;")

    # If this was a standalone connection outside g, close it
    try:
        if not (current_app and 'db' in g and conn == g.db):
            conn.close()
    except RuntimeError:
        conn.close()


def row_to_user(row: Optional[sqlite3.Row]) -> Optional[User]:
    """Convert a sqlite3.Row to a User instance."""
    if row is None:
        return None
    return User(
        id=row['id'],
        full_name=row['full_name'],
        email=row['email'],
        username=row['username'],
        password_hash=row['password_hash'],
        is_active=row['is_active'],
        is_admin=row['is_admin'],
        created_at=row['created_at'],
        updated_at=row['updated_at']
    )


def create_user(full_name: str, email: str, username: str, password: str, 
                is_admin: int = 0, db_path: Optional[str] = None) -> User:
    """Create a new user with securely hashed password."""
    norm_email = email.strip().lower()
    norm_username = username.strip()
    clean_name = full_name.strip()
    
    # Modern memory-hard scrypt hash
    hashed = generate_password_hash(password, method='scrypt')
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (full_name, email, username, password_hash, is_active, is_admin, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """, (clean_name, norm_email, norm_username, hashed, is_admin, now, now))
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id, db_path=db_path)
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[User]:
    """Fetch user by primary key ID."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[User]:
    """Fetch user by normalized email."""
    norm_email = email.strip().lower()
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (norm_email,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_user_by_username(username: str, db_path: Optional[str] = None) -> Optional[User]:
    """Fetch user by normalized username."""
    norm_username = username.strip()
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (norm_username,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_user_by_username_or_email(identifier: str, db_path: Optional[str] = None) -> Optional[User]:
    """Fetch user by either their username or email."""
    norm_identifier = identifier.strip().lower()
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users 
            WHERE LOWER(username) = ? OR LOWER(email) = ?
        """, (norm_identifier, norm_identifier))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def update_user_password(user_id: int, new_password: str, db_path: Optional[str] = None) -> bool:
    """Update user password using secure scrypt hash."""
    hashed = generate_password_hash(new_password, method='scrypt')
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
        """, (hashed, now, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def save_match_result(user_id: int, original_filename: str, stored_filename: str,
                      job_description: str, match_score: float, analysis_json: Optional[str] = None,
                      db_path: Optional[str] = None) -> int:
    """Persist a resume analysis result linked to the authenticated user ID."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resume_matches (user_id, original_filename, stored_filename, job_description, match_score, analysis_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, original_filename, stored_filename, job_description, match_score, analysis_json))
        conn.commit()
        return cursor.lastrowid
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_user_matches(user_id: int, limit: int = 15, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve match history strictly owned by the specified user."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, original_filename, stored_filename, job_description, match_score, analysis_json, created_at
            FROM resume_matches
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def get_match_by_id_and_user(match_id: int, user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a specific match result enforcing user ownership."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, original_filename, stored_filename, job_description, match_score, analysis_json, created_at
            FROM resume_matches
            WHERE id = ? AND user_id = ?
        """, (match_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()


def delete_match(match_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a match record ensuring user ownership."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM resume_matches
            WHERE id = ? AND user_id = ?
        """, (match_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        try:
            if not (current_app and 'db' in g and conn == g.db):
                conn.close()
        except RuntimeError:
            conn.close()
