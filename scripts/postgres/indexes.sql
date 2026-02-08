CREATE INDEX IF NOT EXISTS idx_users_email_lower ON app.users (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON app.projects (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_project_id ON app.api_keys (project_id);
CREATE INDEX IF NOT EXISTS idx_licenses_user_id ON app.licenses (user_id);

CREATE INDEX IF NOT EXISTS idx_events_project_ts
    ON analytics.analytics_events (project_id, "timestamp");
CREATE INDEX IF NOT EXISTS idx_events_created
    ON analytics.analytics_events (created_at);
CREATE INDEX IF NOT EXISTS idx_hourly_project
    ON analytics.analytics_aggregates_hourly (project_id, hour);
CREATE INDEX IF NOT EXISTS idx_daily_project
    ON analytics.analytics_aggregates_daily (project_id, date);

CREATE INDEX IF NOT EXISTS idx_city_layer_start_ip
    ON lookup.city_layer (start_ip);
CREATE INDEX IF NOT EXISTS idx_city_layer_start_end
    ON lookup.city_layer (start_ip, end_ip);

CREATE INDEX IF NOT EXISTS idx_asn_lookup_start_ip
    ON lookup.asn_lookup (start_ip);
CREATE INDEX IF NOT EXISTS idx_asn_lookup_start_end
    ON lookup.asn_lookup (start_ip, end_ip);

CREATE INDEX IF NOT EXISTS idx_ip_ranges_start_ip
    ON lookup.ip_ranges (start_ip);
CREATE INDEX IF NOT EXISTS idx_ip_ranges_start_end
    ON lookup.ip_ranges (start_ip, end_ip);

CREATE INDEX IF NOT EXISTS idx_vpn_ranges_start_ip
    ON lookup.vpn_ranges (start_ip);
CREATE INDEX IF NOT EXISTS idx_user_type_start_ip
    ON lookup.user_type (start_ip);
CREATE INDEX IF NOT EXISTS idx_user_type_start_end
    ON lookup.user_type (start_ip, end_ip);
CREATE INDEX IF NOT EXISTS idx_threat_level_start_ip
    ON lookup.threat_level (start_ip);
CREATE INDEX IF NOT EXISTS idx_threat_level_end_ip
    ON lookup.threat_level (end_ip);

CREATE INDEX IF NOT EXISTS idx_elevation_lookup_lat_lon
    ON lookup.elevation_lookup (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_crawler_start_ip
    ON lookup.crawler_ranges (start_ip);
CREATE INDEX IF NOT EXISTS idx_iptwo_new_start_end
    ON lookup.iptwo_new (start_ip, end_ip);
