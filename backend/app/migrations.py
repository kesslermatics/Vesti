"""Leichtgewichtige Auto-Migration beim Backend-Start.

`Base.metadata.create_all()` erzeugt nur fehlende *Tabellen*, keine fehlenden
*Spalten*. Diese Funktion ergaenzt neue Spalten idempotent, damit ein Deploy
nach einer Modell-Aenderung nicht mit "column does not exist" abbricht.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("vesti.migrations")

# Erwartete Spalten pro Tabelle:
# (Spaltenname, Postgres-Typ, SQLite-Typ, Default-Ausdruck oder None, nullable)
# nullable=True  → kein NOT NULL, kein Default nötig (für BLOB-Spalten)
# nullable=False → NOT NULL + Default wird angehängt
EXPECTED_COLUMNS: dict[str, list[tuple[str, str, str, str | None, bool]]] = {
    "clothing_items": [
        ("details",          "JSONB",       "JSON",        "'{}'",        False),
        ("quantity",         "INTEGER",     "INTEGER",     "1",           False),
        ("brand",            "VARCHAR(120)","VARCHAR(120)","''",          False),
        ("favorite",         "INTEGER",     "INTEGER",     "0",           False),
        ("thumbnail_data",   "BYTEA",       "BLOB",        None,          True),
        ("ai_image_data",    "BYTEA",       "BLOB",        None,          True),
        ("ai_image_mime",    "VARCHAR(60)", "VARCHAR(60)", "'image/png'", False),
        ("ai_thumbnail_data","BYTEA",       "BLOB",        None,          True),
    ],
    "users": [
        ("measurements",   "JSONB",      "JSON",       "'{}'", False),
        ("sizes",          "JSONB",      "JSON",       "'{}'", False),
        ("fit_preference", "VARCHAR(60)","VARCHAR(60)","''",   False),
        ("body_type",      "VARCHAR(60)","VARCHAR(60)","''",   False),
        ("style_notes",    "TEXT",       "TEXT",       "''",   False),
    ],
    "item_images": [
        ("thumbnail_data", "BYTEA", "BLOB", None, True),
    ],
}


def run_migrations(engine: Engine) -> None:
    """Ergaenzt fehlende Spalten. Idempotent und sicher bei jedem Start."""
    is_postgres = engine.dialect.name == "postgresql"

    # Inspector ausserhalb jeder Transaktion aufrufen (frische Verbindung)
    with engine.connect() as probe:
        inspector = inspect(probe)
        existing_tables = set(inspector.get_table_names())
        # Spalten-Sets vorab einlesen
        present_by_table = {
            table: {c["name"] for c in inspector.get_columns(table)}
            for table in EXPECTED_COLUMNS
            if table in existing_tables
        }

    for table, columns in EXPECTED_COLUMNS.items():
        if table not in existing_tables:
            continue

        present = present_by_table[table]

        for entry in columns:
            # Abwärtskompatibel: 4-Tuple (alter Code) oder 5-Tuple (neu)
            if len(entry) == 5:
                name, pg_type, sqlite_type, default, nullable = entry
            else:
                name, pg_type, sqlite_type, default = entry  # type: ignore[misc]
                nullable = default is None  # kein Default → nullable

            if name in present:
                continue

            col_type = pg_type if is_postgres else sqlite_type

            if is_postgres:
                if nullable:
                    # Nullable-Spalte: kein NOT NULL, kein Default nötig
                    stmt = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {col_type}"
                else:
                    default_sql = f" DEFAULT {default}" if default is not None else ""
                    stmt = (
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN IF NOT EXISTS {name} {col_type}{default_sql} NOT NULL"
                    )
            else:
                # SQLite kennt kein IF NOT EXISTS bei ADD COLUMN
                default_sql = f" DEFAULT {default}" if default is not None else ""
                stmt = f"ALTER TABLE {table} ADD COLUMN {name} {col_type}{default_sql}"

            # Jede Spalte in ihrer eigenen Transaktion, damit ein Fehler
            # nicht alle folgenden Spalten blockiert
            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
                logger.info("Migration: Spalte %s.%s ergaenzt", table, name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Migration fuer %s.%s fehlgeschlagen: %s", table, name, exc
                )
