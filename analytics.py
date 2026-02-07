"""
TrueGeoIP Analytics Module.
Privacy-first, server-side analytics for network traffic intelligence.
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

# Database files
ANALYTICS_DB = "ripe.sqlite"  # Use main DB for analytics tables
USERS_DB = "users.db"

# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------

def init_analytics_db():
    """Create analytics tables if they don't exist."""
    conn = sqlite3.connect(ANALYTICS_DB)
    cursor = conn.cursor()
    
    # Temporary event storage (24-72 hour retention)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    ''')
    
    # Hourly aggregates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics_aggregates_hourly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            hour TEXT NOT NULL,
            country_code TEXT,
            asn TEXT,
            is_datacenter INTEGER,
            is_vpn INTEGER,
            request_count INTEGER DEFAULT 0,
            unique_ip_estimate INTEGER DEFAULT 0,
            UNIQUE(project_id, hour, country_code, asn, is_datacenter, is_vpn)
        )
    ''')
    
    # Daily aggregates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics_aggregates_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_project_ts ON analytics_events(project_id, timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_created ON analytics_events(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hourly_project ON analytics_aggregates_hourly(project_id, hour)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_project ON analytics_aggregates_daily(project_id, date)')
    
    conn.commit()
    conn.close()
    print("Analytics tables initialized.")


def init_projects_db():
    """Create projects and api_keys tables in users.db."""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # API Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    
    # Add plan column to users if not exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "plan" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
        print("Added 'plan' column to users table.")
    
    conn.commit()
    conn.close()
    print("Projects and API keys tables initialized.")


# -----------------------------------------------------------------------------
# Privacy Functions
# -----------------------------------------------------------------------------

def hash_ip(ip: str, salt: str = "truegeoip-2026") -> str:
    """
    Create a privacy-safe hash of an IP address.
    Uses a daily rotating salt component for short-term deduplication.
    """
    daily_salt = datetime.utcnow().strftime("%Y-%m-%d")
    combined = f"{salt}:{daily_salt}:{ip}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


# -----------------------------------------------------------------------------
# Project & API Key Management
# -----------------------------------------------------------------------------

def generate_project_id() -> str:
    """Generate a unique project ID."""
    return f"proj_{secrets.token_hex(8)}"


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"ipint_{secrets.token_urlsafe(32)}"


def create_project(user_id: int, name: str) -> Dict[str, Any]:
    """Create a new project for a user."""
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    project_id = generate_project_id()
    cursor.execute(
        "INSERT INTO projects (id, user_id, name) VALUES (?, ?, ?)",
        (project_id, user_id, name)
    )
    conn.commit()
    
    # Also create a default API key
    api_key = generate_api_key()
    cursor.execute(
        "INSERT INTO api_keys (key, project_id, name) VALUES (?, ?, ?)",
        (api_key, project_id, "Default Key")
    )
    conn.commit()
    conn.close()
    
    return {"project_id": project_id, "api_key": api_key, "name": name}


def get_user_projects(user_id: int) -> List[Dict[str, Any]]:
    """Get all projects for a user."""
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_project_api_keys(project_id: str) -> List[Dict[str, Any]]:
    """Get all API keys for a project."""
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, key, name, created_at, last_used FROM api_keys WHERE project_id = ?", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Validate an API key and return project info.
    Returns None if invalid.
    """
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ak.project_id, p.user_id, p.name as project_name, u.plan
        FROM api_keys ak
        JOIN projects p ON ak.project_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE ak.key = ?
    """, (api_key,))
    row = cursor.fetchone()
    
    if row:
        # Update last_used
        cursor.execute("UPDATE api_keys SET last_used = ? WHERE key = ?", 
                      (datetime.utcnow().isoformat(), api_key))
        conn.commit()
        conn.close()
        return dict(row)
    
    conn.close()
    return None


# -----------------------------------------------------------------------------
# Event Ingestion
# -----------------------------------------------------------------------------

def ingest_event(
    project_id: str,
    ip: str,
    timestamp: str,
    ip_info: Dict[str, Any],
    path: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Ingest an analytics event with IP enrichment.
    Raw IP is hashed before storage for privacy.
    """
    conn = sqlite3.connect(ANALYTICS_DB)
    cursor = conn.cursor()
    
    # Hash the IP for privacy
    hashed_ip = hash_ip(ip)
    
    # Extract enriched data
    country_code = ip_info.get("country_code") or ip_info.get("country")
    country_name = ip_info.get("country_name") or ip_info.get("country_full")
    city = ip_info.get("city")
    region = ip_info.get("region")
    asn = str(ip_info.get("asn", "")) if ip_info.get("asn") else None
    asn_name = ip_info.get("asn_name")
    netname = ip_info.get("netname")
    is_datacenter = 1 if ip_info.get("is_datacenter") else 0
    is_vpn = 1 if ip_info.get("is_vpn") else 0
    user_type = ip_info.get("user_type")
    
    cursor.execute("""
        INSERT INTO analytics_events 
        (project_id, timestamp, hashed_ip, country_code, country_name, city, region,
         asn, asn_name, netname, is_datacenter, is_vpn, user_type, path, method, status_code, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id, timestamp, hashed_ip, country_code, country_name, city, region,
        asn, asn_name, netname, is_datacenter, is_vpn, user_type, path, method, status_code,
        json.dumps(metadata) if metadata else None
    ))
    
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    
    return {"event_id": event_id, "status": "ingested"}


# -----------------------------------------------------------------------------
# Aggregation Functions
# -----------------------------------------------------------------------------

def aggregate_hourly(project_id: Optional[str] = None):
    """
    Aggregate events into hourly buckets.
    Should be run periodically (e.g., every 5-15 minutes).
    """
    conn = sqlite3.connect(ANALYTICS_DB)
    cursor = conn.cursor()
    
    # Get the current hour boundary
    now = datetime.utcnow()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    prev_hour = current_hour - timedelta(hours=1)
    hour_str = prev_hour.strftime("%Y-%m-%dT%H:00:00Z")
    
    # Build query
    where_clause = "WHERE timestamp >= ? AND timestamp < ?"
    params = [prev_hour.isoformat(), current_hour.isoformat()]
    
    if project_id:
        where_clause += " AND project_id = ?"
        params.append(project_id)
    
    # Aggregate by dimensions
    cursor.execute(f"""
        INSERT OR REPLACE INTO analytics_aggregates_hourly 
        (project_id, hour, country_code, asn, is_datacenter, is_vpn, request_count, unique_ip_estimate)
        SELECT 
            project_id,
            '{hour_str}' as hour,
            country_code,
            asn,
            is_datacenter,
            is_vpn,
            COUNT(*) as request_count,
            COUNT(DISTINCT hashed_ip) as unique_ip_estimate
        FROM analytics_events
        {where_clause}
        GROUP BY project_id, country_code, asn, is_datacenter, is_vpn
    """, params)
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    return {"aggregated_rows": rows_affected, "hour": hour_str}


def aggregate_daily(project_id: Optional[str] = None):
    """
    Aggregate events into daily buckets.
    Should be run once per day.
    """
    conn = sqlite3.connect(ANALYTICS_DB)
    cursor = conn.cursor()
    
    # Get yesterday's date
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    where_clause = "WHERE date(timestamp) = ?"
    params = [yesterday]
    
    if project_id:
        where_clause += " AND project_id = ?"
        params.append(project_id)
    
    cursor.execute(f"""
        INSERT OR REPLACE INTO analytics_aggregates_daily
        (project_id, date, country_code, asn, netname, request_count, unique_ip_estimate, vpn_count, datacenter_count)
        SELECT 
            project_id,
            '{yesterday}' as date,
            country_code,
            asn,
            netname,
            COUNT(*) as request_count,
            COUNT(DISTINCT hashed_ip) as unique_ip_estimate,
            SUM(is_vpn) as vpn_count,
            SUM(is_datacenter) as datacenter_count
        FROM analytics_events
        {where_clause}
        GROUP BY project_id, country_code, asn, netname
    """, params)
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    return {"aggregated_rows": rows_affected, "date": yesterday}


def cleanup_old_events(retention_hours: int = 72):
    """Delete events older than retention period."""
    conn = sqlite3.connect(ANALYTICS_DB)
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(hours=retention_hours)).isoformat()
    cursor.execute("DELETE FROM analytics_events WHERE created_at < ?", (cutoff,))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    return {"deleted_events": deleted}


# -----------------------------------------------------------------------------
# Dashboard Query Functions
# -----------------------------------------------------------------------------

def get_analytics_overview(project_id: str, days: int = 7) -> Dict[str, Any]:
    """Get overview stats for the dashboard."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Total requests and unique IPs
    cursor.execute("""
        SELECT 
            COUNT(*) as total_requests,
            COUNT(DISTINCT hashed_ip) as unique_ips,
            COUNT(DISTINCT country_code) as country_count,
            COUNT(DISTINCT asn) as asn_count,
            SUM(is_datacenter) as datacenter_count,
            SUM(is_vpn) as vpn_count
        FROM analytics_events
        WHERE project_id = ? AND created_at >= ?
    """, (project_id, cutoff))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row or row["total_requests"] == 0:
        return {
            "total_requests": 0,
            "unique_ips": 0,
            "country_count": 0,
            "asn_count": 0,
            "datacenter_percent": 0,
            "vpn_percent": 0
        }
    
    total = row["total_requests"]
    return {
        "total_requests": total,
        "unique_ips": row["unique_ips"],
        "country_count": row["country_count"],
        "asn_count": row["asn_count"],
        "datacenter_percent": round((row["datacenter_count"] or 0) / total * 100, 1),
        "vpn_percent": round((row["vpn_count"] or 0) / total * 100, 1)
    }


def get_timeseries(project_id: str, interval: str = "hour", days: int = 7) -> List[Dict[str, Any]]:
    """Get time series data for charts."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    if interval == "hour":
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%dT%H:00:00Z', timestamp) as bucket,
                COUNT(*) as requests,
                COUNT(DISTINCT hashed_ip) as unique_ips
            FROM analytics_events
            WHERE project_id = ? AND created_at >= ?
            GROUP BY bucket
            ORDER BY bucket
        """, (project_id, cutoff))
    else:  # day
        cursor.execute("""
            SELECT 
                date(timestamp) as bucket,
                COUNT(*) as requests,
                COUNT(DISTINCT hashed_ip) as unique_ips
            FROM analytics_events
            WHERE project_id = ? AND created_at >= ?
            GROUP BY bucket
            ORDER BY bucket
        """, (project_id, cutoff))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_top_countries(project_id: str, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get top countries by request count."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT
            UPPER(TRIM(country_code)) as country_code,
            MAX(country_name) as country_name,
            COUNT(*) as requests,
            COUNT(DISTINCT hashed_ip) as unique_ips
        FROM analytics_events
        WHERE project_id = ?
          AND created_at >= ?
          AND country_code IS NOT NULL
          AND LENGTH(TRIM(country_code)) = 2
          AND UPPER(TRIM(country_code)) GLOB '[A-Z][A-Z]'
        GROUP BY UPPER(TRIM(country_code))
        ORDER BY requests DESC
        LIMIT ?
    """, (project_id, cutoff, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_top_asns(project_id: str, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get top ASNs by request count."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT 
            asn,
            asn_name,
            netname,
            COUNT(*) as requests,
            COUNT(DISTINCT hashed_ip) as unique_ips,
            SUM(is_datacenter) as datacenter_count
        FROM analytics_events
        WHERE project_id = ? AND created_at >= ? AND asn IS NOT NULL
        GROUP BY asn
        ORDER BY requests DESC
        LIMIT ?
    """, (project_id, cutoff, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_risk_breakdown(project_id: str, days: int = 7) -> Dict[str, Any]:
    """Get VPN/datacenter/residential breakdown."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_vpn = 1 THEN 1 ELSE 0 END) as vpn_count,
            SUM(CASE WHEN is_datacenter = 1 THEN 1 ELSE 0 END) as datacenter_count,
            SUM(CASE WHEN user_type = 'Residential' THEN 1 ELSE 0 END) as residential_count,
            SUM(CASE WHEN user_type = 'Mobile' THEN 1 ELSE 0 END) as mobile_count
        FROM analytics_events
        WHERE project_id = ? AND created_at >= ?
    """, (project_id, cutoff))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row or row["total"] == 0:
        return {"vpn": 0, "datacenter": 0, "residential": 0, "mobile": 0, "other": 0}
    
    total = row["total"]
    vpn = row["vpn_count"] or 0
    dc = row["datacenter_count"] or 0
    res = row["residential_count"] or 0
    mob = row["mobile_count"] or 0
    other = total - vpn - dc - res - mob
    
    return {
        "vpn": vpn,
        "vpn_percent": round(vpn / total * 100, 1),
        "datacenter": dc,
        "datacenter_percent": round(dc / total * 100, 1),
        "residential": res,
        "residential_percent": round(res / total * 100, 1),
        "mobile": mob,
        "mobile_percent": round(mob / total * 100, 1),
        "other": other,
        "other_percent": round(other / total * 100, 1) if other > 0 else 0,
        "total": total
    }


def get_top_cities(project_id: str, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get top cities by request count."""
    conn = sqlite3.connect(ANALYTICS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT 
            city,
            region,
            country_code,
            COUNT(*) as requests
        FROM analytics_events
        WHERE project_id = ? AND created_at >= ? AND city IS NOT NULL AND city != 'N/A'
        GROUP BY city, country_code
        ORDER BY requests DESC
        LIMIT ?
    """, (project_id, cutoff, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# -----------------------------------------------------------------------------
# Tier Limits
# -----------------------------------------------------------------------------

TIER_LIMITS = {
    "free": {
        "history_days": 7,
        "max_projects": 1,
        "exports": False,
        "advanced_breakdown": False,
        "monthly_requests": 3000  # 100/day
    },
    "start": {
        "history_days": 30,
        "max_projects": 3,
        "exports": False,
        "advanced_breakdown": True,
        "monthly_requests": 50000
    },
    "pro": {
        "history_days": 90,
        "max_projects": 10,
        "exports": True,
        "advanced_breakdown": True,
        "monthly_requests": 500000
    },
    "max": {
        "history_days": 180,
        "max_projects": 25,
        "exports": True,
        "advanced_breakdown": True,
        "monthly_requests": 2000000
    },
    "enterprise": {
        "history_days": 365,
        "max_projects": 999,
        "exports": True,
        "advanced_breakdown": True,
        "monthly_requests": float('inf')
    }
}


def get_tier_limits(plan: str) -> Dict[str, Any]:
    """Get limits for a subscription tier."""
    return TIER_LIMITS.get(plan, TIER_LIMITS["free"])


# Initialize databases on import
init_analytics_db()
init_projects_db()
