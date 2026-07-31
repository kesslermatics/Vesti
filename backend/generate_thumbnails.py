"""Einmaliges Script zur Generierung von Thumbnails für bestehende Bilder."""

import sys
from pathlib import Path

# Backend-Modul in den Pfad aufnehmen
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.database import engine, get_db
from app.models import ClothingItem, ItemImage, _create_thumbnail

def generate_thumbnails():
    """Generiert Thumbnails für alle ClothingItems und ItemImages ohne Thumbnail."""
    db = next(get_db())
    
    # ClothingItems
    items = db.scalars(select(ClothingItem)).all()
    updated_items = 0
    for item in items:
        if item.image_data and not item.thumbnail_data:
            print(f"Generiere Thumbnail für Item {item.id}: {item.name or item.category}")
            item.thumbnail_data = _create_thumbnail(item.image_data)
            updated_items += 1
    
    # ItemImages
    images = db.scalars(select(ItemImage)).all()
    updated_images = 0
    for img in images:
        if img.image_data and not img.thumbnail_data:
            print(f"Generiere Thumbnail für ItemImage {img.id}")
            img.thumbnail_data = _create_thumbnail(img.image_data)
            updated_images += 1
    
    db.commit()
    print(f"\n✓ Fertig!")
    print(f"  - {updated_items} ClothingItem-Thumbnails generiert")
    print(f"  - {updated_images} ItemImage-Thumbnails generiert")

if __name__ == "__main__":
    generate_thumbnails()
