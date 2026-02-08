#!/usr/bin/env python3
"""
Verify SQLite -> PostgreSQL migration by comparing row counts table-by-table.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from migration_config import MIGRATION_TABLES, TableSpec

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "psycopg2 is required for verification. Install with: pip install psycopg2-binary"
    ) from exc


def resolve_default_lookup_db() -> str:
    env_value = (os.getenv("IP_DB_FILE", "") or "").strip()
    if env_value:
        return env_value
    if os.path.exists("databasefull.sqlite"):
        return "databasefull.sqlite"
    return "ripe.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify SQLite -> PostgreSQL migration.")
    parser.add_argument(
        "--pg-dsn",
        default=(os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL") or "").strip(),
        help="PostgreSQL DSN",
    )
    parser.add_argument("--users-db", default="users.db", help="Path to users SQLite DB")
    parser.add_argument("--lookup-db", default=resolve_default_lookup_db(), help="Path to lookup SQLite DB")
    parser.add_argument("--fail-on-mismatch", action="store_true", help="Exit non-zero if any mismatch")
    return parser.parse_args()


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sqlite_count(conn: sqlite3.Connection, table_name: str) -> int:
    cursor = conn.execute(f"SELECT COUNT(*) FROM {quote_ident(table_name)}")
    return int(cursor.fetchone()[0])


def pg_count(conn, spec: TableSpec) -> int:
    query = (
        f"SELECT COUNT(*) FROM {quote_ident(spec.pg_schema)}.{quote_ident(spec.pg_table)}"
    )
    with conn.cursor() as cursor:
        cursor.execute(query)
        return int(cursor.fetchone()[0])


def main() -> int:
    args = parse_args()
    if not args.pg_dsn:
        print("Missing PostgreSQL DSN. Set --pg-dsn or DATABASE_URL / POSTGRES_DSN.")
        return 2

    if not os.path.exists(args.users_db):
        print(f"users SQLite DB not found: {args.users_db}")
        return 2
    if not os.path.exists(args.lookup_db):
        print(f"lookup SQLite DB not found: {args.lookup_db}")
        return 2

    sqlite_conns: Dict[str, sqlite3.Connection] = {
        "users": sqlite3.connect(f"file:{args.users_db}?mode=ro", uri=True),
        "lookup": sqlite3.connect(f"file:{args.lookup_db}?mode=ro", uri=True),
    }

    mismatches = 0
    try:
        pg_conn = psycopg2.connect(args.pg_dsn)

        print("Table Count Verification")
        print("-" * 100)
        print(f"{'Table':50} {'SQLite':>15} {'Postgres':>15} {'Status':>12}")
        print("-" * 100)

        for spec in MIGRATION_TABLES:
            sqlite_rows = sqlite_count(sqlite_conns[spec.source_db], spec.sqlite_table)
            postgres_rows = pg_count(pg_conn, spec)
            ok = sqlite_rows == postgres_rows
            status = "OK" if ok else "MISMATCH"
            if not ok:
                mismatches += 1
            print(
                f"{spec.sqlite_table + ' -> ' + spec.target_name:50} "
                f"{sqlite_rows:15,} {postgres_rows:15,} {status:>12}"
            )

        print("-" * 100)
        if mismatches == 0:
            print("Verification passed: all table counts match.")
            return 0

        print(f"Verification failed: {mismatches} table(s) mismatched.")
        return 1 if args.fail_on_mismatch else 0
    finally:
        for conn in sqlite_conns.values():
            conn.close()
        if "pg_conn" in locals():
            pg_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
