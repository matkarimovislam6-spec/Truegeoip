import sqlite3
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DB_FILE = "ripe.sqlite"

def get_utc_offset(timezone_name):
    """
    Get standard UTC offset for a given timezone name.
    Returns formatted string like '+05:00' or '-08:00'
    """
    if not timezone_name or timezone_name in ('', 'N/A'):
        return None
    
    try:
        # Use January 15 to ensure standard time (not DST)
        tz = ZoneInfo(timezone_name)
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tz)
        offset = dt.utcoffset()
        
        if offset is None:
            return None
        
        # Convert to +HH:MM format
        total_seconds = int(offset.total_seconds())
        hours = total_seconds // 3600
        minutes = abs(total_seconds % 3600) // 60
        
        sign = '+' if total_seconds >= 0 else '-'
        return f"{sign}{abs(hours):02d}:{minutes:02d}"
    
    except ZoneInfoNotFoundError:
        print(f"Warning: Timezone not found: {timezone_name}")
        return None
    except Exception as e:
        print(f"Error processing timezone {timezone_name}: {e}")
        return None

def populate_utc_offsets():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("Analyzing missing UTC offsets...")
    
    # Count rows needing update
    cursor.execute("""
        SELECT COUNT(*) 
        FROM City_layer 
        WHERE (utc_offset IS NULL OR utc_offset = '' OR utc_offset = 'N/A')
        AND time_zone IS NOT NULL 
        AND time_zone != ''
        AND time_zone != 'N/A'
    """)
    total_to_update = cursor.fetchone()[0]
    print(f"Rows needing UTC offset: {total_to_update:,}")
    
    # Get unique timezones that need offsets
    cursor.execute("""
        SELECT DISTINCT time_zone 
        FROM City_layer 
        WHERE (utc_offset IS NULL OR utc_offset = '' OR utc_offset = 'N/A')
        AND time_zone IS NOT NULL 
        AND time_zone != ''
        AND time_zone != 'N/A'
    """)
    
    timezones = [row[0] for row in cursor.fetchall()]
    print(f"Unique timezones to process: {len(timezones)}")
    
    # Create mapping
    print("\nGenerating UTC offset mappings...")
    tz_to_offset = {}
    for tz in timezones:
        offset = get_utc_offset(tz)
        if offset:
            tz_to_offset[tz] = offset
    
    print(f"Successfully mapped {len(tz_to_offset)} timezones")
    
    # Update database in batches
    print("\nUpdating database...")
    updated_count = 0
    batch_size = 10000
    
    for tz, offset in tz_to_offset.items():
        cursor.execute("""
            UPDATE City_layer 
            SET utc_offset = ? 
            WHERE time_zone = ? 
            AND (utc_offset IS NULL OR utc_offset = '' OR utc_offset = 'N/A')
        """, (offset, tz))
        
        updated_count += cursor.rowcount
        
        # Commit periodically
        if updated_count % batch_size == 0:
            conn.commit()
            print(f"  Updated {updated_count:,} rows...")
    
    conn.commit()
    print(f"\n✓ Total rows updated: {updated_count:,}")
    
    # Verify new coverage
    cursor.execute("""
        SELECT COUNT(*) 
        FROM City_layer 
        WHERE utc_offset IS NOT NULL 
        AND utc_offset != '' 
        AND utc_offset != 'N/A'
    """)
    filled = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM City_layer")
    total = cursor.fetchone()[0]
    
    coverage = (filled / total) * 100
    print(f"\nNew UTC Offset Coverage: {coverage:.2f}%")
    print(f"Filled: {filled:,} / {total:,}")
    
    conn.close()

if __name__ == "__main__":
    populate_utc_offsets()
