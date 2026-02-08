#!/usr/bin/env python3
"""
Shared migration metadata for SQLite -> PostgreSQL migration.
"""

from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple


@dataclass(frozen=True)
class TableSpec:
    source_db: str
    sqlite_table: str
    pg_schema: str
    pg_table: str
    source_columns: Sequence[str]
    column_map: Dict[str, str] = field(default_factory=dict)
    bool_columns: Sequence[str] = field(default_factory=tuple)
    json_columns: Sequence[str] = field(default_factory=tuple)
    date_columns: Sequence[str] = field(default_factory=tuple)
    timestamp_columns: Sequence[str] = field(default_factory=tuple)
    defaults_for_missing: Dict[str, object] = field(default_factory=dict)

    @property
    def target_columns(self) -> Sequence[str]:
        return [self.column_map.get(col, col) for col in self.source_columns]

    @property
    def target_name(self) -> str:
        return f"{self.pg_schema}.{self.pg_table}"


MIGRATION_TABLES: Sequence[TableSpec] = (
    TableSpec(
        source_db="users",
        sqlite_table="users",
        pg_schema="app",
        pg_table="users",
        source_columns=(
            "id",
            "email",
            "password_hash",
            "name",
            "google_id",
            "created_at",
            "is_verified",
            "verification_code",
            "plan",
            "api_key",
            "api_requests_count",
            "last_api_usage_date",
        ),
        bool_columns=("is_verified",),
        date_columns=("last_api_usage_date",),
        timestamp_columns=("created_at",),
        defaults_for_missing={
            "is_verified": 0,
            "verification_code": None,
            "plan": "free",
            "api_key": None,
            "api_requests_count": 0,
            "last_api_usage_date": None,
        },
    ),
    TableSpec(
        source_db="users",
        sqlite_table="projects",
        pg_schema="app",
        pg_table="projects",
        source_columns=("id", "user_id", "name", "created_at"),
        timestamp_columns=("created_at",),
    ),
    TableSpec(
        source_db="users",
        sqlite_table="api_keys",
        pg_schema="app",
        pg_table="api_keys",
        source_columns=("id", "key", "project_id", "name", "created_at", "last_used"),
        timestamp_columns=("created_at", "last_used"),
    ),
    TableSpec(
        source_db="users",
        sqlite_table="licenses",
        pg_schema="app",
        pg_table="licenses",
        source_columns=(
            "id",
            "user_id",
            "license_key",
            "plan_type",
            "status",
            "created_at",
            "expires_at",
            "last_downloaded_at",
        ),
        timestamp_columns=("created_at", "expires_at", "last_downloaded_at"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="analytics_events",
        pg_schema="analytics",
        pg_table="analytics_events",
        source_columns=(
            "id",
            "project_id",
            "timestamp",
            "hashed_ip",
            "country_code",
            "country_name",
            "city",
            "region",
            "asn",
            "asn_name",
            "netname",
            "is_datacenter",
            "is_vpn",
            "user_type",
            "path",
            "method",
            "status_code",
            "metadata",
            "created_at",
        ),
        bool_columns=("is_datacenter", "is_vpn"),
        json_columns=("metadata",),
        timestamp_columns=("timestamp", "created_at"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="analytics_aggregates_hourly",
        pg_schema="analytics",
        pg_table="analytics_aggregates_hourly",
        source_columns=(
            "id",
            "project_id",
            "hour",
            "country_code",
            "asn",
            "is_datacenter",
            "is_vpn",
            "request_count",
            "unique_ip_estimate",
        ),
        bool_columns=("is_datacenter", "is_vpn"),
        timestamp_columns=("hour",),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="analytics_aggregates_daily",
        pg_schema="analytics",
        pg_table="analytics_aggregates_daily",
        source_columns=(
            "id",
            "project_id",
            "date",
            "country_code",
            "asn",
            "netname",
            "request_count",
            "unique_ip_estimate",
            "vpn_count",
            "datacenter_count",
        ),
        date_columns=("date",),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="City_layer",
        pg_schema="lookup",
        pg_table="city_layer",
        source_columns=(
            "network",
            "continent_code",
            "continent_name",
            "country_iso_code",
            "country_name",
            "subdivision_1_iso_code",
            "subdivision_1_name",
            "city_name",
            "metro_code",
            "time_zone",
            "postal_code",
            "latitude",
            "longitude",
            "accuracy_radius",
            "start_ip",
            "end_ip",
            "is_Multicast",
            "is_fallback",
            "is_crawler",
            "netname",
            "org",
            "asn",
            "source",
            "utc_offset",
            "zip_code",
        ),
        column_map={"is_Multicast": "is_multicast"},
        bool_columns=("is_multicast", "is_fallback", "is_crawler"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="Threat_level",
        pg_schema="lookup",
        pg_table="threat_level",
        source_columns=("start_ip", "end_ip", "threat_level"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="asn_lookup",
        pg_schema="lookup",
        pg_table="asn_lookup",
        source_columns=("start_ip", "end_ip", "asn", "name", "org", "domain", "country_code"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="countries",
        pg_schema="lookup",
        pg_table="countries",
        source_columns=("alpha2", "alpha3", "numeric", "name_short", "name_long"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="country_currency",
        pg_schema="lookup",
        pg_table="country_currency",
        source_columns=("country_code", "country_name", "currency_name", "currency_code"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="country_dial",
        pg_schema="lookup",
        pg_table="country_dial",
        source_columns=("country_code", "dial_code"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="crawler_ranges",
        pg_schema="lookup",
        pg_table="crawler_ranges",
        source_columns=("start_ip", "end_ip", "bot_name", "cidr"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="elevation_lookup",
        pg_schema="lookup",
        pg_table="elevation_lookup",
        source_columns=("latitude", "longitude", "elevation"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="fallback_city",
        pg_schema="lookup",
        pg_table="fallback_city",
        source_columns=("country_code", "capital_city"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="ip_ranges",
        pg_schema="lookup",
        pg_table="ip_ranges",
        source_columns=("start_ip", "end_ip", "country", "netname", "org", "source", "is_vpn"),
        bool_columns=("is_vpn",),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="iptwo_new",
        pg_schema="lookup",
        pg_table="iptwo_new",
        source_columns=(
            "ip_from",
            "ip_to",
            "country_code",
            "country_name",
            "region",
            "city",
            "latitude",
            "longitude",
            "zipcode",
            "utc_offset",
            "start_ip",
            "end_ip",
        ),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="user_type",
        pg_schema="lookup",
        pg_table="user_type",
        source_columns=("start_ip", "end_ip", "ip_type"),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="vpn_overrides",
        pg_schema="lookup",
        pg_table="vpn_overrides",
        source_columns=("ip",),
    ),
    TableSpec(
        source_db="lookup",
        sqlite_table="vpn_ranges",
        pg_schema="lookup",
        pg_table="vpn_ranges",
        source_columns=("start_ip", "end_ip"),
    ),
)


IDENTITY_TABLES: Sequence[Tuple[str, str, str]] = (
    ("app", "users", "id"),
    ("app", "api_keys", "id"),
    ("app", "licenses", "id"),
    ("analytics", "analytics_events", "id"),
    ("analytics", "analytics_aggregates_hourly", "id"),
    ("analytics", "analytics_aggregates_daily", "id"),
)
