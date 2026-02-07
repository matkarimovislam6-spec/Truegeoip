
import sqlite3
import pandas as pd

def hex_to_int(hex_str):
    try:
        return int(hex_str, 16)
    except:
        return 0

def analyze_coverage():
    print("Connecting to database...")
    conn = sqlite3.connect('ripe.sqlite')
    
    print("Fetching City_layer data...")
    df = pd.read_sql_query("SELECT start_ip, end_ip, country_iso_code FROM City_layer", conn)
    conn.close()
    
    print(f"Loaded {len(df)} records.")
    
    # Convert hex to int
    print("Converting IP addresses...")
    df['start_int'] = df['start_ip'].apply(hex_to_int)
    df['end_int'] = df['end_ip'].apply(hex_to_int)
    
    # Filter valid IPv4 (max 2^32 - 1)
    # 0xFFFFFFFF = 4294967295
    MAX_IPV4 = 4294967295
    df = df[df['end_int'] <= MAX_IPV4]
    
    print(f"Valid IPv4 records: {len(df)}")
    
    # Sort by start_ip
    df = df.sort_values('start_int')
    
    # Calculate unique IPs covered (handling overlaps)
    print("Calculating unique coverage...")
    total_ips = 0
    current_start = -1
    current_end = -1
    
    # We can't easily do this with pandas vectorization perfectly if there are many overlaps,
    # but let's do a simple iteration or optimized approach.
    # Actually, simplistic sum is a good upper bound, but let's try to be accurate.
    
    # Merging intervals
    intervals = []
    for _, row in df[['start_int', 'end_int']].iterrows():
        s, e = row['start_int'], row['end_int']
        if s > current_end + 1:
            if current_start != -1:
                total_ips += (current_end - current_start + 1)
            current_start = s
            current_end = e
        else:
            current_end = max(current_end, e)
            
    if current_start != -1:
        total_ips += (current_end - current_start + 1)
        
    print(f"Total Unique IPs Covered: {total_ips:,}")
    percentage = (total_ips / MAX_IPV4) * 100
    print(f"Coverage Percentage: {percentage:.2f}%")
    
    # Country breakdown (approximation using simple sum, knowing overlap might skew slightly but good for ranking)
    df['count'] = df['end_int'] - df['start_int'] + 1
    country_stats = df.groupby('country_iso_code')['count'].sum().sort_values(ascending=False)
    
    print("\nTop 10 Countries by IP Count:")
    print(country_stats.head(10))
    
    print("\nBottom 10 Countries (potential improvement areas):")
    print(country_stats.tail(10))

if __name__ == "__main__":
    analyze_coverage()
