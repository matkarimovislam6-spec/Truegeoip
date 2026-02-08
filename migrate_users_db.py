#!/usr/bin/env python3
"""
Migrate users.db (SQLite) to PostgreSQL
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

# Configuration
SQLITE_DB = "users.db"
PG_HOST = os.getenv("PG_HOST", "/tmp")
PG_DB = os.getenv("PG_DATABASE", "truegeoip")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "Islam1717@")

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )

def main():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found.")
        return

    print(f"Migrating {SQLITE_DB} to PostgreSQL...")
    
    # Connect
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = get_pg_connection()
    pg_cur = pg_conn.cursor()
    
    # Enable foreign keys
    # pg_cur.execute("SET session_replication_role = 'replica';") # Option to disable triggers/FKs temporarily

    # 1. Migrate Users
    print("Migrating users...")
    # Create table if not exists (matching schema from auth.py)
    pg_cur.execute("""
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
    """)
    
    users = sqlite_conn.execute("SELECT * FROM users").fetchall()
    if users:
        # Get columns dynamically
        columns = users[0].keys()
        # id explicitly inserted to maintain relationships
        cols_str = ", ".join(columns)
        vals_str = ", ".join(["%s"] * len(columns))
        
        data = [tuple(user) for user in users]
        
        # PostgreSQL specific: handle INSERT ... ON CONFLICT to avoid duplicates on re-run
        # But for migration, we might just truncate or ensure empty
        # For simplicity, we'll try INSERT and ignore conflicts on ID, or just truncate first
        pg_cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        
        execute_values(pg_cur, f"INSERT INTO users ({cols_str}) VALUES %s", data)
        print(f"  ✓ {len(users)} users migrated")
        
        # Reset sequence
        if users:
             max_id = max(u["id"] for u in users)
             pg_cur.execute(f"SELECT setval('users_id_seq', {max_id}, true)")

    # 2. Migrate Projects
    print("Migrating projects...")
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    projects = sqlite_conn.execute("SELECT * FROM projects").fetchall()
    if projects:
        columns = projects[0].keys()
        cols_str = ", ".join(columns)
        data = [tuple(p) for p in projects]
        pg_cur.execute("TRUNCATE TABLE projects CASCADE;")
        execute_values(pg_cur, f"INSERT INTO projects ({cols_str}) VALUES %s", data)
        print(f"  ✓ {len(projects)} projects migrated")

    # 3. Migrate API Keys
    print("Migrating api_keys...")
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
    """)
    
    keys = sqlite_conn.execute("SELECT * FROM api_keys").fetchall()
    if keys:
        columns = keys[0].keys()
        cols_str = ", ".join(columns)
        data = [tuple(k) for k in keys]
        pg_cur.execute("TRUNCATE TABLE api_keys RESTART IDENTITY CASCADE;") # api_keys usually has ID
        execute_values(pg_cur, f"INSERT INTO api_keys ({cols_str}) VALUES %s", data)
        print(f"  ✓ {len(keys)} api_keys migrated")
        
        max_id = max(k["id"] for k in keys) if keys else 0
        if max_id:
            pg_cur.execute(f"SELECT setval('api_keys_id_seq', {max_id}, true)")

    # 4. Migrate Licenses
    print("Migrating licenses...")
    pg_cur.execute("""
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
    """)
    
    # Check if licenses table exists in SQLite
    try:
        licenses = sqlite_conn.execute("SELECT * FROM licenses").fetchall()
        if licenses:
            columns = licenses[0].keys()
            cols_str = ", ".join(columns)
            data = [tuple(l) for l in licenses]
            pg_cur.execute("TRUNCATE TABLE licenses RESTART IDENTITY CASCADE;")
            execute_values(pg_cur, f"INSERT INTO licenses ({cols_str}) VALUES %s", data)
            print(f"  ✓ {len(licenses)} licenses migrated")
            
            max_id = max(l["id"] for l in licenses) if licenses else 0
            if max_id:
                pg_cur.execute(f"SELECT setval('licenses_id_seq', {max_id}, true)")
    except sqlite3.OperationalError:
        print("  (licenses table not found in SQLite, skipping)")

    # Create Indexes
    print("Creating indexes...")
    pg_cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);")

    pg_conn.commit()
    pg_conn.close()
    sqlite_conn.close()
    
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    main()
