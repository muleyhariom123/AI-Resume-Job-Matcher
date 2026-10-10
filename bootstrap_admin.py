"""
Secure Administrator Bootstrap Script
====================================
Safely creates or upgrades an administrator account without hardcoding credentials.
Supports both non-interactive environment variables and interactive CLI prompts.

Usage via environment variables:
    $env:ADMIN_FULL_NAME="System Administrator"
    $env:ADMIN_EMAIL="admin@yourdomain.com"
    $env:ADMIN_USERNAME="sysadmin"
    $env:ADMIN_PASSWORD="YourStrongPassword123!"
    python bootstrap_admin.py

Usage via interactive prompt:
    python bootstrap_admin.py
"""

import os
import sys
import getpass
from config import Config
from database import init_db, get_user_by_username, get_user_by_email, create_user, get_db
from security import validate_registration_input, normalize_email

def bootstrap_admin():
    print("=" * 60)
    print("AI Resume Matcher - Administrator Account Provisioning")
    print("=" * 60)

    # Ensure database schema exists
    init_db()

    # Read from environment variables if present
    full_name = os.environ.get('ADMIN_FULL_NAME')
    email = os.environ.get('ADMIN_EMAIL')
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')

    # If not in environment, prompt interactively
    if not (full_name and email and username and password):
        print("\n[Interactive Mode] Enter administrator details below:")
        try:
            full_name = input("Full Name [Administrator]: ").strip() or "Administrator"
            email = input("Admin Email: ").strip()
            username = input("Admin Username: ").strip()
            password = getpass.getpass("Admin Password (min 8 chars): ")
            confirm = getpass.getpass("Confirm Admin Password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

        if password != confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)
    else:
        print("\n[Environment Mode] Using configuration from environment variables.")

    # Validate inputs
    is_valid, error = validate_registration_input(
        full_name=full_name,
        email=email,
        username=username,
        password=password,
        confirm_password=password,
        terms_accepted=True
    )
    if not is_valid:
        print(f"Validation Error: {error}")
        sys.exit(1)

    norm_email = normalize_email(email)

    # Check if user already exists
    existing_user = get_user_by_username(username) or get_user_by_email(norm_email)
    if existing_user:
        print(f"User '{existing_user.username}' ({existing_user.email}) already exists.")
        conn = get_db()
        try:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (existing_user.id,))
            conn.commit()
            print(f"Successfully granted administrator privileges to '{existing_user.username}'.")
        finally:
            conn.close()
        return

    # Create new administrator
    try:
        user = create_user(
            full_name=full_name,
            email=norm_email,
            username=username,
            password=password,
            is_admin=1
        )
        print(f"\n[SUCCESS] Administrator account created successfully:")
        print(f"  User ID : {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email   : {user.email}")
        print("  Status  : Active (Admin privileges enabled)")
    except Exception as e:
        print(f"\n[ERROR] Failed to provision administrator: {e}")
        sys.exit(1)

if __name__ == '__main__':
    bootstrap_admin()
