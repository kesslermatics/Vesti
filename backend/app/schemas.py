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


class AnalyzeResponse(BaseModel):
    """Antwort der Bildanalyse: Vorschlag der Metadaten + Bild (base64) zur Rueckgabe beim Speichern."""

    metadata: ItemMetadata
    image_base64: str
    image_mime: str


class ItemCreate(ItemMetadata):
    image_base64: str
    image_mime: str = "image/jpeg"
    details: dict = {}


class ItemOut(ItemMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    details: dict = {}
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
    explanation: str
