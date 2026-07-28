import base64

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import gemini_service, models
from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from .categories import CATEGORIES, CATEGORY_GROUPS, MATERIALS, OCCASIONS, SEASONS, STYLES
from .config import get_settings
from .database import Base, engine, get_db
from .schemas import (
    AnalyzeResponse,
    ItemCreate,
    ItemMetadata,
    ItemOut,
    RecommendedPiece,
    RecommendRequest,
    RecommendResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
)

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vesti API", version="2.0.0")

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

    return RecommendResponse(pieces=pieces, explanation=result["explanation"])
