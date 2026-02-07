"""
enrich_zip_codes.py - Enriches zip_code field using GeoNames postal code data.

Uses GeoNames allCountries.txt format:
country_code, postal_code, place_name, admin_name1, admin_code1, admin_name2, admin_code2, 
admin_name3, admin_code3, latitude, longitude, accuracy
"""

import sqlite3
import os
import time
from collections import defaultdict

DB_FILE = "ripe.sqlite"
GEONAMES_FILE = "allCountries.txt"


def load_geonames_lookup():
    """
    Load GeoNames postal code data into a lookup dictionary.
    Key: (country_code, normalized_city_name)
    Value: postal_code (first one found, as cities can have multiple)
    """
    print("Loading GeoNames postal code data...")
    start = time.time()
    
    # Dictionary: (country_code, city_lower) -> postal_code
    lookup = {}
    # Also track admin regions for fallback
    admin_lookup = defaultdict(str)  # (country_code, admin_name) -> postal_code
    
    with open(GEONAMES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue
            
            country_code = parts[0].strip()
            postal_code = parts[1].strip()
            place_name = parts[2].strip()
            admin_name1 = parts[3].strip() if len(parts) > 3 else ""
            
            if not country_code or not postal_code or not place_name:
                continue
            
            # Normalize city name (lowercase, strip whitespace)
            city_key = place_name.lower()
            key = (country_code, city_key)
            
            # Only store the first postal code for each city (they can have multiple)
            if key not in lookup:
                lookup[key] = postal_code
            
            # Also store by admin region for broader fallback
            if admin_name1:
                admin_key = (country_code, admin_name1.lower())
                if admin_key not in admin_lookup:
                    admin_lookup[admin_key] = postal_code
    
    print(f"Loaded {len(lookup):,} city->postal mappings in {time.time() - start:.2f}s")
    print(f"Loaded {len(admin_lookup):,} admin region fallback mappings")
    
    return lookup, admin_lookup


def enrich_database():
    """Main enrichment function."""
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return
    
    if not os.path.exists(GEONAMES_FILE):
        print(f"Error: {GEONAMES_FILE} not found. Please download from GeoNames.")
        return
    
    # Load lookup
    lookup, admin_lookup = load_geonames_lookup()
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get rows that need zip_code enrichment
    print("\nLoading City_layer rows missing zip_code...")
    cursor.execute("""
        SELECT rowid, country_iso_code, city_name, subdivision_1_name
        FROM City_layer
        WHERE (zip_code IS NULL OR zip_code = '')
        AND city_name IS NOT NULL AND city_name != ''
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows):,} rows to enrich")
    
    # Process and collect updates
    updates = []
    matched_city = 0
    matched_admin = 0
    not_found = 0
    
    for row in rows:
        rowid = row["rowid"]
        country = row["country_iso_code"]
        city = row["city_name"]
        admin = row["subdivision_1_name"]
        
        if not country or not city:
            not_found += 1
            continue
        
        # Try exact city match first
        city_lower = city.lower()
        key = (country, city_lower)
        
        if key in lookup:
            updates.append((lookup[key], rowid))
            matched_city += 1
        elif admin:
            # Try admin region fallback
            admin_key = (country, admin.lower())
            if admin_key in admin_lookup:
                updates.append((admin_lookup[admin_key], rowid))
                matched_admin += 1
            else:
                not_found += 1
        else:
            not_found += 1
    
    print(f"\n--- Match Results ---")
    print(f"Matched by city name: {matched_city:,}")
    print(f"Matched by admin region: {matched_admin:,}")
    print(f"Not found: {not_found:,}")
    print(f"Total updates to apply: {len(updates):,}")
    
    # Apply updates
    if updates:
        print("\nApplying updates to database...")
        start = time.time()
        
        cursor.executemany(
            "UPDATE City_layer SET zip_code = ? WHERE rowid = ?",
            updates
        )
        conn.commit()
        
        print(f"Updated {len(updates):,} rows in {time.time() - start:.2f}s")
    
    # Verify new coverage
    print("\n--- New Coverage Stats ---")
    cursor.execute("SELECT COUNT(*) FROM City_layer")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM City_layer WHERE zip_code IS NOT NULL AND zip_code != ''")
    filled = cursor.fetchone()[0]
    
    coverage = (filled / total * 100) if total > 0 else 0
    print(f"Total rows: {total:,}")
    print(f"Rows with zip_code: {filled:,}")
    print(f"New coverage: {coverage:.2f}%")
    
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    enrich_database()
