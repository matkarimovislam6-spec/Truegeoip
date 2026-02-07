
import sqlite3
import uuid
import datetime
import secrets

# Use the same DB as users for foreign key integrity
DB_FILE = "users.db"

def init_licenses_db():
    """Initialize the licenses table in users.db"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            license_key TEXT UNIQUE NOT NULL,
            plan_type TEXT DEFAULT 'annual_db',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            last_downloaded_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Licenses table initialized.")

def generate_license_key():
    """Generate a random license key (e.g. IPINT-XXXX-XXXX-XXXX)"""
    # 3 groups of 4 random hex characters
    random_part = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])
    return f"IPINT-{random_part}"

def create_license(user_id, plan_type='annual_db', duration_days=365):
    """Create a new license for a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    key = generate_license_key()
    expires_at = datetime.datetime.now() + datetime.timedelta(days=duration_days)
    
    try:
        cursor.execute(
            "INSERT INTO licenses (user_id, license_key, plan_type, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, key, plan_type, expires_at)
        )
        conn.commit()
        return key
    except sqlite3.Error as e:
        print(f"Error creating license: {e}")
        return None
    finally:
        conn.close()

def get_user_licenses(user_id):
    """Get all licenses for a user"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM licenses WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def validate_license(key):
    """
    Validate a license key for download.
    Returns (is_valid, message, license_obj)
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM licenses WHERE license_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, "Invalid license key", None
        
    license_data = dict(row)
    
    # Check status
    if license_data['status'] != 'active':
        return False, f"License is {license_data['status']}", None
        
    # Check expiry
    # Allow for string timestamp parsing if sqlite returns string
    expires_at_str = license_data['expires_at']
    if expires_at_str:
        expires_at = datetime.datetime.fromisoformat(expires_at_str) if isinstance(expires_at_str, str) else expires_at_str
        if datetime.datetime.now() > expires_at:
             return False, "License has expired", None

    return True, "Valid", license_data

def record_download(key):
    """Update last_downloaded_at timestamp"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE licenses SET last_downloaded_at = CURRENT_TIMESTAMP WHERE license_key = ?",
        (key,)
    )
    conn.commit()
    conn.close()

# Initialize on import
init_licenses_db()
