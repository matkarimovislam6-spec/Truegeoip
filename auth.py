"""
Authentication module for IP Intelligence.
Handles user database, password hashing, sessions, and Google OAuth.
"""

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
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

# PostgreSQL Configuration
PG_HOST = os.getenv("PG_HOST", "/tmp")
PG_API_DB = os.getenv("PG_DATABASE", "truegeoip")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "Islam1717@")

# We'll use a pool if initialized by main.py, otherwise create new connections
pg_pool = None

def get_db_connection():
    if pg_pool:
        return pg_pool.getconn()
    return psycopg2.connect(
        host=PG_HOST,
        database=PG_API_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        options="-c search_path=app,analytics,lookup,public"
    )

def release_db_connection(conn):
    if pg_pool:
        pg_pool.putconn(conn)
    else:
        conn.close()

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
True Geo IP Team
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
        "subject": "Verify your account - True Geo IP",
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
    message["Subject"] = "Verify your account - True Geo IP"
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
    # Tables are now managed via migration scripts or manual setup.
    # This function checks connectivity and essential tables for startup.
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("""
            SELECT exists(
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if not exists:
            # Basic schema creation if missing (failsafe)
            print("Creating users table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    name TEXT,
                    google_id TEXT,
                    verification_code TEXT,
                    is_verified INTEGER DEFAULT 0,
                    api_key TEXT UNIQUE,
                    api_requests_count INTEGER DEFAULT 0,
                    last_api_usage_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    plan TEXT DEFAULT 'free'
                );
            ''')
            
            print("Creating projects table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            ''')
            
            print("Creating api_keys table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    project_id TEXT NOT NULL,
                    name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                );
            ''')
            
            print("Creating licenses table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    license_key TEXT UNIQUE NOT NULL,
                    plan_type TEXT DEFAULT 'annual_db',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_downloaded_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
            ''')
            
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);")
            conn.commit()
            print("Users database tables initialized.")
            
        cursor.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        release_db_connection(conn)



# Removed get_db as it was specific to SQLite. Use get_db_connection instead.



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
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        password_hash = hash_password(password)
        verification_code = generate_code()
        api_key = str(uuid.uuid4())
        
        # NOTE: Postgres uses boolean `is_verified`; keep it at default false.
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, verification_code, api_key) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (email.lower(), password_hash, name or email.split("@")[0], verification_code, api_key),
        )
        user_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        
        return {
            "id": user_id, 
            "email": email.lower(), 
            "name": name or email.split('@')[0],
            "verification_code": verification_code,
            "api_key": api_key
        }
    except psycopg2.IntegrityError:
        conn.rollback()
        return None  # Email already exists
    except Exception as e:
        print(f"Create user error: {e}")
        conn.rollback()
        return None
    finally:
        release_db_connection(conn)

def verify_user_email(email: str, code: str) -> bool:
    """Verify user email with code."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT id FROM users WHERE email = %s AND verification_code = %s",
            (email.lower(), code)
        )
        user = cursor.fetchone()
        
        if user:
            cursor.execute(
                "UPDATE users SET is_verified = TRUE, verification_code = NULL WHERE id = %s",
                (user["id"],),
            )
            conn.commit()
            cursor.close()
            return True
        
        cursor.close()
        return False
    finally:
        release_db_connection(conn)

def create_or_get_google_user(email: str, google_id: str, name: str) -> Dict[str, Any]:
    """Create or get a user from Google OAuth."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user exists by google_id or email
        cursor.execute(
            "SELECT * FROM users WHERE google_id = %s OR email = %s",
            (google_id, email.lower())
        )
        row = cursor.fetchone()
        
        if row:
            # Update google_id if not set (user registered with email first)
            if not row['google_id']:
                cursor.execute(
                    "UPDATE users SET google_id = %s, name = %s WHERE email = %s",
                    (google_id, name, email.lower())
                )
                conn.commit()
            cursor.close()
            return {"id": row['id'], "email": row['email'], "name": row['name'] or name}
        
        # Create new user
        api_key = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO users (email, google_id, name, api_key, is_verified) "
            "VALUES (%s, %s, %s, %s, TRUE) RETURNING id",
            (email.lower(), google_id, name, api_key)
        )
        user_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        return {"id": user_id, "email": email.lower(), "name": name}
    finally:
        release_db_connection(conn)

def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Validate an API key and return project info.
    Returns None if invalid.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT ak.project_id, p.user_id, p.name as project_name, u.plan
            FROM api_keys ak
            JOIN projects p ON ak.project_id = p.id
            JOIN users u ON p.user_id = u.id
            WHERE ak.key = %s
        """, (api_key,))
        row = cursor.fetchone()
        
        if row:
            # Update last_used
            cursor.execute("UPDATE api_keys SET last_used = %s WHERE key = %s", 
                          (datetime.utcnow().isoformat(), api_key))
            conn.commit()
            cursor.close()
            return dict(row)
        
        cursor.close()
        return None
    finally:
        release_db_connection(conn)

def get_db_user_by_email(email: str): # Helper to avoid circular deps if needed
    return get_user_by_email(email)



def create_project(user_id: int, name: str) -> Dict[str, Any]:
    """Create a new project for a user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        project_id = generate_project_id()
        cursor.execute(
            "INSERT INTO projects (id, user_id, name) VALUES (%s, %s, %s)",
            (project_id, user_id, name)
        )
        
        # Also create a default API key
        api_key = generate_api_key()
        cursor.execute(
            "INSERT INTO api_keys (key, project_id, name) VALUES (%s, %s, %s)",
            (api_key, project_id, "Default Key")
        )
        conn.commit()
        cursor.close()
        
        return {"project_id": project_id, "api_key": api_key, "name": name}
    finally:
        release_db_connection(conn)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get a user by email."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None
    finally:
        release_db_connection(conn)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get a user by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None
    finally:
        release_db_connection(conn)


def update_user_name(user_id: int, name: str) -> bool:
    """Update the display name for a user."""
    clean_name = (name or "").strip()
    if not clean_name:
        return False

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = %s WHERE id = %s", (clean_name, user_id))
        conn.commit()
        updated = cursor.rowcount > 0
        cursor.close()
        return updated
    finally:
        release_db_connection(conn)


def delete_user_account(user_id: int) -> Dict[str, Any]:
    """
    Delete a user and related records in users.db.
    Returns metadata including affected project IDs for downstream cleanup.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # In PostgreSQL we can rely on CASCADE if configured, but to be safe and match logic:
        # Get project IDs
        cursor.execute("SELECT id FROM projects WHERE user_id = %s", (user_id,))
        project_rows = cursor.fetchall()
        project_ids = [row["id"] for row in project_rows]

        if project_ids:
            # Delete API keys and Projects
            # Note: execute(query, (tuple,)) requires tuple for IN clause in psycopg2?
            # Better to use ANY(%s) or build query manually safely
            cursor.execute("DELETE FROM api_keys WHERE project_id = ANY(%s)", (project_ids,))
            cursor.execute("DELETE FROM projects WHERE id = ANY(%s)", (project_ids,))

        cursor.execute("DELETE FROM licenses WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        deleted_user = cursor.rowcount > 0

        conn.commit()
        cursor.close()
        return {"deleted": deleted_user, "project_ids": project_ids}
    except Exception as e:
        print(f"Delete user error: {e}")
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)


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
