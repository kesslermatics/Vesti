"""MCP-kompatibler Read-Only Router.

Alle 6 Endpoints akzeptieren Authentifizierung über einen API-Key, der im
Header `X-API-Key` übermittelt wird. Die Endpoints geben ausschließlich
JSON zurück (keine Bilder, keine Binärdaten) und sind damit direkt als
MCP-Tools nutzbar.

Endpoints:
    GET /mcp/clothing        – Kleidungsstücke
    GET /mcp/watches         – Uhren
    GET /mcp/fragrances      – Düfte
    GET /mcp/accessories     – Accessoires
    GET /mcp/analytics/watches      – Uhren-Statistiken
    GET /mcp/analytics/fragrances   – Duft-Statistiken
    GET /mcp/analytics/accessories  – Accessoire-Statistiken
"""

from collections import Counter

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .analytics import compute_stats
from .analytics_collections import compute_fragrance_stats, compute_watch_stats
from .auth import get_user_by_api_key
from .collections_api import (
    _accessory_dict,
    _fragrance_dict,
    _watch_dict,
    user_accessories,
    user_fragrances,
    user_watches,
)
from .accessories import accessory_group
from .database import get_db
from .shared import wrist_cm

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ── Auth-Dependency ────────────────────────────────────────────────────────────

def _api_key_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> models.User:
    """Liest den API-Key aus dem Header und gibt den zugehörigen User zurück."""
    return get_user_by_api_key(x_api_key, db)


# ── Kleidung ───────────────────────────────────────────────────────────────────

@router.get(
    "/clothing",
    summary="Kleidungsstücke abrufen",
    description=(
        "Gibt alle Kleidungsstücke des Nutzers zurück. "
        "Felder: id, name, category, color, material, pattern, style, occasion, "
        "season, description, details, quantity, brand, favorite, created_at."
    ),
)
def mcp_clothing(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    items = db.scalars(
        select(models.ClothingItem)
        .where(models.ClothingItem.user_id == user.id)
        .order_by(models.ClothingItem.created_at.desc())
    ).all()
    return [
        {
            "id": it.id,
            "name": it.name,
            "category": it.category,
            "color": it.color,
            "material": it.material,
            "pattern": it.pattern,
            "style": it.style,
            "occasion": it.occasion,
            "season": it.season,
            "description": it.description,
            "details": it.details or {},
            "quantity": it.quantity,
            "brand": it.brand,
            "favorite": bool(it.favorite),
            "has_ai_image": bool(it.has_ai_image),
            "created_at": it.created_at,
        }
        for it in items
    ]


# ── Uhren ──────────────────────────────────────────────────────────────────────

@router.get(
    "/watches",
    summary="Uhren abrufen",
    description=(
        "Gibt alle Uhren der Sammlung zurück. "
        "Felder: id, name, brand, model, reference, year, movement, case_material, "
        "case_diameter, dial_color, band_material, style, occasions, complications, "
        "condition, purchase_price, current_value, favorite, needs_review, "
        "description, notes, created_at."
    ),
)
def mcp_watches(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    return user_watches(db, user.id)


# ── Düfte ──────────────────────────────────────────────────────────────────────

@router.get(
    "/fragrances",
    summary="Düfte abrufen",
    description=(
        "Gibt alle Düfte der Sammlung zurück. "
        "Felder: id, name, brand, line, concentration, year, family, "
        "top_notes, heart_notes, base_notes, sillage, longevity, occasions, "
        "seasons, bottle_size, fill_level, quantity, purchase_price, "
        "favorite, needs_review, description, notes, created_at."
    ),
)
def mcp_fragrances(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    return user_fragrances(db, user.id)


# ── Accessoires ────────────────────────────────────────────────────────────────

@router.get(
    "/accessories",
    summary="Accessoires abrufen",
    description=(
        "Gibt alle Accessoires der Sammlung zurück. "
        "Felder: id, name, brand, type, model, material, color, stone, style, "
        "occasions, condition, details, purchase_price, current_value, "
        "favorite, needs_review, description, notes, created_at."
    ),
)
def mcp_accessories(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    return user_accessories(db, user.id)


# ── Statistiken ────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/watches",
    summary="Uhren-Statistiken",
    description=(
        "Kennzahlen der Uhrensammlung: Verteilung nach Stil, Marke, Werk, "
        "Gehäusematerial, Zifferblattfarbe, Anlass, Komplikationen. "
        "Enthält außerdem Service-Fälligkeiten, aktive Garantien, "
        "Sammlungswert und erkannte Lücken."
    ),
)
def mcp_analytics_watches(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    watches = user_watches(db, user.id)
    return compute_watch_stats(watches, wrist_cm(user))


@router.get(
    "/analytics/fragrances",
    summary="Duft-Statistiken",
    description=(
        "Kennzahlen der Duftsammlung: Verteilung nach Duftfamilie, Note, "
        "Konzentration, Marke, Anlass, Tageszeit und Saison. "
        "Enthält niedrige Füllstände, bald ablaufende Flakons und erkannte Lücken."
    ),
)
def mcp_analytics_fragrances(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    fragrances = user_fragrances(db, user.id)
    return compute_fragrance_stats(fragrances)


@router.get(
    "/analytics/accessories",
    summary="Accessoire-Statistiken",
    description=(
        "Kennzahlen der Accessoire-Sammlung: Verteilung nach Typ, Gruppe, "
        "Marke, Material, Stil und Anlass."
    ),
)
def mcp_analytics_accessories(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
):
    rows = user_accessories(db, user.id)
    if not rows:
        return {"empty": True, "total": 0}

    type_counter: Counter = Counter()
    group_counter: Counter = Counter()
    brand_counter: Counter = Counter()
    material_counter: Counter = Counter()
    style_counter: Counter = Counter()
    occasion_counter: Counter = Counter()
    needs_review = 0

    for a in rows:
        if a.get("type"):
            type_counter[a["type"]] += 1
            group_counter[accessory_group(a["type"])] += 1
        if a.get("brand"):
            brand_counter[a["brand"]] += 1
        if a.get("material"):
            material_counter[a["material"]] += 1
        if a.get("style"):
            style_counter[a["style"]] += 1
        for occ in a.get("occasions") or []:
            occasion_counter[occ] += 1
        if a.get("needs_review"):
            needs_review += 1

    def _list(c: Counter) -> list[dict]:
        total = sum(c.values())
        return [
            {"label": k, "count": v, "share": round(v / total * 100) if total else 0}
            for k, v in c.most_common()
        ]

    return {
        "empty": False,
        "total": len(rows),
        "groups": _list(group_counter),
        "types": _list(type_counter)[:15],
        "brands": _list(brand_counter)[:10],
        "materials": _list(material_counter)[:10],
        "styles": _list(style_counter),
        "occasions": _list(occasion_counter),
        "needs_review": needs_review,
    }
