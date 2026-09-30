"""REST-Endpunkte für gespeicherte Outfits."""

import base64
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import openai_service, models
from .auth import get_current_user
from .database import get_db
from .shared import api_base

router = APIRouter()


# ── Hilfsfunktionen ──────────────────────────────────────────────────

def _resolve_item(db: Session, item_id: int, request: Request) -> dict[str, Any] | None:
    item = db.get(models.ClothingItem, item_id)
    if not item:
        return None
    base = api_base(request)
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "color": item.color,
        "material": item.material,
        "style": item.style,
        "brand": item.brand,
        "image_url": f"{base}/api/items/{item.id}/image",
        "thumbnail_url": f"{base}/api/items/{item.id}/thumbnail",
        "ai_image_url": f"{base}/api/items/{item.id}/ai-image" if item.has_ai_image else "",
        "ai_thumbnail_url": f"{base}/api/items/{item.id}/ai-thumbnail" if item.has_ai_image else "",
        "has_ai_image": bool(item.has_ai_image),
    }


def _resolve_watch(db: Session, watch_id: int | None, request: Request) -> dict[str, Any] | None:
    if not watch_id:
        return None
    w = db.get(models.Watch, watch_id)
    if not w:
        return None
    base = api_base(request)
    has_ai = bool(w.ai_image_data)
    return {
        "id": w.id,
        "name": w.name or f"{w.brand} {w.model}".strip(),
        "brand": w.brand,
        "model": w.model,
        "thumbnail_url": f"{base}/api/watches/{w.id}/thumbnail",
        "ai_thumbnail_url": f"{base}/api/watches/{w.id}/ai-thumbnail" if has_ai else "",
        "has_ai_image": has_ai,
    }


def _resolve_fragrance(db: Session, frag_id: int | None, request: Request) -> dict[str, Any] | None:
    if not frag_id:
        return None
    f = db.get(models.Fragrance, frag_id)
    if not f:
        return None
    base = api_base(request)
    has_ai = bool(f.ai_image_data)
    return {
        "id": f.id,
        "name": f.name,
        "brand": f.brand,
        "thumbnail_url": f"{base}/api/fragrances/{f.id}/thumbnail",
        "ai_thumbnail_url": f"{base}/api/fragrances/{f.id}/ai-thumbnail" if has_ai else "",
        "has_ai_image": has_ai,
    }


def _resolve_accessory(db: Session, acc_id: int | None, request: Request) -> dict[str, Any] | None:
    if not acc_id:
        return None
    a = db.get(models.Accessory, acc_id)
    if not a:
        return None
    base = api_base(request)
    has_ai = bool(a.ai_image_data)
    return {
        "id": a.id,
        "name": a.name or a.type,
        "type": a.type,
        "brand": a.brand,
        "thumbnail_url": f"{base}/api/accessories/{a.id}/thumbnail",
        "ai_thumbnail_url": f"{base}/api/accessories/{a.id}/ai-thumbnail" if has_ai else "",
        "has_ai_image": has_ai,
    }


def _outfit_out(outfit: models.SavedOutfit, db: Session, request: Request) -> dict[str, Any]:
    items = [
        r for iid in (outfit.item_ids or [])
        if (r := _resolve_item(db, iid, request)) is not None
    ]
    return {
        "id": outfit.id,
        "title": outfit.title,
        "description": outfit.description,
        "items": items,
        "watch": _resolve_watch(db, outfit.watch_id, request),
        "fragrance": _resolve_fragrance(db, outfit.fragrance_id, request),
        "accessory": _resolve_accessory(db, outfit.accessory_id, request),
        "occasion": outfit.occasion,
        "season": outfit.season,
        "weather": outfit.weather,
        "tags": outfit.tags or [],
        "ai_rating": outfit.ai_rating,
        "created_at": outfit.created_at.isoformat(),
        "updated_at": outfit.updated_at.isoformat(),
    }


# ── Endpunkte ─────────────────────────────────────────────────────────

@router.get("/api/outfits/saved")
def list_saved_outfits(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    outfits = db.scalars(
        select(models.SavedOutfit)
        .where(models.SavedOutfit.user_id == user.id)
        .order_by(models.SavedOutfit.created_at.desc())
    ).all()
    return [_outfit_out(o, db, request) for o in outfits]


@router.post("/api/outfits/saved")
def create_saved_outfit(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Speichert ein neues Outfit. Generiert automatisch Titel + Beschreibung via KI."""
    item_ids = [int(i) for i in (payload.get("item_ids") or []) if i]
    if not item_ids:
        raise HTTPException(status_code=400, detail="Mindestens ein Kleidungsstück angeben.")

    occasion = str(payload.get("occasion") or "")
    season = str(payload.get("season") or "")
    weather = str(payload.get("weather") or "")
    watch_id = payload.get("watch_id")
    fragrance_id = payload.get("fragrance_id")
    accessory_id = payload.get("accessory_id")
    tags = list(payload.get("tags") or [])

    # Tags aus Anlass/Saison/Wetter automatisch ergänzen
    for val in [occasion, season, weather]:
        if val and val not in tags:
            tags.append(val)

    # KI-Titel und -Beschreibung generieren
    items_data = [
        _resolve_item(db, iid, request) or {}
        for iid in item_ids
    ]
    items_data = [i for i in items_data if i]

    title = str(payload.get("title") or "")
    description = str(payload.get("description") or "")

    if not title:
        try:
            generated = openai_service.generate_outfit_title(
                items_data, occasion=occasion, season=season, weather=weather
            )
            title = generated.get("title", "Mein Outfit")
            if not description:
                description = generated.get("description", "")
        except Exception:  # noqa: BLE001
            title = title or "Mein Outfit"

    outfit = models.SavedOutfit(
        user_id=user.id,
        title=title,
        description=description,
        item_ids=item_ids,
        watch_id=int(watch_id) if watch_id else None,
        fragrance_id=int(fragrance_id) if fragrance_id else None,
        accessory_id=int(accessory_id) if accessory_id else None,
        occasion=occasion,
        season=season,
        weather=weather,
        tags=tags,
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return _outfit_out(outfit, db, request)


@router.patch("/api/outfits/saved/{outfit_id}")
def update_saved_outfit(
    outfit_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    outfit = db.get(models.SavedOutfit, outfit_id)
    if not outfit or outfit.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    for field in ("title", "description", "occasion", "season", "weather"):
        if field in payload:
            setattr(outfit, field, str(payload[field] or ""))

    if "tags" in payload and isinstance(payload["tags"], list):
        outfit.tags = payload["tags"]

    if "item_ids" in payload:
        outfit.item_ids = [int(i) for i in payload["item_ids"] if i]

    for field in ("watch_id", "fragrance_id", "accessory_id"):
        if field in payload:
            val = payload[field]
            setattr(outfit, field, int(val) if val else None)

    db.commit()
    db.refresh(outfit)
    return _outfit_out(outfit, db, request)


@router.delete("/api/outfits/saved/{outfit_id}")
def delete_saved_outfit(
    outfit_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    outfit = db.get(models.SavedOutfit, outfit_id)
    if not outfit or outfit.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    db.delete(outfit)
    db.commit()
    return {"status": "deleted"}


@router.post("/api/outfits/saved/{outfit_id}/rate")
def rate_saved_outfit(
    outfit_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Lässt die KI das Outfit bewerten und cached das Ergebnis."""
    outfit = db.get(models.SavedOutfit, outfit_id)
    if not outfit or outfit.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    items_data = [
        _resolve_item(db, iid, request) or {}
        for iid in (outfit.item_ids or [])
    ]
    items_data = [i for i in items_data if i]

    watch_data = _resolve_watch(db, outfit.watch_id, request)
    fragrance_data = _resolve_fragrance(db, outfit.fragrance_id, request)
    accessory_data = _resolve_accessory(db, outfit.accessory_id, request)

    # Detailliertere Item-Daten für die Bewertung aus der DB laden
    full_items = []
    for iid in (outfit.item_ids or []):
        item = db.get(models.ClothingItem, iid)
        if item:
            full_items.append({
                "name": item.name,
                "category": item.category,
                "color": item.color,
                "material": item.material,
                "style": item.style,
                "occasion": item.occasion,
                "season": item.season,
                "brand": item.brand,
            })

    try:
        rating = openai_service.rate_outfit(
            items=full_items,
            occasion=outfit.occasion,
            season=outfit.season,
            weather=outfit.weather,
            watch=watch_data,
            fragrance=fragrance_data,
            accessory=accessory_data,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Bewertung fehlgeschlagen: {exc}")

    outfit.ai_rating = rating
    db.commit()
    return rating


@router.post("/api/outfits/saved/{outfit_id}/regenerate-title")
def regenerate_outfit_title(
    outfit_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Generiert Titel und Beschreibung neu."""
    outfit = db.get(models.SavedOutfit, outfit_id)
    if not outfit or outfit.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    full_items = []
    for iid in (outfit.item_ids or []):
        item = db.get(models.ClothingItem, iid)
        if item:
            full_items.append({
                "name": item.name, "category": item.category,
                "color": item.color, "material": item.material,
            })

    try:
        generated = openai_service.generate_outfit_title(
            full_items,
            occasion=outfit.occasion,
            season=outfit.season,
            weather=outfit.weather,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Titel-Generierung fehlgeschlagen: {exc}")

    outfit.title = generated.get("title", outfit.title)
    outfit.description = generated.get("description", outfit.description)
    db.commit()
    db.refresh(outfit)
    return _outfit_out(outfit, db, request)
