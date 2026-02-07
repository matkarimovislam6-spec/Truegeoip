import sqlite3
import csv
import os
import time
from typing import List, Tuple

DB_FILE = "ripe.sqlite"
OUTPUT_FILE = "missing_user_types.csv"

def load_data():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return None, None

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Loading City_layer ranges...")
    # Fetching columns needed for report + start/end for logic
    cursor.execute("""
        SELECT start_ip, end_ip, country_iso_code, netname, org, source 
        FROM City_layer 
        ORDER BY start_ip
    """)
    city_ranges = [dict(row) for row in cursor]
    print(f"Loaded {len(city_ranges):,} City_layer ranges.")

    print("Loading user_type ranges...")
    cursor.execute("SELECT start_ip, end_ip FROM user_type ORDER BY start_ip")
    # Store as tuples for faster access: (start_ip, end_ip)
    user_type_ranges = [(row["start_ip"], row["end_ip"]) for row in cursor]
    print(f"Loaded {len(user_type_ranges):,} user_type ranges.")

    conn.close()
    return city_ranges, user_type_ranges

def is_hex_range_covered(city_start: str, city_end: str, user_ranges: List[Tuple[str, str]]) -> bool:
    """
    Checks if the city range is covered by ANY user_type range.
    Uses binary search or efficient scanning since user_ranges is sorted.
    
    Since we need to check if ANY part of the city range overlaps, 
    we need to find if there exists a user range [u_start, u_end] such that:
    max(city_start, u_start) <= min(city_end, u_end)
    Refined: We want to know if the city range is *fully covered* or just *overlaps*.
    The user request says "fill up later", implying they want to find ranges that have NO user_type.
    So if even a partial overlap exists, we might count it as covered? 
    Or strictly checks for ranges that are completely absent?
    
    Let's assume "missing" means the city range has NO corresponding user_type entry 
    for its IP space. 
    However, 1-to-1 mapping is ideal. A city range might be large and partially covered.
    For simplicity and "filling up", let's flag it if we can't find a covering range.
    
    Optimized approach for sorted lists:
    We can iterate through city ranges and maintain a pointer in user_ranges.
    """
    return False # Placeholder - logic implemented in main loop for efficiency

def analyze():
    city_ranges, user_type_ranges = load_data()
    if not city_ranges or not user_type_ranges:
        return

    print("Analyzing for missing user types...")
    start_time = time.time()

    missing_ranges = []
    
    # Pointers
    u_idx = 0
    n_users = len(user_type_ranges)
    
    # Stats
    checked_count = 0
    
    for city in city_ranges:
        c_start = city["start_ip"]
        c_end = city["end_ip"]
        
        # Advance user pointer while user range ends before city range starts
        # user_end < city_start
        while u_idx < n_users and user_type_ranges[u_idx][1] < c_start:
            u_idx += 1
            
        # Check for overlap with current or subsequent user ranges
        # Overlap condition: max(c_start, u_start) <= min(c_end, u_end)
        # Since u_idx is advanced such that u_end >= c_start (or we ran out),
        # we only need to check if u_start <= c_end.
        
        has_overlap = False
        
        # Look ahead in user ranges that might overlap
        # We don't advance u_idx permanently here because a user range might overlap multiple small city ranges
        temp_idx = u_idx
        while temp_idx < n_users:
            u_start, u_end = user_type_ranges[temp_idx]
            
            if u_start > c_end:
                # User range starts after city range ends -> No more possible overlaps for this city
                break
            
            # Since u_end >= c_start (guaranteed by initial while loop)
            # AND u_start <= c_end (guaranteed by simple check above)
            # -> We have an overlap
            has_overlap = True
            break
            
            # Note: We are just checking for ANY overlap. 
            # If we wanted to check for FULL coverage it would be more complex.
            # Given the prompt "fill up later", finding ranges with NO overlap is the safest first step.
            
        if not has_overlap:
            missing_ranges.append(city)
            
        checked_count += 1
        if checked_count % 100000 == 0:
            print(f"Processed {checked_count:,} ranges...")

    print(f"Analysis complete in {time.time() - start_time:.2f}s")
    print(f"Found {len(missing_ranges):,} missing ranges.")
    
    # Save to CSV
    print(f"Saving to {OUTPUT_FILE}...")
    headers = ["start_ip", "end_ip", "country_iso_code", "netname", "org", "source"]
    
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            # Only write keys that exist in headers
            for row in missing_ranges:
                writer.writerow({k: row[k] for k in headers})
                
        print("CSV saved successfully.")
    except Exception as e:
        print(f"Error saving CSV: {e}")

    # Summary by Country
    print("\n--- Top 20 Countries with Missing User Types ---")
    country_counts = {}
    for r in missing_ranges:
        cc = r["country_iso_code"] or "N/A"
        country_counts[cc] = country_counts.get(cc, 0) + 1
        
    sorted_counts = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for cc, count in sorted_counts:
        print(f"{cc}: {count:,}")

if __name__ == "__main__":
    analyze()
