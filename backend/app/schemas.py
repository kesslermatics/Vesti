from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    created_at: datetime
    measurements: dict = {}
    sizes: dict = {}
    fit_preference: str = ""
    body_type: str = ""
    style_notes: str = ""


class ProfileUpdate(BaseModel):
    """Profil-Aktualisierung (alle Felder optional)."""

    name: str | None = None
    measurements: dict | None = None
    sizes: dict | None = None
    fit_preference: str | None = None
    body_type: str | None = None
    style_notes: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Items ----------
class ItemMetadata(BaseModel):
    """Von der KI extrahierte / vom User bestaetigte Metadaten."""

    name: str = ""
    category: str = "Sonstiges"
    color: str = ""
    material: str = ""
    pattern: str = ""
    style: str = ""
    occasion: str = ""
    season: str = ""
    description: str = ""
    brand: str = ""
    quantity: int = 1


class AnalyzeResponse(BaseModel):
    """Antwort der Bildanalyse: Vorschlag der Metadaten + Bild (base64) zur Rueckgabe beim Speichern."""

    metadata: ItemMetadata
    image_base64: str
    image_mime: str


class ImageUpload(BaseModel):
    """Ein einzelnes Bild als base64."""

    image_base64: str
    image_mime: str = "image/jpeg"


class ItemCreate(ItemMetadata):
    image_base64: str
    image_mime: str = "image/jpeg"
    details: dict = {}
    # Weitere Aufnahmen (Futter, Etikett, Details)
    extra_images: list[ImageUpload] = []


class ItemOut(ItemMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    image_urls: list[str] = []
    details: dict = {}
    favorite: bool = False
    created_at: datetime


class RecommendRequest(BaseModel):
    item_id: int
    occasion: str = ""
    note: str = ""


class RecommendedPiece(BaseModel):
    item_id: int
    name: str
    category: str
    image_url: str = ""


class RecommendResponse(BaseModel):
    pieces: list[RecommendedPiece]
    suitability: str = "geht"          # "perfekt" | "geht" | "notlösung" | "ungeeignet"
    suitability_reason: str = ""
    explanation: str


# ---------- Shopping ----------
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ShoppingSuggestRequest(BaseModel):
    """Vorschlaege fuer sinnvolle Ergaenzungen der Garderobe."""

    direction: str = ""              # Freitext: Richtung/Anlass
    history: list[ChatMessage] = []  # bisheriger Chat-Verlauf


class ShoppingSuggestion(BaseModel):
    title: str
    category: str
    reason: str
    color: str = ""
    material: str = ""
    combines_with: list[str] = []


class ShoppingSuggestResponse(BaseModel):
    suggestions: list[ShoppingSuggestion]
    intro: str = ""


class FitCheckRequest(BaseModel):
    """Produktbeschreibung von einem Shop pruefen."""

    product_text: str
    image_base64: str = ""
    image_mime: str = ""


class FitCheckResponse(BaseModel):
    score: int                      # 0-100 Prozent
    verdict: str                    # kurzes Urteil
    explanation: str                # ausfuehrliche Begruendung
    pros: list[str] = []
    cons: list[str] = []
    size_advice: str = ""
    combines_with: list[str] = []
