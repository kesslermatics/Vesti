"""Leichtgewichtige Auto-Migration beim Backend-Start.

`Base.metadata.create_all()` erzeugt nur fehlende *Tabellen*, keine fehlenden
*Spalten*. Diese Funktion ergaenzt neue Spalten idempotent, damit ein Deploy
nach einer Modell-Aenderung nicht mit "column does not exist" abbricht.
"""

import logging

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("vesti.migrations")
logger.setLevel(logging.INFO)  # sichtbar in Railway auch ohne extra Log-Config

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
    # Uhren-Sammlung: Spalten die nach der ersten Version dazugekommen sind
    "watches": [
        ("complications",          "JSONB",        "JSON",         "'[]'",        False),
        ("occasions",              "JSONB",        "JSON",         "'[]'",        False),
        ("needs_review",           "INTEGER",      "INTEGER",      "0",           False),
        ("favorite",               "INTEGER",      "INTEGER",      "0",           False),
        ("currency",               "VARCHAR(10)",  "VARCHAR(10)",  "'EUR'",       False),
        ("thumbnail_data",         "BYTEA",        "BLOB",         None,          True),
        ("ai_image_data",          "BYTEA",        "BLOB",         None,          True),
        ("ai_image_mime",          "VARCHAR(60)",  "VARCHAR(60)",  "'image/png'", False),
        ("ai_thumbnail_data",      "BYTEA",        "BLOB",         None,          True),
    ],
    "watch_images": [
        ("thumbnail_data", "BYTEA", "BLOB", None, True),
    ],
    # Duft-Sammlung
    "fragrances": [
        ("top_notes",         "JSONB",        "JSON",         "'[]'",        False),
        ("heart_notes",       "JSONB",        "JSON",         "'[]'",        False),
        ("base_notes",        "JSONB",        "JSON",         "'[]'",        False),
        ("occasions",         "JSONB",        "JSON",         "'[]'",        False),
        ("seasons",           "JSONB",        "JSON",         "'[]'",        False),
        ("quantity",          "INTEGER",      "INTEGER",      "1",           False),
        ("needs_review",      "INTEGER",      "INTEGER",      "0",           False),
        ("favorite",          "INTEGER",      "INTEGER",      "0",           False),
        ("currency",          "VARCHAR(10)",  "VARCHAR(10)",  "'EUR'",       False),
        ("thumbnail_data",    "BYTEA",        "BLOB",         None,          True),
        ("ai_image_data",     "BYTEA",        "BLOB",         None,          True),
        ("ai_image_mime",     "VARCHAR(60)",  "VARCHAR(60)",  "'image/png'", False),
        ("ai_thumbnail_data", "BYTEA",        "BLOB",         None,          True),
    ],
    "fragrance_images": [
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


def migrate_legacy_watches(engine: Engine) -> int:
    """Zieht Uhren aus `clothing_items` in die eigene Tabelle `watches` um."""
    from sqlalchemy.orm import Session

    from . import models
    from .categories import LEGACY_WATCH_CATEGORIES

    with engine.connect() as probe:
        tables = set(inspect(probe).get_table_names())
    if "clothing_items" not in tables or "watches" not in tables:
        return 0

    moved = 0
    try:
        with Session(engine) as db:
            legacy = db.scalars(
                select(models.ClothingItem).where(
                    models.ClothingItem.category.in_(LEGACY_WATCH_CATEGORIES)
                )
            ).all()

            if not legacy:
                return 0

            total = len(legacy)
            logger.info(
                "Migration: %s Uhr(en) gefunden – starte Umzug in die Uhren-Sammlung",
                total,
            )

            for idx, item in enumerate(legacy, start=1):
                logger.info(
                    "Migration: Uhr %s/%s – %s (user_id=%s)",
                    idx,
                    total,
                    item.name or item.category,
                    item.user_id,
                )
                watch = models.Watch(
                    user_id=item.user_id,
                    name=item.name or "Uhr",
                    brand=item.brand or "",
                    dial_color=item.color or "",
                    band_material=item.material or "",
                    description=item.description or "",
                    style="",
                    occasions=[item.occasion] if item.occasion else [],
                    complications=[],
                    favorite=1 if item.favorite else 0,
                    image_data=item.image_data,
                    image_mime=item.image_mime or "image/jpeg",
                    thumbnail_data=item.thumbnail_data,
                    ai_image_data=item.ai_image_data,
                    ai_image_mime=item.ai_image_mime or "image/png",
                    ai_thumbnail_data=item.ai_thumbnail_data,
                    created_at=item.created_at,
                    needs_review=1,
                )

                for extra in item.extra_images or []:
                    if not extra.image_data:
                        continue
                    watch.extra_images.append(
                        models.WatchImage(
                            position=extra.position,
                            image_data=extra.image_data,
                            image_mime=extra.image_mime or "image/jpeg",
                            thumbnail_data=extra.thumbnail_data,
                        )
                    )

                db.add(watch)
                db.delete(item)
                moved += 1

            logger.info(
                "Migration: Committing %s Uhr(en) …", moved
            )
            db.commit()
            logger.info("Migration: Commit erfolgreich.")

    except Exception as exc:  # noqa: BLE001
        logger.warning("Uhren-Migration fehlgeschlagen: %s", exc)
        return 0

    logger.info("Migration: %s Uhr(en) aus der Garderobe in die Sammlung umgezogen", moved)
    return moved
