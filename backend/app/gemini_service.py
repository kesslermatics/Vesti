"""Kapselt die gesamte Gemini-Kommunikation (Bildanalyse + Outfit-Empfehlung)."""

import json
import mimetypes
from typing import Any

from google import genai
from google.genai import types

from .categories import CATEGORIES, MATERIALS, OCCASIONS, SEASONS, STYLES
from .config import get_settings

settings = get_settings()

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY ist nicht gesetzt.")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _extract_json(text: str) -> dict[str, Any]:
    """Robustes Parsen: entfernt evtl. Markdown-Fences und schneidet auf das JSON-Objekt zu."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if "```" in cleaned else cleaned
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def analyze_image(image_bytes: bytes, filename: str) -> dict[str, Any]:
    """Extrahiert Metadaten eines Kleidungsstuecks aus einem Bild."""
    client = _get_client()
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"

    prompt = f"""Du bist ein Mode-Experte und analysierst ein Bild eines einzelnen Kleidungsstuecks.
Extrahiere die Metadaten und antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein Markdown, kein Text drumherum).

Verwende exakt diese Felder:
{{
  "name": "kurzer sprechender Name, z.B. 'Blaues Leinenhemd'",
  "category": "einer aus: {', '.join(CATEGORIES)}",
  "color": "dominante Farbe(n) auf Deutsch",
  "material": "einer aus: {', '.join(MATERIALS)}",
  "pattern": "Muster/Textur, z.B. 'uni', 'gestreift', 'kariert', 'gebluemt'",
  "style": "einer aus: {', '.join(STYLES)}",
  "occasion": "einer aus: {', '.join(OCCASIONS)}",
  "season": "einer aus: {', '.join(SEASONS)}",
  "description": "ein kurzer deutscher Satz zum Stueck"
}}

Waehle immer den am besten passenden erlaubten Wert. Antworte nur mit dem JSON."""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ],
    )

    data = _extract_json(response.text or "{}")

    # Nur bekannte Felder durchreichen
    allowed = {"name", "category", "color", "material", "pattern",
               "style", "occasion", "season", "description"}
    return {k: str(data.get(k, "")) for k in allowed}


def recommend_outfit(
    base_item: dict[str, Any],
    wardrobe: list[dict[str, Any]],
    occasion: str,
    note: str,
) -> dict[str, Any]:
    """Empfiehlt passende Teile aus der Garderobe zu einem Basis-Teil."""
    client = _get_client()

    wardrobe_lines = []
    for it in wardrobe:
        wardrobe_lines.append(
            f"- ID {it['id']}: {it.get('name') or it['category']} "
            f"({it['category']}, Farbe: {it.get('color', '?')}, "
            f"Stil: {it.get('style', '?')}, Material: {it.get('material', '?')})"
        )
    wardrobe_text = "\n".join(wardrobe_lines) if wardrobe_lines else "(keine weiteren Teile)"

    base_text = (
        f"ID {base_item['id']}: {base_item.get('name') or base_item['category']} "
        f"({base_item['category']}, Farbe: {base_item.get('color', '?')}, "
        f"Stil: {base_item.get('style', '?')})"
    )

    prompt = f"""Du bist ein professioneller Stylist. Der Nutzer moechte ein Outfit rund um dieses Basis-Kleidungsstueck:
{base_text}

Anlass: {occasion or 'nicht angegeben'}
Zusatzwunsch des Nutzers: {note or 'keiner'}

Verfuegbare Kleidungsstuecke in der Garderobe (nur diese IDs duerfen verwendet werden):
{wardrobe_text}

Stelle ein stimmiges Outfit zusammen. Waehle ausschliesslich passende IDs aus der Garderobe
(das Basis-Teil ID {base_item['id']} ist automatisch Teil des Outfits, muss nicht erneut genannt werden).
Achte auf Farbharmonie, Stil und Anlass.

Antworte AUSSCHLIESSLICH mit folgendem JSON (kein Markdown):
{{
  "item_ids": [Liste der empfohlenen IDs als Zahlen],
  "explanation": "eine ansprechende deutsche Beschreibung (2-4 Saetze), warum das Outfit zusammenpasst und wie es aesthetisch wirkt"
}}"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[prompt],
    )

    data = _extract_json(response.text or "{}")
    raw_ids = data.get("item_ids", [])
    item_ids: list[int] = []
    for x in raw_ids:
        try:
            item_ids.append(int(x))
        except (ValueError, TypeError):
            continue
    return {
        "item_ids": item_ids,
        "explanation": str(data.get("explanation", "")),
    }
