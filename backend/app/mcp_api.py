"""MCP-kompatibler Read-Only Router.

Alle Endpoints akzeptieren Authentifizierung über einen API-Key, der im
Header `X-API-Key` übermittelt wird. Die Endpoints geben ausschließlich
JSON zurück (keine Bilder, keine Binärdaten) und sind damit direkt als
MCP-Tools nutzbar.

Endpoints:
    GET /mcp/clothing        – Kleidungsstücke (Filter: category, color, style, occasion, season, brand, favorite)
    GET /mcp/watches         – Uhren          (Filter: brand, style, movement, condition, favorite)
    GET /mcp/fragrances      – Düfte          (Filter: brand, family, concentration, season, occasion, favorite)
    GET /mcp/accessories     – Accessoires    (Filter: type, brand, style, occasion, favorite)
    GET /mcp/analytics/watches      – Uhren-Statistiken
    GET /mcp/analytics/fragrances   – Duft-Statistiken
    GET /mcp/analytics/accessories  – Accessoire-Statistiken
"""

from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
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


# ── Hilfsfunktionen ────────────────────────────────────────────────────────────

def _icontains(value: str, query: str) -> bool:
    """Prüft ob value den query-String case-insensitiv enthält."""
    return query.lower() in (value or "").lower()


def _list_icontains(lst: list, query: str) -> bool:
    """Prüft ob ein Element der Liste den query-String enthält (case-insensitiv)."""
    q = query.lower()
    return any(q in (item or "").lower() for item in lst)


# ── Kleidung ───────────────────────────────────────────────────────────────────

@router.get(
    "/clothing",
    summary="Kleidungsstücke abrufen",
    description=(
        "Gibt Kleidungsstücke des Nutzers zurück. Alle Filter sind optional und "
        "werden als case-insensitiver Substring-Match angewendet. "
        "Felder: id, name, category, color, material, pattern, style, occasion, "
        "season, description, details, quantity, brand, favorite, has_ai_image, created_at."
    ),
)
def mcp_clothing(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
    category: Optional[str] = Query(None, description="Kategorie, z.B. 'Oberteile'"),
    color: Optional[str] = Query(None, description="Farbe, z.B. 'Weiß'"),
    style: Optional[str] = Query(None, description="Stil, z.B. 'Business'"),
    occasion: Optional[str] = Query(None, description="Anlass, z.B. 'Formell'"),
    season: Optional[str] = Query(None, description="Saison, z.B. 'Sommer'"),
    brand: Optional[str] = Query(None, description="Marke, z.B. 'Zara'"),
    favorite: Optional[bool] = Query(None, description="Nur Favoriten (true/false)"),
):
    items = db.scalars(
        select(models.ClothingItem)
        .where(models.ClothingItem.user_id == user.id)
        .order_by(models.ClothingItem.created_at.desc())
    ).all()

    result = []
    for it in items:
        if category is not None and not _icontains(it.category, category):
            continue
        if color is not None and not _icontains(it.color, color):
            continue
        if style is not None and not _icontains(it.style, style):
            continue
        if occasion is not None and not _icontains(it.occasion, occasion):
            continue
        if season is not None and not _icontains(it.season, season):
            continue
        if brand is not None and not _icontains(it.brand, brand):
            continue
        if favorite is not None and bool(it.favorite) != favorite:
            continue

        result.append({
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
        })

    return result


# ── Uhren ──────────────────────────────────────────────────────────────────────

@router.get(
    "/watches",
    summary="Uhren abrufen",
    description=(
        "Gibt Uhren der Sammlung zurück. Alle Filter sind optional und "
        "werden als case-insensitiver Substring-Match angewendet. "
        "Felder: id, name, brand, model, reference, year, movement, case_material, "
        "case_diameter, dial_color, band_material, style, occasions, complications, "
        "condition, purchase_price, current_value, favorite, needs_review, "
        "description, notes, created_at."
    ),
)
def mcp_watches(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
    brand: Optional[str] = Query(None, description="Marke, z.B. 'Rolex'"),
    style: Optional[str] = Query(None, description="Stil, z.B. 'Sport'"),
    movement: Optional[str] = Query(None, description="Werk, z.B. 'Automatik'"),
    condition: Optional[str] = Query(None, description="Zustand, z.B. 'Sehr gut'"),
    favorite: Optional[bool] = Query(None, description="Nur Favoriten (true/false)"),
):
    watches = user_watches(db, user.id)

    if brand is None and style is None and movement is None and condition is None and favorite is None:
        return watches

    result = []
    for w in watches:
        if brand is not None and not _icontains(w.get("brand", ""), brand):
            continue
        if style is not None and not _icontains(w.get("style", ""), style):
            continue
        if movement is not None and not _icontains(w.get("movement", ""), movement):
            continue
        if condition is not None and not _icontains(w.get("condition", ""), condition):
            continue
        if favorite is not None and bool(w.get("favorite")) != favorite:
            continue
        result.append(w)

    return result


# ── Düfte ──────────────────────────────────────────────────────────────────────

@router.get(
    "/fragrances",
    summary="Düfte abrufen",
    description=(
        "Gibt Düfte der Sammlung zurück. Alle Filter sind optional und "
        "werden als case-insensitiver Substring-Match angewendet. "
        "season und occasion matchen gegen die jeweiligen Listen-Felder. "
        "Felder: id, name, brand, line, concentration, year, family, "
        "top_notes, heart_notes, base_notes, sillage, longevity, occasions, "
        "seasons, bottle_size, fill_level, quantity, purchase_price, "
        "favorite, needs_review, description, notes, created_at."
    ),
)
def mcp_fragrances(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
    brand: Optional[str] = Query(None, description="Marke, z.B. 'Dior'"),
    family: Optional[str] = Query(None, description="Duftfamilie, z.B. 'Holzig'"),
    concentration: Optional[str] = Query(None, description="Konzentration, z.B. 'EDP'"),
    season: Optional[str] = Query(None, description="Saison, z.B. 'Winter' (matcht gegen seasons-Liste)"),
    occasion: Optional[str] = Query(None, description="Anlass, z.B. 'Büro' (matcht gegen occasions-Liste)"),
    favorite: Optional[bool] = Query(None, description="Nur Favoriten (true/false)"),
):
    fragrances = user_fragrances(db, user.id)

    if brand is None and family is None and concentration is None and season is None and occasion is None and favorite is None:
        return fragrances

    result = []
    for f in fragrances:
        if brand is not None and not _icontains(f.get("brand", ""), brand):
            continue
        if family is not None and not (
            _icontains(f.get("family", ""), family)
            or _icontains(f.get("secondary_family", ""), family)
        ):
            continue
        if concentration is not None and not _icontains(f.get("concentration", ""), concentration):
            continue
        if season is not None and not _list_icontains(f.get("seasons") or [], season):
            continue
        if occasion is not None and not _list_icontains(f.get("occasions") or [], occasion):
            continue
        if favorite is not None and bool(f.get("favorite")) != favorite:
            continue
        result.append(f)

    return result


# ── Accessoires ────────────────────────────────────────────────────────────────

@router.get(
    "/accessories",
    summary="Accessoires abrufen",
    description=(
        "Gibt Accessoires der Sammlung zurück. Alle Filter sind optional und "
        "werden als case-insensitiver Substring-Match angewendet. "
        "occasion matcht gegen die occasions-Liste. "
        "Felder: id, name, brand, type, model, material, color, stone, style, "
        "occasions, condition, details, purchase_price, current_value, "
        "favorite, needs_review, description, notes, created_at."
    ),
)
def mcp_accessories(
    db: Session = Depends(get_db),
    user: models.User = Depends(_api_key_user),
    type: Optional[str] = Query(None, description="Typ, z.B. 'Ring' oder 'Sonnenbrille'"),
    brand: Optional[str] = Query(None, description="Marke, z.B. 'Ray-Ban'"),
    style: Optional[str] = Query(None, description="Stil, z.B. 'Casual'"),
    occasion: Optional[str] = Query(None, description="Anlass, z.B. 'Alltag' (matcht gegen occasions-Liste)"),
    favorite: Optional[bool] = Query(None, description="Nur Favoriten (true/false)"),
):
    accessories = user_accessories(db, user.id)

    if type is None and brand is None and style is None and occasion is None and favorite is None:
        return accessories

    result = []
    for a in accessories:
        if type is not None and not _icontains(a.get("type", ""), type):
            continue
        if brand is not None and not _icontains(a.get("brand", ""), brand):
            continue
        if style is not None and not _icontains(a.get("style", ""), style):
            continue
        if occasion is not None and not _list_icontains(a.get("occasions") or [], occasion):
            continue
        if favorite is not None and bool(a.get("favorite")) != favorite:
            continue
        result.append(a)

    return result


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
