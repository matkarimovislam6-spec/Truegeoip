#!/usr/bin/env python3
"""
Populate the Threat_level table with data from multiple open-source threat feeds.

Sources (HIGH threat - confirmed malicious):
- FireHOL Level 1 (C&C, botnets, worst offenders)
- Spamhaus DROP (hijacked IP space)
- abuse.ch Feodo Tracker (banking trojans)

Sources (MEDIUM threat - active attacks):
- FireHOL Level 2 (scanning, brute force)
- blocklist.de (honeypot attacks)
- IPsum (aggregated from 30+ lists)

Sources (LOW threat - lower confidence):
- FireHOL Level 3 (mass scanning)
- DShield (top attackers)
"""

import sqlite3
import ipaddress
import urllib.request
import sys
from typing import Tuple, Generator, Union, List

DB_FILE = "ripe.sqlite"

# Sources organized by threat level
THREAT_SOURCES = {
    "high": [
        # FireHOL Level 1 - worst offenders
        "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
        # Spamhaus DROP - hijacked IP space (CIDR blocks)
        "https://www.spamhaus.org/drop/drop.txt",
        # abuse.ch Feodo Tracker - banking trojans C&C
        "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
        # Emerging Threats compromised IPs
        "https://rules.emergingthreats.net/blockrules/compromised-ips.txt",
        # TOR exit nodes (high risk for abuse)
        "https://raw.githubusercontent.com/SecOps-Institute/Tor-IP-Addresses/master/tor-exit-nodes.lst",
        # IPsum Level 6 (IPs in 6 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/6.txt",
        # IPsum Level 7 (IPs in 7 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/7.txt",
        # IPsum Level 8 (IPs in 8+ lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/8.txt",
    ],
    "medium": [
        # FireHOL Level 2 - active threats
        "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level2.netset",
        # blocklist.de - all attack types from honeypots
        "https://lists.blocklist.de/lists/all.txt",
        # IPsum Level 3 (IPs in 3 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/3.txt",
        # IPsum Level 4 (IPs in 4 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/4.txt",
        # IPsum Level 5 (IPs in 5 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/5.txt",
        # Data-Shield Full List (~100k IPs) - usage policy: attribution required
        "https://raw.githubusercontent.com/duggytuxy/Data-Shield_IPv4_Blocklist/main/prod_data-shield_ipv4_blocklist.txt",
        # CI Army badguys
        "https://cinsscore.com/list/ci-badguys.txt",
        # Greensnow blocklist
        "https://blocklist.greensnow.co/greensnow.txt",
    ],
    "low": [
        # FireHOL Level 3 - lower confidence
        "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level3.netset", 
        # DShield - top attackers (high turnover)
        "https://feeds.dshield.org/block.txt",
        # Bruteforce login attempts
        "https://lists.blocklist.de/lists/bruteforcelogin.txt",
        # SSH attacks
        "https://lists.blocklist.de/lists/ssh.txt",
        # Mail server attacks
        "https://lists.blocklist.de/lists/mail.txt",
        # FTP attacks
        "https://lists.blocklist.de/lists/ftp.txt",
        # Apache/web attacks
        "https://lists.blocklist.de/lists/apache.txt",
        # IMAP attacks
        "https://lists.blocklist.de/lists/imap.txt",
        # SIP/VoIP attacks
        "https://lists.blocklist.de/lists/sip.txt",
        # IPsum Level 1 (IPs in 1+ lists - very noisy)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/1.txt",
        # IPsum Level 2 (IPs in 2 lists)
        "https://raw.githubusercontent.com/stamparm/ipsum/master/levels/2.txt",
        # OpenProxyDB - Wikipedia blocked proxies (daily)
        "https://raw.githubusercontent.com/NetworkCats/OpenProxyDB/main/proxydb.csv",
        # Bots/Crawlers IPs
        "https://lists.blocklist.de/lists/bots.txt",
        # StrongVPN/NordVPN datacenter ranges (aggregated)
        "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/vpn/ipv4.txt",
        # Datacenter IP ranges
        "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/datacenter/ipv4.txt",
        # Cloud provider ranges (AWS, GCP, Azure - often abused)
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/all/ipv4_merged.txt",
        # Myip.ms blacklist
        "https://myip.ms/files/blacklist/general/latest_blacklist.txt",
        # Blocklist.de strongips (persistent attackers)
        "https://lists.blocklist.de/lists/strongips.txt",
        # Team Cymru fullbogons (unallocated + reserved - ~600M IPs)
        "https://www.team-cymru.org/Services/Bogons/fullbogons-ipv4.txt",
        # AWS IP ranges (cloud infrastructure)
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/amazon/ipv4_merged.txt",
        # Google Cloud IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/google/ipv4_merged.txt",
        # Microsoft Azure IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/microsoft/ipv4_merged.txt",
        # DigitalOcean IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/digitalocean/ipv4_merged.txt",
        # Oracle Cloud IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/oracle/ipv4_merged.txt",
        # Linode IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/linode/ipv4_merged.txt",
        # Vultr IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/vultr/ipv4_merged.txt",
        # OVH IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/ovh/ipv4_merged.txt",
        # Hetzner IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/hetzner/ipv4_merged.txt",
        # Cloudflare IP ranges
        "https://raw.githubusercontent.com/lord-alfred/ipranges/main/cloudflare/ipv4_merged.txt",
        # Hosting providers aggregated list
        "https://raw.githubusercontent.com/jhassine/server-ip-addresses/master/data/datacenters.txt",
        # China IP ranges (~340M IPs - high attack origin)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/cn/ipv4-aggregated.txt",
        # Russia IP ranges (~50M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ru/ipv4-aggregated.txt",
        # North Korea IP ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/kp/ipv4-aggregated.txt",
        # Iran IP ranges (~15M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ir/ipv4-aggregated.txt",
        # Vietnam IP ranges (~15M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/vn/ipv4-aggregated.txt",
        # Indonesia IP ranges (~20M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/id/ipv4-aggregated.txt",
        # United States IP ranges (~1.6B IPs - LARGEST)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/us/ipv4-aggregated.txt",
        # Japan IP ranges (~200M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/jp/ipv4-aggregated.txt",
        # Germany IP ranges (~120M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/de/ipv4-aggregated.txt",
        # United Kingdom IP ranges (~100M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/gb/ipv4-aggregated.txt",
        # South Korea IP ranges (~110M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/kr/ipv4-aggregated.txt",
        # France IP ranges (~90M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/fr/ipv4-aggregated.txt",
        # Brazil IP ranges (~80M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/br/ipv4-aggregated.txt",
        # Canada IP ranges (~80M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ca/ipv4-aggregated.txt",
        # Australia IP ranges (~60M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/au/ipv4-aggregated.txt",
        # India IP ranges (~50M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/in/ipv4-aggregated.txt",
        # Netherlands IP ranges (~50M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/nl/ipv4-aggregated.txt",
        # Italy IP ranges (~50M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/it/ipv4-aggregated.txt",
        # Spain IP ranges (~40M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/es/ipv4-aggregated.txt",
        # Poland IP ranges (~35M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/pl/ipv4-aggregated.txt",
        # Taiwan IP ranges (~35M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/tw/ipv4-aggregated.txt",
        # Sweden IP ranges (~25M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/se/ipv4-aggregated.txt",
        # Switzerland IP ranges (~20M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ch/ipv4-aggregated.txt",
        # Mexico IP ranges (~30M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/mx/ipv4-aggregated.txt",
        # Argentina IP ranges (~25M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ar/ipv4-aggregated.txt",
        # South Africa IP ranges (~20M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/za/ipv4-aggregated.txt",
        # Turkey IP ranges (~20M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/tr/ipv4-aggregated.txt",
        # Ukraine IP ranges (~15M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ua/ipv4-aggregated.txt",
        # Thailand IP ranges (~15M IPs)
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/th/ipv4-aggregated.txt",
        # Spamhaus EDROP (now merged into DROP - cybercrime networks)
        "https://www.spamhaus.org/drop/edrop.txt",
        # === IPv6 SOURCES ===
        # Team Cymru fullbogons IPv6 (unallocated/reserved)
        "https://www.team-cymru.org/Services/Bogons/fullbogons-ipv6.txt",
        # Spamhaus DROPv6 (hijacked IPv6 space)
        "https://www.spamhaus.org/drop/dropv6.txt",
        # TOR exit nodes IPv6
        "https://raw.githubusercontent.com/SecOps-Institute/Tor-IP-Addresses/master/tor-exit-nodes-ipv6.lst",
        # US IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/us/ipv6-aggregated.txt",
        # China IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/cn/ipv6-aggregated.txt",
        # Germany IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/de/ipv6-aggregated.txt",
        # Japan IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/jp/ipv6-aggregated.txt",
        # UK IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/gb/ipv6-aggregated.txt",
        # France IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/fr/ipv6-aggregated.txt",
        # Russia IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ru/ipv6-aggregated.txt",
        # Netherlands IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/nl/ipv6-aggregated.txt",
        # Brazil IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/br/ipv6-aggregated.txt",
        # Australia IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/au/ipv6-aggregated.txt",
        # India IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/in/ipv6-aggregated.txt",
        # South Korea IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/kr/ipv6-aggregated.txt",
        # Canada IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/ca/ipv6-aggregated.txt",
        # Italy IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/it/ipv6-aggregated.txt",
        # Spain IPv6 ranges
        "https://raw.githubusercontent.com/ipverse/rir-ip/master/country/es/ipv6-aggregated.txt",
    ],
}


def ip_to_hex(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> str:
    """Convert IP address to zero-padded hex string (32 chars for consistency)."""
    return ip.packed.hex().zfill(32)


def parse_ip_list(content: str) -> Generator[Tuple[str, str], None, None]:
    """
    Parse various IP list formats.
    Handles: CIDR, single IPs, comments (#, ;), whitespace, tabs.
    Yields (start_ip_hex, end_ip_hex) tuples.
    """
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        
        # Handle tab/space separated (e.g., DShield format: "Start\tEnd\tCount")
        parts = line.split()
        if not parts:
            continue
        
        # Take first token as IP/CIDR
        ip_str = parts[0]
        
        # Skip non-IP lines (headers, etc.) - allow hex chars for IPv6
        if not (ip_str[0].isdigit() or ip_str[0].lower() in 'abcdef' or ':' in ip_str):
            continue
        
        try:
            if "/" in ip_str:
                # CIDR notation
                network = ipaddress.ip_network(ip_str, strict=False)
                start_ip = network.network_address
                end_ip = network.broadcast_address
            else:
                # Single IP
                ip = ipaddress.ip_address(ip_str)
                start_ip = ip
                end_ip = ip
            
            yield ip_to_hex(start_ip), ip_to_hex(end_ip)
        except ValueError:
            # Skip invalid entries silently (there will be many)
            continue


def download_list(url: str) -> str:
    """Download list content from URL with timeout."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ThreatLevelPopulator/2.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [ERROR] Failed to download {url}: {e}")
        return ""


def create_table(conn: sqlite3.Connection) -> None:
    """Create the Threat_level table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Threat_level (
            start_ip TEXT NOT NULL,
            end_ip TEXT NOT NULL,
            threat_level TEXT NOT NULL CHECK(threat_level IN ('low', 'medium', 'high'))
        )
    """)
    conn.commit()


def deduplicate_table(conn: sqlite3.Connection) -> int:
    """Deduplicate entries, keeping highest threat level. Returns rows removed."""
    print("\nDeduplicating entries (keeping highest threat level)...")
    
    before_count = conn.execute("SELECT COUNT(*) FROM Threat_level").fetchone()[0]
    
    # Create deduplicated table
    conn.execute("""
        CREATE TABLE Threat_level_dedup AS
        SELECT start_ip, end_ip, 
               CASE 
                 WHEN MAX(CASE threat_level WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 END) = 3 THEN 'high'
                 WHEN MAX(CASE threat_level WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 END) = 2 THEN 'medium'
                 ELSE 'low'
               END as threat_level
        FROM Threat_level
        GROUP BY start_ip, end_ip
    """)
    
    # Swap tables
    conn.execute("DROP TABLE Threat_level")
    conn.execute("ALTER TABLE Threat_level_dedup RENAME TO Threat_level")
    conn.commit()
    
    after_count = conn.execute("SELECT COUNT(*) FROM Threat_level").fetchone()[0]
    removed = before_count - after_count
    print(f"  Removed {removed:,} duplicates ({before_count:,} -> {after_count:,})")
    
    return removed


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes for efficient lookups."""
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_threat_level_start ON Threat_level(start_ip)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_threat_level_end ON Threat_level(end_ip)")
    conn.commit()


def populate_threat_level() -> dict:
    """Main function to populate the Threat_level table."""
    conn = sqlite3.connect(DB_FILE)
    
    # Create table
    print("Creating Threat_level table...")
    create_table(conn)
    
    # Clear existing data
    print("Clearing existing data...")
    conn.execute("DELETE FROM Threat_level")
    conn.commit()
    
    stats = {"high": 0, "medium": 0, "low": 0}
    
    for threat_level, urls in THREAT_SOURCES.items():
        print(f"\n{'='*60}")
        print(f"Processing {threat_level.upper()} threat level ({len(urls)} sources)")
        print("="*60)
        
        level_total = 0
        
        for url in urls:
            source_name = url.split("/")[-1][:40]
            print(f"\n  [{source_name}]")
            
            content = download_list(url)
            if not content:
                continue
            
            entries = list(parse_ip_list(content))
            if not entries:
                print(f"    No valid entries found")
                continue
            
            print(f"    Parsed {len(entries):,} entries")
            
            # Batch insert
            conn.executemany(
                "INSERT INTO Threat_level (start_ip, end_ip, threat_level) VALUES (?, ?, ?)",
                [(start, end, threat_level) for start, end in entries]
            )
            conn.commit()
            
            level_total += len(entries)
        
        stats[threat_level] = level_total
        print(f"\n  SUBTOTAL: {level_total:,} {threat_level} entries")
    
    # Deduplicate
    deduplicate_table(conn)
    
    # Create indexes
    create_indexes(conn)
    
    # Final statistics
    final_stats = {}
    for level in ["high", "medium", "low"]:
        count = conn.execute(
            "SELECT COUNT(*) FROM Threat_level WHERE threat_level = ?", (level,)
        ).fetchone()[0]
        final_stats[level] = count
    
    final_stats["total"] = conn.execute("SELECT COUNT(*) FROM Threat_level").fetchone()[0]
    
    conn.close()
    
    return final_stats


if __name__ == "__main__":
    print("=" * 60)
    print("Enhanced Threat Level Importer v2.0")
    print("=" * 60)
    
    stats = populate_threat_level()
    
    print("\n" + "=" * 60)
    print("FINAL STATISTICS (after deduplication)")
    print("=" * 60)
    print(f"  HIGH threat entries:   {stats['high']:>10,}")
    print(f"  MEDIUM threat entries: {stats['medium']:>10,}")
    print(f"  LOW threat entries:    {stats['low']:>10,}")
    print(f"  {'─' * 30}")
    print(f"  TOTAL unique entries:  {stats['total']:>10,}")
    print("=" * 60)
    print("Done!")
