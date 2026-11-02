import hashlib
import os
import time
from pathlib import Path


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=5)


def migrate():
    with connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(87623001)")
        connection.execute("CREATE TABLE IF NOT EXISTS wecode_migrations (name text PRIMARY KEY, checksum text NOT NULL)")
        for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
            source = path.read_text()
            checksum = hashlib.sha256(source.encode()).hexdigest()
            existing = connection.execute("SELECT checksum FROM wecode_migrations WHERE name=%s", (path.name,)).fetchone()
            if existing:
                if existing["checksum"] != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}")
                continue
            connection.execute(source)
            connection.execute("INSERT INTO wecode_migrations VALUES (%s,%s)", (path.name, checksum))


def migrate_with_retry(attempts=10, interval=2):
    """Bound startup retries for a database provisioned alongside the app."""
    import psycopg
    for attempt in range(attempts):
        try:
            migrate()
            return
        except psycopg.OperationalError:
            if attempt == attempts - 1:
                raise
            print("Waiting for assignment database readiness...", flush=True)
            time.sleep(interval)
