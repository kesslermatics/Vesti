"""Migriert alle bestehenden Kleidungsstücke:

1. Neue Analyse (Kategorie, Farbe, Details, Pflegehinweise)
2. KI-Inszenierungsfoto (gemini-3.1-flash-image-preview)
3. Thumbnails (400×400 JPEG) für Haupt- und Zusatzbilder
4. Vollbilder auf max. 1200px komprimieren

Aufruf (aus dem backend/-Ordner mit aktivierter venv):
    python migrate_all_items.py [--dry-run] [--skip-ai] [--only-thumbs] [--user-id 42]

Optionen:
    --dry-run     Nur anzeigen was gemacht würde, nichts speichern
    --skip-ai     Keine neue Analyse und kein KI-Foto (nur Thumbnails + Kompression)
    --only-thumbs Nur Thumbnails generieren, alles andere überspringen
    --user-id N   Nur Items eines bestimmten Nutzers migrieren
    --item-id N   Nur ein bestimmtes Item migrieren
    --no-compress Vollbilder nicht neu komprimieren
"""

import argparse
import sys
import time
from pathlib import Path

# Backend-Modul in den Pfad aufnehmen
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import ClothingItem, ItemImage, _compress_image, _create_thumbnail
from app import gemini_service


def _refs(item: ClothingItem) -> list[tuple[bytes, str]]:
    refs = []
    if item.image_data:
        refs.append((item.image_data, item.image_mime or "image/jpeg"))
    for extra in sorted(item.extra_images or [], key=lambda x: x.position):
        if extra.image_data:
            refs.append((extra.image_data, extra.image_mime or "image/jpeg"))
    return refs


def migrate(
    dry_run: bool = False,
    skip_ai: bool = False,
    only_thumbs: bool = False,
    user_id: int | None = None,
    item_id: int | None = None,
    no_compress: bool = False,
) -> None:
    db = SessionLocal()

    try:
        # Items laden
        q = select(ClothingItem)
        if user_id:
            q = q.where(ClothingItem.user_id == user_id)
        if item_id:
            q = q.where(ClothingItem.id == item_id)
        q = q.order_by(ClothingItem.id)
        items = db.scalars(q).all()

        total = len(items)
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Starte Migration von {total} Item(s)...\n")

        for n, item in enumerate(items, 1):
            label = f"[{n}/{total}] #{item.id} {item.name or item.category!r}"
            print(label)

            refs = _refs(item)
            if not refs:
                print("  ⚠ Kein Bild – übersprungen")
                continue

            changed = False

            # ── 1. Vollbild komprimieren ─────────────────────────────────
            if not no_compress and not only_thumbs:
                orig_size = len(item.image_data) if item.image_data else 0
                compressed = _compress_image(item.image_data) if item.image_data else b""
                if compressed and len(compressed) < orig_size:
                    saved_kb = (orig_size - len(compressed)) // 1024
                    print(f"  📦 Vollbild {orig_size//1024} KB → {len(compressed)//1024} KB "
                          f"(−{saved_kb} KB)")
                    if not dry_run:
                        item.image_data = compressed
                        item.image_mime = "image/jpeg"
                    changed = True
                # Zusatzbilder komprimieren
                for extra in item.extra_images or []:
                    if not extra.image_data:
                        continue
                    orig = len(extra.image_data)
                    comp = _compress_image(extra.image_data)
                    if len(comp) < orig:
                        print(f"    📦 Zusatzbild #{extra.id} {orig//1024} KB → {len(comp)//1024} KB")
                        if not dry_run:
                            extra.image_data = comp
                            extra.image_mime = "image/jpeg"
                        changed = True

            # ── 2. Thumbnails ─────────────────────────────────────────────
            if not item.thumbnail_data:
                print("  🖼 Erstelle Thumbnail …")
                if not dry_run:
                    item.thumbnail_data = _create_thumbnail(item.image_data)
                changed = True
            for extra in item.extra_images or []:
                if extra.image_data and not extra.thumbnail_data:
                    print(f"    🖼 Thumbnail für Zusatzbild #{extra.id}")
                    if not dry_run:
                        extra.thumbnail_data = _create_thumbnail(extra.image_data)
                    changed = True

            if only_thumbs:
                if changed and not dry_run:
                    db.commit()
                    print("  ✓ gespeichert")
                else:
                    print("  – nichts zu tun")
                continue

            if skip_ai:
                if changed and not dry_run:
                    db.commit()
                    print("  ✓ gespeichert")
                continue

            # ── 3. Neue Analyse (Kategorie + Details) ─────────────────────
            print("  🔍 Analysiere …", end=" ", flush=True)
            try:
                quick = gemini_service.quick_analyze_image(refs)
                category = quick.get("category") or item.category
                detail = gemini_service.detail_analyze_image(refs, category=category)

                if not dry_run:
                    item.category = category
                    item.color = quick.get("color") or item.color
                    item.name = detail.get("name") or item.name
                    item.material = detail.get("material") or item.material
                    item.pattern = detail.get("pattern") or item.pattern
                    item.style = detail.get("style") or item.style
                    item.occasion = detail.get("occasion") or item.occasion
                    item.season = detail.get("season") or item.season
                    item.description = detail.get("description") or item.description
                    new_details = detail.get("details") or {}
                    if new_details:
                        merged = dict(item.details or {})
                        merged.update(new_details)
                        item.details = merged

                print(f"OK ({category}, {quick.get('color', '?')})")
                changed = True
            except Exception as exc:
                print(f"FEHLER: {exc}")
                # Weitermachen – KI-Foto trotzdem versuchen

            # ── 4. KI-Inszenierungsfoto ───────────────────────────────────
            print("  ✨ Generiere KI-Foto …", end=" ", flush=True)
            try:
                result = gemini_service.generate_product_shot(
                    refs,
                    category=item.category,
                    color=item.color,
                    material=item.material,
                )
                if result:
                    data, mime = result
                    print(f"OK ({len(data)//1024} KB)")
                    if not dry_run:
                        item.ai_image_data = data
                        item.ai_image_mime = mime
                        item.ai_thumbnail_data = _create_thumbnail(data)
                    changed = True
                else:
                    print("kein Bild zurück")
            except Exception as exc:
                print(f"FEHLER: {exc}")

            # ── Speichern ─────────────────────────────────────────────────
            if changed and not dry_run:
                db.commit()
                print("  ✓ gespeichert")
            elif not changed:
                print("  – nichts zu tun")

            # Kurze Pause zwischen Items damit die API nicht überlastet wird
            if n < total:
                time.sleep(2)

    finally:
        db.close()

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Migration abgeschlossen.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migriert alle Kleidungsstücke.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur anzeigen, nichts speichern")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Keine KI-Analyse und kein KI-Foto")
    parser.add_argument("--only-thumbs", action="store_true",
                        help="Nur Thumbnails generieren")
    parser.add_argument("--user-id", type=int, default=None,
                        help="Nur Items dieses Nutzers")
    parser.add_argument("--item-id", type=int, default=None,
                        help="Nur dieses eine Item")
    parser.add_argument("--no-compress", action="store_true",
                        help="Vollbilder nicht komprimieren")
    args = parser.parse_args()

    migrate(
        dry_run=args.dry_run,
        skip_ai=args.skip_ai,
        only_thumbs=args.only_thumbs,
        user_id=args.user_id,
        item_id=args.item_id,
        no_compress=args.no_compress,
    )
