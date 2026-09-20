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
    # Optionales KI-generiertes Produktfoto (base64), falls im Wizard erzeugt
    ai_image_base64: str = ""
    ai_image_mime: str = "image/png"


class ItemOut(ItemMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    thumbnail_url: str = ""
    image_urls: list[str] = []
    thumbnail_urls: list[str] = []
    # KI-Produktfoto
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    details: dict = {}
    favorite: bool = False
    created_at: datetime


class RecommendRequest(BaseModel):
    item_id: int
    occasion: str = ""
    note: str = ""
    weather: str = ""


class RecommendedPiece(BaseModel):
    item_id: int
    name: str
    category: str
    image_url: str = ""
    thumbnail_url: str = ""
    # KI-inszeniertes Produktfoto, falls vorhanden
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False


class RecommendedWatch(BaseModel):
    """Zum Outfit passende Uhr aus der Sammlung."""

    watch_id: int
    name: str
    brand: str = ""
    image_url: str = ""
    thumbnail_url: str = ""
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    reason: str = ""


class RecommendedFragrance(BaseModel):
    """Zum Outfit passender Duft aus der Sammlung."""

    fragrance_id: int
    name: str
    brand: str = ""
    image_url: str = ""
    thumbnail_url: str = ""
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    reason: str = ""


class RecommendResponse(BaseModel):
    pieces: list[RecommendedPiece]
    suitability: str = "geht"
    suitability_reason: str = ""
    explanation: str
    watch: RecommendedWatch | None = None
    fragrance: RecommendedFragrance | None = None
    accessory: "RecommendedAccessory | None" = None


# ---------- Shopping ----------
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ShoppingSuggestRequest(BaseModel):
    """Vorschlaege fuer sinnvolle Ergaenzungen der Garderobe."""

    direction: str = ""              # Freitext: Richtung/Anlass
    history: list[ChatMessage] = []  # bisheriger Chat-Verlauf
    # "" = alle Sammlungen, sonst "Kleidung" | "Uhr" | "Duft"
    domain: str = ""


class ShoppingSuggestion(BaseModel):
    title: str
    category: str
    reason: str
    color: str = ""
    material: str = ""
    combines_with: list[str] = []
    # "Kleidung" | "Uhr" | "Duft" – welche Sammlung ergaenzt werden soll
    domain: str = "Kleidung"


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


# ---------- Uhren ----------
class WatchMetadata(BaseModel):
    """Von der KI extrahierte / vom User bestaetigte Uhren-Daten."""

    name: str = ""
    brand: str = ""
    model: str = ""
    reference: str = ""
    year: int | None = None

    movement: str = ""
    case_material: str = ""
    case_diameter: float | None = None
    case_thickness: float | None = None
    lug_width: float | None = None
    crystal: str = ""
    water_resistance: int | None = None
    complications: list[str] = []

    dial_color: str = ""
    band_type: str = ""
    band_material: str = ""
    band_color: str = ""
    clasp: str = ""

    style: str = ""
    occasions: list[str] = []

    condition: str = ""
    box_papers: str = ""
    purchase_date: datetime | None = None
    purchase_price: float | None = None
    current_value: float | None = None
    currency: str = "EUR"
    serviced_at: datetime | None = None
    service_interval_years: int | None = None
    warranty_until: datetime | None = None

    description: str = ""
    notes: str = ""


class WatchCreate(WatchMetadata):
    image_base64: str
    image_mime: str = "image/jpeg"
    extra_images: list[ImageUpload] = []
    ai_image_base64: str = ""
    ai_image_mime: str = "image/png"


class WatchOut(WatchMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    thumbnail_url: str = ""
    image_urls: list[str] = []
    thumbnail_urls: list[str] = []
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    favorite: bool = False
    needs_review: bool = False
    # Rechnerische Zusatzinfos, vom Backend gefuellt
    service_due: bool = False
    service_due_date: datetime | None = None
    wrist_advice: str = ""
    created_at: datetime


class WatchAnalyzeResponse(BaseModel):
    """Ergebnis der Uhren-Bildanalyse (noch nicht gespeichert)."""

    metadata: WatchMetadata
    images: list[ImageUpload] = []
    confidence: str = ""
    identified: bool = False


# ---------- Duefte ----------
class FragranceMetadata(BaseModel):
    """Von der KI extrahierte / vom User bestaetigte Duft-Daten."""

    name: str = ""
    brand: str = ""
    line: str = ""
    concentration: str = ""
    year: int | None = None
    perfumer: str = ""
    audience: str = ""

    family: str = ""
    secondary_family: str = ""
    top_notes: list[str] = []
    heart_notes: list[str] = []
    base_notes: list[str] = []
    sillage: str = ""
    longevity: str = ""

    occasions: list[str] = []
    seasons: list[str] = []
    time_of_day: str = ""

    bottle_size: int | None = None
    fill_level: int | None = None
    quantity: int = 1
    batch_code: str = ""
    purchase_date: datetime | None = None
    purchase_price: float | None = None
    currency: str = "EUR"
    opened_at: datetime | None = None

    description: str = ""
    notes: str = ""


class FragranceCreate(FragranceMetadata):
    image_base64: str
    image_mime: str = "image/jpeg"
    extra_images: list[ImageUpload] = []
    ai_image_base64: str = ""
    ai_image_mime: str = "image/png"


class FragranceOut(FragranceMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    thumbnail_url: str = ""
    image_urls: list[str] = []
    thumbnail_urls: list[str] = []
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    favorite: bool = False
    needs_review: bool = False
    # Rechnerische Zusatzinfos
    expires_at: datetime | None = None
    expired: bool = False
    low_stock: bool = False
    created_at: datetime


class FragranceAnalyzeResponse(BaseModel):
    """Ergebnis der Duft-Bildanalyse (noch nicht gespeichert)."""

    metadata: FragranceMetadata
    images: list[ImageUpload] = []
    confidence: str = ""
    identified: bool = False


# ---------- Accessoires ----------
class AccessoryMetadata(BaseModel):
    """Von der KI extrahierte / vom User bestätigte Accessoire-Daten."""

    name: str = ""
    brand: str = ""
    type: str = ""
    model: str = ""
    reference: str = ""
    year: int | None = None

    material: str = ""
    secondary_material: str = ""
    color: str = ""
    stone: str = ""
    details: dict = {}

    style: str = ""
    occasions: list[str] = []

    condition: str = ""
    authenticity_card: int = 0
    purchase_date: datetime | None = None
    purchase_price: float | None = None
    current_value: float | None = None
    currency: str = "EUR"
    warranty_until: datetime | None = None

    description: str = ""
    notes: str = ""


class AccessoryCreate(AccessoryMetadata):
    image_base64: str
    image_mime: str = "image/jpeg"
    extra_images: list[ImageUpload] = []
    ai_image_base64: str = ""
    ai_image_mime: str = "image/png"


class AccessoryOut(AccessoryMetadata):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str = ""
    thumbnail_url: str = ""
    image_urls: list[str] = []
    thumbnail_urls: list[str] = []
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    favorite: bool = False
    needs_review: bool = False
    created_at: datetime


class AccessoryAnalyzeResponse(BaseModel):
    """Ergebnis der Accessoire-Bildanalyse (noch nicht gespeichert)."""

    metadata: AccessoryMetadata
    images: list[ImageUpload] = []
    confidence: str = ""
    identified: bool = False


class RecommendedAccessory(BaseModel):
    """Zum Outfit passendes Accessoire aus der Sammlung."""

    accessory_id: int
    name: str
    type: str = ""
    brand: str = ""
    image_url: str = ""
    thumbnail_url: str = ""
    ai_image_url: str = ""
    ai_thumbnail_url: str = ""
    has_ai_image: bool = False
    reason: str = ""
