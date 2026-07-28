import base64

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import gemini_service, models
from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from .brands import KNOWN_BRANDS, canonicalize, normalize_key
from .categories import CATEGORIES, CATEGORY_GROUPS, MATERIALS, OCCASIONS, SEASONS, STYLES
from .config import get_settings
from .database import Base, engine, get_db
from .migrations import run_migrations
from .measurements import (
    BODY_TYPES,
    FIT_PREFERENCES,
    MEASUREMENT_FIELDS,
    SIZE_FIELDS,
)
from .schemas import (
    AnalyzeResponse,
    FitCheckRequest,
    FitCheckResponse,
    ItemCreate,
    ItemMetadata,
    ItemOut,
    ProfileUpdate,
    RecommendedPiece,
    RecommendRequest,
    RecommendResponse,
    ShoppingSuggestRequest,
    ShoppingSuggestResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
)

settings = get_settings()

Base.metadata.create_all(bind=engine)
run_migrations(engine)

app = FastAPI(title="Vesti API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _image_url(request: Request, item_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/items/{item_id}/image"


def _to_out(request: Request, item: models.ClothingItem) -> ItemOut:
    out = ItemOut.model_validate(item)
    out.image_url = _image_url(request, item.id)
    return out


# ---------- Health / Meta ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "model": settings.gemini_model}


@app.get("/api/meta")
def meta():
    return {
        "category_groups": CATEGORY_GROUPS,
        "categories": CATEGORIES,  # flache Liste fuer Rueckwaertskompatibilitaet
        "styles": STYLES,
        "occasions": OCCASIONS,
        "seasons": SEASONS,
        "materials": MATERIALS,
    }


# ---------- Auth ----------
@app.post("/api/auth/register", response_model=TokenResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    exists = db.scalar(select(models.User).where(models.User.email == email))
    if exists:
        raise HTTPException(status_code=409, detail="E-Mail ist bereits registriert.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 6 Zeichen haben.")

    user = models.User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch.")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)):
    return UserOut.model_validate(user)


# ---------- Marken ----------
def _user_brands(db: Session, user_id: int) -> list[str]:
    """Alle Marken, die der Nutzer bereits verwendet, nach Haeufigkeit sortiert."""
    rows = db.execute(
        select(models.ClothingItem.brand, func.count(models.ClothingItem.id))
        .where(
            models.ClothingItem.user_id == user_id,
            models.ClothingItem.brand != "",
        )
        .group_by(models.ClothingItem.brand)
        .order_by(func.count(models.ClothingItem.id).desc())
    ).all()
    return [r[0] for r in rows]


@app.get("/api/brands")
def brands(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Marken des Nutzers (zuerst) plus bekannte Marken als Vorschlaege."""
    mine = _user_brands(db, user.id)
    mine_keys = {normalize_key(b) for b in mine}
    suggestions = [b for b in KNOWN_BRANDS if normalize_key(b) not in mine_keys]
    return {"mine": mine, "suggestions": suggestions}


# ---------- Profil ----------
@app.get("/api/profile/fields")
def profile_fields():
    """Liefert die Mess-Felder inkl. Anleitung und die Groessen-Felder."""
    return {
        "measurements": MEASUREMENT_FIELDS,
        "sizes": SIZE_FIELDS,
        "fit_preferences": FIT_PREFERENCES,
        "body_types": BODY_TYPES,
    }


@app.put("/api/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.measurements is not None:
        user.measurements = payload.measurements
    if payload.sizes is not None:
        user.sizes = payload.sizes
    if payload.fit_preference is not None:
        user.fit_preference = payload.fit_preference
    if payload.body_type is not None:
        user.body_type = payload.body_type
    if payload.style_notes is not None:
        user.style_notes = payload.style_notes

    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


# ---------- Analyse (zweistufig) ----------
@app.post("/api/analyze/quick")
async def analyze_quick(
    file: UploadFile = File(...),
    hint: str = Form(default=""),
    user: models.User = Depends(get_current_user),
):
    """Schritt 1: Schnelle Kategorie & Farbe-Erkennung."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Leere Datei.")

    mime = file.content_type or "image/jpeg"
    try:
        data = gemini_service.quick_analyze_image(contents, file.filename or "upload.jpg", hint=hint)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"KI-Analyse fehlgeschlagen: {exc}")

    return {
        "category": data["category"],
        "color": data["color"],
        "image_base64": base64.b64encode(contents).decode(),
        "image_mime": mime,
    }


@app.post("/api/analyze/detail")
async def analyze_detail(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    """Schritt 2: Detaillierte Metadaten-Extraktion basierend auf Kategorie."""
    try:
        image_bytes = base64.b64decode(payload["image_base64"])
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    category = payload.get("category", "")
    hint = payload.get("hint", "")

    try:
        data = gemini_service.detail_analyze_image(
            image_bytes, "upload.jpg", category=category, hint=hint
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Detail-Analyse fehlgeschlagen: {exc}")

    return data


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    hint: str = Form(default=""),
    user: models.User = Depends(get_current_user),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Leere Datei.")

    mime = file.content_type or "image/jpeg"
    try:
        data = gemini_service.analyze_image(contents, file.filename or "upload.jpg", hint=hint)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"KI-Analyse fehlgeschlagen: {exc}")

    return AnalyzeResponse(
        metadata=ItemMetadata(**data),
        image_base64=base64.b64encode(contents).decode(),
        image_mime=mime,
    )


# ---------- Items ----------
@app.post("/api/items", response_model=ItemOut)
def create_item(
    payload: ItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    # Marke gegen bereits verwendete Schreibweisen normalisieren
    brand = canonicalize(payload.brand, _user_brands(db, user.id)) if payload.brand else ""

    item = models.ClothingItem(
        user_id=user.id,
        name=payload.name,
        category=payload.category,
        color=payload.color,
        material=payload.material,
        pattern=payload.pattern,
        style=payload.style,
        occasion=payload.occasion,
        season=payload.season,
        description=payload.description,
        details=payload.details or {},
        brand=brand,
        quantity=max(1, payload.quantity),
        image_data=image_bytes,
        image_mime=payload.image_mime or "image/jpeg",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(request, item)


@app.get("/api/items", response_model=list[ItemOut])
def list_items(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    items = db.scalars(
        select(models.ClothingItem)
        .where(models.ClothingItem.user_id == user.id)
        .order_by(models.ClothingItem.created_at.desc())
    ).all()
    return [_to_out(request, it) for it in items]


@app.get("/api/items/{item_id}/image")
def get_item_image(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Bild als Binaerdaten. Oeffentlich (per ID), damit <img>-Tags es laden koennen."""
    item = db.get(models.ClothingItem, item_id)
    if not item or not item.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return Response(content=item.image_data, media_type=item.image_mime)


@app.patch("/api/items/{item_id}/quantity", response_model=ItemOut)
def update_quantity(
    item_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Stueckzahl eines Teils aendern."""
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    try:
        qty = int(payload.get("quantity", 1))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Ungueltige Stückzahl.")
    item.quantity = max(1, min(999, qty))
    db.commit()
    db.refresh(item)
    return _to_out(request, item)


@app.delete("/api/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    base = db.get(models.ClothingItem, payload.item_id)
    if not base or base.user_id != user.id:
        raise HTTPException(status_code=404, detail="Basis-Teil nicht gefunden.")

    all_items = db.scalars(
        select(models.ClothingItem).where(models.ClothingItem.user_id == user.id)
    ).all()
    wardrobe = [
        {
            "id": it.id,
            "name": it.name,
            "category": it.category,
            "color": it.color,
            "style": it.style,
            "material": it.material,
        }
        for it in all_items
        if it.id != base.id
    ]

    base_dict = {
        "id": base.id,
        "name": base.name,
        "category": base.category,
        "color": base.color,
        "style": base.style,
    }

    try:
        result = gemini_service.recommend_outfit(
            base_dict, wardrobe, payload.occasion, payload.note
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Empfehlung fehlgeschlagen: {exc}")

    by_id = {it.id: it for it in all_items}
    ordered_ids = [base.id] + [i for i in result["item_ids"] if i in by_id and i != base.id]

    pieces = []
    for pid in ordered_ids:
        it = by_id.get(pid)
        if not it:
            continue
        pieces.append(
            RecommendedPiece(
                item_id=it.id,
                name=it.name or it.category,
                category=it.category,
                image_url=_image_url(request, it.id),
            )
        )

    return RecommendResponse(
        pieces=pieces,
        suitability=result.get("suitability", "geht"),
        suitability_reason=result.get("suitability_reason", ""),
        explanation=result["explanation"],
    )


# ---------- Shopping ----------
def _full_wardrobe(db: Session, user_id: int) -> list[dict]:
    """Komplette Garderobe eines Nutzers inkl. Details und Stueckzahl."""
    items = db.scalars(
        select(models.ClothingItem).where(models.ClothingItem.user_id == user_id)
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
            "brand": it.brand,
            "quantity": it.quantity,
            "details": it.details or {},
        }
        for it in items
    ]


def _profile_dict(user: models.User) -> dict:
    return {
        "measurements": user.measurements or {},
        "sizes": user.sizes or {},
        "fit_preference": user.fit_preference,
        "body_type": user.body_type,
        "style_notes": user.style_notes,
    }


@app.post("/api/shopping/suggest", response_model=ShoppingSuggestResponse)
def shopping_suggest(
    payload: ShoppingSuggestRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Schlaegt sinnvolle Ergaenzungen zur Garderobe vor (chatfaehig)."""
    wardrobe = _full_wardrobe(db, user.id)
    history = [{"role": m.role, "content": m.content} for m in payload.history]

    try:
        result = gemini_service.shopping_suggestions(
            wardrobe=wardrobe,
            profile=_profile_dict(user),
            direction=payload.direction,
            history=history,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Vorschläge fehlgeschlagen: {exc}")

    return ShoppingSuggestResponse(**result)


@app.post("/api/shopping/fitcheck", response_model=FitCheckResponse)
def shopping_fitcheck(
    payload: FitCheckRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Prueft ein Produkt aus einem Online-Shop gegen Garderobe und Profil."""
    if not payload.product_text.strip():
        raise HTTPException(status_code=400, detail="Bitte eine Produktbeschreibung angeben.")

    image_bytes = None
    if payload.image_base64:
        try:
            image_bytes = base64.b64decode(payload.image_base64)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    wardrobe = _full_wardrobe(db, user.id)

    try:
        result = gemini_service.fit_check(
            product_text=payload.product_text,
            wardrobe=wardrobe,
            profile=_profile_dict(user),
            image_bytes=image_bytes,
            image_mime=payload.image_mime or "image/jpeg",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Fit-Check fehlgeschlagen: {exc}")

    return FitCheckResponse(**result)
