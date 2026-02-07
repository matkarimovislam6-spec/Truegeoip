"""
enrich_vpn_ranges.py - Detects and adds VPN IP ranges based on ASN and keyword matching.

Detection methods:
1. Known VPN provider ASNs (NordVPN, ExpressVPN, Surfshark, ProtonVPN, etc.)
2. VPN-related keywords in netname/org fields
3. Known VPN hosting providers (M247, Datacamp, etc.)
"""

import sqlite3
import os
import time
import ipaddress

DB_FILE = "ripe.sqlite"

# ============================================================================
# KNOWN VPN PROVIDER ASNs (from research)
# ============================================================================

VPN_PROVIDER_ASNS = {
    # NordVPN
    "141039",   # PacketHub (NordVPN)
    "147049",   # PacketHub (NordVPN)
    "207137",   # Tefincom (NordVPN)
    "212238",   # CDNEXT (NordVPN related)
    
    # ExpressVPN
    "137409",   # ExpressVPN
    "206092",   # IPXO (ExpressVPN hosting)
    
    # Surfshark
    "209854",   # Cyberzone/Surfshark
    "26527",    # LightWave Networks (Surfshark)
    
    # ProtonVPN
    "209103",   # Proton AG
    "199218",   # Proton AG
    
    # Private Internet Access (PIA)
    "30633",    # LeaseWeb (PIA hosting)
    "132907",   # Krypt Technologies (PIA)
    
    # Mullvad VPN
    "39351",    # 31173 Services (Mullvad)
    
    # IPVanish
    "33438",    # Highwinds Network (IPVanish parent)
    
    # CyberGhost
    "9009",     # M247 (major VPN hosting - CyberGhost, many others)
    
    # Hide.me
    "206264",   # Amarutu Technology
    
    # VyprVPN / Golden Frog
    "55967",    # Golden Frog
    
    # TunnelBear
    "40824",    # McAfee (TunnelBear owner)
    
    # Known VPN hosting providers
    "60068",    # Datacamp Limited (VPN favorite)
    "51852",    # Private Layer
    "44927",    # Constant Company
    "62240",    # Clouvider (VPN hosting)
    "56106",    # 1337 Services (privacy hosting)
    "200019",   # AlexHost (VPN friendly)
    "62005",    # BlueVPS
    
    # Additional VPN-focused networks
    "29802",    # Hivelocity (VPN hosting)
    "204957",   # Green Floid (VPN)
    "61317",    # Asimia Damaskou (VPN services)
    "35913",    # DediPath (VPN hosting)
    "46562",    # Performive (VPN)
    "25369",    # Hydra Communications
}

# ============================================================================
# VPN KEYWORDS (for netname/org matching)
# ============================================================================

VPN_KEYWORDS = {
    "vpn", "nordvpn", "expressvpn", "surfshark", "protonvpn", "proton ag",
    "mullvad", "cyberghost", "ipvanish", "hide.me", "vyprvpn", "tunnelbear",
    "private internet access", "pia vpn", "hotspot shield", "windscribe",
    "privatevpn", "purevpn", "zenmate", "strongvpn", "airvpn", "ivpn",
    "astrill", "torguard", "perfect privacy", "azire", "oeck",
    "safervpn", "invisiblebrowsing", "ibvpn", "privateinternetaccess",
    "virtual private network", "anonymous proxy", "anonymizer",
    "tefincom", "packethub", "cyberzone",
}

# ============================================================================
# DETECTION LOGIC
# ============================================================================

def is_vpn_range(asn: str, netname: str, org: str) -> bool:
    """Check if the range belongs to a VPN provider."""
    asn_str = str(asn or "").strip()
    netname_lower = (netname or "").lower()
    org_lower = (org or "").lower()
    combined = f"{netname_lower} {org_lower}"
    
    # Check ASN
    if asn_str in VPN_PROVIDER_ASNS:
        return True
    
    # Check keywords
    for keyword in VPN_KEYWORDS:
        if keyword in combined:
            return True
    
    return False


def enrich_vpn_ranges():
    """Main enrichment function."""
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Scanning for VPN ranges...")
    start_time = time.time()
    
    # Load existing vpn_ranges to avoid duplicates
    cursor.execute("SELECT start_ip FROM vpn_ranges")
    existing = set(row["start_ip"] for row in cursor.fetchall())
    print(f"Existing VPN ranges: {len(existing):,}")
    
    # Scan asn_lookup table (has ASN info)
    print("\nScanning asn_lookup table...")
    cursor.execute("""
        SELECT start_ip, end_ip, asn, name, org
        FROM asn_lookup
    """)
    asn_rows = cursor.fetchall()
    
    new_vpn_ranges = []
    
    for row in asn_rows:
        if row["start_ip"] in existing:
            continue
            
        if is_vpn_range(row["asn"], row["name"], row["org"]):
            new_vpn_ranges.append((row["start_ip"], row["end_ip"]))
            existing.add(row["start_ip"])
    
    print(f"Found {len(new_vpn_ranges):,} new VPN ranges from asn_lookup")
    
    # Scan City_layer (has netname/org)
    print("\nScanning City_layer table...")
    cursor.execute("""
        SELECT start_ip, end_ip, asn, netname, org
        FROM City_layer
        WHERE netname IS NOT NULL OR org IS NOT NULL
    """)
    
    city_vpn_count = 0
    for row in cursor:
        if row["start_ip"] in existing:
            continue
            
        if is_vpn_range(row["asn"], row["netname"], row["org"]):
            new_vpn_ranges.append((row["start_ip"], row["end_ip"]))
            existing.add(row["start_ip"])
            city_vpn_count += 1
    
    print(f"Found {city_vpn_count:,} additional VPN ranges from City_layer")
    
    # Insert new ranges
    if new_vpn_ranges:
        print(f"\nInserting {len(new_vpn_ranges):,} new VPN ranges...")
        insert_start = time.time()
        
        cursor.executemany(
            "INSERT OR IGNORE INTO vpn_ranges (start_ip, end_ip) VALUES (?, ?)",
            new_vpn_ranges
        )
        conn.commit()
        
        print(f"Inserted in {time.time() - insert_start:.2f}s")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM vpn_ranges")
    total = cursor.fetchone()[0]
    print(f"\n--- Results ---")
    print(f"Total VPN ranges now: {total:,}")
    print(f"Time taken: {time.time() - start_time:.2f}s")
    
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    enrich_vpn_ranges()
