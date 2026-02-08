#!/usr/bin/env python3
"""
Migrate TrueGeoIP SQLite databases into PostgreSQL.

This migrates:
- users.db       -> app schema (users/projects/api_keys/licenses)
- databasefull.sqlite (or ripe.sqlite) -> analytics + lookup schemas
"""

import argparse
import csv
import io
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from migration_config import IDENTITY_TABLES, MIGRATION_TABLES, TableSpec

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "psycopg2 is required for migration. Install with: pip install psycopg2-binary"
    ) from exc


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def resolve_default_lookup_db() -> str:
    env_value = (os.getenv("IP_DB_FILE", "") or "").strip()
    if env_value:
        return env_value
    if os.path.exists("databasefull.sqlite"):
        return "databasefull.sqlite"
    return "ripe.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SQLite data into PostgreSQL.")
    parser.add_argument(
        "--pg-dsn",
        default=(os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL") or "").strip(),
        help="PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/dbname",
    )
    parser.add_argument("--users-db", default="users.db", help="Path to users SQLite DB")
    parser.add_argument(
        "--lookup-db",
        default=resolve_default_lookup_db(),
        help="Path to lookup/analytics SQLite DB",
    )
    parser.add_argument(
        "--schema-sql",
        default=str(SCRIPT_DIR / "schema.sql"),
        help="Path to PostgreSQL schema SQL file",
    )
    parser.add_argument(
        "--indexes-sql",
        default=str(SCRIPT_DIR / "indexes.sql"),
        help="Path to PostgreSQL indexes SQL file",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=20000,
        help="Rows per COPY batch (default: 20000)",
    )
    parser.add_argument(
        "--truncate-first",
        action="store_true",
        help="Truncate target tables before import",
    )
    parser.add_argument("--skip-users", action="store_true", help="Skip app schema tables")
    parser.add_argument("--skip-analytics", action="store_true", help="Skip analytics schema tables")
    parser.add_argument("--skip-lookup", action="store_true", help="Skip lookup schema tables")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run ANALYZE on all migrated tables after import",
    )
    return parser.parse_args()


def load_sql_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def normalize_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    raw = str(value).strip().lower()
    if raw in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "f", "no", "n", "off", ""}:
        return False
    return None


def normalize_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return json.dumps({"raw": raw}, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def normalize_temporal(value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    return raw


def normalize_value(spec: TableSpec, target_column: str, value):
    if target_column in spec.bool_columns:
        return normalize_bool(value)
    if target_column in spec.json_columns:
        return normalize_json(value)
    if target_column in spec.date_columns or target_column in spec.timestamp_columns:
        return normalize_temporal(value)
    if isinstance(value, str):
        return value.strip() or None
    return value


def value_for_copy(value) -> str:
    if value is None:
        return r"\N"
    if isinstance(value, bool):
        return "t" if value else "f"
    return str(value)


def sqlite_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cursor = conn.execute(f"PRAGMA table_info({quote_ident(table_name)})")
    return [row[1] for row in cursor.fetchall()]


def table_row_count_sqlite(conn: sqlite3.Connection, table_name: str) -> int:
    cursor = conn.execute(f"SELECT COUNT(*) FROM {quote_ident(table_name)}")
    return int(cursor.fetchone()[0])


def copy_table(
    spec: TableSpec,
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    chunk_size: int,
) -> int:
    available_columns = sqlite_columns(sqlite_conn, spec.sqlite_table)
    selected_source_columns = [col for col in spec.source_columns if col in available_columns]
    missing_columns = [col for col in spec.source_columns if col not in available_columns]

    if missing_columns:
        missing_text = ", ".join(missing_columns)
        print(f"[WARN] {spec.sqlite_table}: missing SQLite columns -> {missing_text}")

    select_sql = (
        f"SELECT {', '.join(quote_ident(col) for col in selected_source_columns)} "
        f"FROM {quote_ident(spec.sqlite_table)}"
    )
    select_cur = sqlite_conn.cursor()
    select_cur.execute(select_sql)

    selected_index = {col: idx for idx, col in enumerate(selected_source_columns)}
    source_indexes: List[Optional[int]] = [selected_index.get(col) for col in spec.source_columns]
    target_columns = list(spec.target_columns)

    copy_sql = (
        f"COPY {quote_ident(spec.pg_schema)}.{quote_ident(spec.pg_table)} "
        f"({', '.join(quote_ident(col) for col in target_columns)}) "
        r"FROM STDIN WITH (FORMAT CSV, NULL '\N')"
    )

    copied_rows = 0
    progress_checkpoint = max(chunk_size * 25, 200000)

    with pg_conn.cursor() as pg_cur:
        while True:
            rows = select_cur.fetchmany(chunk_size)
            if not rows:
                break

            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            for row in rows:
                out_row = []
                for col_idx, source_col in enumerate(spec.source_columns):
                    row_index = source_indexes[col_idx]
                    if row_index is None:
                        raw_value = spec.defaults_for_missing.get(source_col)
                    else:
                        raw_value = row[row_index]

                    target_col = target_columns[col_idx]
                    normalized = normalize_value(spec, target_col, raw_value)
                    out_row.append(value_for_copy(normalized))
                writer.writerow(out_row)

            buffer.seek(0)
            pg_cur.copy_expert(copy_sql, buffer)
            copied_rows += len(rows)

            if copied_rows % progress_checkpoint == 0:
                print(f"  {spec.target_name}: copied {copied_rows:,} rows...")

        pg_conn.commit()

    return copied_rows


def truncate_targets(pg_conn, specs: Sequence[TableSpec]) -> None:
    target_tables = ", ".join(
        f"{quote_ident(spec.pg_schema)}.{quote_ident(spec.pg_table)}"
        for spec in specs
    )
    truncate_sql = f"TRUNCATE TABLE {target_tables} RESTART IDENTITY CASCADE"
    with pg_conn.cursor() as cursor:
        cursor.execute(truncate_sql)
    pg_conn.commit()


def reset_identity_sequences(pg_conn) -> None:
    with pg_conn.cursor() as cursor:
        for schema_name, table_name, id_col in IDENTITY_TABLES:
            qualified = f"{schema_name}.{table_name}"
            cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (qualified, id_col))
            seq_name = cursor.fetchone()[0]
            if not seq_name:
                continue

            cursor.execute(
                f"SELECT COALESCE(MAX({quote_ident(id_col)}), 0) "
                f"FROM {quote_ident(schema_name)}.{quote_ident(table_name)}"
            )
            max_id = int(cursor.fetchone()[0] or 0)
            if max_id > 0:
                cursor.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))
            else:
                cursor.execute("SELECT setval(%s, 1, false)", (seq_name,))
    pg_conn.commit()


def should_migrate(spec: TableSpec, args: argparse.Namespace) -> bool:
    if spec.pg_schema == "app" and args.skip_users:
        return False
    if spec.pg_schema == "analytics" and args.skip_analytics:
        return False
    if spec.pg_schema == "lookup" and args.skip_lookup:
        return False
    return True


def apply_sql_script(pg_conn, sql_path: str, label: str) -> None:
    sql_text = load_sql_file(sql_path)
    with pg_conn.cursor() as cursor:
        cursor.execute(sql_text)
    pg_conn.commit()
    print(f"[OK] Applied {label}: {sql_path}")


def main() -> int:
    args = parse_args()

    if not args.pg_dsn:
        print("Missing PostgreSQL DSN. Set --pg-dsn or DATABASE_URL / POSTGRES_DSN env var.")
        return 2

    if not os.path.exists(args.users_db):
        print(f"users SQLite DB not found: {args.users_db}")
        return 2
    if not os.path.exists(args.lookup_db):
        print(f"lookup SQLite DB not found: {args.lookup_db}")
        return 2

    selected_specs = [spec for spec in MIGRATION_TABLES if should_migrate(spec, args)]
    if not selected_specs:
        print("No tables selected to migrate.")
        return 0

    sqlite_conns: Dict[str, sqlite3.Connection] = {}
    started = time.time()

    try:
        sqlite_conns["users"] = sqlite3.connect(f"file:{args.users_db}?mode=ro", uri=True)
        sqlite_conns["lookup"] = sqlite3.connect(f"file:{args.lookup_db}?mode=ro", uri=True)

        pg_conn = psycopg2.connect(args.pg_dsn)
        pg_conn.autocommit = False

        print("[1/5] Creating PostgreSQL schemas and tables...")
        apply_sql_script(pg_conn, args.schema_sql, "schema")

        if args.truncate_first:
            print("[2/5] Truncating target tables...")
            truncate_targets(pg_conn, selected_specs)
        else:
            print("[2/5] Skip truncate (append/merge mode).")

        print("[3/5] Copying data table-by-table...")
        total_rows = 0
        for idx, spec in enumerate(selected_specs, start=1):
            source_conn = sqlite_conns[spec.source_db]
            source_count = table_row_count_sqlite(source_conn, spec.sqlite_table)
            print(
                f"  [{idx}/{len(selected_specs)}] {spec.sqlite_table} -> {spec.target_name} "
                f"(source rows: {source_count:,})"
            )
            copied = copy_table(spec, source_conn, pg_conn, args.chunk_size)
            total_rows += copied
            print(f"     copied {copied:,} rows")

        print("[4/5] Creating PostgreSQL indexes...")
        apply_sql_script(pg_conn, args.indexes_sql, "indexes")

        print("[5/5] Resetting identity sequences...")
        reset_identity_sequences(pg_conn)

        if args.analyze:
            print("Running ANALYZE on migrated tables...")
            with pg_conn.cursor() as cursor:
                for spec in selected_specs:
                    cursor.execute(
                        f"ANALYZE {quote_ident(spec.pg_schema)}.{quote_ident(spec.pg_table)}"
                    )
            pg_conn.commit()

        elapsed = time.time() - started
        print(f"[DONE] Migrated {len(selected_specs)} tables, {total_rows:,} rows in {elapsed:.2f}s")
        print("Run verification:")
        print(
            "  python3 scripts/postgres/verify_postgres_migration.py "
            f"--pg-dsn \"{args.pg_dsn}\" --users-db {args.users_db} --lookup-db {args.lookup_db}"
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] Migration failed: {exc}")
        return 1
    finally:
        for conn in sqlite_conns.values():
            conn.close()
        if "pg_conn" in locals():
            pg_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
