from fastapi import FastAPI, HTTPException, Request, Depends, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import sqlite3
import ipaddress
import uvicorn
import time
import asyncio
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from cachetools import TTLCache
from typing import Optional, Dict, Any
import threading
import bisect
import re
from urllib.parse import quote, urlencode
import httpx  # For elevation API
import auth  # New auth module
import analytics  # Analytics module
import licenses # License module
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# PostgreSQL support
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

# Configuration
# Database backend: "postgresql" or "sqlite"
DB_BACKEND = os.getenv("DB_BACKEND", "postgresql").strip().lower()

# PostgreSQL connection settings
PG_HOST = os.getenv("PG_HOST", "/tmp")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "truegeoip")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "Islam1717@")
PG_MIN_CONN = int(os.getenv("PG_MIN_CONN", "2"))
PG_MAX_CONN = int(os.getenv("PG_MAX_CONN", "10"))

# PostgreSQL connection pool (initialized at startup)
pg_pool = None

def resolve_ip_db_file() -> str:
    """Resolve primary IP data DB path from env or common filenames."""
    env_value = (os.getenv("IP_DB_FILE", "") or "").strip()
    if env_value:
        return env_value

    for candidate in ("databasefull.sqlite", "ripe.sqlite"):
        if os.path.exists(candidate):
            return candidate
    return "ripe.sqlite"


DB_FILE = resolve_ip_db_file()


def env_int(name: str, default: int) -> int:
    """Safely parse integer env config with fallback."""
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


LOOKUP_MODE = (os.getenv("LOOKUP_MODE", "db") or "db").strip().lower()
if LOOKUP_MODE not in {"db", "memory"}:
    LOOKUP_MODE = "db"

CACHE_SIZE = env_int("IP_CACHE_SIZE", 100000)
CACHE_TTL = env_int("IP_CACHE_TTL", 3600)
NUM_WORKERS = env_int("LOOKUP_WORKERS", 4)
LOOKUP_RATE_WINDOW_SECONDS = env_int("LOOKUP_RATE_WINDOW_SECONDS", 10)
LOOKUP_RATE_MAX_REQUESTS = env_int("LOOKUP_RATE_MAX_REQUESTS", 80)
LOOKUP_RATE_BLOCK_SECONDS = env_int("LOOKUP_RATE_BLOCK_SECONDS", 30)
AUTO_CREATE_DB_INDEXES = (os.getenv("AUTO_CREATE_DB_INDEXES", "0") or "").strip().lower() in {
    "1", "true", "yes", "on"
}

# Global resources
executor: ThreadPoolExecutor = None
ip_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
# Elevation cache (fully preloaded only in memory mode).
elevation_data = {}
cache_lock = threading.Lock()
lookup_rate_state = {}
lookup_rate_lock = threading.Lock()

# In-memory sorted data for fast binary search
city_data = []  # [(start_hex, end_hex, row_dict), ...]
asn_data = []   # [(start_int, end_int, row_dict), ...]
asn_new_data = []  # [(start_hex, end_hex, row_dict), ...]
vpn_range_data = [] # [(start_hex, end_hex, row_dict), ...]
threat_data = [] # [(start_hex, end_hex, row_dict), ...]
user_type_data = [] # [(start_hex, end_hex, row_dict), ...]
countries = {}  # alpha2 -> row_dict
currencies = {}  # country_code -> row_dict
dial_codes = {}  # alpha3 -> dial_code
fallback_cities = {}  # alpha3 -> capital_city

LOOKUP_INDEX_SQL = {
    "idx_city_layer_start_ip": "CREATE INDEX IF NOT EXISTS idx_city_layer_start_ip ON City_layer(start_ip)",
    "idx_ip_ranges_start_ip": "CREATE INDEX IF NOT EXISTS idx_ip_ranges_start_ip ON ip_ranges(start_ip)",
    "idx_asn_lookup_start_ip": "CREATE INDEX IF NOT EXISTS idx_asn_lookup_start_ip ON asn_lookup(start_ip)",
    "idx_vpn_ranges_start_ip": "CREATE INDEX IF NOT EXISTS idx_vpn_ranges_start_ip ON vpn_ranges(start_ip)",
    "idx_user_type_start_ip": "CREATE INDEX IF NOT EXISTS idx_user_type_start_ip ON user_type(start_ip)",
    "idx_threat_level_start_ip": "CREATE INDEX IF NOT EXISTS idx_threat_level_start_ip ON Threat_level(start_ip)",
    "idx_elevation_lookup_lat_lon": (
        "CREATE INDEX IF NOT EXISTS idx_elevation_lookup_lat_lon "
        "ON elevation_lookup(latitude, longitude)"
    ),
}

# Pre-compiled IP network objects
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
LOOPBACK_NETWORK = ipaddress.ip_network("127.0.0.0/8")
APIPA_NETWORK = ipaddress.ip_network("169.254.0.0/16")
MULTICAST_NETWORK = ipaddress.ip_network("224.0.0.0/4")
UNSPECIFIED_NETWORK = ipaddress.ip_network("0.0.0.0/8")
RESERVED_NETWORK = ipaddress.ip_network("240.0.0.0/4")
BENCHMARK_NETWORK = ipaddress.ip_network("198.18.0.0/15")

# European Union member countries (ISO 3166-1 alpha-2 codes)
EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE"
}

# Known datacenter/hosting provider ASNs (for is_datacenter detection) - 100+ entries
DATACENTER_ASNS = {
    # Major Cloud Providers
    "16509", "14618", "7224",  # AWS/Amazon
    "8075", "12076", "8074",   # Microsoft/Azure
    "15169", "396982", "19527", "394089", "36040",  # Google
    "14061", "62567",  # DigitalOcean
    "13335", "209242",  # Cloudflare
    "24940", "213230",  # Hetzner
    "16276",  # OVH
    "20473", "20454",  # Vultr
    "63949",  # Linode
    "31898",  # Oracle Cloud (ORACLE-BMC-31898)
    "45090",  # Tencent Cloud
    
    # CDN / Edge Networks
    "20940", "16625", "36183",  # Akamai
    "54113",  # Fastly
    "212238",  # CDNEXT
    
    # Major Hosting Providers
    "9009",   # M247 (major hosting)
    "36352",  # ColoCrossing
    "62240",  # Clouvider
    "7979",   # Servers.com
    "8100",   # QuadraNet
    "46606",  # Unified Layer
    "36351",  # SoftLayer/IBM
    "47583",  # Hostinger
    "398101",  # GoDaddy
    "26347",  # DreamHost
    "22611",  # InMotion Hosting
    "46844", "32244",  # Liquid Web
    "35916",  # Multacom
    "30083",  # HEG US
    "60781",  # LeaseWeb Netherlands
    "28753",  # LeaseWeb Germany
    "56106",  # 1337 Services (privacy hosting)
    "200019",  # AlexHost
    "204957",  # Green Floid
    "50613",  # Makonix
    "62005",  # BlueVPS
    "57043",  # Hostkey
    "35415",  # Webzilla
    "44901",  # Belcloud
    "41079",  # Zurich Datacenter
    
    # Transit / Infrastructure (often used for hosting)
    "174",    # Cogent
    "3356",   # Level3/Lumen
    "3257",   # GTT
    "3549",   # Level3
    "701",    # Verizon/UUNET
    
    # Large Tech Companies (datacenter IPs)
    "714",    # Apple Engineering
    "32934",  # Facebook/Meta
    "8069",   # Microsoft
    "6185",   # Apple
    
    # VPS / Budget Hosting
    "46664",  # VolumeDrive
    "53667",  # FranTech/BuyVM
    "25369",  # Hydra Communications
    "21100",  # ITL-Bulgaria
    "60626",  # ITL
    
    # Regional Hosting Providers
    "19844", "33070",  # Zayo
    "14593",  # SpaceX Starlink (satellite, often flagged)
    
    # Privacy/Anonymity focused (high VPN usage)
    "206264",  # Amarutu Technology (privacy)
    "9009",    # M247 (VPN favorite)
    "60068",   # Datacamp
    "51852",   # Private Layer
    "44927",   # The Constant Company
    "132203",  # Tencent Building
    "61969",   # TeamViewer
    "397423",  # Tier.Net
    "395092",  # Google Fiber
    "6939",    # Hurricane Electric
    "46562",   # Performive
    "30633",   # Leaseweb USA
    "19551",   # Incapsula (Imperva)
    "55286",   # DataCamp
    "40676",   # Psychz Networks
    "23033",   # Wowrack
    "29802",   # HVC-AS (hosting)
    "34549",   # meerfarbig GmbH
    "51167",   # Contabo
    "24961",   # myLoc (hosting)
    "197540",  # netcup
    "29066",   # velia.net
    "42708",   # Portlane
    "50673",   # Serverius
    "49981",   # WorldStream
    "42831",   # UK Dedicated Servers
    "20278",   # Nexeon
    "133618",  # Trellian (hosting)
    "46475",   # Limenet
    "23470",   # ReliableSite
    "55225",   # IT7 Networks
    "36114",   # Orca Wave
    "3223",    # Voxility
    "199883",  # VPSie
}

# Keywords in ASN names that indicate datacenter/hosting
DATACENTER_KEYWORDS = {
    "amazon", "aws", "azure", "microsoft", "google", "cloud", "gcp",
    "digitalocean", "linode", "vultr", "hetzner", "ovh", "cloudflare",
    "hosting", "host", "server", "datacenter", "datacentre", "data center",
    "vps", "dedicated", "colo", "colocation", "rack", "servers",
    "leaseweb", "softlayer", "rackspace", "godaddy", "dreamhost",
    "hostinger", "bluehost", "hostgator", "ionos", "contabo",
    "scaleway", "upcloud", "kamatera", "cherry", "packet",
}


def is_datacenter(asn: str, asn_name: str) -> bool:
    """
    Detect if an IP likely belongs to a datacenter/hosting provider.
    Returns True if the ASN is a known datacenter or contains hosting keywords.
    """
    # Check ASN number directly
    if asn and str(asn) in DATACENTER_ASNS:
        return True
    
    # Check ASN name for keywords
    if asn_name:
        name_lower = asn_name.lower()
        for keyword in DATACENTER_KEYWORDS:
            if keyword in name_lower:
                return True
    
    return False


def get_ip_type_fast(ip_obj) -> str:
    """Optimized IP type detection."""
    try:
        for net in PRIVATE_NETWORKS:
            if ip_obj in net:
                return "Private"
        if ip_obj in CGNAT_NETWORK:
            return "CGNAT"
        if ip_obj in LOOPBACK_NETWORK:
            return "Loopback"
        if ip_obj in APIPA_NETWORK:
            return "APIPA"
        if ip_obj in MULTICAST_NETWORK:
            return "Multicast"
        if str(ip_obj) == "255.255.255.255":
            return "Broadcast"
        if ip_obj in UNSPECIFIED_NETWORK:
            return "Unspecified"
        if ip_obj in RESERVED_NETWORK:
            return "IANA (Reserved)"
        if ip_obj in BENCHMARK_NETWORK:
            return "Benchmarking"
        return "Public"
    except Exception:
        return "Unknown"


def binary_search_range_hex(data, ip_hex):
    """Binary search for IP in sorted hex ranges. Returns the SMALLEST (most specific) matching range."""
    if not data:
        return None
    
    # Binary search to find a starting point
    left, right = 0, len(data) - 1
    candidates = []
    
    while left <= right:
        mid = (left + right) // 2
        start_hex, end_hex, row = data[mid]
        
        if start_hex <= ip_hex <= end_hex:
            # Found a match, but there might be more specific ones
            # Collect this and search nearby for overlapping ranges
            candidates.append((start_hex, end_hex, row))
            
            # Search left for more matches (smaller start_hex that might contain IP)
            i = mid - 1
            while i >= 0:
                s, e, r = data[i]
                if s <= ip_hex <= e:
                    candidates.append((s, e, r))
                elif e < ip_hex:
                    break  # No more matches to the left
                i -= 1
            
            # Search right for more matches
            i = mid + 1
            while i < len(data):
                s, e, r = data[i]
                if s <= ip_hex <= e:
                    candidates.append((s, e, r))
                elif s > ip_hex:
                    break  # No more matches to the right
                i += 1
            break
        elif ip_hex < start_hex:
            right = mid - 1
        else:
            left = mid + 1
    
    if not candidates:
        return None
    
    # Return the SMALLEST range (most specific)
    # Size = end_hex - start_hex (as integers)
    def range_size(item):
        try:
            return int(item[1], 16) - int(item[0], 16)
        except:
            return float('inf')
    
    smallest = min(candidates, key=range_size)
    return smallest[2]  # Return the row dict



def binary_search_range_int(data, ip_int):
    """Binary search for IP in sorted integer ranges."""
    if not data:
        return None
    
    left, right = 0, len(data) - 1
    
    while left <= right:
        mid = (left + right) // 2
        start_int, end_int, row = data[mid]
        
        if start_int <= ip_int <= end_int:
            return row
        elif ip_int < start_int:
            right = mid - 1
        else:
            left = mid + 1
    
    return None


def get_readonly_db_connection():
    """Get a database connection from the pool (PostgreSQL) or SQLite."""
    if DB_BACKEND == "postgresql" and pg_pool:
        return pg_pool.getconn()
    else:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        return conn


def release_db_connection(conn):
    """Release a database connection back to the pool."""
    if DB_BACKEND == "postgresql" and pg_pool and conn:
        pg_pool.putconn(conn)
    elif conn:
        conn.close()


def query_hex_range_db(
    conn,
    table: str,
    ip_hex: str,
    select_columns: str = "*",
) -> Optional[Dict[str, Any]]:
    """Exact range lookup for hex IP tables."""
    # PostgreSQL uses lowercase table names
    table_map = {
        "City_layer": "city_layer",
        "Threat_level": "threat_level",
        "asn_lookup": "asn_lookup",
        "vpn_ranges": "vpn_ranges",
        "user_type": "user_type",
    }
    allowed_tables = set(table_map.keys())
    if table not in allowed_tables:
        raise ValueError(f"Unsupported lookup table: {table}")

    if DB_BACKEND == "postgresql":
        pg_table = table_map.get(table, table.lower())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM {pg_table}
            WHERE start_ip <= %s AND end_ip >= %s
            ORDER BY start_ip DESC
            LIMIT 1
            """,
            (ip_hex, ip_hex)
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None
    else:
        row = conn.execute(
            f"""
            SELECT {select_columns}
            FROM {table}
            WHERE start_ip <= ? AND end_ip >= ?
            ORDER BY start_ip DESC
            LIMIT 1
            """,
            (ip_hex, ip_hex)
        ).fetchone()
        return dict(row) if row else None


def query_int_range_db(
    conn,
    table: str,
    ip_int: int,
    select_columns: str = "*",
) -> Optional[Dict[str, Any]]:
    """Exact range lookup for integer IP tables."""
    if table != "ip_ranges":
        raise ValueError(f"Unsupported lookup table: {table}")

    if DB_BACKEND == "postgresql":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM ip_ranges
            WHERE start_ip <= %s AND end_ip >= %s
            ORDER BY start_ip DESC
            LIMIT 1
            """,
            (ip_int, ip_int)
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None
    else:
        row = conn.execute(
            f"""
            SELECT {select_columns}
            FROM {table}
            WHERE start_ip <= ? AND end_ip >= ?
            ORDER BY start_ip DESC
            LIMIT 1
            """,
            (ip_int, ip_int)
        ).fetchone()
        return dict(row) if row else None


def query_elevation_db(conn, lat: float, lon: float) -> Optional[float]:
    """Read elevation from DB without preloading the full table."""
    if DB_BACKEND == "postgresql":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Cast to ::real to match REAL column type (float32 vs Python's float64)
        cursor.execute(
            "SELECT elevation FROM elevation_lookup WHERE latitude = %s::real AND longitude = %s::real LIMIT 1",
            (lat, lon)
        )
        row = cursor.fetchone()
        cursor.close()
        if row and row["elevation"] is not None:
            return float(row["elevation"])
        return None
    else:
        row = conn.execute(
            "SELECT elevation FROM elevation_lookup WHERE latitude = ? AND longitude = ? LIMIT 1",
            (lat, lon)
        ).fetchone()
        if row and row["elevation"] is not None:
            return float(row["elevation"])
        return None


def ensure_lookup_indexes(auto_create: bool = False) -> None:
    """Check (and optionally create) lookup indexes used by DB mode."""
    conn = sqlite3.connect(DB_FILE)
    try:
        existing = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        }
        missing = [name for name in LOOKUP_INDEX_SQL if name not in existing]
        if not missing:
            return

        if not auto_create:
            print(
                "[WARN] Missing lookup indexes for DB mode: "
                + ", ".join(missing)
                + ". Set AUTO_CREATE_DB_INDEXES=1 once to build them."
            )
            return

        print("Creating lookup indexes (one-time operation)...")
        for name in missing:
            print(f"  - {name}")
            conn.execute(LOOKUP_INDEX_SQL[name])
        conn.commit()
        print("Lookup indexes created.")
    finally:
        conn.close()


def load_reference_metadata(conn) -> None:
    """Load small reference tables used for response enrichment."""
    global countries, currencies, dial_codes, fallback_cities

    if DB_BACKEND == "postgresql":
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM countries")
        countries = {row["alpha2"]: dict(row) for row in cursor.fetchall()}
        
        cursor.execute("SELECT * FROM country_currency")
        currencies = {row["country_code"]: dict(row) for row in cursor.fetchall()}
        
        cursor.execute("SELECT * FROM country_dial")
        dial_codes = {row["country_code"]: row["dial_code"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT * FROM fallback_city")
        fallback_cities = {row["country_code"]: row["capital_city"] for row in cursor.fetchall()}
        cursor.close()
    else:
        cursor = conn.execute("SELECT * FROM countries")
        countries = {row["alpha2"]: dict(row) for row in cursor}

        cursor = conn.execute("SELECT * FROM country_currency")
        currencies = {row["country_code"]: dict(row) for row in cursor}

        cursor = conn.execute("SELECT * FROM country_dial")
        dial_codes = {row["country_code"]: row["dial_code"] for row in cursor}

        cursor = conn.execute("SELECT * FROM fallback_city")
        fallback_cities = {row["country_code"]: row["capital_city"] for row in cursor}


def lookup_rows_db(ip_hex: str, ip_int: Optional[int]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Load lookup rows from database on demand to keep memory usage low."""
    conn = get_readonly_db_connection()
    try:
        row_city = query_hex_range_db(conn, "City_layer", ip_hex)
        row_asn = query_int_range_db(conn, "ip_ranges", ip_int) if ip_int is not None else None
        row_asn_new = query_hex_range_db(conn, "asn_lookup", ip_hex)
        row_vpn = query_hex_range_db(conn, "vpn_ranges", ip_hex, select_columns="start_ip, end_ip")
        row_threat = query_hex_range_db(
            conn, "Threat_level", ip_hex, select_columns="start_ip, end_ip, threat_level"
        )
        row_user_type = query_hex_range_db(
            conn, "user_type", ip_hex, select_columns="start_ip, end_ip, ip_type"
        )
    finally:
        release_db_connection(conn)

    if row_user_type and row_user_type.get("ip_type") and not row_user_type.get("user_type"):
        row_user_type["user_type"] = row_user_type["ip_type"]

    return {
        "city": row_city,
        "asn": row_asn,
        "asn_new": row_asn_new,
        "vpn": row_vpn,
        "threat": row_threat,
        "user_type": row_user_type,
    }


def get_elevation_value(lat: Optional[float], lon: Optional[float]) -> Optional[float]:
    """Return elevation from in-memory cache or DB on demand."""
    if lat is None or lon is None:
        return None

    key = (lat, lon)
    if key in elevation_data:
        return elevation_data[key]

    if LOOKUP_MODE == "memory":
        return elevation_data.get(key)

    try:
        conn = get_readonly_db_connection()
        try:
            elev = query_elevation_db(conn, lat, lon)
        finally:
            release_db_connection(conn)
        if elev is not None:
            elevation_data[key] = elev
        return elev
    except Exception as e:
        print(f"[WARN] elevation DB lookup failed: {e}")
        return None


def lookup_user_type_db(ip_hex: str) -> Optional[str]:
    """
    Fallback DB lookup for user_type when in-memory ranges miss.
    This protects against transient startup load issues or stale in-memory state.
    """
    try:
        conn = get_readonly_db_connection()
        try:
            row = query_hex_range_db(conn, "user_type", ip_hex, select_columns="start_ip, end_ip, ip_type")
        finally:
            release_db_connection(conn)
        if row and row.get("ip_type"):
            return row["ip_type"]
    except Exception as e:
        print(f"[WARN] user_type DB fallback failed: {e}")
    return None


def sanitize_netname(netname):
    """Return N/A for non-informative netname values."""
    if not netname:
        return "N/A"
    # Filter out non-informative RIPE placeholder values
    if "NON-RIPE-NCC-MANAGED" in netname.upper():
        return "N/A"
    # Remove escaped quotes/double quotes from the string
    return netname.replace('"', '').replace('\\', '').strip()


def load_all_data():
    """Initialize lookup data according to configured lookup mode."""
    global city_data, asn_data, asn_new_data, user_type_data, countries, currencies, dial_codes, fallback_cities, vpn_range_data, threat_data, elevation_data
    
    print(f"Initializing lookup data (mode={LOOKUP_MODE}, backend={DB_BACKEND})...")
    start = time.time()
    
    # Get connection from appropriate backend
    if DB_BACKEND == "postgresql" and pg_pool:
        conn = pg_pool.getconn()
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
    
    try:
        print("  Loading country metadata...")
        load_reference_metadata(conn)

        if LOOKUP_MODE == "memory":
            print("  Loading range tables into RAM...")
            # Note: Memory mode with PostgreSQL would need cursor iteration
            # For now, memory mode uses SQLite fallback for bulk load
            if DB_BACKEND == "sqlite":
                cursor = conn.execute("SELECT * FROM City_layer ORDER BY start_ip")
                city_data = [(row["start_ip"], row["end_ip"], dict(row)) for row in cursor]
                print(f"    Loaded {len(city_data):,} city ranges")

                cursor = conn.execute("SELECT * FROM ip_ranges ORDER BY start_ip")
                asn_data = [(row["start_ip"], row["end_ip"], dict(row)) for row in cursor]
                print(f"    Loaded {len(asn_data):,} ASN ranges")

                cursor = conn.execute("SELECT * FROM asn_lookup ORDER BY start_ip")
                asn_new_data = [(row["start_ip"], row["end_ip"], dict(row)) for row in cursor]
                print(f"    Loaded {len(asn_new_data):,} new ASN ranges")

                try:
                    cursor = conn.execute("SELECT start_ip, end_ip FROM vpn_ranges ORDER BY start_ip")
                    vpn_range_data = [(row["start_ip"], row["end_ip"], {"is_vpn": True}) for row in cursor]
                    print(f"    Loaded {len(vpn_range_data):,} VPN ranges")
                except Exception as e:
                    print(f"    [WARN] Could not load vpn_ranges: {e}")
                    vpn_range_data = []

                try:
                    cursor = conn.execute("SELECT latitude, longitude, elevation FROM elevation_lookup")
                    elevation_data = {(row["latitude"], row["longitude"]): row["elevation"] for row in cursor}
                    print(f"    Loaded {len(elevation_data):,} elevation points")
                except Exception as e:
                    print(f"    [WARN] Could not load elevation_lookup: {e}")
                    elevation_data = {}

                try:
                    cursor = conn.execute("SELECT start_ip, end_ip, ip_type FROM user_type ORDER BY start_ip")
                    user_type_data = [(row["start_ip"], row["end_ip"], {"user_type": row["ip_type"]}) for row in cursor]
                    print(f"    Loaded {len(user_type_data):,} user_type ranges")
                except Exception as e:
                    print(f"    [WARN] Could not load user_type: {e}")
                    user_type_data = []

                try:
                    cursor = conn.execute("SELECT start_ip, end_ip, threat_level FROM Threat_level ORDER BY start_ip")
                    threat_data = [(row["start_ip"], row["end_ip"], {"threat_level": row["threat_level"]}) for row in cursor]
                    print(f"    Loaded {len(threat_data):,} Threat_level ranges")
                except Exception as e:
                    print(f"    [WARN] Could not load Threat_level: {e}")
                    threat_data = []
            else:
                print("  Memory mode with PostgreSQL not supported, using DB lookup mode.")
                city_data = []
                asn_data = []
                asn_new_data = []
                vpn_range_data = []
                threat_data = []
                user_type_data = []
                elevation_data = {}
        else:
            # Keep only tiny metadata in memory. Heavy range tables are queried on demand.
            city_data = []
            asn_data = []
            asn_new_data = []
            vpn_range_data = []
            threat_data = []
            user_type_data = []
            elevation_data = {}
            print(f"  DB lookup mode enabled ({DB_BACKEND}): skipped bulk in-memory range preload.")
    finally:
        if DB_BACKEND == "postgresql" and pg_pool:
            pg_pool.putconn(conn)
        else:
            conn.close()

    print(f"Initialization finished in {time.time() - start:.2f}s")


def sync_get_ip_info(ip: str) -> Optional[Dict[str, Any]]:
    """Fast in-memory IP lookup."""
    ip = ip.strip()
    
    # Check cache first
    with cache_lock:
        if ip in ip_cache:
            return ip_cache[ip].copy()
    
    # Validate IP
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return None
    
    # Fast path for non-public IPs
    ip_type = get_ip_type_fast(ip_obj)
    if ip_type != "Public":
        result = {"ip": ip, "ip_type": ip_type, "found": True}
        with cache_lock:
            ip_cache[ip] = result.copy()
        return result
    
    # Prepare parameters
    ip_hex = ip_obj.packed.hex().zfill(32)
    ip_int = int(ip_obj) if ip_obj.version == 4 else None
    
    if LOOKUP_MODE == "memory":
        # Binary search in preloaded arrays.
        row_city = binary_search_range_hex(city_data, ip_hex)
        row_asn = binary_search_range_int(asn_data, ip_int) if ip_int is not None else None
        row_asn_new = binary_search_range_hex(asn_new_data, ip_hex)
        row_vpn = binary_search_range_hex(vpn_range_data, ip_hex)
        row_threat = binary_search_range_hex(threat_data, ip_hex)
        row_user_type = binary_search_range_hex(user_type_data, ip_hex)
        if row_user_type is None:
            fallback_user_type = lookup_user_type_db(ip_hex)
            if fallback_user_type:
                row_user_type = {"user_type": fallback_user_type}
    else:
        # Low-memory mode: query SQLite per request and rely on request cache.
        db_rows = lookup_rows_db(ip_hex, ip_int)
        row_city = db_rows["city"]
        row_asn = db_rows["asn"]
        row_asn_new = db_rows["asn_new"]
        row_vpn = db_rows["vpn"]
        row_threat = db_rows["threat"]
        row_user_type = db_rows["user_type"]

    result = None
    
    if row_city:
        try:
            if ip_obj.version == 4:
                s_ip = str(ipaddress.ip_address(bytes.fromhex(row_city["start_ip"][-8:])))
                e_ip = str(ipaddress.ip_address(bytes.fromhex(row_city["end_ip"][-8:])))
            else:
                s_ip = str(ipaddress.ip_address(bytes.fromhex(row_city["start_ip"])))
                e_ip = str(ipaddress.ip_address(bytes.fromhex(row_city["end_ip"])))
        except:
            s_ip, e_ip = "N/A", "N/A"
        
        result = {
            "ip": ip, "found": True, "range_start": s_ip, "range_end": e_ip,
            "country_code": row_city.get("country_iso_code") or "N/A",  # Renamed from country
            "country_name": row_city.get("country_name") or "N/A",      # Added
            "country_code": row_city.get("country_iso_code") or "N/A",
            "country_name": row_city.get("country_name"),
            "is_eu": row_city.get("country_iso_code") in EU_COUNTRIES,
            
            # Prefer 'org' for 'netname' as requested, fallback to raw 'netname'
            "netname": sanitize_netname(row_city.get("org") or row_city.get("netname")), 
            
            "org": row_city.get("org"),
            "source": row_city.get("source") or "city_layer", 
            "city": row_city.get("city_name"), 
            "is_fallback": bool(row_city.get("is_fallback", 0)),
            "is_vpn": bool(row_city.get("is_vpn", 0) or row_vpn),
            "region": row_city.get("subdivision_1_name"),
            "postal": row_city.get("postal_code"), 
            "timezone": row_city.get("time_zone"),
            "continent": row_city.get("continent_name"),
            "latitude": row_city.get("latitude"), 
            "longitude": row_city.get("longitude"),
            "is_multicast": bool(row_city.get("is_Multicast", 0)),
            "is_crawler": bool(row_city.get("is_crawler", 0)),
            "ip_type": ip_type,
            "threat_level": row_threat["threat_level"] if row_threat else ip_cache.get(ip, {}).get("threat_level", "low"),
            "user_type": row_user_type["user_type"] if row_user_type else "N/A",
            "elevation": get_elevation_value(row_city.get("latitude"), row_city.get("longitude")),
            "domain": None, # Initialize domain
            "utc_offset": row_city.get("utc_offset"), # Added for new geolocation data
            "zip_code": row_city.get("zip_code") # Added for postal codes from iptwo
        }
        if row_asn:
            # Prefer IP range data if City layer lacked it (common for RIPE data)
            if result["netname"] == "N/A" or result["netname"] is None:
                # Prefer 'org' for fallback netname too
                result["netname"] = sanitize_netname(row_asn.get("org") or row_asn.get("netname"))

            if result["org"] == "N/A" or result["org"] is None:
                result["org"] = row_asn.get("org")
                
            if "ARIN" not in str(result["source"]):
                result["source"] += "+ripe"
                
            if row_asn.get("is_vpn"):
                result["is_vpn"] = True
        if row_asn_new:
            result.update({"asn": row_asn_new.get("asn"), "asn_name": row_asn_new.get("name"), "domain": row_asn_new.get("domain")})
            if result["org"] == "N/A":
                result["org"] = row_asn_new.get("org")
            result["source"] += "+mmdb_asn"
            
            # If netname is still missing/bad, try asn_new org
            if result["netname"] == "N/A" or result["netname"] is None:
                 result["netname"] = sanitize_netname(row_asn_new.get("org"))

        # Add datacenter detection
        result["is_datacenter"] = is_datacenter(result.get("asn"), result.get("asn_name"))
    
    elif row_asn:
        country_code = row_asn.get("country") or ""
        # Lookup country name
        c_name = "N/A"
        if country_code and country_code in countries:
            c_name = countries[country_code].get("name_long") or countries[country_code].get("name_short")

        result = {
            "ip": ip, "found": True, "range_start": str(ipaddress.ip_address(row_asn["start_ip"])),
            "range_end": str(ipaddress.ip_address(row_asn["end_ip"])), 
            "country_code": row_asn.get("country"), # Renamed
            "country_name": c_name,                 # Added
            "is_eu": country_code in EU_COUNTRIES,
            
            # Prefer 'org' for 'netname' here too
            "netname": sanitize_netname(row_asn.get("org") or row_asn.get("netname")), 
            
            "org": row_asn.get("org"), "source": row_asn.get("source"),
            "city": None, "region": None, "postal": None, "timezone": None, 
            "is_vpn": bool(row_asn.get("is_vpn", 0)),
            "latitude": None, "longitude": None, "ip_type": ip_type,
            "threat_level": row_threat["threat_level"] if row_threat else "low", # Default to low if not found
            "domain": None, # Initialize domain
            "utc_offset": None, # No utc_offset in RIPE data
            "zip_code": None # No zip_code in RIPE data
        }
        if row_asn_new:
            result.update({"asn": row_asn_new.get("asn"), "asn_name": row_asn_new.get("name"), "domain": row_asn_new.get("domain")})
            if not result["org"] or result["org"] == "N/A":
                result["org"] = row_asn_new.get("org")
            result["source"] += "+mmdb_asn"
        # Add datacenter detection
        result["is_datacenter"] = is_datacenter(result.get("asn"), result.get("asn_name"))
    
    elif row_asn_new:
        country_code = row_asn_new.get("country_code") or ""
        asn_val = row_asn_new.get("asn")
        asn_name_val = row_asn_new.get("name")
        result = {
            "ip": ip, "found": True, "range_start": "N/A", "range_end": "N/A",
            "country": country_code, "is_eu": country_code in EU_COUNTRIES,
            "netname": "N/A", "org": row_asn_new.get("org"),
            "asn": asn_val, "asn_name": asn_name_val, "domain": row_asn_new.get("domain"),
            "source": "mmdb_asn", "city": None, "region": None, "postal": None, 
            "timezone": None, "latitude": None, "longitude": None, "ip_type": ip_type,
            "threat_level": row_threat["threat_level"] if row_threat else "low", # Default to low if not found
            "is_datacenter": is_datacenter(asn_val, asn_name_val)
        }
    
    # If still no result, try fallback to external API (ip-api.com) for real-time data
    if not result:
        print(f"[DEBUG] Local lookup failed for {ip}. Attempting fallback...")
        try:
            import httpx
            # Use a longer timeout to ensure data fetch
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        result = {
                            "ip": ip, "found": True, "range_start": "N/A", "range_end": "N/A",
                            "country": data.get("countryCode"), "is_eu": data.get("countryCode") in EU_COUNTRIES,
                            "netname": "N/A", "org": data.get("org") or data.get("isp"),
                            "source": "external_api", 
                            "city": data.get("city"), 
                            "is_fallback": True,
                            "region": data.get("regionName"),
                            "postal": data.get("zip"), "timezone": data.get("timezone"),
                            "continent": "N/A", "latitude": data.get("lat"), "longitude": data.get("lon"),
                            "asn": data.get("as", "").split(" ")[0] if data.get("as") else "N/A",
                            "asn_name": data.get("as", "").split(" ", 1)[1] if data.get("as") and " " in data.get("as") else "N/A",
                            "is_datacenter": False, # Metadata not available
                            "user_type": "N/A", # Default for fallback
                            "threat_level": "low" # Default for fallback
                        }
                        result["is_datacenter"] = is_datacenter(result.get("asn"), result.get("asn_name"))
        except Exception as e:
            print(f"[WARN] httpx fallback failed: {e}. Trying urllib...")
            try:
                import urllib.request
                import json
                with urllib.request.urlopen(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5.0) as url:
                    data = json.loads(url.read().decode())
                    if data.get("status") == "success":
                        result = {
                            "ip": ip, "found": True, "range_start": "N/A", "range_end": "N/A",
                            "country": data.get("countryCode"), "is_eu": data.get("countryCode") in EU_COUNTRIES,
                            "netname": "N/A", "org": data.get("org") or data.get("isp"),
                            "source": "external_api", 
                            "city": data.get("city"), 
                            "is_fallback": True,
                            "region": data.get("regionName"),
                            "postal": data.get("zip"), "timezone": data.get("timezone"),
                            "continent": "N/A", "latitude": data.get("lat"), "longitude": data.get("lon"),
                            "asn": data.get("as", "").split(" ")[0] if data.get("as") else "N/A",
                            "asn_name": data.get("as", "").split(" ", 1)[1] if data.get("as") and " " in data.get("as") else "N/A",
                            "is_datacenter": False,
                            "user_type": "N/A",
                            "threat_level": "low"
                        }
                        result["is_datacenter"] = is_datacenter(result.get("asn"), result.get("asn_name"))
            except Exception as e2:
                print(f"[ERROR] All fallbacks failed for {ip}: {e2}")

    # Enrich with country metadata (all in-memory, no locks needed)
    if result:
        # Normalize country key usage across different lookup branches.
        country_code = result.get("country_code") or result.get("country")
        if country_code and country_code != "N/A":
            result["country_code"] = country_code
            if not result.get("country") or result.get("country") == "N/A":
                result["country"] = country_code

            if country_code in countries:
                row_country = countries[country_code]
                result.update({
                    "country_full": row_country.get("name_short"),
                    "country_alpha3": row_country.get("alpha3"),
                    "country_numeric": row_country.get("numeric")
                })

                if not result.get("country_name") or result.get("country_name") == "N/A":
                    result["country_name"] = row_country.get("name_long") or row_country.get("name_short") or "N/A"

                c_alpha3 = result.get("country_alpha3")
                if c_alpha3:
                    if c_alpha3 in dial_codes:
                        result["dial_code"] = dial_codes[c_alpha3]

                    if (not result.get("city") or result.get("city") == "N/A") and c_alpha3 in fallback_cities:
                        result["city"] = fallback_cities[c_alpha3]

            if country_code in currencies:
                row_curr = currencies[country_code]
                result.update({
                    "currency_name": row_curr.get("currency_name"),
                    "currency_code": row_curr.get("currency_code")
                })

        # Keep these fields present for consistent landing-page JSON rendering.
        result.setdefault("currency_code", "N/A")
        result.setdefault("currency_name", "N/A")
        
        # Normalize null values to "N/A"
        for key, value in result.items():
            if value is None:
                result[key] = "N/A"
        
        # Apply strict VPN overrides
        if row_vpn:
            result["is_vpn"] = True
            
        # Fallback for Datacenters
        # Strict enforcement: If identified as Datacenter, user_type must be Datacenter
        if result.get("is_datacenter"):
            result["user_type"] = "Datacenter"
            
        # Default threat_level if somehow missing
        result.setdefault("threat_level", "low")

        with cache_lock:
            ip_cache[ip] = result.copy()
        return result
    
    result = {"ip": ip, "found": False, "detail": "IP range not found in database"}
    with cache_lock:
        ip_cache[ip] = result.copy()
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler."""
    global executor, pg_pool
    
    print(
        f"Startup config: DB_BACKEND={DB_BACKEND}, LOOKUP_MODE={LOOKUP_MODE}, LOOKUP_WORKERS={NUM_WORKERS}"
    )
    
    # Initialize PostgreSQL connection pool
    if DB_BACKEND == "postgresql":
        print(f"Initializing PostgreSQL connection pool (min={PG_MIN_CONN}, max={PG_MAX_CONN})...")
        try:
            pg_pool = psycopg2.pool.ThreadedConnectionPool(
                PG_MIN_CONN,
                PG_MAX_CONN,
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DATABASE,
                user=PG_USER,
                password=PG_PASSWORD,
                options="-c search_path=app,analytics,lookup,public"
            )
            print(f"  PostgreSQL pool created successfully")
            
            # Share pool with other modules
            auth.pg_pool = pg_pool
            analytics.pg_pool = pg_pool
            licenses.pg_pool = pg_pool
            
        except Exception as e:
            print(f"  [ERROR] Failed to create PostgreSQL pool: {e}")
            print(f"  [WARN] Falling back to SQLite")
            pg_pool = None
    else:
        ensure_lookup_indexes(auto_create=AUTO_CREATE_DB_INDEXES)
    
    load_all_data()
    executor = ThreadPoolExecutor(max_workers=NUM_WORKERS)
    yield
    executor.shutdown(wait=True)
    
    # Close PostgreSQL pool on shutdown
    if pg_pool:
        print("Closing PostgreSQL connection pool...")
        pg_pool.closeall()


app = FastAPI(lifespan=lifespan)

# Security: Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security: Trusted Host Middleware
# ALLOWED_HOSTS = ["example.com", "*.example.com", "localhost", "127.0.0.1"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"]) # TODO: User should restrict this in prod

# Security: Custom Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # HSTS (Strict-Transport-Security) - Uncomment for Production with HTTPS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Add session middleware (Secure configuration)
# Note: 'https_only=True' requires HTTPS. 'same_site="lax"' is good for CSRF.
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "fallback-secret-key"), https_only=False, same_site="lax")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    # Explicit root favicon route helps browsers that ignore page-level icon tags.
    return FileResponse("static/img/logo.png", media_type="image/png")


@app.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon() -> FileResponse:
    return FileResponse("static/img/logo.png", media_type="image/png")

DEFAULT_CHECKOUT_PLAN = "start"
CHECKOUT_PLAN_CATALOG = {
    "free": {
        "name": "Free",
        "category": "API",
        "price": "$0",
        "period": "/mo",
        "description": "Perfect for testing and experiments.",
        "cta_label": "Get Started",
        "features": [
            "100 requests per day",
            "Basic IP geolocation",
            "Community support",
            "No ASN data",
            "No VPN detection"
        ]
    },
    "start": {
        "name": "Starter",
        "category": "API",
        "price": "$7",
        "period": "/mo",
        "description": "For small apps and early products.",
        "cta_label": "Upgrade to Starter",
        "features": [
            "50,000 requests per month",
            "IP & network insights",
            "IP type & user type",
            "Datacenter detection",
            "Network name",
            "Location data",
            "Country & continent",
            "City & region",
            "Time zone",
            "Coordinates (latitude & longitude)",
            "EU compliance flag"
        ]
    },
    "pro": {
        "name": "Pro",
        "category": "API",
        "price": "$15",
        "period": "/mo",
        "description": "For scaling and production use.",
        "cta_label": "Upgrade to Pro",
        "features": [
            "500,000 requests per month",
            "Everything in Starter, plus:",
            "Advanced network intelligence",
            "ASN & ASN name",
            "Associated domain",
            "Security & traffic signals",
            "VPN detection",
            "Crawler / bot detection",
            "Enhanced location data",
            "ZIP / postal code",
            "Elevation",
            "Time & currency info",
            "UTC offset",
            "Local currency code & name"
        ]
    },
    "max": {
        "name": "Max",
        "category": "API",
        "price": "$25",
        "period": "/mo",
        "description": "Limited offer • High-volume & high-performance.",
        "cta_label": "Start Free Trial",
        "features": [
            "2,000,000 requests per month",
            "Everything in Pro, plus:",
            "Bulk IP lookup endpoint",
            "High-concurrency support",
            "Optimized for large-scale workloads"
        ]
    },
    "db_onetime": {
        "name": "One-Time Purchase",
        "category": "Database",
        "price": "$599",
        "period": "",
        "description": "One-time payment for full database access.",
        "cta_label": "Buy One-Time Purchase",
        "features": [
            "One-time payment",
            "Full SQLite download",
            "Priority support",
            "No recurring billing"
        ]
    },
    "db_license": {
        "name": "Annual License",
        "category": "Database",
        "price": "$999",
        "period": "/yr",
        "description": "Annual database license with monthly updates.",
        "cta_label": "Get Annual License",
        "features": [
            "Monthly database updates",
            "Annual commercial usage rights",
            "Business support",
            "Full SQLite access"
        ]
    }
}


def get_checkout_plan_key(plan: Optional[str]) -> str:
    """Return a valid checkout plan key."""
    candidate = (plan or "").strip().lower()
    if candidate in CHECKOUT_PLAN_CATALOG:
        return candidate
    return DEFAULT_CHECKOUT_PLAN


def safe_internal_path(target: Optional[str], default: str = "/") -> str:
    """Only allow local in-app redirect paths."""
    value = (target or "").strip()
    if not value:
        return default
    if not value.startswith("/") or value.startswith("//"):
        return default
    if "\r" in value or "\n" in value:
        return default
    return value


def signin_with_next_url(next_path: str) -> str:
    """Build sign-in URL with safe encoded next path."""
    safe_next = safe_internal_path(next_path, "/")
    return f"/signin?next={quote(safe_next, safe='')}"


async def get_full_ip_info(ip: str) -> Optional[Dict[str, Any]]:
    """Async wrapper for IP lookup (memory or DB mode)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, sync_get_ip_info, ip)


@app.get("/docs", response_class=HTMLResponse)
async def docs(request: Request):
    return templates.TemplateResponse("docs.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    client_ip = request.client.host or ""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
    
    user = request.session.get("user")
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "client_ip": client_ip,
        "user": user
    })


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("pricing.html", {"request": request, "user": user})


@app.get("/billing")
async def billing_entry(request: Request, plan: str = DEFAULT_CHECKOUT_PLAN):
    """
    Billing entry point.
    - Logged-in users go to payment/billing flow.
    - Logged-out users go to pricing.
    """
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/pricing", status_code=status.HTTP_303_SEE_OTHER)

    plan_key = get_checkout_plan_key(plan)
    return RedirectResponse(
        url=f"/payment?{urlencode({'plan': plan_key})}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/start-checkout")
async def start_checkout(request: Request, plan: str = DEFAULT_CHECKOUT_PLAN):
    """Route plan CTA clicks through auth, then redirect to payment."""
    plan_key = get_checkout_plan_key(plan)
    payment_target = f"/payment?{urlencode({'plan': plan_key})}"
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url=signin_with_next_url(payment_target), status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url=payment_target, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request, plan: str = DEFAULT_CHECKOUT_PLAN):
    """Render payment page for authenticated users."""
    user = request.session.get("user")
    plan_key = get_checkout_plan_key(plan)
    payment_target = f"/payment?{urlencode({'plan': plan_key})}"

    if not user:
        return RedirectResponse(url=signin_with_next_url(payment_target), status_code=status.HTTP_303_SEE_OTHER)

    selected_plan = CHECKOUT_PLAN_CATALOG[plan_key]
    plan_cards = [
        {"key": key, **value}
        for key, value in CHECKOUT_PLAN_CATALOG.items()
    ]
    return templates.TemplateResponse(
        "payment.html",
        {
            "request": request,
            "user": user,
            "selected_plan_key": plan_key,
            "selected_plan": selected_plan,
            "plan_cards": plan_cards
        }
    )


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("contact.html", {"request": request, "user": user})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("privacy.html", {"request": request, "user": user})


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("terms.html", {"request": request, "user": user})


# --- Authentication Routes ---

# Helper to decide response type
def is_json_request(request: Request):
    accept = request.headers.get("accept", "")
    return "application/json" in accept


PROFILE_SUCCESS_MESSAGES = {
    "profile_updated": "Profile updated successfully.",
}

PROFILE_ERROR_MESSAGES = {
    "invalid_name": "Please enter a valid name (2-80 characters).",
    "update_failed": "Unable to update your profile right now.",
    "delete_confirm": 'Type "DELETE" to confirm account deletion.',
    "email_mismatch": "Confirmation email does not match your account email.",
    "password_required": "Please enter your current password to continue.",
    "invalid_password": "Current password is incorrect.",
    "delete_failed": "Unable to delete your account right now. Please try again.",
}

DELETE_FORM_ERROR_CODES = {
    "delete_confirm",
    "email_mismatch",
    "password_required",
    "invalid_password",
    "delete_failed",
}

PASSWORD_SYMBOL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")


def validate_signup_password(password: str) -> Optional[str]:
    """Enforce signup password rules."""
    if len(password or "") < 6:
        return "Password must be at least 6 characters."
    if not PASSWORD_SYMBOL_PATTERN.search(password or ""):
        return "Password must include at least one symbol."
    return None


def cleanup_user_analytics(project_ids):
    """Delete analytics rows linked to user projects."""
    if not project_ids:
        return

    if DB_BACKEND == "postgresql":
        conn = analytics.get_db_connection()
        try:
            cursor = conn.cursor()
            for table in ("analytics_events", "analytics_aggregates_hourly", "analytics_aggregates_daily"):
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE project_id = ANY(%s)", (project_ids,))
                except Exception as e:
                    print(f"[WARN] Failed to delete analytics rows from {table}: {e}")
            conn.commit()
            cursor.close()
        finally:
            analytics.release_db_connection(conn)
        return

    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in project_ids)
        for table in ("analytics_events", "analytics_aggregates_hourly", "analytics_aggregates_daily"):
            try:
                cursor.execute(f"DELETE FROM {table} WHERE project_id IN ({placeholders})", project_ids)
            except sqlite3.Error as e:
                print(f"[WARN] Failed to delete analytics rows from {table}: {e}")
        conn.commit()
    finally:
        conn.close()


@app.get("/api/user")
async def get_current_user(request: Request):
    """Return current logged in user or null."""
    return request.session.get("user") or None


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, success: str = "", error: str = ""):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse(url=signin_with_next_url("/profile"), status_code=status.HTTP_303_SEE_OTHER)

    user_data = auth.get_user_by_id(user_session["id"])
    if not user_data:
        request.session.pop("user", None)
        return RedirectResponse(url=signin_with_next_url("/profile"), status_code=status.HTTP_303_SEE_OTHER)

    session_user = {
        "id": user_data["id"],
        "name": user_data.get("name") or user_data["email"].split("@")[0],
        "email": user_data["email"]
    }
    request.session["user"] = session_user

    conn = auth.get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) AS c FROM projects WHERE user_id = %s", (user_data["id"],))
        project_count = int(cursor.fetchone()["c"] or 0)
        cursor.execute("SELECT COUNT(*) AS c FROM licenses WHERE user_id = %s", (user_data["id"],))
        license_count = int(cursor.fetchone()["c"] or 0)
        cursor.close()
    finally:
        auth.release_db_connection(conn)

    created_at_display = str(user_data.get("created_at") or "N/A").replace("T", " ")
    success_message = PROFILE_SUCCESS_MESSAGES.get(success, "")
    error_message = PROFILE_ERROR_MESSAGES.get(error, "")
    show_delete_form = error in DELETE_FORM_ERROR_CODES

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": session_user,
            "user_data": user_data,
            "has_password": bool(user_data.get("password_hash")),
            "project_count": project_count,
            "license_count": license_count,
            "created_at_display": created_at_display,
            "success_message": success_message,
            "error_message": error_message,
            "show_delete_form": show_delete_form
        }
    )


@app.post("/profile/update")
async def profile_update(request: Request, name: str = Form(...)):
    user_session = request.session.get("user")
    if not user_session:
        if is_json_request(request):
            return Response(content='{"error":"Authentication required."}', media_type="application/json", status_code=401)
        return RedirectResponse(url=signin_with_next_url("/profile"), status_code=status.HTTP_303_SEE_OTHER)

    clean_name = (name or "").strip()
    if len(clean_name) < 2 or len(clean_name) > 80:
        if is_json_request(request):
            return Response(content='{"error":"Invalid name."}', media_type="application/json", status_code=400)
        return RedirectResponse(url="/profile?error=invalid_name", status_code=status.HTTP_303_SEE_OTHER)

    updated = auth.update_user_name(user_session["id"], clean_name)
    if not updated:
        if is_json_request(request):
            return Response(content='{"error":"Update failed."}', media_type="application/json", status_code=500)
        return RedirectResponse(url="/profile?error=update_failed", status_code=status.HTTP_303_SEE_OTHER)

    request.session["user"] = {
        "id": user_session["id"],
        "name": clean_name,
        "email": user_session["email"]
    }

    if is_json_request(request):
        return {"success": True, "name": clean_name}
    return RedirectResponse(url="/profile?success=profile_updated", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/profile/delete")
async def delete_profile(
    request: Request,
    confirm_text: str = Form(""),
    confirm_email: str = Form(""),
    current_password: str = Form("")
):
    user_session = request.session.get("user")
    if not user_session:
        if is_json_request(request):
            return Response(content='{"error":"Authentication required."}', media_type="application/json", status_code=401)
        return RedirectResponse(url=signin_with_next_url("/profile"), status_code=status.HTTP_303_SEE_OTHER)

    user_data = auth.get_user_by_id(user_session["id"])
    if not user_data:
        request.session.pop("user", None)
        if is_json_request(request):
            return Response(content='{"error":"User not found."}', media_type="application/json", status_code=404)
        return RedirectResponse(url=signin_with_next_url("/profile"), status_code=status.HTTP_303_SEE_OTHER)

    if confirm_text.strip().upper() != "DELETE":
        if is_json_request(request):
            return Response(content='{"error":"Invalid confirmation text."}', media_type="application/json", status_code=400)
        return RedirectResponse(url="/profile?error=delete_confirm", status_code=status.HTTP_303_SEE_OTHER)

    if confirm_email.strip().lower() != user_data["email"].lower():
        if is_json_request(request):
            return Response(content='{"error":"Email mismatch."}', media_type="application/json", status_code=400)
        return RedirectResponse(url="/profile?error=email_mismatch", status_code=status.HTTP_303_SEE_OTHER)

    if user_data.get("password_hash"):
        if not current_password:
            if is_json_request(request):
                return Response(content='{"error":"Current password is required."}', media_type="application/json", status_code=400)
            return RedirectResponse(url="/profile?error=password_required", status_code=status.HTTP_303_SEE_OTHER)
        if not auth.verify_password(current_password, user_data["password_hash"]):
            if is_json_request(request):
                return Response(content='{"error":"Invalid password."}', media_type="application/json", status_code=400)
            return RedirectResponse(url="/profile?error=invalid_password", status_code=status.HTTP_303_SEE_OTHER)

    try:
        delete_result = auth.delete_user_account(user_data["id"])
        if not delete_result.get("deleted"):
            raise RuntimeError("User row was not deleted.")
        cleanup_user_analytics(delete_result.get("project_ids", []))
    except Exception as e:
        print(f"[ERR] Failed to delete user {user_data['id']}: {e}")
        if is_json_request(request):
            return Response(content='{"error":"Delete failed."}', media_type="application/json", status_code=500)
        return RedirectResponse(url="/profile?error=delete_failed", status_code=status.HTTP_303_SEE_OTHER)

    request.session.pop("user", None)

    if is_json_request(request):
        return {"success": True}
    return RedirectResponse(url="/?account_deleted=1", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, next: str = "/"):
    next_path = safe_internal_path(next, "/")
    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request,
            "next": next_path,
            "next_encoded": quote(next_path, safe=""),
            "name_value": "",
            "email_value": ""
        }
    )


@app.post("/signup")
@limiter.limit("3/hour")
async def signup_action(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    next: str = Form("/")
):
    next_path = safe_internal_path(next, "/")

    def render_signup_error(message: str):
        if is_json_request(request):
            return Response(content=f'{{"error": "{message}"}}', media_type="application/json", status_code=400)
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": message,
                "next": next_path,
                "next_encoded": quote(next_path, safe=""),
                "name_value": name,
                "email_value": email
            }
        )

    if password != confirm_password:
        return render_signup_error("Passwords do not match.")

    password_error = validate_signup_password(password)
    if password_error:
        return render_signup_error(password_error)

    user = auth.create_user(email, password, name)
    
    if is_json_request(request):
        if not user:
            return Response(content='{"error": "Email already registered."}', media_type="application/json", status_code=400)
        
        # Send verification email
        sent = await auth.send_verification_email(email, user['verification_code'])
        if not sent:
            return Response(
                content='{"error":"Unable to send verification email. Configure email provider."}',
                media_type="application/json",
                status_code=500
            )
        return {"success": True, "message": "Verification code sent.", "email": email, "next": next_path}

    if not user:
        return render_signup_error("Email already registered.")
    
    # Send verification email
    sent = await auth.send_verification_email(email, user['verification_code'])
    
    redirect_params = {"email": email, "next": next_path}
    if not sent:
        # Debug fallback: Pass code in URL if email delivery fails
        redirect_params["debug_code"] = user["verification_code"]
    redirect_url = f"/verify?{urlencode(redirect_params)}"
    
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request, email: str = "", debug_code: str = "", next: str = "/"):
    next_path = safe_internal_path(next, "/")
    return templates.TemplateResponse(
        "verify.html",
        {
            "request": request,
            "email": email,
            "debug_code": debug_code,
            "next": next_path,
            "next_encoded": quote(next_path, safe="")
        }
    )


@app.post("/verify")
async def verify_action(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    next: str = Form("/")
):
    next_path = safe_internal_path(next, "/")
    success = auth.verify_user_email(email, code)
    
    if is_json_request(request):
        if success:
            user = auth.get_user_by_email(email)
            request.session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"]}
            return {"success": True, "user": request.session["user"], "next": next_path}
        else:
             return Response(content='{"error": "Invalid verification code."}', media_type="application/json", status_code=400)

    if success:
        # Verification success - Login the user
        user = auth.get_user_by_email(email)
        request.session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"]}
        return RedirectResponse(url=next_path, status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse(
            "verify.html",
            {
                "request": request,
                "email": email,
                "next": next_path,
                "next_encoded": quote(next_path, safe=""),
                "error": "Invalid verification code."
            }
        )


@app.get("/signin", response_class=HTMLResponse)
async def signin_page(request: Request, next: str = "/"):
    next_path = safe_internal_path(next, "/")
    if request.session.get("user"):
        return RedirectResponse(url=next_path, status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "signin.html",
        {
            "request": request,
            "next": next_path,
            "next_encoded": quote(next_path, safe="")
        }
    )


@app.post("/signin")
@limiter.limit("5/minute")
async def signin_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/")
):
    next_path = safe_internal_path(next, "/")
    user = auth.authenticate_user(email, password)
    
    if is_json_request(request):
        if not user:
             return Response(content='{"error": "Invalid credentials."}', media_type="application/json", status_code=401)
        request.session["user"] = user
        return {"success": True, "user": user, "redirect_to": next_path}

    if not user:
        return templates.TemplateResponse(
            "signin.html",
            {
                "request": request,
                "next": next_path,
                "next_encoded": quote(next_path, safe=""),
                "error": "Invalid credentials."
            }
        )
    
    request.session["user"] = user
    return RedirectResponse(url=next_path, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/signout")
async def signout(request: Request):
    request.session.pop("user", None)
    if is_json_request(request):
        return {"success": True}
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/auth/google")
async def google_login(request: Request):
    # Dynamic redirect URI based on request (handles localhost/127.0.0.1 automatic switching)
    redirect_uri = request.url_for('google_callback')
    print(f"DEBUG: sending redirect_uri={redirect_uri}")
    return await auth.oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await auth.oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            # Try to fetch userinfo manually if not in token
            resp = await auth.oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()
            
        user = auth.create_or_get_google_user(
            email=user_info['email'],
            google_id=user_info['sub'],
            name=user_info.get('name', user_info['email'].split('@')[0])
        )
        
        request.session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"]}
        # Redirect to React Frontend (Dev)
        return RedirectResponse(url="http://localhost:5173/", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"OAuth Error: {e}")
        return RedirectResponse(url="/signin?error=OAuth+Failed", status_code=status.HTTP_303_SEE_OTHER)


def save_elevation_to_db(lat: float, lon: float, elev: float):
    """Save fetched elevation to database (runs in background thread)."""
    try:
        if DB_BACKEND == "postgresql":
            conn = analytics.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO elevation_lookup (latitude, longitude, elevation)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (latitude, longitude) DO UPDATE
                    SET elevation = EXCLUDED.elevation
                    """,
                    (lat, lon, elev),
                )
                conn.commit()
                cursor.close()
            finally:
                analytics.release_db_connection(conn)
            return

        conn = sqlite3.connect(DB_FILE)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO elevation_lookup (latitude, longitude, elevation) VALUES (?, ?, ?)",
                (lat, lon, elev),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Failed to save elevation to DB: {e}")

async def lazy_fetch_elevation(lat: float, lon: float) -> Optional[float]:
    """Fetch elevation from API on cache miss and persist to DB."""
    # Double check memory (race condition optimization)
    if (lat, lon) in elevation_data:
        return elevation_data[(lat, lon)]
            
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
            resp = await client.get(url)
            
            if resp.status_code == 200:
                data = resp.json()
                if "elevation" in data and data["elevation"]:
                    elev = float(data["elevation"][0])
                    
                    # Update in-memory cache
                    elevation_data[(lat, lon)] = elev
                    
                    # Persist to DB in background
                    asyncio.get_event_loop().run_in_executor(None, save_elevation_to_db, lat, lon, elev)
                    
                    return elev
            elif resp.status_code == 429:
                print(f"[WARN] Open-Meteo rate limit hit for {lat},{lon}")
    except Exception as e:
        print(f"[ERR] Lazy fetch failed: {e}")
        
    return None

def get_request_client_id(request: Request) -> str:
    """Resolve client identifier for lookup abuse protection."""
    x_forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if x_forwarded_for:
        first_ip = x_forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown-client"


def check_lookup_speed_limit(request: Request) -> Dict[str, Any]:
    """In-memory per-client speed limiter to reduce abusive traffic bursts."""
    if LOOKUP_RATE_MAX_REQUESTS <= 0 or LOOKUP_RATE_WINDOW_SECONDS <= 0:
        return {"allowed": True, "retry_after": 0}

    client_id = get_request_client_id(request)
    now = time.monotonic()

    with lookup_rate_lock:
        state = lookup_rate_state.get(client_id)
        if not state:
            state = {"window_start": now, "count": 0, "blocked_until": 0.0}

        blocked_until = float(state.get("blocked_until", 0.0))
        if blocked_until > now:
            retry_after = int(blocked_until - now) + 1
            return {"allowed": False, "retry_after": retry_after}

        window_start = float(state.get("window_start", now))
        count = int(state.get("count", 0))

        if now - window_start >= LOOKUP_RATE_WINDOW_SECONDS:
            window_start = now
            count = 0

        count += 1
        if count > LOOKUP_RATE_MAX_REQUESTS:
            blocked_until = now + max(1, LOOKUP_RATE_BLOCK_SECONDS)
            lookup_rate_state[client_id] = {
                "window_start": window_start,
                "count": count,
                "blocked_until": blocked_until,
            }
            return {
                "allowed": False,
                "retry_after": int(max(1, LOOKUP_RATE_BLOCK_SECONDS)),
            }

        lookup_rate_state[client_id] = {
            "window_start": window_start,
            "count": count,
            "blocked_until": 0.0,
        }

        # Best-effort cleanup to keep memory bounded.
        if len(lookup_rate_state) > 100000:
            stale = [
                key for key, value in lookup_rate_state.items()
                if now - float(value.get("window_start", now)) > (LOOKUP_RATE_WINDOW_SECONDS * 3)
                and float(value.get("blocked_until", 0.0)) <= now
            ]
            for key in stale[:50000]:
                lookup_rate_state.pop(key, None)

    return {"allowed": True, "retry_after": 0}


@app.get("/api/check")
async def check_ip(request: Request, ip: str, response: Response):
    # Anti-abuse guard: keep lookup public but reject very fast bursts per client.
    speed_status = check_lookup_speed_limit(request)
    if not speed_status["allowed"]:
        retry_after = max(1, int(speed_status.get("retry_after", 1)))
        error_response = Response(
            content=f'{{"error": "Too many lookup requests from this IP. Slow down and retry in {retry_after}s."}}',
            media_type="application/json",
            status_code=429,
        )
        error_response.headers["Retry-After"] = str(retry_after)
        return error_response

    # 1. Check Cache
    if ip in ip_cache:
        return ip_cache[ip]

    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    start_time = time.time()
    info = await get_full_ip_info(ip)
    process_time = (time.time() - start_time) * 1000
    
    if info is None:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    
    # Lazy load elevation if missing
    if info.get("elevation") is None and info.get("latitude") and info.get("longitude"):
        info["elevation"] = await lazy_fetch_elevation(info["latitude"], info["longitude"])
    
    info["latency_server"] = round(process_time, 2)
    with cache_lock:
        ip_cache[ip] = info.copy()
    return info


# -----------------------------------------------------------------------------
# Analytics API Endpoints
# -----------------------------------------------------------------------------

class IngestEvent(BaseModel):
    ip: str
    timestamp: str
    event_type: Optional[str] = "request"
    path: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    metadata: Optional[dict] = None


def get_api_key(request: Request) -> Optional[str]:
    """Extract API key from request headers."""
    return request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")


@app.post("/v1/analytics/ingest")
async def analytics_ingest(event: IngestEvent, request: Request):
    """Ingest an analytics event."""
    api_key = get_api_key(request)
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required. Use X-API-Key header.")
    
    # Validate API key
    key_info = analytics.validate_api_key(api_key)
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    project_id = key_info["project_id"]
    
    # Enrich the IP using existing pipeline
    ip_info = await get_full_ip_info(event.ip)
    if not ip_info:
        ip_info = {"found": False}
    
    # Ingest the event
    result = analytics.ingest_event(
        project_id=project_id,
        ip=event.ip,
        timestamp=event.timestamp,
        ip_info=ip_info,
        path=event.path,
        method=event.method,
        status_code=event.status_code,
        metadata=event.metadata
    )
    
    return result


@app.get("/v1/analytics/overview")
async def analytics_overview(request: Request, days: int = 7):
    """Get analytics overview for the authenticated user's project."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get user's first project (or specified project)
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return {"total_requests": 0, "unique_ips": 0, "country_count": 0, "asn_count": 0, "datacenter_percent": 0, "vpn_percent": 0}
    
    project_id = projects[0]["id"]
    return analytics.get_analytics_overview(project_id, days)


@app.get("/v1/analytics/timeseries")
async def analytics_timeseries(request: Request, days: int = 7, interval: str = "hour"):
    """Get time series data."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return []
    
    project_id = projects[0]["id"]
    return analytics.get_timeseries(project_id, interval, days)


@app.get("/v1/analytics/countries")
async def analytics_countries(request: Request, days: int = 7, limit: int = 10):
    """Get top countries."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return []
    
    project_id = projects[0]["id"]
    return analytics.get_top_countries(project_id, days, limit)


@app.get("/v1/analytics/cities")
async def analytics_cities(request: Request, days: int = 7, limit: int = 10):
    """Get top cities."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return []
    
    project_id = projects[0]["id"]
    return analytics.get_top_cities(project_id, days, limit)


@app.get("/v1/analytics/asns")
async def analytics_asns(request: Request, days: int = 7, limit: int = 10):
    """Get top ASNs."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return []
    
    project_id = projects[0]["id"]
    return analytics.get_top_asns(project_id, days, limit)


@app.get("/v1/analytics/risk")
async def analytics_risk(request: Request, days: int = 7):
    """Get VPN/datacenter/residential breakdown."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    projects = analytics.get_user_projects(user["id"])
    if not projects:
        return {"vpn": 0, "datacenter": 0, "residential": 0, "mobile": 0, "other": 0}
    
    project_id = projects[0]["id"]
    return analytics.get_risk_breakdown(project_id, days)


# -----------------------------------------------------------------------------
# Dashboard Routes
# -----------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Analytics dashboard page."""
    try:
        user = request.session.get("user")
        project = None
        analytics_api_key = None
        
        today_usage = 0
        limit = 100
        plan = "free"
        
        if user:
            # Fetch fresh user data from DB
            user_row = auth.get_user_by_id(user["id"])
            
            if user_row:
                # Update session user with fresh data
                user = dict(user_row)
                today_usage = user.get("api_requests_count", 0)
                plan = user.get("plan", "free")
                
                # Reset usage if new day (basic check)
                last_date = user.get("last_api_usage_date")
                today = datetime.utcnow().strftime("%Y-%m-%d")
                if last_date != today:
                    today_usage = 0
                
                # Get limit based on plan
                limits = analytics.get_tier_limits(plan)
                limit = limits.get("monthly_requests", 100) # Default to 100/day equivalent if monthly not set
                if plan == "free":
                    limit = 100 # Explict 100/day for free
                else:
                     limit = limits.get("monthly_requests") # Show monthly for others

            projects = analytics.get_user_projects(user["id"])
            if projects:
                project = projects[0]
                project_keys = analytics.get_project_api_keys(project["id"])
                if project_keys:
                    analytics_api_key = project_keys[0].get("key")

        # Fetch user licenses
        user_licenses = []
        if user:
            user_licenses = licenses.get_user_licenses(user['id'])

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "project": project,
            "analytics_api_key": analytics_api_key,
            "licenses": user_licenses,
            "today_usage": today_usage,
            "limit": limit,
            "plan": plan
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"Internal Server Error: {e}", status_code=500)



@app.post("/dashboard/create-project")
async def create_project(request: Request, project_name: str = Form(...)):
    """Create a new analytics project."""
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)
    
    # Check project limit
    projects = analytics.get_user_projects(user["id"])
    user_data = auth.get_user_by_email(user["email"])
    plan = user_data.get("plan", "free") if user_data else "free"
    limits = analytics.get_tier_limits(plan)
    
    if len(projects) >= limits["max_projects"]:
        return RedirectResponse(url="/dashboard?error=project_limit", status_code=status.HTTP_303_SEE_OTHER)
    
    analytics.create_project(user["id"], project_name)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

# --- License System Endpoints ---



@app.post("/api/licenses/create-demo")
async def create_demo_license(request: Request):
    """Create a demo license for the current user."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Check if user already has a license
    existing = licenses.get_user_licenses(user['id'])
    if existing:
        return {"key": existing[0]['license_key'], "status": "existing"}
        
    key = licenses.create_license(user['id'], plan_type='demo', duration_days=30)
    return {"key": key, "status": "created"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
