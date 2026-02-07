
import sqlite3
import pandas as pd

def hex_to_int(hex_str):
    try:
        return int(hex_str, 16)
    except:
        return 0

def analyze_details():
    try:
        conn = sqlite3.connect('ripe.sqlite')
        
        print("\n--- User Type Analysis ---")
        df_user = pd.read_sql_query("SELECT ip_type, start_ip, end_ip FROM user_type", conn)
        df_user['start_int'] = df_user['start_ip'].apply(hex_to_int)
        df_user['end_int'] = df_user['end_ip'].apply(hex_to_int)
        df_user['count'] = df_user['end_int'] - df_user['start_int'] + 1
        
        # Max IPv4 filter
        MAX_IPV4 = 4294967295
        df_user = df_user[df_user['end_int'] <= MAX_IPV4]
        
        user_stats = df_user.groupby('ip_type')['count'].sum().sort_values(ascending=False)
        print(user_stats)
        
        print("\n--- VPN Analysis ---")
        df_vpn = pd.read_sql_query("SELECT start_ip, end_ip FROM vpn_ranges", conn)
        df_vpn['start_int'] = df_vpn['start_ip'].apply(hex_to_int)
        df_vpn['end_int'] = df_vpn['end_ip'].apply(hex_to_int)
        df_vpn['count'] = df_vpn['end_int'] - df_vpn['start_int'] + 1
        df_vpn = df_vpn[df_vpn['end_int'] <= MAX_IPV4]
        
        total_vpn_ips = df_vpn['count'].sum()
        print(f"Total VPN IPs: {total_vpn_ips:,}")
        
        print("\n--- Top ASNs (by IP Count) ---")
        # For ASN, we use City_layer as a proxy for now, but City_layer has 'asn' field.
        # Ideally we'd use asn_lookup table if it exists and is populated?
        # Step 961 shows table 'asn_lookup'. Let's check it.
        # But for request "total coverage %", City_layer is the main one.
        # Let's use City_layer's 'asn' column.
        
        df_city = pd.read_sql_query("SELECT asn, start_ip, end_ip FROM City_layer WHERE asn IS NOT NULL AND asn != ''", conn)
        df_city['start_int'] = df_city['start_ip'].apply(hex_to_int)
        df_city['end_int'] = df_city['end_ip'].apply(hex_to_int)
        df_city['count'] = df_city['end_int'] - df_city['start_int'] + 1
        df_city = df_city[df_city['end_int'] <= MAX_IPV4]
        
        asn_stats = df_city.groupby('asn')['count'].sum().sort_values(ascending=False).head(10)
        print(asn_stats)
        
        print("\n--- Top Netnames (by IP Count) ---")
        df_net = pd.read_sql_query("SELECT netname, start_ip, end_ip FROM City_layer WHERE netname IS NOT NULL", conn)
        df_net['start_int'] = df_net['start_ip'].apply(hex_to_int)
        df_net['end_int'] = df_net['end_ip'].apply(hex_to_int)
        df_net['count'] = df_net['end_int'] - df_net['start_int'] + 1
        df_net = df_net[df_net['end_int'] <= MAX_IPV4]
        
        net_stats = df_net.groupby('netname')['count'].sum().sort_values(ascending=False).head(10)
        print(net_stats)
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_details()
