"""
enrich_user_types.py - Enriches user_type data based on research patterns.

Classification Logic:
1. DATACENTER: Known hosting ASNs, cloud provider keywords, hosting-related netnames
2. MOBILE: Mobile carrier keywords (mobile, cellular, wireless, 3G, 4G, 5G, LTE)
3. RESIDENTIAL: Everything else (ISPs, telecom that aren't mobile/datacenter)
"""

import sqlite3
import time
import os

DB_FILE = "ripe.sqlite"

# ============================================================================
# DATACENTER CLASSIFICATION
# ============================================================================

# Known datacenter/hosting ASN numbers (from research)
DATACENTER_ASNS = {
    # Major Cloud Providers
    "16509", "14618", "8987",  # AWS/Amazon
    "15169", "396982", "19527", "394089", "36040",  # Google
    "8075", "12076", "8074", "8069",  # Microsoft/Azure
    "13335", "209242",  # Cloudflare
    "14061", "62567",  # DigitalOcean
    "20940", "16625", "63949",  # Akamai
    "16276",  # OVH
    "24940", "213230",  # Hetzner
    "31898",  # Oracle Cloud
    "45102", "37963",  # Alibaba Cloud
    "132203", "45090",  # Tencent Cloud
    "20473", "20454",  # Vultr
    "63949",  # Linode/Akamai
    "51167",  # Contabo
    "12876",  # Scaleway
    "8560",  # IONOS
    "26496", "398101", "400754",  # GoDaddy
    "47583",  # Hostinger
    "22612",  # Namecheap
    "36351",  # IBM/SoftLayer
    
    # Major Hosting Providers
    "9009",  # M247
    "36352",  # ColoCrossing
    "62240",  # Clouvider
    "7979",  # Servers.com
    "8100",  # QuadraNet
    "46606",  # Unified Layer
    "26347",  # DreamHost
    "22611",  # InMotion
    "46844", "32244",  # Liquid Web
    "35916",  # Multacom
    "30083",  # HEG US
    "60781", "28753", "30633", "395954",  # LeaseWeb
    "56106",  # 1337 Services
    "200019",  # AlexHost
    "204957",  # Green Floid
    "50613",  # Makonix
    "62005",  # BlueVPS
    "57043",  # Hostkey
    "35415",  # Webzilla
    "44901",  # Belcloud
    "41079",  # Zurich Datacenter
    
    # VPS / Infrastructure
    "174",  # Cogent
    "3356",  # Level3/Lumen
    "3257",  # GTT
    "6939",  # Hurricane Electric
    "714",  # Apple (engineering)
    "32934",  # Facebook/Meta
    "46664",  # VolumeDrive
    "53667",  # FranTech/BuyVM
    "25369",  # Hydra
    "21100", "60626",  # ITL
    "19844", "33070",  # Zayo
    "206264",  # Amarutu
    "60068",  # Datacamp
    "51852",  # Private Layer
    "44927",  # Constant Company
    "61969",  # TeamViewer
    "397423",  # Tier.Net
    "6939",  # Hurricane Electric
    "46562",  # Performive
    "19551",  # Incapsula
    "55286",  # DataCamp
    "40676",  # Psychz Networks
    "23033",  # Wowrack
    "29802",  # HVC/Hivelocity
    "34549",  # meerfarbig
    "24961",  # myLoc
    "197540",  # netcup
    "29066",  # velia.net
    "42708",  # Portlane
    "50673",  # Serverius
    "49981",  # WorldStream
    "42831",  # UK Dedicated Servers
    "20278",  # Nexeon
    "133618",  # Trellian
    "46475",  # Limenet
    "23470",  # ReliableSite
    "55225",  # IT7 Networks
    "36114",  # Orca Wave
    "3223",  # Voxility
    "199883",  # VPSie
    "19969",  # Joe's Datacenter
    "20264", "27257",  # Webair
    "23352",  # Server Central
    "18779",  # EGIHosting
    "18978",  # Enzu
    "19871",  # Network Solutions
    "22552",  # eSited
    "25820",  # IT7 Networks
    "30475",  # Handy Networks
}

# Keywords in netname/org that indicate datacenter
DATACENTER_KEYWORDS = {
    "amazon", "aws", "azure", "microsoft", "google", "cloud", "gcp",
    "digitalocean", "linode", "vultr", "hetzner", "ovh", "cloudflare",
    "hosting", "host", "server", "datacenter", "datacentre", "data center",
    "vps", "dedicated", "colo", "colocation", "rack", "servers",
    "leaseweb", "softlayer", "rackspace", "godaddy", "dreamhost",
    "hostinger", "bluehost", "hostgator", "ionos", "contabo",
    "scaleway", "upcloud", "kamatera", "cherry", "packet",
    "akamai", "fastly", "cdn", "edgecast", "stackpath",
    "alibaba", "tencent", "huawei cloud", "hwcloud",
    "selectel", "m247", "zenlayer", "imperva", "incapsula",
    "psychz", "quadranet", "phoenixnap", "equinix",
    "gcore", "g-core", "lumen", "cogent",
    "colo", "idc", "noc", "netcup", "myloc", "serverius",
    "worldstream", "frantech", "buyvm", "choopa", "constant",
    "vpn", "proxy", "tunnel", "tor",
}

# ============================================================================
# MOBILE CLASSIFICATION
# ============================================================================

# Keywords in netname/org that indicate mobile carrier
MOBILE_KEYWORDS = {
    "mobile", "cellular", "wireless", "4g", "5g", "3g", "lte", "gsm", "umts",
    "vodafone", "t-mobile", "tmobile", "at&t", "verizon", "sprint",
    "orange mobile", "o2", "ee", "three", "telefonica", "movistar",
    "docomo", "softbank", "kddi", "au by kddi", "rakuten mobile",
    "jio", "reliance jio", "airtel", "vi ", "vodafone idea", "bsnl mobile",
    "china mobile", "china unicom", "china telecom mobile", "cmcc",
    "kt mobile", "sk telecom", "lg uplus", "lgu+",
    "singtel mobile", "starhub mobile", "m1 mobile",
    "globe telecom", "smart communications", "dito",
    "telkomsel", "indosat", "xl axiata", "tri indonesia",
    "maxis", "digi", "celcom", "u mobile",
    "ais", "dtac", "true move", "truemove",
    "viettel", "vinaphone", "mobifone",
    "grameenphone", "robi", "banglalink",
    "jazz", "telenor pak", "zong", "ufone",
    "mtn", "safaricom", "airtel africa", "glo mobile",
    "claro mobile", "movistar mobile", "entel mobile", "personal argentina",
    "telcel", "at&t mexico", "movistar mexico",
    "bell mobility", "rogers wireless", "telus mobility", "freedom mobile",
    "optus mobile", "telstra mobile", "vodafone au",
    "2degrees", "spark nz mobile", "vodafone nz",
    "turkcell", "türk telekom mobile", "vodafone turkey",
    "mts russia", "megafon", "beeline", "tele2 russia",
    "play mobile", "plus gsm", "orange poland", "t-mobile poland",
    "telenor", "telia mobile", "hi3g", "tre",
    "-mobile", "wireless internet", "mobile broadband", "mbb",
    "tot-mobile", "tot mobile",
}

# ============================================================================
# RESIDENTIAL ISP PATTERNS (to ensure they don't get classified as datacenter)
# ============================================================================

RESIDENTIAL_KEYWORDS = {
    "residential", "home", "consumer", "subscriber", "dsl", "adsl", "vdsl",
    "fiber", "fttx", "ftth", "fttp", "cable", "broadband",
    "comcast", "spectrum", "cox", "xfinity", "charter",
    "centurylink", "frontier", "windstream",
    "bt ", "sky ", "virgin media", "talktalk", "plusnet",
    "deutsche telekom", "telekom", "1&1", "unitymedia",
    "free ", "sfr", "bouygues", "orange france",
    "proximus", "telenet", "scarlet",
    "kpn", "ziggo", "t-mobile thuis",
    "telia", "telenor", "tdc ",
    "swisscom", "sunrise", "salt ",
    "movistar", "orange spain", "vodafone spain",
    "tim ", "fastweb", "wind tre",
    "ntt east", "ntt west", "so-net", "ocn", "biglobe",
    "chunghwa telecom", "hinet",
    "pccw", "hkbn", "hkt ",
    "singtel", "starhub", "m1 ",
    "true internet", "3bb", "tot ",
    "pldt", "globe ", "converge",
    "telkom indonesia", "biznet", "cbn ",
    "jcom", "itscom", "catv",
    "customer", "pool", "dynamic", "dhcp", "ppp",
}


def classify_user_type(netname: str, org: str, asn: str) -> str:
    """
    Classify IP range as Datacenter, Mobile, or Residential.
    Priority: Datacenter > Mobile > Residential
    """
    netname_lower = (netname or "").lower()
    org_lower = (org or "").lower()
    asn_str = str(asn or "").strip()
    combined = f"{netname_lower} {org_lower}"
    
    # 1. Check for known datacenter ASN
    if asn_str in DATACENTER_ASNS:
        return "Datacenter"
    
    # 2. Check for datacenter keywords
    for keyword in DATACENTER_KEYWORDS:
        if keyword in combined:
            # Make sure it's not a residential service from a big ISP
            is_residential = any(rk in combined for rk in RESIDENTIAL_KEYWORDS)
            if not is_residential:
                return "Datacenter"
    
    # 3. Check for mobile keywords
    for keyword in MOBILE_KEYWORDS:
        if keyword in combined:
            return "Mobile"
    
    # 4. Default to Residential
    return "Residential"


def enrich_database():
    """Main enrichment function."""
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Loading City_layer ranges that need user_type...")
    start_time = time.time()
    
    # Load all City_layer rows
    cursor.execute("""
        SELECT rowid, start_ip, end_ip, country_iso_code, netname, org, asn
        FROM City_layer
        ORDER BY start_ip
    """)
    city_rows = cursor.fetchall()
    print(f"Loaded {len(city_rows):,} City_layer rows in {time.time() - start_time:.2f}s")
    
    # Load existing user_type ranges for overlap detection
    print("Loading existing user_type ranges...")
    cursor.execute("SELECT start_ip, end_ip FROM user_type ORDER BY start_ip")
    user_type_existing = [(row["start_ip"], row["end_ip"]) for row in cursor.fetchall()]
    print(f"Loaded {len(user_type_existing):,} existing user_type ranges")
    
    # Classify and prepare inserts
    print("Classifying ranges...")
    new_entries = []
    stats = {"Datacenter": 0, "Mobile": 0, "Residential": 0}
    
    u_idx = 0
    n_users = len(user_type_existing)
    processed = 0
    skipped_existing = 0
    
    for row in city_rows:
        c_start = row["start_ip"]
        c_end = row["end_ip"]
        
        # Advance user pointer
        while u_idx < n_users and user_type_existing[u_idx][1] < c_start:
            u_idx += 1
        
        # Check for overlap (already has user_type)
        has_overlap = False
        temp_idx = u_idx
        while temp_idx < n_users:
            u_start, u_end = user_type_existing[temp_idx]
            if u_start > c_end:
                break
            has_overlap = True
            break
            temp_idx += 1
        
        if has_overlap:
            skipped_existing += 1
            processed += 1
            if processed % 500000 == 0:
                print(f"Processed {processed:,}...")
            continue
        
        # Classify
        user_type = classify_user_type(row["netname"], row["org"], row["asn"])
        new_entries.append((c_start, c_end, user_type))
        stats[user_type] += 1
        
        processed += 1
        if processed % 500000 == 0:
            print(f"Processed {processed:,}...")
    
    print(f"\nClassification complete in {time.time() - start_time:.2f}s")
    print(f"Skipped (already has user_type): {skipped_existing:,}")
    print(f"New entries to insert: {len(new_entries):,}")
    print(f"  Datacenter: {stats['Datacenter']:,}")
    print(f"  Mobile:     {stats['Mobile']:,}")
    print(f"  Residential: {stats['Residential']:,}")
    
    # Insert new entries
    if new_entries:
        print("\nInserting new user_type entries...")
        insert_start = time.time()
        
        cursor.executemany(
            "INSERT INTO user_type (start_ip, end_ip, ip_type) VALUES (?, ?, ?)",
            new_entries
        )
        conn.commit()
        
        print(f"Inserted {len(new_entries):,} rows in {time.time() - insert_start:.2f}s")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM user_type")
    total = cursor.fetchone()[0]
    print(f"\nTotal user_type rows now: {total:,}")
    
    cursor.execute("SELECT ip_type, COUNT(*) as cnt FROM user_type GROUP BY ip_type")
    for row in cursor.fetchall():
        print(f"  {row['ip_type']}: {row['cnt']:,}")
    
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    enrich_database()
