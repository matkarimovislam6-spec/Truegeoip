# PostgreSQL Migration

This folder contains the full SQLite -> PostgreSQL migration pipeline.

## What gets migrated

- `users.db` tables:
  - `users` -> `app.users`
  - `projects` -> `app.projects`
  - `api_keys` -> `app.api_keys`
  - `licenses` -> `app.licenses`
- `databasefull.sqlite` (or `ripe.sqlite`) tables:
  - analytics tables -> `analytics.*`
  - lookup tables -> `lookup.*`

## Files

- `schema.sql`: target PostgreSQL schemas/tables
- `indexes.sql`: performance indexes (created after data copy)
- `migration_config.py`: table mapping + type normalization rules
- `migrate_sqlite_to_postgres.py`: bulk migration script
- `verify_postgres_migration.py`: row-count verification script

## Usage

```bash
python3 scripts/postgres/migrate_sqlite_to_postgres.py --pg-dsn "postgresql://USER:PASS@HOST:5432/DB" --truncate-first
python3 scripts/postgres/verify_postgres_migration.py --pg-dsn "postgresql://USER:PASS@HOST:5432/DB" --fail-on-mismatch
```
