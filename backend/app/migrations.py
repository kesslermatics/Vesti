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
        ("has_ai_image",     "BOOLEAN",     "INTEGER",     "false",       False),
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
    "accessory_images": [
        ("thumbnail_data", "BYTEA", "BLOB", None, True),
    ],
    "accessories": [
        ("occasions",           "JSONB",        "JSON",         "'[]'",        False),
        ("details",             "JSONB",        "JSON",         "'{}'",        False),
        ("authenticity_card",   "INTEGER",      "INTEGER",      "0",           False),
        ("needs_review",        "INTEGER",      "INTEGER",      "0",           False),
        ("favorite",            "INTEGER",      "INTEGER",      "0",           False),
        ("currency",            "VARCHAR(10)",  "VARCHAR(10)",  "'EUR'",       False),
        ("thumbnail_data",      "BYTEA",        "BLOB",         None,          True),
        ("ai_image_data",       "BYTEA",        "BLOB",         None,          True),
        ("ai_image_mime",       "VARCHAR(60)",  "VARCHAR(60)",  "'image/png'", False),
        ("ai_thumbnail_data",   "BYTEA",        "BLOB",         None,          True),
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

    _backfill_has_ai_image(engine, is_postgres)


def _backfill_has_ai_image(engine: Engine, is_postgres: bool) -> None:
    """Setzt has_ai_image=true fuer Items die bereits ai_image_data haben.

    Laeuft nur wenn has_ai_image gerade neu angelegt wurde (alle Werte false/0).
    Liest KEINEN Blob in Python – prueft nur serverseitig ob der Blob NOT NULL ist.
    """
    try:
        with engine.connect() as probe:
            inspector = inspect(probe)
            if "clothing_items" not in inspector.get_table_names():
                return

        with engine.begin() as conn:
            if is_postgres:
                # Pruefe ob ueberhaupt Items mit true existieren (dann schon migriert)
                already = conn.execute(
                    text("SELECT COUNT(*) FROM clothing_items WHERE has_ai_image = true")
                ).scalar()
                if already:
                    return
                result = conn.execute(
                    text(
                        "UPDATE clothing_items "
                        "SET has_ai_image = true "
                        "WHERE ai_image_data IS NOT NULL "
                        "  AND octet_length(ai_image_data) > 0"
                    )
                )
            else:
                already = conn.execute(
                    text("SELECT COUNT(*) FROM clothing_items WHERE has_ai_image = 1")
                ).scalar()
                if already:
                    return
                result = conn.execute(
                    text(
                        "UPDATE clothing_items "
                        "SET has_ai_image = 1 "
                        "WHERE ai_image_data IS NOT NULL "
                        "  AND length(ai_image_data) > 0"
                    )
                )
            if result.rowcount:
                logger.info(
                    "Migration: has_ai_image fuer %d Items gesetzt", result.rowcount
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backfill has_ai_image fehlgeschlagen: %s", exc)


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


def migrate_legacy_accessories(engine: Engine) -> int:
    """Zieht Schmuck, Taschen und Brillen aus clothing_items in accessories um.

    Analog zur Uhren-Migration: Bilder werden uebernommen, spezifische Felder
    bleiben leer und werden mit needs_review=1 zur KI-Neuanalyse markiert.
    Idempotent – entfernte Kategorien kommen nicht wieder.
    """
    from sqlalchemy.orm import Session

    from . import models
    from .accessories import LEGACY_ACCESSORY_CATEGORIES, accessory_group

    # Kategorie -> Typ-Mapping: direkte Uebertragung soweit moeglich
    CATEGORY_TO_TYPE: dict[str, str] = {
        "Schmuck": "Sonstiges Accessoire",
        "Halskette": "Halskette",
        "Armband": "Armband",
        "Ring": "Ring",
        "Ohrringe": "Ohrringe",
        "Tasche": "Umhängetasche",
        "Handtasche": "Handtasche",
        "Umhängetasche": "Umhängetasche",
        "Rucksack": "Rucksack",
        "Clutch": "Clutch",
        "Brille": "Korrektionsbrille",
        "Sonnenbrille": "Sonnenbrille",
        "Einstecktuch": "Einstecktuch",
    }

    with engine.connect() as probe:
        tables = set(inspect(probe).get_table_names())
    if "clothing_items" not in tables or "accessories" not in tables:
        return 0

    moved = 0
    try:
        with Session(engine) as db:
            legacy = db.scalars(
                select(models.ClothingItem).where(
                    models.ClothingItem.category.in_(LEGACY_ACCESSORY_CATEGORIES)
                )
            ).all()

            if not legacy:
                return 0

            total = len(legacy)
            logger.info(
                "Migration: %s Accessoire(s) gefunden – starte Umzug", total
            )

            for idx, item in enumerate(legacy, start=1):
                item_type = CATEGORY_TO_TYPE.get(item.category, "Sonstiges Accessoire")
                logger.info(
                    "Migration: Accessoire %s/%s – %s → %s (user_id=%s)",
                    idx, total, item.name or item.category,
                    item_type, item.user_id,
                )

                acc = models.Accessory(
                    user_id=item.user_id,
                    name=item.name or item.category,
                    brand=item.brand or "",
                    type=item_type,
                    color=item.color or "",
                    material=item.material or "",
                    description=item.description or "",
                    style=item.style or "",
                    occasions=[item.occasion] if item.occasion else [],
                    details={},
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
                    acc.extra_images.append(
                        models.AccessoryImage(
                            position=extra.position,
                            image_data=extra.image_data,
                            image_mime=extra.image_mime or "image/jpeg",
                            thumbnail_data=extra.thumbnail_data,
                        )
                    )

                db.add(acc)
                db.delete(item)
                moved += 1

            logger.info("Migration: Committing %s Accessoire(s) …", moved)
            db.commit()
            logger.info("Migration: Accessoires-Commit erfolgreich.")

    except Exception as exc:  # noqa: BLE001
        logger.warning("Accessoires-Migration fehlgeschlagen: %s", exc)
        return 0

    logger.info(
        "Migration: %s Accessoire(s) aus der Garderobe in die Sammlung umgezogen", moved
    )
    return moved
