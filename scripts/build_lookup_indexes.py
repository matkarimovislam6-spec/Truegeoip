#!/usr/bin/env python3
"""
Build lookup indexes for True Geo IP SQLite database.

Run once on the deployment machine:
    python3 scripts/build_lookup_indexes.py --db /var/www/truegeoip/ripe.sqlite
"""

import argparse
import sqlite3
import time
import os

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lookup indexes in SQLite DB.")
    default_db = "databasefull.sqlite" if os.path.exists("databasefull.sqlite") else "ripe.sqlite"
    parser.add_argument("--db", default=default_db, help="Path to IP lookup SQLite DB")
    args = parser.parse_args()

    started = time.time()
    print(f"Opening database: {args.db}")
    conn = sqlite3.connect(args.db)
    try:
        for idx_name, ddl in LOOKUP_INDEX_SQL.items():
            print(f"Creating {idx_name} ...")
            conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()

    print(f"Done in {time.time() - started:.2f}s")


if __name__ == "__main__":
    main()
