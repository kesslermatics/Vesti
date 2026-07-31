"""Migriert alle bestehenden Kleidungsstücke (async, parallel):

1. Neue Analyse (Kategorie, Farbe, Details, Pflegehinweise)
2. KI-Inszenierungsfoto (gemini-3.1-flash-image-preview)
3. Thumbnails (400×400 JPEG) für Haupt- und Zusatzbilder
4. Vollbilder auf max. 1200px komprimieren

Aufruf:
    python migrate_all_items.py [--dry-run] [--skip-ai] [--only-thumbs]
                                [--user-id 42] [--item-id 149] [--concurrency 4]

Optionen:
    --dry-run        Nur anzeigen was gemacht würde, nichts speichern
    --skip-ai        Keine neue Analyse und kein KI-Foto (nur Thumbnails + Kompression)
    --only-thumbs    Nur Thumbnails generieren, alles andere überspringen
    --user-id N      Nur Items eines bestimmten Nutzers migrieren
    --item-id N      Nur ein bestimmtes Item migrieren
    --no-compress    Vollbilder nicht komprimieren
    --concurrency N  Wie viele Items gleichzeitig (Standard: 4, max empfohlen: 6)
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import ClothingItem, _compress_image, _create_thumbnail
from app import gemini_service


# ── Progress-Bar ─────────────────────────────────────────────────────────────
try:
    from tqdm.asyncio import tqdm as _atqdm

    def _make_bar(total: int, desc: str):
        return _atqdm(total=total, desc=desc, unit="item", dynamic_ncols=True, colour="green")

except ImportError:
    class _FallbackBar:
        def __init__(self, total, desc):
            self.total = total
            self.desc = desc
            self.n = 0
            self.t0 = time.monotonic()

        def update(self, n=1):
            self.n += n
            pct = int(self.n / self.total * 40) if self.total else 40
            elapsed = time.monotonic() - self.t0
            bar = "█" * pct + "░" * (40 - pct)
            eta = ""
            if self.n > 0 and self.n < self.total:
                rem = elapsed / self.n * (self.total - self.n)
                eta = f"  ETA {int(rem)}s"
            line = f"\r{self.desc}: [{bar}] {self.n}/{self.total}{eta}  "
            sys.stdout.write(line)
            sys.stdout.flush()

        def close(self):
            sys.stdout.write("\n")
            sys.stdout.flush()

    def _make_bar(total, desc):
        return _FallbackBar(total, desc)


# ── Stats ─────────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.compressed = 0
        self.compressed_kb = 0
        self.thumbnails = 0
        self.analyzed = 0
        self.ai_photos = 0
        self.skipped = 0
        self.errors = 0
        self._lock = asyncio.Lock()

    async def add(self, **kwargs):
        async with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, getattr(self, k) + v)

    def summary(self):
        lines = ["\n─────────────── Zusammenfassung ───────────────"]
        if self.compressed:
            lines.append(f"  📦 Bilder komprimiert:   {self.compressed:>4}  (−{self.compressed_kb} KB gespart)")
        if self.thumbnails:
            lines.append(f"  🖼  Thumbnails erstellt:  {self.thumbnails:>4}")
        if self.analyzed:
            lines.append(f"  🔍 Neu analysiert:       {self.analyzed:>4}")
        if self.ai_photos:
            lines.append(f"  ✨ KI-Fotos generiert:   {self.ai_photos:>4}")
        if self.skipped:
            lines.append(f"  ─  Übersprungen:         {self.skipped:>4}")
        if self.errors:
            lines.append(f"  ⚠  Fehler:               {self.errors:>4}")
        lines.append("────────────────────────────────────────────────")
        return "\n".join(lines)


# ── Log ohne Bar zerstören ────────────────────────────────────────────────────
_log_lock = asyncio.Lock() if sys.version_info >= (3, 10) else None  # wird in main gesetzt

async def _log(msg: str) -> None:
    # tqdm.write() ist threadsafe und respektiert die Bar
    try:
        from tqdm import tqdm as _t
        _t.write(f"  {msg}")
    except ImportError:
        sys.stdout.write(f"\n  {msg}")
        sys.stdout.flush()


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def _refs(item: ClothingItem) -> list[tuple[bytes, str]]:
    refs = []
    if item.image_data:
        refs.append((item.image_data, item.image_mime or "image/jpeg"))
    for extra in sorted(item.extra_images or [], key=lambda x: x.position):
        if extra.image_data:
            refs.append((extra.image_data, extra.image_mime or "image/jpeg"))
    return refs


# ── Ein Item verarbeiten ──────────────────────────────────────────────────────
async def _process_item(
    item_id: int,
    dry_run: bool,
    skip_ai: bool,
    only_thumbs: bool,
    no_compress: bool,
    stats: Stats,
    db_lock: asyncio.Lock,
) -> None:
    """Verarbeitet ein Item komplett. Eigene DB-Session pro Task."""
    db = SessionLocal()
    try:
        item = db.get(ClothingItem, item_id)
        if item is None:
            return

        refs = _refs(item)
        if not refs:
            await _log(f"⚠ #{item_id} kein Bild – übersprungen")
            await stats.add(skipped=1)
            return

        changed = False

        # ── 1. Vollbild komprimieren ──────────────────────────────────────
        if not no_compress and not only_thumbs:
            if item.image_data:
                orig = len(item.image_data)
                # CPU-bound → in ThreadPool damit async nicht blockiert
                comp = await asyncio.get_event_loop().run_in_executor(
                    None, _compress_image, item.image_data
                )
                if len(comp) < orig:
                    saved = (orig - len(comp)) // 1024
                    await _log(f"📦 #{item_id} {orig//1024}KB→{len(comp)//1024}KB (−{saved}KB)")
                    if not dry_run:
                        item.image_data = comp
                        item.image_mime = "image/jpeg"
                    await stats.add(compressed=1, compressed_kb=saved)
                    changed = True
            for extra in item.extra_images or []:
                if not extra.image_data:
                    continue
                orig = len(extra.image_data)
                comp = await asyncio.get_event_loop().run_in_executor(
                    None, _compress_image, extra.image_data
                )
                if len(comp) < orig:
                    if not dry_run:
                        extra.image_data = comp
                        extra.image_mime = "image/jpeg"
                    await stats.add(compressed=1, compressed_kb=(orig - len(comp)) // 1024)
                    changed = True

        # ── 2. Thumbnails ─────────────────────────────────────────────────
        if not item.thumbnail_data and item.image_data:
            thumb = await asyncio.get_event_loop().run_in_executor(
                None, _create_thumbnail, item.image_data
            )
            if not dry_run:
                item.thumbnail_data = thumb
            await stats.add(thumbnails=1)
            changed = True
        for extra in item.extra_images or []:
            if extra.image_data and not extra.thumbnail_data:
                thumb = await asyncio.get_event_loop().run_in_executor(
                    None, _create_thumbnail, extra.image_data
                )
                if not dry_run:
                    extra.thumbnail_data = thumb
                await stats.add(thumbnails=1)
                changed = True

        if only_thumbs or skip_ai:
            if changed and not dry_run:
                db.commit()
            elif not changed:
                await stats.add(skipped=1)
            return

        # ── 3. Neue Analyse ───────────────────────────────────────────────
        try:
            # Gemini-Calls sind I/O-bound → run_in_executor damit der Event-Loop läuft
            quick = await asyncio.get_event_loop().run_in_executor(
                None, lambda: gemini_service.quick_analyze_image(refs)
            )
            category = quick.get("category") or item.category
            detail = await asyncio.get_event_loop().run_in_executor(
                None, lambda: gemini_service.detail_analyze_image(refs, category=category)
            )

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

            await _log(f"🔍 #{item_id} → {category} / {quick.get('color', '?')}")
            await stats.add(analyzed=1)
            changed = True

        except Exception as exc:
            await _log(f"⚠ #{item_id} Analyse: {str(exc)[:80]}")
            await stats.add(errors=1)

        # ── 4. KI-Inszenierungsfoto ───────────────────────────────────────
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: gemini_service.generate_product_shot(
                    refs,
                    category=item.category,
                    color=item.color,
                    material=item.material,
                ),
            )
            if result:
                data, mime = result
                ai_thumb = await asyncio.get_event_loop().run_in_executor(
                    None, _create_thumbnail, data
                )
                await _log(f"✨ #{item_id} KI-Foto {len(data)//1024} KB")
                if not dry_run:
                    item.ai_image_data = data
                    item.ai_image_mime = mime
                    item.ai_thumbnail_data = ai_thumb
                await stats.add(ai_photos=1)
                changed = True
            else:
                await _log(f"⚠ #{item_id} KI-Foto: kein Bild zurück")

        except Exception as exc:
            await _log(f"⚠ #{item_id} KI-Foto: {str(exc)[:80]}")
            await stats.add(errors=1)

        # ── Speichern ─────────────────────────────────────────────────────
        if changed and not dry_run:
            db.commit()
        elif not changed:
            await stats.add(skipped=1)

    finally:
        db.close()


# ── Hauptfunktion ─────────────────────────────────────────────────────────────
async def migrate(
    dry_run: bool = False,
    skip_ai: bool = False,
    only_thumbs: bool = False,
    user_id: int | None = None,
    item_id: int | None = None,
    no_compress: bool = False,
    concurrency: int = 4,
) -> None:
    # Item-IDs vorab laden (kurze Session)
    db = SessionLocal()
    try:
        q = select(ClothingItem.id)
        if user_id:
            q = q.where(ClothingItem.user_id == user_id)
        if item_id:
            q = q.where(ClothingItem.id == item_id)
        q = q.order_by(ClothingItem.id)
        item_ids: list[int] = list(db.scalars(q).all())
    finally:
        db.close()

    total = len(item_ids)
    prefix = "[DRY-RUN] " if dry_run else ""
    mode = "only-thumbs" if only_thumbs else "skip-ai" if skip_ai else "komplett"
    print(f"\n{prefix}Migriere {total} Item(s) · Modus: {mode} · Parallel: {concurrency}")
    print("  tipp: pip install tqdm  für bessere Progress-Bar\n"
          if "tqdm" not in sys.modules else "")

    stats = Stats()
    db_lock = asyncio.Lock()
    bar = _make_bar(total, f"{prefix}Fortschritt")

    # Semaphore begrenzt parallele Gemini-Calls
    sem = asyncio.Semaphore(concurrency)

    async def _worker(iid: int) -> None:
        async with sem:
            await _process_item(
                item_id=iid,
                dry_run=dry_run,
                skip_ai=skip_ai,
                only_thumbs=only_thumbs,
                no_compress=no_compress,
                stats=stats,
                db_lock=db_lock,
            )
            bar.update(1)

    t0 = time.monotonic()
    await asyncio.gather(*[_worker(iid) for iid in item_ids])
    bar.close()

    elapsed = int(time.monotonic() - t0)
    print(stats.summary())
    print(f"\n{prefix}Fertig in {elapsed//60}m {elapsed%60}s\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migriert alle Kleidungsstücke.")
    parser.add_argument("--dry-run", action="store_true", help="Nichts speichern")
    parser.add_argument("--skip-ai", action="store_true", help="Keine KI-Analyse/Foto")
    parser.add_argument("--only-thumbs", action="store_true", help="Nur Thumbnails")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--item-id", type=int, default=None)
    parser.add_argument("--no-compress", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Parallele Items (Standard: 4)")
    args = parser.parse_args()

    asyncio.run(migrate(
        dry_run=args.dry_run,
        skip_ai=args.skip_ai,
        only_thumbs=args.only_thumbs,
        user_id=args.user_id,
        item_id=args.item_id,
        no_compress=args.no_compress,
        concurrency=args.concurrency,
    ))
