#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates databasefull.sqlite to PostgreSQL database 'truegeoip'
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
from datetime import datetime

# Configuration
SQLITE_DB = "databasefull.sqlite"
PG_HOST = "/tmp"
PG_DB = "truegeoip"
PG_USER = "postgres"
PG_PASSWORD = "Islam1717@"
BATCH_SIZE = 10000

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_DB)

# PostgreSQL schema - converted from SQLite
PG_SCHEMA = """
-- Drop tables if they exist (for clean migration)
DROP TABLE IF EXISTS analytics_aggregates_daily CASCADE;
DROP TABLE IF EXISTS analytics_aggregates_hourly CASCADE;
DROP TABLE IF EXISTS analytics_events CASCADE;
DROP TABLE IF EXISTS threat_level CASCADE;
DROP TABLE IF EXISTS user_type CASCADE;
DROP TABLE IF EXISTS iptwo_new CASCADE;
DROP TABLE IF EXISTS crawler_ranges CASCADE;
DROP TABLE IF EXISTS elevation_lookup CASCADE;
DROP TABLE IF EXISTS vpn_ranges CASCADE;
DROP TABLE IF EXISTS vpn_overrides CASCADE;
DROP TABLE IF EXISTS fallback_city CASCADE;
DROP TABLE IF EXISTS asn_lookup CASCADE;
DROP TABLE IF EXISTS city_layer CASCADE;
DROP TABLE IF EXISTS country_dial CASCADE;
DROP TABLE IF EXISTS country_currency CASCADE;
DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS ip_ranges CASCADE;

-- Create tables
CREATE TABLE ip_ranges (
    start_ip BIGINT NOT NULL,
    end_ip BIGINT NOT NULL,
    country TEXT,
    netname TEXT,
    org TEXT,
    source TEXT,
    is_vpn BOOLEAN DEFAULT FALSE
);

CREATE TABLE countries (
    alpha2 TEXT PRIMARY KEY,
    alpha3 TEXT,
    numeric INTEGER,
    name_short TEXT,
    name_long TEXT
);

CREATE TABLE country_currency (
    country_code TEXT PRIMARY KEY,
    country_name TEXT,
    currency_name TEXT,
    currency_code TEXT
);

CREATE TABLE country_dial (
    country_code TEXT PRIMARY KEY,
    dial_code TEXT
);

CREATE TABLE city_layer (
    network TEXT,
    continent_code TEXT,
    continent_name TEXT,
    country_iso_code TEXT,
    country_name TEXT,
    subdivision_1_iso_code TEXT,
    subdivision_1_name TEXT,
    city_name TEXT,
    metro_code INTEGER,
    time_zone TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    accuracy_radius INTEGER,
    start_ip TEXT,
    end_ip TEXT,
    is_multicast INTEGER DEFAULT 0,
    is_fallback INTEGER DEFAULT 0,
    is_crawler BOOLEAN DEFAULT FALSE,
    netname TEXT,
    org TEXT,
    asn TEXT,
    source TEXT,
    utc_offset TEXT,
    zip_code TEXT
);

CREATE TABLE asn_lookup (
    start_ip TEXT,
    end_ip TEXT,
    asn TEXT,
    name TEXT,
    org TEXT,
    domain TEXT,
    country_code TEXT
);

CREATE TABLE fallback_city (
    country_code TEXT PRIMARY KEY,
    capital_city TEXT
);

CREATE TABLE vpn_overrides (
    ip TEXT PRIMARY KEY
);

CREATE TABLE vpn_ranges (
    start_ip TEXT,
    end_ip TEXT,
    PRIMARY KEY (start_ip, end_ip)
);

CREATE TABLE elevation_lookup (
    latitude REAL,
    longitude REAL,
    elevation REAL,
    PRIMARY KEY (latitude, longitude)
);

CREATE TABLE crawler_ranges (
    start_ip TEXT PRIMARY KEY,
    end_ip TEXT,
    bot_name TEXT,
    cidr TEXT
);

CREATE TABLE iptwo_new (
    ip_from BIGINT,
    ip_to BIGINT,
    country_code TEXT,
    country_name TEXT,
    region TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    zipcode TEXT,
    utc_offset TEXT,
    start_ip TEXT,
    end_ip TEXT
);

CREATE TABLE user_type (
    start_ip TEXT,
    end_ip TEXT,
    ip_type TEXT
);

CREATE TABLE analytics_events (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    hashed_ip TEXT NOT NULL,
    country_code TEXT,
    country_name TEXT,
    city TEXT,
    region TEXT,
    asn TEXT,
    asn_name TEXT,
    netname TEXT,
    is_datacenter INTEGER DEFAULT 0,
    is_vpn INTEGER DEFAULT 0,
    user_type TEXT,
    path TEXT,
    method TEXT,
    status_code INTEGER,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE analytics_aggregates_hourly (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    hour TEXT NOT NULL,
    country_code TEXT,
    asn TEXT,
    is_datacenter INTEGER,
    is_vpn INTEGER,
    request_count INTEGER DEFAULT 0,
    unique_ip_estimate INTEGER DEFAULT 0,
    UNIQUE(project_id, hour, country_code, asn, is_datacenter, is_vpn)
);

CREATE TABLE analytics_aggregates_daily (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    date TEXT NOT NULL,
    country_code TEXT,
    asn TEXT,
    netname TEXT,
    request_count INTEGER DEFAULT 0,
    unique_ip_estimate INTEGER DEFAULT 0,
    vpn_count INTEGER DEFAULT 0,
    datacenter_count INTEGER DEFAULT 0,
    UNIQUE(project_id, date, country_code, asn)
);

CREATE TABLE threat_level (
    start_ip TEXT,
    end_ip TEXT,
    threat_level TEXT
);
"""

PG_INDEXES = """
-- Create indexes
CREATE INDEX idx_ip ON ip_ranges (start_ip, end_ip);
CREATE INDEX idx_ip_ranges_start_ip ON ip_ranges(start_ip);

CREATE INDEX idx_city_ip_hex ON city_layer (start_ip, end_ip);
CREATE INDEX idx_city_start_end ON city_layer(start_ip, end_ip);
CREATE INDEX idx_city_layer_start_ip ON city_layer(start_ip);

CREATE INDEX idx_asn_ip_hex ON asn_lookup (start_ip, end_ip);
CREATE INDEX idx_asn_start_end ON asn_lookup(start_ip, end_ip);
CREATE INDEX idx_asn_lookup_start_ip ON asn_lookup(start_ip);

CREATE INDEX idx_crawler_start_ip ON crawler_ranges(start_ip);

CREATE INDEX idx_iptwo_new_ip ON iptwo_new(start_ip, end_ip);

CREATE INDEX idx_user_type_range ON user_type(start_ip, end_ip);
CREATE INDEX idx_user_type_start_ip ON user_type(start_ip);

CREATE INDEX idx_threat_level_start ON threat_level(start_ip);
CREATE INDEX idx_threat_level_end ON threat_level(end_ip);
CREATE INDEX idx_threat_level_start_ip ON threat_level(start_ip);

CREATE INDEX idx_vpn_ranges_start_ip ON vpn_ranges(start_ip);

CREATE INDEX idx_elevation_lookup_lat_lon ON elevation_lookup(latitude, longitude);

CREATE INDEX idx_events_project_ts ON analytics_events(project_id, timestamp);
CREATE INDEX idx_events_created ON analytics_events(created_at);
CREATE INDEX idx_hourly_project ON analytics_aggregates_hourly(project_id, hour);
CREATE INDEX idx_daily_project ON analytics_aggregates_daily(project_id, date);
"""

# Table migration order and mapping
TABLES = [
    # (sqlite_table_name, pg_table_name, column_list or None for *)
    ("countries", "countries", None),
    ("country_currency", "country_currency", None),
    ("country_dial", "country_dial", None),
    ("fallback_city", "fallback_city", None),
    ("vpn_overrides", "vpn_overrides", None),
    ("vpn_ranges", "vpn_ranges", None),
    ("elevation_lookup", "elevation_lookup", None),
    ("crawler_ranges", "crawler_ranges", None),
    ("ip_ranges", "ip_ranges", None),
    ("City_layer", "city_layer", None),
    ("asn_lookup", "asn_lookup", None),
    ("iptwo_new", "iptwo_new", None),
    ("user_type", "user_type", None),
    ("Threat_level", "threat_level", None),
    ("analytics_events", "analytics_events", "project_id, timestamp, hashed_ip, country_code, country_name, city, region, asn, asn_name, netname, is_datacenter, is_vpn, user_type, path, method, status_code, metadata, created_at"),
    ("analytics_aggregates_hourly", "analytics_aggregates_hourly", "project_id, hour, country_code, asn, is_datacenter, is_vpn, request_count, unique_ip_estimate"),
    ("analytics_aggregates_daily", "analytics_aggregates_daily", "project_id, date, country_code, asn, netname, request_count, unique_ip_estimate, vpn_count, datacenter_count"),
]

def migrate_table(sqlite_conn, pg_conn, sqlite_table, pg_table, columns=None):
    """Migrate a single table from SQLite to PostgreSQL"""
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()
    
    # Get row count
    sqlite_cur.execute(f"SELECT COUNT(*) FROM {sqlite_table}")
    total_rows = sqlite_cur.fetchone()[0]
    
    if total_rows == 0:
        log(f"  {sqlite_table}: empty, skipping")
        return
    
    log(f"  {sqlite_table} -> {pg_table}: {total_rows:,} rows")
    
    # Get column names if not specified
    if columns is None:
        sqlite_cur.execute(f"PRAGMA table_info({sqlite_table})")
        columns = ",".join([row[1] for row in sqlite_cur.fetchall()])
    
    col_list = [c.strip() for c in columns.split(",")]
    placeholders = ",".join(["%s"] * len(col_list))
    insert_sql = f"INSERT INTO {pg_table} ({columns}) VALUES ({placeholders})"
    
    # Migrate in batches
    offset = 0
    migrated = 0
    
    while offset < total_rows:
        sqlite_cur.execute(f"SELECT {columns} FROM {sqlite_table} LIMIT {BATCH_SIZE} OFFSET {offset}")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            break
        
        # Use execute_values for faster insertion
        execute_values(
            pg_cur,
            f"INSERT INTO {pg_table} ({columns}) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )
        pg_conn.commit()
        
        migrated += len(rows)
        offset += BATCH_SIZE
        
        # Progress update every 100k rows
        if migrated % 100000 == 0 or migrated == total_rows:
            pct = (migrated / total_rows) * 100
            log(f"    Progress: {migrated:,}/{total_rows:,} ({pct:.1f}%)")
    
    log(f"    ✓ Completed: {migrated:,} rows")

def main():
    log("=" * 60)
    log("SQLite to PostgreSQL Migration")
    log("=" * 60)
    
    # Connect to databases
    log("Connecting to databases...")
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_pg_connection()
    pg_cur = pg_conn.cursor()
    
    # Create schema
    log("Creating PostgreSQL schema...")
    pg_cur.execute(PG_SCHEMA)
    pg_conn.commit()
    log("  ✓ Schema created")
    
    # Migrate tables
    log("\nMigrating tables...")
    for sqlite_table, pg_table, columns in TABLES:
        try:
            migrate_table(sqlite_conn, pg_conn, sqlite_table, pg_table, columns)
        except Exception as e:
            log(f"  ✗ Error migrating {sqlite_table}: {e}")
            pg_conn.rollback()
    
    # Create indexes
    log("\nCreating indexes...")
    for idx_stmt in PG_INDEXES.strip().split(";"):
        if idx_stmt.strip():
            try:
                pg_cur.execute(idx_stmt)
                pg_conn.commit()
            except Exception as e:
                log(f"  Warning: {e}")
    log("  ✓ Indexes created")
    
    # Verify migration
    log("\nVerifying migration...")
    for sqlite_table, pg_table, _ in TABLES:
        sqlite_conn.execute(f"SELECT COUNT(*) FROM {sqlite_table}")
        sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {sqlite_table}").fetchone()[0]
        
        pg_cur.execute(f"SELECT COUNT(*) FROM {pg_table}")
        pg_count = pg_cur.fetchone()[0]
        
        status = "✓" if sqlite_count == pg_count else "✗"
        log(f"  {status} {pg_table}: SQLite={sqlite_count:,}, PostgreSQL={pg_count:,}")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    log("\n" + "=" * 60)
    log("Migration completed!")
    log("=" * 60)
    log(f"\nPostgreSQL connection string:")
    log(f"  postgresql://{PG_USER}:{PG_PASSWORD}@localhost/{PG_DB}")

if __name__ == "__main__":
    main()
