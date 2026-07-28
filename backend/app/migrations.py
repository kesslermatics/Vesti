"""Leichtgewichtige Auto-Migration beim Backend-Start.

`Base.metadata.create_all()` erzeugt nur fehlende *Tabellen*, keine fehlenden
*Spalten*. Diese Funktion ergaenzt neue Spalten idempotent, damit ein Deploy
nach einer Modell-Aenderung nicht mit "column does not exist" abbricht.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("vesti.migrations")

# Erwartete Spalten pro Tabelle: (Spaltenname, Postgres-Typ, SQLite-Typ, Default)
EXPECTED_COLUMNS: dict[str, list[tuple[str, str, str, str | None]]] = {
    "clothing_items": [
        ("details", "JSONB", "JSON", "'{}'"),
        ("quantity", "INTEGER", "INTEGER", "1"),
        ("brand", "VARCHAR(120)", "VARCHAR(120)", "''"),
    ],
    "users": [
        ("measurements", "JSONB", "JSON", "'{}'"),
        ("sizes", "JSONB", "JSON", "'{}'"),
        ("fit_preference", "VARCHAR(60)", "VARCHAR(60)", "''"),
        ("body_type", "VARCHAR(60)", "VARCHAR(60)", "''"),
        ("style_notes", "TEXT", "TEXT", "''"),
    ],
}


def run_migrations(engine: Engine) -> None:
    """Ergaenzt fehlende Spalten. Idempotent und sicher bei jedem Start."""
    is_postgres = engine.dialect.name == "postgresql"
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in EXPECTED_COLUMNS.items():
            if table not in existing_tables:
                continue  # wird von create_all() frisch erzeugt

            present = {c["name"] for c in inspector.get_columns(table)}

            for name, pg_type, sqlite_type, default in columns:
                if name in present:
                    continue

                col_type = pg_type if is_postgres else sqlite_type
                default_sql = f" DEFAULT {default}" if default is not None else ""
                # SQLite kennt kein "IF NOT EXISTS" bei ADD COLUMN, daher oben gepruefte Liste
                if is_postgres:
                    stmt = (
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN IF NOT EXISTS {name} {col_type}{default_sql} NOT NULL"
                    )
                else:
                    stmt = f"ALTER TABLE {table} ADD COLUMN {name} {col_type}{default_sql}"

                try:
                    conn.execute(text(stmt))
                    logger.info("Migration: Spalte %s.%s ergänzt", table, name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Migration für %s.%s fehlgeschlagen: %s", table, name, exc)
