"""
Authentication module for IP Intelligence.
Handles user database, password hashing, sessions, and Google OAuth.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Database file
USERS_DB = "users.db"

# OAuth configuration
config = Config(environ=os.environ)
oauth = OAuth()

# Register Google OAuth client
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    # server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Email delivery configuration
import aiosmtplib
import httpx
from email.message import EmailMessage


def _build_verification_email_text(code: str) -> str:
    return f"""
Hello,

Your verification code is: {code}

Please enter this code to verify your account.

Best regards,
TrueGeoIP Team
    """.strip()


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def _send_with_resend(to_email: str, code: str) -> bool:
    resend_api_key = (os.getenv("RESEND_API_KEY", "") or "").strip()
    resend_from = (os.getenv("RESEND_FROM", "onboarding@resend.dev") or "").strip()
    resend_api_url = (os.getenv("RESEND_API_URL", "https://api.resend.com/emails") or "").strip()
    resend_reply_to = (os.getenv("RESEND_REPLY_TO", "") or "").strip()

    placeholder_keys = {"", "your-resend-api-key-here"}
    if resend_api_key in placeholder_keys:
        return False

    payload = {
        "from": resend_from,
        "to": [to_email],
        "subject": "Verify your account - TrueGeoIP",
        "text": _build_verification_email_text(code),
    }
    if resend_reply_to:
        payload["reply_to"] = resend_reply_to

    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(resend_api_url, json=payload, headers=headers)
        if 200 <= response.status_code < 300:
            return True
        print(
            f"Resend email delivery failed ({response.status_code}) for {to_email}: "
            f"{response.text[:240]}"
        )
    except Exception as e:
        print(f"Resend email delivery error for {to_email}: {e}")

    return False


async def _send_with_smtp(to_email: str, code: str) -> bool:
    smtp_server = (os.getenv("SMTP_SERVER", "smtp.gmail.com") or "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_user = (os.getenv("SMTP_USER", "") or "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "") or ""
    smtp_from = (os.getenv("SMTP_FROM", smtp_user) or smtp_user).strip()

    # Auto-pick common TLS mode unless explicitly configured.
    smtp_use_tls_env = (os.getenv("SMTP_USE_TLS", "") or "").strip()
    smtp_starttls_env = (os.getenv("SMTP_STARTTLS", "") or "").strip()
    smtp_use_tls = _is_truthy(smtp_use_tls_env)
    smtp_starttls = _is_truthy(smtp_starttls_env)

    if not smtp_use_tls_env and not smtp_starttls_env:
        if smtp_port == 465:
            smtp_use_tls = True
            smtp_starttls = False
        else:
            smtp_use_tls = False
            smtp_starttls = True

    placeholder_users = {"", "your-email@gmail.com"}
    placeholder_passwords = {"", "your-app-password-here"}
    if smtp_user in placeholder_users or smtp_password.strip() in placeholder_passwords:
        return False

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = "Verify your account - TrueGeoIP"
    message.set_content(_build_verification_email_text(code))

    passwords_to_try = [smtp_password]
    compact_password = smtp_password.replace(" ", "")
    if compact_password != smtp_password:
        passwords_to_try.append(compact_password)

    last_error = None
    for password_value in passwords_to_try:
        try:
            await aiosmtplib.send(
                message,
                hostname=smtp_server,
                port=smtp_port,
                use_tls=smtp_use_tls,
                start_tls=smtp_starttls,
                username=smtp_user,
                password=password_value,
                timeout=20
            )
            return True
        except Exception as e:
            last_error = e

    print(f"SMTP email delivery failed for {to_email}: {last_error}")
    return False


async def send_verification_email(to_email: str, code: str):
    """Send a verification email with the code."""
    provider = (os.getenv("EMAIL_PROVIDER", "auto") or "auto").strip().lower()
    if provider not in {"auto", "resend", "smtp"}:
        provider = "auto"

    # Production-like default: transactional provider first, SMTP fallback.
    if provider in {"auto", "resend"}:
        if await _send_with_resend(to_email, code):
            return True
        if provider == "resend":
            return False

    if provider in {"auto", "smtp"}:
        if await _send_with_smtp(to_email, code):
            return True

    print(
        "Email delivery is not configured. Set RESEND_API_KEY (recommended) "
        "or SMTP_USER/SMTP_PASSWORD in .env and restart the server."
    )
    return False


import random
import string
import uuid

# ... imports ...

def init_db():
    """Initialize the users database."""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT,
            google_id TEXT,
            verification_code TEXT,
            is_verified INTEGER DEFAULT 0,
            api_key TEXT UNIQUE,
            api_requests_count INTEGER DEFAULT 0,
            last_api_usage_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Check if columns exist
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "is_verified" not in columns:
        print("Migrating database: adding is_verified column")
        conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        conn.execute("UPDATE users SET is_verified = 1") # Mark existing users as verified
    
    if "verification_code" not in columns:
        print("Migrating database: adding verification_code column")
        conn.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")

    if "api_key" not in columns:
        print("Migrating database: adding api_key column")
        conn.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
        # Generate keys for existing users
        existing_users = conn.execute("SELECT id FROM users").fetchall()
        for user in existing_users:
            new_key = str(uuid.uuid4())
            conn.execute("UPDATE users SET api_key = ? WHERE id = ?", (new_key, user[0]))
        # Add index after populating data
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")
    
    if "api_requests_count" not in columns:
        print("Migrating database: adding api_requests_count column")
        conn.execute("ALTER TABLE users ADD COLUMN api_requests_count INTEGER DEFAULT 0")

    if "last_api_usage_date" not in columns:
        print("Migrating database: adding last_api_usage_date column")
        conn.execute("ALTER TABLE users ADD COLUMN last_api_usage_date TEXT")
    
    conn.commit()
    conn.close()
    print(f"Users database initialized: {USERS_DB}")


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    return conn


# Password functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def generate_code(length=6):
    """Generate a random verification code."""
    return ''.join(random.choices(string.digits, k=length))

# User CRUD operations
def create_user(email: str, password: str, name: str = None) -> Optional[Dict[str, Any]]:
    """Create a new user with email/password (unverified)."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        verification_code = generate_code()
        api_key = str(uuid.uuid4())
        
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, verification_code, is_verified, api_key) VALUES (?, ?, ?, ?, 0, ?)",
            (email.lower(), password_hash, name or email.split('@')[0], verification_code, api_key)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return {
            "id": user_id, 
            "email": email.lower(), 
            "name": name or email.split('@')[0],
            "verification_code": verification_code,
            "api_key": api_key
        }
    except sqlite3.IntegrityError:
        conn.close()
        return None  # Email already exists

def verify_user_email(email: str, code: str) -> bool:
    """Verify user email with code."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND verification_code = ?",
        (email.lower(), code)
    )
    user = cursor.fetchone()
    
    if user:
        cursor.execute("UPDATE users SET is_verified = 1, verification_code = NULL WHERE id = ?", (user['id'],))
        conn.commit()
        conn.close()
        return True
        
    conn.close()
    return False

def get_db_user_by_email(email: str): # Helper to avoid circular deps if needed
    return get_user_by_email(email)



def create_or_get_google_user(email: str, google_id: str, name: str) -> Dict[str, Any]:
    """Create or get a user from Google OAuth."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists by google_id or email
    cursor.execute(
        "SELECT * FROM users WHERE google_id = ? OR email = ?",
        (google_id, email.lower())
    )
    row = cursor.fetchone()
    
    if row:
        # Update google_id if not set (user registered with email first)
        if not row['google_id']:
            cursor.execute(
                "UPDATE users SET google_id = ?, name = ? WHERE email = ?",
                (google_id, name, email.lower())
            )
            conn.commit()
        conn.close()
        return {"id": row['id'], "email": row['email'], "name": row['name'] or name}
    
    # Create new user
    api_key = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (email, google_id, name, api_key) VALUES (?, ?, ?, ?)",
        (email.lower(), google_id, name, api_key)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "email": email.lower(), "name": name}


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get a user by email."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get a user by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_user_name(user_id: int, name: str) -> bool:
    """Update the display name for a user."""
    clean_name = (name or "").strip()
    if not clean_name:
        return False

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE id = ?", (clean_name, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def delete_user_account(user_id: int) -> Dict[str, Any]:
    """
    Delete a user and related records in users.db.
    Returns metadata including affected project IDs for downstream cleanup.
    """
    conn = get_db()
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        project_rows = cursor.execute(
            "SELECT id FROM projects WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        project_ids = [row["id"] for row in project_rows]

        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            cursor.execute(f"DELETE FROM api_keys WHERE project_id IN ({placeholders})", project_ids)
            cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)

        cursor.execute("DELETE FROM licenses WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        deleted_user = cursor.rowcount > 0

        conn.commit()
        return {"deleted": deleted_user, "project_ids": project_ids}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with email/password."""
    user = get_user_by_email(email)
    
    if not user:
        return None
    
    if not user.get('password_hash'):
        return None  # OAuth-only user
    
    if not verify_password(password, user['password_hash']):
        return None
    
    return {"id": user['id'], "email": user['email'], "name": user['name']}


# Initialize database on import
init_db()
