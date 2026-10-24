"""Verschiebt bestehende Bilder aus der Datenbank nach S3 (Ordner Vesti/).

Aufruf (S3_* und DATABASE_URL muessen gesetzt sein, z. B. im Container):
    python migrate_images_to_s3.py [--dry-run] [--limit N]

Das Script ist idempotent: Spalten, die bereits einen `s3:`-Marker enthalten,
werden uebersprungen. Pro Spalte wird erst hochgeladen, die Groesse in S3
geprueft und erst dann der Marker in die DB geschrieben (ein Commit pro Wert).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text  # noqa: E402

from app import storage  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import engine  # noqa: E402

TARGETS: list[tuple[str, str, list[str]]] = [
    ("clothing_items", "clothing", ["image_data", "thumbnail_data", "ai_image_data", "ai_thumbnail_data"]),
    ("item_images", "clothing", ["image_data", "thumbnail_data"]),
    ("watches", "watches", ["image_data", "thumbnail_data", "ai_image_data", "ai_thumbnail_data"]),
    ("watch_images", "watches", ["image_data", "thumbnail_data"]),
    ("fragrances", "fragrances", ["image_data", "thumbnail_data", "ai_image_data", "ai_thumbnail_data"]),
    ("fragrance_images", "fragrances", ["image_data", "thumbnail_data"]),
    ("accessories", "accessories", ["image_data", "thumbnail_data", "ai_image_data", "ai_thumbnail_data"]),
    ("accessory_images", "accessories", ["image_data", "thumbnail_data"]),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nur zaehlen, nichts hochladen")
    parser.add_argument("--limit", type=int, default=0, help="Maximal N Werte migrieren (0 = alle)")
    args = parser.parse_args()

    if not storage.s3_enabled():
        print("S3 ist nicht konfiguriert (S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY).")
        return 1

    settings = get_settings()
    print(f"Ziel: bucket={settings.s3_bucket} prefix={settings.s3_key_prefix!r}")

    migrated = skipped = failed = 0
    saved_bytes = 0
    done = False

    for table, folder, columns in TARGETS:
        with engine.connect() as conn:
            ids = [r[0] for r in conn.execute(text(f"SELECT id FROM {table} ORDER BY id"))]
        print(f"\n{table}: {len(ids)} Zeilen")

        for row_id in ids:
            for col in columns:
                with engine.connect() as conn:
                    raw = conn.execute(
                        text(f"SELECT {col} FROM {table} WHERE id = :id"), {"id": row_id}
                    ).scalar()
                if raw is None:
                    continue
                raw = bytes(raw)
                if not raw or storage.decode_marker(raw):
                    skipped += 1
                    continue

                if args.dry_run:
                    migrated += 1
                    saved_bytes += len(raw)
                    continue

                try:
                    key = storage.put_blob(folder, raw)
                    head = storage._client().head_object(Bucket=settings.s3_bucket, Key=key)
                    if head["ContentLength"] != len(raw):
                        raise RuntimeError(
                            f"Groesse stimmt nicht ({head['ContentLength']} != {len(raw)})"
                        )
                    with engine.begin() as conn:
                        conn.execute(
                            text(f"UPDATE {table} SET {col} = :v WHERE id = :id"),
                            {"v": storage.encode_marker(key), "id": row_id},
                        )
                    migrated += 1
                    saved_bytes += len(raw)
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(f"  FEHLER {table}.{col} id={row_id}: {exc}")

                if args.limit and migrated >= args.limit:
                    done = True
                    break
            if done:
                break
            if migrated and migrated % 50 == 0:
                print(f"  ... {migrated} Werte migriert")
        if done:
            break

    mb = saved_bytes / (1024 * 1024)
    verb = "wuerden migriert" if args.dry_run else "migriert"
    print(f"\nFertig: {migrated} Werte {verb} ({mb:.1f} MB), {skipped} bereits in S3, {failed} Fehler")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
