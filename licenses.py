import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
import uuid
import datetime
import secrets
import os

# PostgreSQL Configuration
PG_HOST = os.getenv("PG_HOST", "/tmp")
PG_API_DB = os.getenv("PG_DATABASE", "truegeoip")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "Islam1717@")

# We'll use a pool if initialized by main.py
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

def init_licenses_db():
    """Initialize the licenses table (managed by migration/auth.py in reality)."""
    # Just a placeholder or basic check
    pass

def generate_license_key():
    """Generate a random license key (e.g. IPINT-XXXX-XXXX-XXXX)"""
    # 3 groups of 4 random hex characters
    random_part = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])
    return f"IPINT-{random_part}"

def create_license(user_id, plan_type='annual_db', duration_days=365):
    """Create a new license for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        key = generate_license_key()
        expires_at = datetime.datetime.now() + datetime.timedelta(days=duration_days)
        
        cursor.execute(
            "INSERT INTO licenses (user_id, license_key, plan_type, expires_at) VALUES (%s, %s, %s, %s)",
            (user_id, key, plan_type, expires_at)
        )
        conn.commit()
        cursor.close()
        return key
    except Exception as e:
        print(f"Error creating license: {e}")
        return None
    finally:
        release_db_connection(conn)

def get_user_licenses(user_id):
    """Get all licenses for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM licenses WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]
    finally:
        release_db_connection(conn)

def validate_license(key):
    """
    Validate a license key for download.
    Returns (is_valid, message, license_obj)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (key,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return False, "Invalid license key", None
            
        license_data = dict(row)
        
        # Check status
        if license_data['status'] != 'active':
            return False, f"License is {license_data['status']}", None
            
        # Check expiry
        expires_at = license_data['expires_at']
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.datetime.fromisoformat(expires_at)
            
            if datetime.datetime.now() > expires_at:
                 return False, "License has expired", None
    
        return True, "Valid", license_data
    finally:
        release_db_connection(conn)

def record_download(key):
    """Update last_downloaded_at timestamp"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE licenses SET last_downloaded_at = CURRENT_TIMESTAMP WHERE license_key = %s",
            (key,)
        )
        conn.commit()
        cursor.close()
    finally:
        release_db_connection(conn)

# Initialize on import
init_licenses_db()
