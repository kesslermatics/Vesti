import base64
import json

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
from .analytics import compute_stats
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


def _thumbnail_url(request: Request, item_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/items/{item_id}/thumbnail"


def _extra_image_url(request: Request, image_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/item-images/{image_id}"


def _extra_thumbnail_url(request: Request, image_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/item-images/{image_id}/thumbnail"


def _ai_image_url(request: Request, item_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/items/{item_id}/ai-image"


def _ai_thumbnail_url(request: Request, item_id: int) -> str:
    return str(request.base_url).rstrip("/") + f"/api/items/{item_id}/ai-thumbnail"


def _to_out(request: Request, item: models.ClothingItem) -> ItemOut:
    out = ItemOut.model_validate(item)
    out.image_url = _image_url(request, item.id)
    out.thumbnail_url = _thumbnail_url(request, item.id)
    out.image_urls = [out.image_url] + [
        _extra_image_url(request, img.id) for img in (item.extra_images or [])
    ]
    out.thumbnail_urls = [out.thumbnail_url] + [
        _extra_thumbnail_url(request, img.id) for img in (item.extra_images or [])
    ]
    # KI-Produktfoto (nur wenn vorhanden)
    if item.ai_image_data:
        out.has_ai_image = True
        out.ai_image_url = _ai_image_url(request, item.id)
        out.ai_thumbnail_url = _ai_thumbnail_url(request, item.id)
    return out


def _generate_welcome_message(new_item: models.ClothingItem, existing_items: list[models.ClothingItem]) -> str:
    """Generiert eine kontextbezogene Willkommensnachricht für ein neues Teil."""
    if not existing_items:
        return f"🎉 Super Start! Dein {new_item.name or new_item.category} ist das erste Teil in deiner Garderobe."
    
    # Ähnliche Teile finden (gleiche Kategorie oder Farbe)
    same_category = [it for it in existing_items if it.category == new_item.category]
    same_color = [it for it in existing_items if it.color and new_item.color and it.color.lower() == new_item.color.lower()]
    
    # INTELLIGENTE Kombinationen - nach Style-Regeln
    style_matches = {
        # Accessoires
        "Gürtel": {
            "matches": ["Schuhe", "Stiefel", "Sneaker", "Loafer", "Boots"],
            "rule": "color",
            "message": "Perfekt kombinierbar mit deinen {color} {category}!"
        },
        "Schuhe": {
            "matches": ["Gürtel", "Anzughose", "Chino", "Jeans"],
            "rule": "style",
            "message": "Tolle Ergänzung zu deinem {style}-Stil!"
        },
        "Sneaker": {
            "matches": ["Jeans", "Chino", "Jogginghose", "Shorts"],
            "rule": "casual",
            "message": "Lässig kombinierbar mit deinen {category}!"
        },
        "Stiefel": {
            "matches": ["Gürtel", "Jeans", "Chino"],
            "rule": "color",
            "message": "Robuste Ergänzung zu deinen {category}!"
        },
        "Boots": {
            "matches": ["Gürtel", "Jeans", "Chino"],
            "rule": "color",
            "message": "Starke Kombi mit deinen {category}!"
        },
        "Loafer": {
            "matches": ["Gürtel", "Chino", "Anzughose"],
            "rule": "formal",
            "message": "Elegante Basis mit deiner {category}!"
        },
        "Krawatte": {
            "matches": ["Hemd", "Anzug", "Blazer", "Sakko"],
            "rule": "occasion",
            "message": "Perfekt für formelle Anlässe mit deinem {category}!"
        },
        "Fliege": {
            "matches": ["Hemd", "Anzug", "Smoking"],
            "rule": "occasion",
            "message": "Elegantes Detail zu deinem {category}!"
        },
        "Einstecktuch": {
            "matches": ["Anzug", "Blazer", "Sakko"],
            "rule": "occasion",
            "message": "Elegante Ergänzung zu deinem {category}!"
        },
        "Schal": {
            "matches": ["Mantel", "Jacke", "Parka"],
            "rule": "layer",
            "message": "Hält dich warm mit deiner {category}!"
        },
        "Mütze": {
            "matches": ["Mantel", "Jacke", "Parka"],
            "rule": "layer",
            "message": "Perfekt für kalte Tage mit deiner {category}!"
        },
        "Cap": {
            "matches": ["T-Shirt", "Hoodie", "Jogginghose"],
            "rule": "casual",
            "message": "Casual-Style mit deinem {category}!"
        },
        
        # Oberteile
        "T-Shirt": {
            "matches": ["Jeans", "Chino", "Shorts", "Jogginghose"],
            "rule": "casual",
            "message": "Lässig kombinierbar mit deinen {category}!"
        },
        "Hemd": {
            "matches": ["Anzughose", "Chino", "Blazer", "Sakko", "Anzug"],
            "rule": "formal",
            "message": "Elegante Basis für Outfits mit deiner {category}!"
        },
        "Polo": {
            "matches": ["Chino", "Jeans", "Shorts"],
            "rule": "smart-casual",
            "message": "Smart-Casual mit deinen {category}!"
        },
        "Pullover": {
            "matches": ["Hemd", "Jeans", "Chino"],
            "rule": "layer",
            "message": "Schöne Schicht über deinem {category}!"
        },
        "Cardigan": {
            "matches": ["Hemd", "T-Shirt", "Chino"],
            "rule": "layer",
            "message": "Vielseitige Layer-Option mit deinem {category}!"
        },
        "Hoodie": {
            "matches": ["Jeans", "Jogginghose", "Shorts"],
            "rule": "casual",
            "message": "Gemütlich kombinierbar mit deinen {category}!"
        },
        "Sweatshirt": {
            "matches": ["Jeans", "Chino", "Jogginghose"],
            "rule": "casual",
            "message": "Relaxed-Fit mit deinen {category}!"
        },
        "Weste": {
            "matches": ["Hemd", "Anzug", "Chino"],
            "rule": "formal",
            "message": "Elegante Schicht zu deinem {category}!"
        },
        
        # Jacken & Mäntel
        "Blazer": {
            "matches": ["Hemd", "Chino", "Anzughose"],
            "rule": "formal",
            "message": "Verleiht deinem {category} mehr Eleganz!"
        },
        "Sakko": {
            "matches": ["Hemd", "Chino", "Anzughose"],
            "rule": "formal",
            "message": "Business-ready mit deinem {category}!"
        },
        "Anzug": {
            "matches": ["Hemd", "Krawatte", "Fliege"],
            "rule": "formal",
            "message": "Komplettiert dein formelles Outfit mit {category}!"
        },
        "Smoking": {
            "matches": ["Hemd", "Fliege", "Krawatte"],
            "rule": "formal",
            "message": "Höchste Eleganz mit deinem {category}!"
        },
        "Jacke": {
            "matches": ["T-Shirt", "Hemd", "Pullover"],
            "rule": "layer",
            "message": "Praktische Ergänzung zu deinem {category}!"
        },
        "Mantel": {
            "matches": ["Anzug", "Hemd", "Pullover", "Schal"],
            "rule": "layer",
            "message": "Stilvoller Schutz über deinem {category}!"
        },
        "Parka": {
            "matches": ["Hoodie", "Pullover", "Sweatshirt"],
            "rule": "casual",
            "message": "Warm und praktisch mit deinem {category}!"
        },
        "Lederjacke": {
            "matches": ["T-Shirt", "Jeans", "Chino"],
            "rule": "casual",
            "message": "Cooler Edge mit deinen {category}!"
        },
        "Bomberjacke": {
            "matches": ["T-Shirt", "Hoodie", "Jeans"],
            "rule": "casual",
            "message": "Streetstyle-Vibe mit deinem {category}!"
        },
        
        # Hosen
        "Anzughose": {
            "matches": ["Hemd", "Blazer", "Sakko", "Anzug"],
            "rule": "formal",
            "message": "Business-ready mit deinem {category}!"
        },
        "Chino": {
            "matches": ["Hemd", "T-Shirt", "Pullover", "Blazer", "Polo"],
            "rule": "versatile",
            "message": "Vielseitig kombinierbar mit deinem {category}!"
        },
        "Jeans": {
            "matches": ["T-Shirt", "Hemd", "Pullover", "Jacke", "Hoodie"],
            "rule": "casual",
            "message": "Klassische Kombi mit deinem {category}!"
        },
        "Jogginghose": {
            "matches": ["Hoodie", "Sweatshirt", "T-Shirt"],
            "rule": "casual",
            "message": "Relaxed-Look mit deinem {category}!"
        },
        "Shorts": {
            "matches": ["T-Shirt", "Polo", "Hoodie"],
            "rule": "casual",
            "message": "Sommer-ready mit deinem {category}!"
        },
        
        # Weitere
        "Kleid": {
            "matches": ["Jacke", "Blazer", "Cardigan", "Mantel"],
            "rule": "layer",
            "message": "Elegante Ergänzung zu deinem {category}!"
        },
        "Rock": {
            "matches": ["T-Shirt", "Hemd", "Pullover", "Blazer"],
            "rule": "versatile",
            "message": "Schön kombinierbar mit deinem {category}!"
        },
    }
    
    # Prüfe ob es intelligente Style-Matches gibt
    if new_item.category in style_matches:
        match_config = style_matches[new_item.category]
        target_categories = match_config["matches"]
        rule = match_config["rule"]
        
        # Suche passende Teile nach Regel
        matching_items = []
        for it in existing_items:
            if it.category not in target_categories:
                continue
            
            # Regel anwenden
            if rule == "color" and new_item.color and it.color:
                # Farbvergleich (exakt oder neutral)
                neutrals = ["schwarz", "weiß", "grau", "beige", "braun"]
                if (new_item.color.lower() == it.color.lower() or 
                    (new_item.color.lower() in neutrals and it.color.lower() in neutrals)):
                    matching_items.append(it)
            elif rule == "style" and new_item.style and it.style:
                if new_item.style.lower() == it.style.lower():
                    matching_items.append(it)
            elif rule in ["formal", "casual", "versatile", "layer", "occasion", "smart-casual"]:
                matching_items.append(it)
        
        if matching_items:
            example = matching_items[0]
            msg_template = match_config["message"]
            return msg_template.format(
                category=example.category,
                color=example.color or "",
                style=example.style or ""
            ).replace("  ", " ")
    
    # Fallback: Zu viele vom gleichen?
    if len(same_category) >= 3:
        return f"Du liebst {new_item.category}! Mit {len(same_category) + 1} Stück hast du jetzt eine solide Auswahl."
    
    # Fallback: Garderobe wächst
    if len(existing_items) < 5:
        return f"Deine Garderobe wächst! {new_item.name or new_item.category} ist eine tolle Ergänzung."
    
    # Standard-Fallback
    return f"✨ {new_item.name or new_item.category} wurde zur Garderobe hinzugefügt!"


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
    files: list[UploadFile] = File(...),
    hint: str = Form(default=""),
    user: models.User = Depends(get_current_user),
):
    """Schritt 1: Schnelle Kategorie & Farbe-Erkennung (ein oder mehrere Bilder)."""
    images: list[tuple[bytes, str]] = []
    for f in files:
        data = await f.read()
        if data:
            images.append((data, f.content_type or "image/jpeg"))

    if not images:
        raise HTTPException(status_code=400, detail="Keine Bilddaten empfangen.")

    try:
        result = gemini_service.quick_analyze_image(images, hint=hint)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"KI-Analyse fehlgeschlagen: {exc}")

    encoded = [
        {"image_base64": base64.b64encode(data).decode(), "image_mime": mime}
        for data, mime in images
    ]

    return {
        "category": result["category"],
        "color": result["color"],
        # Erstes Bild bleibt das Hauptbild (Rueckwaertskompatibilitaet)
        "image_base64": encoded[0]["image_base64"],
        "image_mime": encoded[0]["image_mime"],
        "images": encoded,
    }


@app.post("/api/analyze/detail")
async def analyze_detail(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    """Schritt 2: Detaillierte Metadaten-Extraktion basierend auf Kategorie."""
    raw_images = payload.get("images")
    if not raw_images:
        raw_images = [
            {
                "image_base64": payload.get("image_base64", ""),
                "image_mime": payload.get("image_mime", "image/jpeg"),
            }
        ]

    images: list[tuple[bytes, str]] = []
    for entry in raw_images:
        b64 = (entry or {}).get("image_base64", "")
        if not b64:
            continue
        try:
            images.append((base64.b64decode(b64), entry.get("image_mime") or "image/jpeg"))
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    if not images:
        raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    category = payload.get("category", "")
    hint = payload.get("hint", "")

    try:
        data = gemini_service.detail_analyze_image(
            images, category=category, hint=hint
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Detail-Analyse fehlgeschlagen: {exc}")

    return data


@app.post("/api/analyze/product-shot")
async def analyze_product_shot(
    payload: dict,
    user: models.User = Depends(get_current_user),
):
    """Schritt 3 (optional): Erzeugt aus den Nutzerfotos ein sauberes KI-Produktfoto."""
    raw_images = payload.get("images")
    if not raw_images:
        raw_images = [
            {
                "image_base64": payload.get("image_base64", ""),
                "image_mime": payload.get("image_mime", "image/jpeg"),
            }
        ]

    images: list[tuple[bytes, str]] = []
    for entry in raw_images:
        b64 = (entry or {}).get("image_base64", "")
        if not b64:
            continue
        try:
            images.append((base64.b64decode(b64), entry.get("image_mime") or "image/jpeg"))
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    if not images:
        raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")

    try:
        result = gemini_service.generate_product_shot(
            images,
            category=payload.get("category", ""),
            color=payload.get("color", ""),
            material=payload.get("material", ""),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Bildgenerierung fehlgeschlagen: {exc}")

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    return {
        "ai_image_base64": base64.b64encode(data).decode(),
        "ai_image_mime": mime,
    }


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
@app.post("/api/items")
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
        thumbnail_data=models._create_thumbnail(image_bytes),
    )

    # Optionales KI-Produktfoto übernehmen
    if payload.ai_image_base64:
        try:
            ai_bytes = base64.b64decode(payload.ai_image_base64)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="KI-Bilddaten ungueltig.")
        item.ai_image_data = ai_bytes
        item.ai_image_mime = payload.ai_image_mime or "image/png"
        item.ai_thumbnail_data = models._create_thumbnail(ai_bytes)

    # Zusatzbilder (Futter, Etikett, Detailaufnahmen)
    for idx, extra in enumerate(payload.extra_images or []):
        if not extra.image_base64:
            continue
        try:
            extra_bytes = base64.b64decode(extra.image_base64)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Zusatzbild ungueltig.")
        item.extra_images.append(
            models.ItemImage(
                position=idx,
                image_data=extra_bytes,
                image_mime=extra.image_mime or "image/jpeg",
                thumbnail_data=models._create_thumbnail(extra_bytes),
            )
        )

    db.add(item)
    db.commit()
    db.refresh(item)
    
    # Generiere Welcome-Message basierend auf Garderobe
    existing_items = db.scalars(
        select(models.ClothingItem)
        .where(
            models.ClothingItem.user_id == user.id,
            models.ClothingItem.id != item.id
        )
    ).all()
    
    welcome_msg = _generate_welcome_message(item, existing_items)
    
    result = _to_out(request, item)
    # Füge Welcome-Message hinzu (als zusätzliches Feld im Response)
    result_dict = result.model_dump()
    result_dict["welcome_message"] = welcome_msg
    
    return result_dict


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


@app.get("/api/items/{item_id}/thumbnail")
def get_item_thumbnail(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Thumbnail als Binaerdaten für schnelleres Laden in Übersichten."""
    item = db.get(models.ClothingItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden.")
    # Fallback auf Vollbild wenn kein Thumbnail
    data = item.thumbnail_data if item.thumbnail_data else item.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return Response(content=data, media_type="image/jpeg")


@app.get("/api/item-images/{image_id}")
def get_extra_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    """Zusatzbild als Binaerdaten (Futter, Etikett, Detail)."""
    img = db.get(models.ItemImage, image_id)
    if not img or not img.image_data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return Response(content=img.image_data, media_type=img.image_mime)


@app.get("/api/item-images/{image_id}/thumbnail")
def get_extra_thumbnail(
    image_id: int,
    db: Session = Depends(get_db),
):
    """Zusatzbild-Thumbnail für schnelleres Laden."""
    img = db.get(models.ItemImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    # Fallback auf Vollbild wenn kein Thumbnail
    data = img.thumbnail_data if img.thumbnail_data else img.image_data
    if not data:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return Response(content=data, media_type="image/jpeg")


@app.get("/api/items/{item_id}/ai-image")
def get_ai_image(
    item_id: int,
    db: Session = Depends(get_db),
):
    """KI-generiertes Produktfoto (Vollauflösung)."""
    item = db.get(models.ClothingItem, item_id)
    if not item or not item.ai_image_data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    return Response(content=item.ai_image_data, media_type=item.ai_image_mime or "image/png")


@app.get("/api/items/{item_id}/ai-thumbnail")
def get_ai_thumbnail(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Thumbnail des KI-Produktfotos."""
    item = db.get(models.ClothingItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden.")
    data = item.ai_thumbnail_data if item.ai_thumbnail_data else item.ai_image_data
    if not data:
        raise HTTPException(status_code=404, detail="Kein KI-Bild vorhanden.")
    return Response(content=data, media_type="image/jpeg")


@app.post("/api/items/{item_id}/generate-image", response_model=ItemOut)
def generate_item_image(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Erzeugt (oder erneuert) das KI-Produktfoto für ein bestehendes Teil.

    Nutzt das Originalbild + alle Zusatzbilder als Referenz.
    """
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    # Referenzbilder sammeln (Original zuerst, dann Zusatzbilder)
    refs: list[tuple[bytes, str]] = [(item.image_data, item.image_mime or "image/jpeg")]
    for extra in item.extra_images or []:
        if extra.image_data:
            refs.append((extra.image_data, extra.image_mime or "image/jpeg"))

    try:
        result = gemini_service.generate_product_shot(
            refs,
            category=item.category,
            color=item.color,
            material=item.material,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Bildgenerierung fehlgeschlagen: {exc}")

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    item.ai_image_data = data
    item.ai_image_mime = mime
    item.ai_thumbnail_data = models._create_thumbnail(data)
    db.commit()
    db.refresh(item)
    return _to_out(request, item)


@app.delete("/api/items/{item_id}/ai-image", response_model=ItemOut)
def delete_ai_image(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Entfernt das KI-Produktfoto wieder."""
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    item.ai_image_data = None
    item.ai_thumbnail_data = None
    db.commit()
    db.refresh(item)
    return _to_out(request, item)


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


@app.patch("/api/items/{item_id}/favorite", response_model=ItemOut)
def toggle_favorite(
    item_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Favoriten-Status umschalten."""
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    item.favorite = bool(payload.get("favorite", False))
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


def _item_reference_images(item: models.ClothingItem) -> list[tuple[bytes, str]]:
    """Sammelt Original + Zusatzbilder eines Teils als (bytes, mime)-Liste."""
    refs: list[tuple[bytes, str]] = []
    if item.image_data:
        refs.append((item.image_data, item.image_mime or "image/jpeg"))
    for extra in item.extra_images or []:
        if extra.image_data:
            refs.append((extra.image_data, extra.image_mime or "image/jpeg"))
    return refs


@app.post("/api/items/{item_id}/reanalyze", response_model=ItemOut)
def reanalyze_item(
    item_id: int,
    request: Request,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Analysiert ein bestehendes Teil erneut anhand der gespeicherten Bilder.

    Aktualisiert Metadaten + Details und erzeugt optional ein neues KI-Produktfoto.
    """
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    refs = _item_reference_images(item)
    if not refs:
        raise HTTPException(status_code=400, detail="Keine Bilder zum Analysieren.")

    regenerate_image = True
    if payload and "regenerate_image" in payload:
        regenerate_image = bool(payload.get("regenerate_image"))

    # Schritt 1: Kategorie & Farbe
    try:
        quick = gemini_service.quick_analyze_image(refs)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")

    category = quick.get("category") or item.category

    # Schritt 2: Details
    try:
        detail = gemini_service.detail_analyze_image(refs, category=category)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Detail-Analyse fehlgeschlagen: {exc}")

    # Metadaten aktualisieren
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
        # bestehende Details mit neuen zusammenführen (neue gewinnen)
        merged = dict(item.details or {})
        merged.update(new_details)
        item.details = merged

    # Schritt 3: optional neues KI-Produktfoto
    if regenerate_image:
        try:
            result = gemini_service.generate_product_shot(
                refs,
                category=item.category,
                color=item.color,
                material=item.material,
            )
            if result:
                data, mime = result
                item.ai_image_data = data
                item.ai_image_mime = mime
                item.ai_thumbnail_data = models._create_thumbnail(data)
        except Exception:  # noqa: BLE001
            pass  # KI-Foto ist optional

    db.commit()
    db.refresh(item)
    return _to_out(request, item)


@app.post("/api/items/{item_id}/images", response_model=ItemOut)
def add_item_images(
    item_id: int,
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Fügt einem bestehenden Teil nachträglich weitere Bilder hinzu."""
    item = db.get(models.ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    raw_images = payload.get("images") or []
    if not raw_images:
        raise HTTPException(status_code=400, detail="Keine Bilder empfangen.")

    # Nächste Position bestimmen
    existing = item.extra_images or []
    next_pos = (max((e.position for e in existing), default=-1)) + 1

    added = 0
    for entry in raw_images:
        b64 = (entry or {}).get("image_base64", "")
        if not b64:
            continue
        try:
            data = base64.b64decode(b64)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Bilddaten ungueltig.")
        item.extra_images.append(
            models.ItemImage(
                position=next_pos,
                image_data=data,
                image_mime=entry.get("image_mime") or "image/jpeg",
                thumbnail_data=models._create_thumbnail(data),
            )
        )
        next_pos += 1
        added += 1

    if not added:
        raise HTTPException(status_code=400, detail="Keine gültigen Bilder.")

    db.commit()
    db.refresh(item)
    return _to_out(request, item)


@app.delete("/api/item-images/{image_id}")
def delete_extra_image(
    image_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Löscht ein einzelnes Zusatzbild."""
    img = db.get(models.ItemImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    item = db.get(models.ClothingItem, img.item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Nicht gefunden.")
    db.delete(img)
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


@app.post("/api/outfits/generate")
def generate_outfits_endpoint(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Generiert mehrere komplette Outfit-Vorschläge aus der Garderobe."""
    occasion = payload.get("occasion", "")
    note = payload.get("note", "")
    count = min(10, max(1, int(payload.get("count", 5))))
    
    all_items = db.scalars(
        select(models.ClothingItem).where(models.ClothingItem.user_id == user.id)
    ).all()
    
    if not all_items:
        raise HTTPException(status_code=400, detail="Deine Garderobe ist noch leer.")
    
    wardrobe = [
        {
            "id": it.id,
            "name": it.name,
            "category": it.category,
            "color": it.color,
            "style": it.style,
            "material": it.material,
            "quantity": it.quantity,
        }
        for it in all_items
    ]
    
    try:
        result = gemini_service.generate_outfits(wardrobe, occasion, note, count)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Outfit-Generierung fehlgeschlagen: {exc}")
    
    by_id = {it.id: it for it in all_items}
    
    outfits = []
    for outfit in result["outfits"]:
        items = []
        for item_id in outfit["item_ids"]:
            it = by_id.get(item_id)
            if not it:
                continue
            items.append({
                "id": it.id,
                "name": it.name or it.category,
                "category": it.category,
                "image_url": _image_url(request, it.id),
            })
        
        if items:  # Only include outfits with valid items
            outfits.append({
                "items": items,
                "title": outfit["title"],
                "why": outfit["why"],
            })
    
    return {"outfits": outfits}


@app.post("/api/outfits/tryon")
def outfit_tryon(
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Generiert ein KI-Anprobe-Bild: eine Person, die das Outfit trägt.

    Erwartet {"item_ids": [...], "occasion": "..."}. Kostet ~3-4 Cent pro Aufruf,
    daher nur auf expliziten Wunsch (Button), nicht automatisch.
    """
    raw_ids = payload.get("item_ids") or []
    occasion = payload.get("occasion", "")

    item_ids: list[int] = []
    for i in raw_ids:
        try:
            item_ids.append(int(i))
        except (ValueError, TypeError):
            continue

    if not item_ids:
        raise HTTPException(status_code=400, detail="Keine Teile angegeben.")

    # Bevorzugt das Hauptbild jedes Teils als Referenz (max. ~10 Teile)
    refs: list[tuple[bytes, str]] = []
    labels: list[str] = []
    for iid in item_ids[:10]:
        it = db.get(models.ClothingItem, iid)
        if not it or it.user_id != user.id or not it.image_data:
            continue
        refs.append((it.image_data, it.image_mime or "image/jpeg"))
        label = it.name or it.category
        if it.color:
            label = f"{label} ({it.color})"
        labels.append(label)

    if not refs:
        raise HTTPException(status_code=400, detail="Keine gültigen Teile gefunden.")

    try:
        result = gemini_service.generate_outfit_tryon(refs, labels, occasion)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Anprobe-Bild fehlgeschlagen: {exc}")

    if not result:
        raise HTTPException(status_code=502, detail="Es konnte kein Bild erzeugt werden.")

    data, mime = result
    return {
        "image_base64": base64.b64encode(data).decode(),
        "image_mime": mime,
    }


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


# ---------- Analyse ----------
def _wardrobe_with_dates(db: Session, user_id: int) -> list[dict]:
    """Garderobe inkl. created_at fuer die Statistik."""
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
            "created_at": it.created_at,
        }
        for it in items
    ]


@app.get("/api/analytics/stats")
def analytics_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Rechnerische Statistiken – laedt sofort, ohne KI."""
    return compute_stats(_wardrobe_with_dates(db, user.id))


@app.post("/api/analytics/insights")
def analytics_insights(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """KI-Einschaetzung der Garderobe (dauert einige Sekunden)."""
    wardrobe = _wardrobe_with_dates(db, user.id)
    if not wardrobe:
        raise HTTPException(status_code=400, detail="Garderobe ist noch leer.")

    stats = compute_stats(wardrobe)
    try:
        return gemini_service.analyze_wardrobe(
            wardrobe=wardrobe,
            profile=_profile_dict(user),
            stats=stats,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Analyse fehlgeschlagen: {exc}")


# ---------- Chat ----------
@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    history: str = Form(default="[]"),
    image: UploadFile = File(default=None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Freier Chat mit dem Style-Assistenten."""
    if not message.strip() and not image:
        raise HTTPException(status_code=400, detail="Nachricht oder Bild erforderlich.")
    
    # Parse history
    try:
        history_list = json.loads(history) if history else []
    except Exception:  # noqa: BLE001
        history_list = []
    
    # Read image if provided
    image_bytes = None
    image_mime = "image/jpeg"
    if image:
        image_bytes = await image.read()
        image_mime = image.content_type or "image/jpeg"
    
    wardrobe = _full_wardrobe(db, user.id)
    
    try:
        result = gemini_service.chat_with_stylist(
            message=message.strip(),
            wardrobe=wardrobe,
            profile=_profile_dict(user),
            history=history_list,
            image_bytes=image_bytes,
            image_mime=image_mime,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Chat fehlgeschlagen: {exc}")
    
    return result
