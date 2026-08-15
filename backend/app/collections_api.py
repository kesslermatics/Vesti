"""REST-Endpunkte fuer die Uhren- und die Duftsammlung.

Beide Sammlungen folgen demselben Muster wie /api/items: erst analysieren,
dann bestaetigt speichern, Bilder liegen als Binaerdaten in der Datenbank.
Als eigener Router ausgelagert, damit main.py nicht weiter waechst.
"""

import base64
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import gemini_service, models
from .analytics_collections import (
    compute_fragrance_stats,
    compute_watch_stats,
    expiry_date,
    service_due_date,
)
from .auth import get_current_user
from .brands import canonicalize
from .database import get_db
from .fragrances import FRAGRANCE_BRANDS
from .schemas import (
    FragranceAnalyzeResponse,
    FragranceCreate,
    FragranceMetadata,
    FragranceOut,
    ImageUpload,
    WatchAnalyzeResponse,
    WatchCreate,
    WatchMetadata,
    WatchOut,
)
from .shared import (
    api_base,
    decode_b64,
    decode_image_payload,
    img_response,
    profile_dict,
    raise_image_error,
    wrist_cm,
)
from .watches import WATCH_BRANDS, wrist_size_advice

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════
#  Feldtypen fuer partielle Updates
# ══════════════════════════════════════════════════════════════════════

WATCH_FIELDS: dict[str, str] = {
    "name": "str", "brand": "str", "model": "str", "reference": "str",
    "movement": "str", "case_material": "str", "crystal": "str",
    "dial_color": "str", "band_type": "str", "band_material": "str",
    "band_color": "str", "clasp": "str", "style": "str",
    "condition": "str", "box_papers": "str", "currency": "str",
    "description": "str", "notes": "str",
    "case_diameter": "float", "case_thickness": "float", "lug_width": "float",
    "purchase_price": "float", "current_value": "float",
    "year": "int", "water_resistance": "int", "service_interval_years": "int",
    "complications": "list", "occasions": "list",
    "purchase_date": "date", "serviced_at": "date", "warranty_until": "date",
}

FRAGRANCE_FIELDS: dict[str, str] = {
    "name": "str", "brand": "str", "line": "str", "concentration": "str",
    "perfumer": "str", "audience": "str", "family": "str",
    "secondary_family": "str", "sillage": "str", "longevity": "str",
    "time_of_day": "str", "batch_code": "str", "currency": "str",
    "description": "str", "notes": "str",
    "purchase_price": "float",
    "year": "int", "bottle_size": "int", "fill_level": "int", "quantity": "int",
    "top_notes": "list", "heart_notes": "list", "base_notes": "list",
    "occasions": "list", "seasons": "list",
    "purchase_date": "date", "opened_at": "date",
}


def _parse_date(value: Any) -> datetime | None:
    """Nimmt ISO-Strings ('2024-05-01' oder mit Uhrzeit) und datetime-Objekte."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Nur Jahr angegeben
        if text.isdigit() and len(text) == 4:
            return datetime(int(text), 1, 1)
        raise HTTPException(status_code=400, detail=f"Datum '{value}' ist ungueltig.")


def _apply_updates(target: Any, payload: dict, fields: dict[str, str]) -> None:
    """Uebertraegt erlaubte Felder typgerecht auf ein Modell-Objekt."""
    for field, kind in fields.items():
        if field not in payload:
            continue
        raw = payload[field]

        if kind == "str":
            setattr(target, field, str(raw or ""))
        elif kind == "float":
            setattr(target, field, gemini_service._num(raw))
        elif kind == "int":
            setattr(target, field, gemini_service._int_or_none(raw))
        elif kind == "list":
            setattr(target, field, gemini_service._str_list_from(raw))
        elif kind == "date":
            setattr(target, field, _parse_date(raw))


def _fill_level_guard(value: Any) -> int | None:
    """Fuellstand auf 0-100 begrenzen."""
    parsed = gemini_service._int_or_none(value)
    if parsed is None:
        return None
    return max(0, min(100, parsed))


# ══════════════════════════════════════════════════════════════════════
#  Ausgabe-Mapper
# ══════════════════════════════════════════════════════════════════════

def _watch_out(request: Request, watch: models.Watch, wrist: float | None = None) -> WatchOut:
    base = api_base(request)
    out = WatchOut.model_validate(watch)
    out.image_url = f"{base}/api/watches/{watch.id}/image"
    out.thumbnail_url = f"{base}/api/watches/{watch.id}/thumbnail"
    out.image_urls = [out.image_url] + [
        f"{base}/api/watch-images/{img.id}" for img in (watch.extra_images or [])
    ]
    out.thumbnail_urls = [out.thumbnail_url] + [
        f"{base}/api/watch-images/{img.id}/thumbnail" for img in (watch.extra_images or [])
    ]
    if watch.ai_image_data:
        out.has_ai_image = True
        out.ai_image_url = f"{base}/api/watches/{watch.id}/ai-image"
        out.ai_thumbnail_url = f"{base}/api/watches/{watch.id}/ai-thumbnail"

    # Rechnerische Zusatzinfos
    due = service_due_date(_watch_dict(watch))
    if due:
        out.service_due_date = due
        out.service_due = due <= datetime.now(timezone.utc)
    out.wrist_advice = wrist_size_advice(wrist, watch.case_diameter)
    return out


def _fragrance_out(request: Request, frag: models.Fragrance) -> FragranceOut:
    base = api_base(request)
    out = FragranceOut.model_validate(frag)
    out.image_url = f"{base}/api/fragrances/{frag.id}/image"
    out.thumbnail_url = f"{base}/api/fragrances/{frag.id}/thumbnail"
    out.image_urls = [out.image_url] + [
        f"{base}/api/fragrance-images/{img.id}" for img in (frag.extra_images or [])
    ]
    out.thumbnail_urls = [out.thumbnail_url] + [
        f"{base}/api/fragrance-images/{img.id}/thumbnail" for img in (frag.extra_images or [])
    ]
    if frag.ai_image_data:
        out.has_ai_image = True
        out.ai_image_url = f"{base}/api/fragrances/{frag.id}/ai-image"
        out.ai_thumbnail_url = f"{base}/api/fragrances/{frag.id}/ai-thumbnail"

    expires = expiry_date(_fragrance_dict(frag))
    if expires:
        out.expires_at = expires
        out.expired = expires <= datetime.now(timezone.utc)
    if frag.fill_level is not None:
        out.low_stock = frag.fill_level <= 15
    return out


# ══════════════════════════════════════════════════════════════════════
#  Dict-Aufbereitung fuer KI und Statistik
# ══════════════════════════════════════════════════════════════════════

def _watch_dict(w: models.Watch) -> dict[str, Any]:
    return {
        "id": w.id,
        "name": w.name,
        "brand": w.brand,
        "model": w.model,
        "reference": w.reference,
        "year": w.year,
        "movement": w.movement,
        "case_material": w.case_material,
        "case_diameter": w.case_diameter,
        "case_thickness": w.case_thickness,
        "lug_width": w.lug_width,
        "crystal": w.crystal,
        "water_resistance": w.water_resistance,
        "complications": w.complications or [],
        "dial_color": w.dial_color,
        "band_type": w.band_type,
        "band_material": w.band_material,
        "band_color": w.band_color,
        "clasp": w.clasp,
        "style": w.style,
        "occasions": w.occasions or [],
        "condition": w.condition,
        "box_papers": w.box_papers,
        "purchase_date": w.purchase_date,
        "purchase_price": w.purchase_price,
        "current_value": w.current_value,
        "serviced_at": w.serviced_at,
        "service_interval_years": w.service_interval_years,
        "warranty_until": w.warranty_until,
        "favorite": bool(w.favorite),
        "needs_review": bool(w.needs_review),
        "description": w.description,
        "notes": w.notes,
        "created_at": w.created_at,
    }


def _fragrance_dict(f: models.Fragrance) -> dict[str, Any]:
    return {
        "id": f.id,
        "name": f.name,
        "brand": f.brand,
        "line": f.line,
        "concentration": f.concentration,
        "year": f.year,
        "perfumer": f.perfumer,
        "audience": f.audience,
        "family": f.family,
        "secondary_family": f.secondary_family,
        "top_notes": f.top_notes or [],
        "heart_notes": f.heart_notes or [],
        "base_notes": f.base_notes or [],
        "sillage": f.sillage,
        "longevity": f.longevity,
        "occasions": f.occasions or [],
        "seasons": f.seasons or [],
        "time_of_day": f.time_of_day,
        "bottle_size": f.bottle_size,
        "fill_level": f.fill_level,
        "quantity": f.quantity,
        "batch_code": f.batch_code,
        "purchase_date": f.purchase_date,
        "purchase_price": f.purchase_price,
        "opened_at": f.opened_at,
        "favorite": bool(f.favorite),
        "needs_review": bool(f.needs_review),
        "description": f.description,
        "notes": f.notes,
        "created_at": f.created_at,
    }


def user_watches(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Alle Uhren eines Nutzers als Dicts (fuer KI-Prompts und Statistik)."""
    rows = db.scalars(
        select(models.Watch)
        .where(models.Watch.user_id == user_id)
        .order_by(models.Watch.created_at.desc())
    ).all()
    return [_watch_dict(w) for w in rows]


def user_fragrances(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Alle Duefte eines Nutzers als Dicts (fuer KI-Prompts und Statistik)."""
    rows = db.scalars(
        select(models.Fragrance)
        .where(models.Fragrance.user_id == user_id)
        .order_by(models.Fragrance.created_at.desc())
    ).all()
    return [_fragrance_dict(f) for f in rows]


def _collection_brands(db: Session, model, user_id: int) -> list[str]:
    """Bereits verwendete Marken einer Sammlung, nach Haeufigkeit."""
    rows = db.execute(
        select(model.brand, func.count(model.id))
        .where(model.user_id == user_id, model.brand != "")
        .group_by(model.brand)
        .order_by(func.count(model.id).desc())
    ).all()
    return [r[0] for r in rows]


def _get_owned(db: Session, model, obj_id: int, user_id: int):
    obj = db.get(model, obj_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    return obj


def _reference_images(obj) -> list[tuple[bytes, str]]:
    """Hauptbild + Zusatzbilder als Referenzen fuer die KI."""
    refs: list[tuple[bytes, str]] = []
    if obj.image_data:
        refs.append((obj.image_data, obj.image_mime or "image/jpeg"))
    for extra in obj.extra_images or []:
        if extra.image_data:
            refs.append((extra.image_data, extra.image_mime or "image/jpeg"))
    return refs


# ══════════════════════════════════════════════════════════════════════
#  Marken
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/brands/watches")
def watch_brands(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    mine = _collection_brands(db, models.Watch, user.id)
    mine_lower = {b.lower() for b in mine}
    return {
        "mine": mine,
        "suggestions": [b for b in WATCH_BRANDS if b.lower() not in mine_lower],
    }


@router.get("/api/brands/fragrances")
def fragrance_brands(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    mine = _collection_brands(db, models.Fragrance, user.id)
    mine_lower = {b.lower() for b in mine}
    return {
        "mine": mine,
        "suggestions": [b for b in FRAGRANCE_BRANDS if b.lower() not in mine_lower],
    }


# ══════════════════════════════════════════════════════════════════════
#  Uhren: Analyse
# ══════════════════════════════════════════════════════════════════════

@router.post("/api/analyze/watch", response_model=WatchAnalyzeResponse)
def analyze_watch(
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Erkennt eine Uhr aus den Aufnahmen. Speichert noch nichts.

    Anders als bei Kleidung genuegt ein Durchgang: ist das Modell ueber
    Zifferblatt oder Referenznummer identifiziert, kommen die technischen Daten
    aus dem Modellwissen und nicht aus einer optischen Schaetzung.
    """
    images = decode_image_payload(payload)
    known = _collection_brands(db, models.Watch, user.id)

    try:
        data = gemini_service.analyze_watch_image(
            images, hint=payload.get("hint", ""), known_brands=known
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Uhren-Analyse fehlgeschlagen: {exc}")

    identified = data.pop("identified", False)
    confidence = data.pop("confidence", "")
    if data.get("brand"):
        data["brand"] = canonicalize(data["brand"], known + WATCH_BRANDS)

    return WatchAnalyzeResponse(
        metadata=WatchMetadata(**data),
        images=[
            ImageUpload(image_base64=base64.b64encode(d).decode(), image_mime=m)
            for d, m in images
        ],
        confidence=confidence,
        identified=identified,
    )


@router.post("/api/analyze/watch-shot")
def analyze_watch_shot(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    """Erzeugt aus den Aufnahmen ein sauberes Studio-Produktfoto der Uhr."""
    images = decode_image_payload(payload)

    try:
        result = gemini_service.generate_watch_shot(
            images,
            brand=payload.get("brand", ""),
            model=payload.get("model", ""),
            dial_color=payload.get("dial_color", ""),
            case_material=payload.get("case_material", ""),
            band_material=payload.get("band_material", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise_image_error(exc)

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    return {
        "ai_image_base64": base64.b64encode(data).decode(),
        "ai_image_mime": mime,
    }


# ══════════════════════════════════════════════════════════════════════
#  Uhren: CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/watches", response_model=list[WatchOut])
def list_watches(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watches = db.scalars(
        select(models.Watch)
        .where(models.Watch.user_id == user.id)
        .order_by(models.Watch.created_at.desc())
    ).all()
    wrist = wrist_cm(user)
    return [_watch_out(request, w, wrist) for w in watches]


@router.post("/api/watches", response_model=WatchOut)
def create_watch(
    payload: WatchCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    image_bytes = models._compress_image(decode_b64(payload.image_base64))

    known = _collection_brands(db, models.Watch, user.id)
    brand = canonicalize(payload.brand, known + WATCH_BRANDS) if payload.brand else ""

    data = payload.model_dump(
        exclude={"image_base64", "image_mime", "extra_images", "ai_image_base64", "ai_image_mime"}
    )
    data["brand"] = brand

    watch = models.Watch(
        user_id=user.id,
        image_data=image_bytes,
        image_mime=payload.image_mime or "image/jpeg",
        thumbnail_data=models._create_thumbnail(image_bytes),
        **data,
    )

    if payload.ai_image_base64:
        ai_bytes = decode_b64(payload.ai_image_base64, "KI-Bilddaten")
        watch.ai_image_data = ai_bytes
        watch.ai_image_mime = payload.ai_image_mime or "image/png"
        watch.ai_thumbnail_data = models._create_thumbnail(ai_bytes)

    for idx, extra in enumerate(payload.extra_images or []):
        if not extra.image_base64:
            continue
        extra_bytes = decode_b64(extra.image_base64, "Zusatzbild")
        watch.extra_images.append(
            models.WatchImage(
                position=idx,
                image_data=models._compress_image(extra_bytes),
                image_mime=extra.image_mime or "image/jpeg",
                thumbnail_data=models._create_thumbnail(extra_bytes),
            )
        )

    db.add(watch)
    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.patch("/api/watches/{watch_id}", response_model=WatchOut)
def update_watch(
    watch_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    _apply_updates(watch, payload, WATCH_FIELDS)

    if watch.brand:
        watch.brand = canonicalize(
            watch.brand, _collection_brands(db, models.Watch, user.id) + WATCH_BRANDS
        )
    # Eine manuelle Korrektur gilt als Pruefung
    watch.needs_review = False

    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.patch("/api/watches/{watch_id}/favorite", response_model=WatchOut)
def toggle_watch_favorite(
    watch_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    watch.favorite = bool(payload.get("favorite", False))
    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.delete("/api/watches/{watch_id}")
def delete_watch(
    watch_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    db.delete(watch)
    db.commit()
    return {"status": "deleted"}


@router.post("/api/watches/{watch_id}/reanalyze", response_model=WatchOut)
def reanalyze_watch(
    watch_id: int,
    request: Request,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Analysiert eine gespeicherte Uhr erneut anhand ihrer Bilder.

    Das ist der Weg fuer die aus der Garderobe migrierten Uhren: dort fehlen
    alle technischen Daten, weil sie als Kleidungsstueck erfasst waren.
    """
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    refs = _reference_images(watch)
    if not refs:
        raise HTTPException(status_code=400, detail="Keine Bilder zum Analysieren.")

    regenerate = True
    if payload and "regenerate_image" in payload:
        regenerate = bool(payload.get("regenerate_image"))

    known = _collection_brands(db, models.Watch, user.id)
    try:
        data = gemini_service.analyze_watch_image(refs, known_brands=known)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")

    data.pop("identified", None)
    data.pop("confidence", None)

    # Erkannte Werte gewinnen, leere Antworten ueberschreiben nichts
    for field, value in data.items():
        if field == "brand":
            if value:
                watch.brand = canonicalize(value, known + WATCH_BRANDS)
            continue
        if value in (None, "", []):
            continue
        setattr(watch, field, value)

    watch.needs_review = False

    if regenerate:
        try:
            result = gemini_service.generate_watch_shot(
                refs,
                brand=watch.brand,
                model=watch.model,
                dial_color=watch.dial_color,
                case_material=watch.case_material,
                band_material=watch.band_material,
            )
            if result:
                img, mime = result
                watch.ai_image_data = img
                watch.ai_image_mime = mime
                watch.ai_thumbnail_data = models._create_thumbnail(img)
        except Exception:  # noqa: BLE001
            pass  # KI-Foto ist optional

    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.post("/api/watches/{watch_id}/generate-image", response_model=WatchOut)
def generate_watch_image(
    watch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    refs = _reference_images(watch)
    if not refs:
        raise HTTPException(status_code=400, detail="Keine Bilder als Referenz.")

    try:
        result = gemini_service.generate_watch_shot(
            refs,
            brand=watch.brand,
            model=watch.model,
            dial_color=watch.dial_color,
            case_material=watch.case_material,
            band_material=watch.band_material,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise_image_error(exc)

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    watch.ai_image_data = data
    watch.ai_image_mime = mime
    watch.ai_thumbnail_data = models._create_thumbnail(data)
    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.delete("/api/watches/{watch_id}/ai-image", response_model=WatchOut)
def delete_watch_ai_image(
    watch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    watch.ai_image_data = None
    watch.ai_thumbnail_data = None
    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


@router.post("/api/watches/{watch_id}/images", response_model=WatchOut)
def add_watch_images(
    watch_id: int,
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watch = _get_owned(db, models.Watch, watch_id, user.id)
    raw = payload.get("images") or []
    if not raw:
        raise HTTPException(status_code=400, detail="Keine Bilder empfangen.")

    next_pos = max((e.position for e in watch.extra_images or []), default=-1) + 1
    added = 0
    for entry in raw:
        b64 = (entry or {}).get("image_base64", "")
        if not b64:
            continue
        data = decode_b64(b64)
        watch.extra_images.append(
            models.WatchImage(
                position=next_pos,
                image_data=models._compress_image(data),
                image_mime=entry.get("image_mime") or "image/jpeg",
                thumbnail_data=models._create_thumbnail(data),
            )
        )
        next_pos += 1
        added += 1

    if not added:
        raise HTTPException(status_code=400, detail="Keine gültigen Bilder.")

    db.commit()
    db.refresh(watch)
    return _watch_out(request, watch, wrist_cm(user))


# --- Uhren: Bild-Auslieferung (oeffentlich per ID, damit <img> sie laden kann) ---

@router.get("/api/watches/{watch_id}/image")
def get_watch_image(watch_id: int, db: Session = Depends(get_db)):
    watch = db.get(models.Watch, watch_id)
    if not watch or not watch.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return img_response(watch.image_data, watch.image_mime or "image/jpeg")


@router.get("/api/watches/{watch_id}/thumbnail")
def get_watch_thumbnail(watch_id: int, db: Session = Depends(get_db)):
    watch = db.get(models.Watch, watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    data = watch.thumbnail_data or watch.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    mime = "image/jpeg" if watch.thumbnail_data else (watch.image_mime or "image/jpeg")
    return img_response(data, mime)


@router.get("/api/watches/{watch_id}/ai-image")
def get_watch_ai_image(watch_id: int, db: Session = Depends(get_db)):
    watch = db.get(models.Watch, watch_id)
    if not watch or not watch.ai_image_data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    return img_response(watch.ai_image_data, watch.ai_image_mime or "image/png")


@router.get("/api/watches/{watch_id}/ai-thumbnail")
def get_watch_ai_thumbnail(watch_id: int, db: Session = Depends(get_db)):
    watch = db.get(models.Watch, watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    data = watch.ai_thumbnail_data or watch.ai_image_data
    if not data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    mime = "image/jpeg" if watch.ai_thumbnail_data else (watch.ai_image_mime or "image/png")
    return img_response(data, mime)


@router.get("/api/watch-images/{image_id}")
def get_watch_extra_image(image_id: int, db: Session = Depends(get_db)):
    img = db.get(models.WatchImage, image_id)
    if not img or not img.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return img_response(img.image_data, img.image_mime or "image/jpeg")


@router.get("/api/watch-images/{image_id}/thumbnail")
def get_watch_extra_thumbnail(image_id: int, db: Session = Depends(get_db)):
    img = db.get(models.WatchImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    data = img.thumbnail_data or img.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    mime = "image/jpeg" if img.thumbnail_data else (img.image_mime or "image/jpeg")
    return img_response(data, mime)


@router.delete("/api/watch-images/{image_id}")
def delete_watch_extra_image(
    image_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    img = db.get(models.WatchImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    _get_owned(db, models.Watch, img.watch_id, user.id)
    db.delete(img)
    db.commit()
    return {"status": "deleted"}


# ══════════════════════════════════════════════════════════════════════
#  Duefte: Analyse
# ══════════════════════════════════════════════════════════════════════

@router.post("/api/analyze/fragrance", response_model=FragranceAnalyzeResponse)
def analyze_fragrance(
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Erkennt einen Duft aus den Aufnahmen. Speichert noch nichts.

    Ein Duft ist auf einem Foto nicht riechbar – der Weg fuehrt ueber das
    Etikett. Ist der Duft identifiziert, liefert das Modell die Duftpyramide
    aus seinem Wissen; ist er es nicht, bleiben die Noten leer.
    """
    images = decode_image_payload(payload)
    known = _collection_brands(db, models.Fragrance, user.id)

    try:
        data = gemini_service.analyze_fragrance_image(
            images, hint=payload.get("hint", ""), known_brands=known
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Duft-Analyse fehlgeschlagen: {exc}")

    identified = data.pop("identified", False)
    confidence = data.pop("confidence", "")
    if data.get("brand"):
        data["brand"] = canonicalize(data["brand"], known + FRAGRANCE_BRANDS)

    return FragranceAnalyzeResponse(
        metadata=FragranceMetadata(**data),
        images=[
            ImageUpload(image_base64=base64.b64encode(d).decode(), image_mime=m)
            for d, m in images
        ],
        confidence=confidence,
        identified=identified,
    )


@router.post("/api/analyze/fragrance-shot")
def analyze_fragrance_shot(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    """Erzeugt aus den Aufnahmen ein sauberes Studio-Produktfoto des Flakons."""
    images = decode_image_payload(payload)

    try:
        result = gemini_service.generate_fragrance_shot(
            images,
            brand=payload.get("brand", ""),
            name=payload.get("name", ""),
            family=payload.get("family", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise_image_error(exc)

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    return {
        "ai_image_base64": base64.b64encode(data).decode(),
        "ai_image_mime": mime,
    }


# ══════════════════════════════════════════════════════════════════════
#  Duefte: CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/fragrances", response_model=list[FragranceOut])
def list_fragrances(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = db.scalars(
        select(models.Fragrance)
        .where(models.Fragrance.user_id == user.id)
        .order_by(models.Fragrance.created_at.desc())
    ).all()
    return [_fragrance_out(request, f) for f in rows]


@router.post("/api/fragrances", response_model=FragranceOut)
def create_fragrance(
    payload: FragranceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    image_bytes = models._compress_image(decode_b64(payload.image_base64))

    known = _collection_brands(db, models.Fragrance, user.id)
    brand = canonicalize(payload.brand, known + FRAGRANCE_BRANDS) if payload.brand else ""

    data = payload.model_dump(
        exclude={"image_base64", "image_mime", "extra_images", "ai_image_base64", "ai_image_mime"}
    )
    data["brand"] = brand
    data["quantity"] = max(1, data.get("quantity") or 1)
    data["fill_level"] = _fill_level_guard(data.get("fill_level"))

    frag = models.Fragrance(
        user_id=user.id,
        image_data=image_bytes,
        image_mime=payload.image_mime or "image/jpeg",
        thumbnail_data=models._create_thumbnail(image_bytes),
        **data,
    )

    if payload.ai_image_base64:
        ai_bytes = decode_b64(payload.ai_image_base64, "KI-Bilddaten")
        frag.ai_image_data = ai_bytes
        frag.ai_image_mime = payload.ai_image_mime or "image/png"
        frag.ai_thumbnail_data = models._create_thumbnail(ai_bytes)

    for idx, extra in enumerate(payload.extra_images or []):
        if not extra.image_base64:
            continue
        extra_bytes = decode_b64(extra.image_base64, "Zusatzbild")
        frag.extra_images.append(
            models.FragranceImage(
                position=idx,
                image_data=models._compress_image(extra_bytes),
                image_mime=extra.image_mime or "image/jpeg",
                thumbnail_data=models._create_thumbnail(extra_bytes),
            )
        )

    db.add(frag)
    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.patch("/api/fragrances/{fragrance_id}", response_model=FragranceOut)
def update_fragrance(
    fragrance_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    _apply_updates(frag, payload, FRAGRANCE_FIELDS)

    if "fill_level" in payload:
        frag.fill_level = _fill_level_guard(payload["fill_level"])
    if "quantity" in payload:
        frag.quantity = max(1, min(99, frag.quantity or 1))
    if frag.brand:
        frag.brand = canonicalize(
            frag.brand, _collection_brands(db, models.Fragrance, user.id) + FRAGRANCE_BRANDS
        )
    frag.needs_review = False

    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.patch("/api/fragrances/{fragrance_id}/favorite", response_model=FragranceOut)
def toggle_fragrance_favorite(
    fragrance_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    frag.favorite = bool(payload.get("favorite", False))
    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.patch("/api/fragrances/{fragrance_id}/fill-level", response_model=FragranceOut)
def update_fill_level(
    fragrance_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Fuellstand in Prozent setzen – die Basis fuer die Nachkauf-Warnung."""
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    frag.fill_level = _fill_level_guard(payload.get("fill_level"))
    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.delete("/api/fragrances/{fragrance_id}")
def delete_fragrance(
    fragrance_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    db.delete(frag)
    db.commit()
    return {"status": "deleted"}


@router.post("/api/fragrances/{fragrance_id}/reanalyze", response_model=FragranceOut)
def reanalyze_fragrance(
    fragrance_id: int,
    request: Request,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    refs = _reference_images(frag)
    if not refs:
        raise HTTPException(status_code=400, detail="Keine Bilder zum Analysieren.")

    regenerate = True
    if payload and "regenerate_image" in payload:
        regenerate = bool(payload.get("regenerate_image"))

    known = _collection_brands(db, models.Fragrance, user.id)
    try:
        data = gemini_service.analyze_fragrance_image(refs, known_brands=known)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")

    data.pop("identified", None)
    data.pop("confidence", None)

    for field, value in data.items():
        if field == "brand":
            if value:
                frag.brand = canonicalize(value, known + FRAGRANCE_BRANDS)
            continue
        if value in (None, "", []):
            continue
        setattr(frag, field, value)

    frag.needs_review = False

    if regenerate:
        try:
            result = gemini_service.generate_fragrance_shot(
                refs, brand=frag.brand, name=frag.name, family=frag.family
            )
            if result:
                img, mime = result
                frag.ai_image_data = img
                frag.ai_image_mime = mime
                frag.ai_thumbnail_data = models._create_thumbnail(img)
        except Exception:  # noqa: BLE001
            pass

    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.post("/api/fragrances/{fragrance_id}/generate-image", response_model=FragranceOut)
def generate_fragrance_image(
    fragrance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    refs = _reference_images(frag)
    if not refs:
        raise HTTPException(status_code=400, detail="Keine Bilder als Referenz.")

    try:
        result = gemini_service.generate_fragrance_shot(
            refs, brand=frag.brand, name=frag.name, family=frag.family
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise_image_error(exc)

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    frag.ai_image_data = data
    frag.ai_image_mime = mime
    frag.ai_thumbnail_data = models._create_thumbnail(data)
    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.delete("/api/fragrances/{fragrance_id}/ai-image", response_model=FragranceOut)
def delete_fragrance_ai_image(
    fragrance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    frag.ai_image_data = None
    frag.ai_thumbnail_data = None
    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


@router.post("/api/fragrances/{fragrance_id}/images", response_model=FragranceOut)
def add_fragrance_images(
    fragrance_id: int,
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    frag = _get_owned(db, models.Fragrance, fragrance_id, user.id)
    raw = payload.get("images") or []
    if not raw:
        raise HTTPException(status_code=400, detail="Keine Bilder empfangen.")

    next_pos = max((e.position for e in frag.extra_images or []), default=-1) + 1
    added = 0
    for entry in raw:
        b64 = (entry or {}).get("image_base64", "")
        if not b64:
            continue
        data = decode_b64(b64)
        frag.extra_images.append(
            models.FragranceImage(
                position=next_pos,
                image_data=models._compress_image(data),
                image_mime=entry.get("image_mime") or "image/jpeg",
                thumbnail_data=models._create_thumbnail(data),
            )
        )
        next_pos += 1
        added += 1

    if not added:
        raise HTTPException(status_code=400, detail="Keine gültigen Bilder.")

    db.commit()
    db.refresh(frag)
    return _fragrance_out(request, frag)


# --- Duefte: Bild-Auslieferung ---

@router.get("/api/fragrances/{fragrance_id}/image")
def get_fragrance_image(fragrance_id: int, db: Session = Depends(get_db)):
    frag = db.get(models.Fragrance, fragrance_id)
    if not frag or not frag.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return img_response(frag.image_data, frag.image_mime or "image/jpeg")


@router.get("/api/fragrances/{fragrance_id}/thumbnail")
def get_fragrance_thumbnail(fragrance_id: int, db: Session = Depends(get_db)):
    frag = db.get(models.Fragrance, fragrance_id)
    if not frag:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    data = frag.thumbnail_data or frag.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    mime = "image/jpeg" if frag.thumbnail_data else (frag.image_mime or "image/jpeg")
    return img_response(data, mime)


@router.get("/api/fragrances/{fragrance_id}/ai-image")
def get_fragrance_ai_image(fragrance_id: int, db: Session = Depends(get_db)):
    frag = db.get(models.Fragrance, fragrance_id)
    if not frag or not frag.ai_image_data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    return img_response(frag.ai_image_data, frag.ai_image_mime or "image/png")


@router.get("/api/fragrances/{fragrance_id}/ai-thumbnail")
def get_fragrance_ai_thumbnail(fragrance_id: int, db: Session = Depends(get_db)):
    frag = db.get(models.Fragrance, fragrance_id)
    if not frag:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    data = frag.ai_thumbnail_data or frag.ai_image_data
    if not data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    mime = "image/jpeg" if frag.ai_thumbnail_data else (frag.ai_image_mime or "image/png")
    return img_response(data, mime)


@router.get("/api/fragrance-images/{image_id}")
def get_fragrance_extra_image(image_id: int, db: Session = Depends(get_db)):
    img = db.get(models.FragranceImage, image_id)
    if not img or not img.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return img_response(img.image_data, img.image_mime or "image/jpeg")


@router.get("/api/fragrance-images/{image_id}/thumbnail")
def get_fragrance_extra_thumbnail(image_id: int, db: Session = Depends(get_db)):
    img = db.get(models.FragranceImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    data = img.thumbnail_data or img.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    mime = "image/jpeg" if img.thumbnail_data else (img.image_mime or "image/jpeg")
    return img_response(data, mime)


@router.delete("/api/fragrance-images/{image_id}")
def delete_fragrance_extra_image(
    image_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    img = db.get(models.FragranceImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    _get_owned(db, models.Fragrance, img.fragrance_id, user.id)
    db.delete(img)
    db.commit()
    return {"status": "deleted"}


# ══════════════════════════════════════════════════════════════════════
#  Statistik & KI-Einschaetzung der Sammlungen
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/analytics/watches")
def watch_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return compute_watch_stats(user_watches(db, user.id), wrist_cm(user))


@router.post("/api/analytics/watches/insights")
def watch_insights(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    watches = user_watches(db, user.id)
    if not watches:
        raise HTTPException(status_code=400, detail="Es sind noch keine Uhren erfasst.")

    stats = compute_watch_stats(watches, wrist_cm(user))
    try:
        return gemini_service.analyze_watch_collection(
            watches=watches, profile=profile_dict(user), stats=stats
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")


@router.get("/api/analytics/fragrances")
def fragrance_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return compute_fragrance_stats(user_fragrances(db, user.id))


@router.post("/api/analytics/fragrances/insights")
def fragrance_insights(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fragrances = user_fragrances(db, user.id)
    if not fragrances:
        raise HTTPException(status_code=400, detail="Es sind noch keine Düfte erfasst.")

    stats = compute_fragrance_stats(fragrances)
    try:
        return gemini_service.analyze_fragrance_collection(
            fragrances=fragrances, profile=profile_dict(user), stats=stats
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")


@router.post("/api/fragrances/advice")
def fragrance_advice_endpoint(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Gezielte Duftberatung aus dem eigenen Bestand.

    Beantwortet "welchen Duft nehme ich heute" mit einer konkreten Empfehlung
    plus Alternative, statt allgemein ueber Duftfamilien zu reden.
    """
    fragrances = user_fragrances(db, user.id)
    if not fragrances:
        raise HTTPException(status_code=400, detail="Es sind noch keine Düfte erfasst.")

    try:
        result = gemini_service.fragrance_advice(
            question=payload.get("question", ""),
            fragrances=fragrances,
            profile=profile_dict(user),
            occasion=payload.get("occasion", ""),
            season=payload.get("season", ""),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Beratung fehlgeschlagen: {exc}")

    def _detail(frag_id: int | None) -> dict | None:
        if not frag_id:
            return None
        frag = db.get(models.Fragrance, frag_id)
        if not frag or frag.user_id != user.id:
            return None
        out = _fragrance_out(request, frag)
        return {
            "id": frag.id,
            "name": frag.name,
            "brand": frag.brand,
            "thumbnail_url": out.ai_thumbnail_url or out.thumbnail_url,
        }

    return {
        "pick": _detail(result.get("fragrance_id")),
        "alternative": _detail(result.get("alternative_id")),
        "reason": result.get("reason", ""),
        "application": result.get("application", ""),
        "gap": result.get("gap", ""),
    }


@router.get("/api/collections/pending-review")
def pending_review(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Wie viele migrierte Eintraege noch auf die KI-Neuanalyse warten.

    Die aus der Garderobe umgezogenen Uhren haben keine technischen Daten,
    weil sie als Kleidungsstueck erfasst waren. Das Frontend blendet daraus
    einen Hinweis ein.
    """
    watches = db.scalar(
        select(func.count(models.Watch.id)).where(
            models.Watch.user_id == user.id, models.Watch.needs_review == True  # noqa: E712
        )
    ) or 0
    fragrances = db.scalar(
        select(func.count(models.Fragrance.id)).where(
            models.Fragrance.user_id == user.id,
            models.Fragrance.needs_review == True,  # noqa: E712
        )
    ) or 0
    return {"watches": watches, "fragrances": fragrances, "total": watches + fragrances}
