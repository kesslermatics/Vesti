"""Kapselt die gesamte Gemini-Kommunikation (Bildanalyse + Outfit-Empfehlung)."""

import json
import mimetypes
import time
from typing import Any

from google import genai
from google.genai import types

from .categories import CATEGORIES, CATEGORY_DETAILS, MATERIALS, OCCASIONS, SEASONS, STYLES
from .config import get_settings

settings = get_settings()

_client: genai.Client | None = None

# Retry-Konfiguration fuer transiente Gemini-Fehler (503 Überlastung, 429 Rate-Limit)
_RETRYABLE_CODES = {429, 500, 503}
_MAX_RETRIES = 4
_BASE_DELAY = 2.0   # Sekunden, wird bei jedem Versuch verdoppelt


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY ist nicht gesetzt.")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _call_with_retry(model: str, contents: list) -> Any:
    """Ruft generate_content mit exponentiellem Backoff auf."""
    client = _get_client()
    last_exc: Exception | None = None
    delay = _BASE_DELAY

    for attempt in range(_MAX_RETRIES):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            # Pruefen ob der Fehler retryable ist
            is_retryable = (
                "503" in msg
                or "429" in msg
                or "500" in msg
                or "unavailable" in msg
                or "overloaded" in msg
                or "high demand" in msg
                or "resource_exhausted" in msg
                or "internal" in msg
            )
            if not is_retryable or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= 2  # exponentiell: 2s → 4s → 8s → ...

    raise last_exc  # type: ignore[misc]


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


def quick_analyze_image(image_bytes: bytes, filename: str, hint: str = "") -> dict[str, Any]:
    """Schritt 1: Schnelle Erkennung von Kategorie und Farbe."""
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}"
        if hint and hint.strip()
        else ""
    )

    prompt = f"""Du bist ein Mode-Experte. Analysiere dieses Bild und erkenne NUR die Kategorie und die dominante Farbe.{hint_block}

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "category": "einer aus: {', '.join(CATEGORIES[:20])}...",
  "color": "dominante Farbe(n) auf Deutsch"
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ],
    )

    data = _extract_json(response.text or "{}")
    return {
        "category": str(data.get("category", "")),
        "color": str(data.get("color", "")),
    }


def detail_analyze_image(
    image_bytes: bytes, filename: str, category: str, hint: str = ""
) -> dict[str, Any]:
    """Schritt 2: Detaillierte Analyse aller Metadaten basierend auf der Kategorie."""
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}"
        if hint and hint.strip()
        else ""
    )

    # Kategorienspezifische Detail-Felder holen
    detail_fields = CATEGORY_DETAILS.get(category, [])
    detail_prompt = ""
    if detail_fields:
        detail_prompt = f"""  "details": {{
    {', '.join(f'"{field}": "Wert"' for field in detail_fields)}
  }},"""

    prompt = f"""Du bist ein Mode-Experte. Analysiere dieses {category} im Detail.{hint_block}

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "name": "kurzer sprechender Name, z.B. 'Blaues Leinenhemd'",
  "material": "einer aus: {', '.join(MATERIALS[:15])}...",
  "pattern": "Muster/Textur, z.B. 'uni', 'gestreift', 'kariert'",
  "style": "einer aus: {', '.join(STYLES)}",
  "occasion": "einer aus: {', '.join(OCCASIONS[:10])}...",
  "season": "einer aus: {', '.join(SEASONS)}",
  "description": "ein kurzer deutscher Satz zum Stueck",
{detail_prompt}
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ],
    )

    data = _extract_json(response.text or "{}")
    details = data.pop("details", {}) if "details" in data else {}

    return {
        "name": str(data.get("name", "")),
        "material": str(data.get("material", "")),
        "pattern": str(data.get("pattern", "")),
        "style": str(data.get("style", "")),
        "occasion": str(data.get("occasion", "")),
        "season": str(data.get("season", "")),
        "description": str(data.get("description", "")),
        "details": details if isinstance(details, dict) else {},
    }


def analyze_image(image_bytes: bytes, filename: str, hint: str = "") -> dict[str, Any]:
    """Legacy: einstufige Analyse (fuer Abwaertskompatibilitaet, wird nicht mehr verwendet)."""
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"

    hint_block = (
        f"\nZusatzinfo vom Nutzer (Marke, Größe, Material o.ä.): {hint.strip()}"
        if hint and hint.strip()
        else ""
    )

    prompt = f"""Du bist ein Mode-Experte und analysierst ein Bild eines einzelnen Kleidungsstuecks.
Extrahiere die Metadaten und antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein Markdown, kein Text drumherum).{hint_block}

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

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ],
    )

    data = _extract_json(response.text or "{}")
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

    response = _call_with_retry(
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


def _profile_block(profile: dict[str, Any]) -> str:
    """Formatiert die Profil-Daten des Nutzers fuer den Prompt."""
    if not profile:
        return "(keine Profildaten hinterlegt)"

    lines = []
    m = profile.get("measurements") or {}
    s = profile.get("sizes") or {}

    if m:
        maße = ", ".join(f"{k}: {v} cm" for k, v in m.items() if v)
        if maße:
            lines.append(f"Körpermaße: {maße}")
    if s:
        größen = ", ".join(f"{k.replace('size_', '')}: {v}" for k, v in s.items() if v)
        if größen:
            lines.append(f"Konfektionsgrößen: {größen}")
    if profile.get("body_type"):
        lines.append(f"Körpertyp: {profile['body_type']}")
    if profile.get("fit_preference"):
        lines.append(f"Bevorzugte Passform: {profile['fit_preference']}")
    if profile.get("style_notes"):
        lines.append(f"Stil-Notizen: {profile['style_notes']}")

    return "\n".join(lines) if lines else "(keine Profildaten hinterlegt)"


def _wardrobe_block(wardrobe: list[dict[str, Any]]) -> str:
    """Formatiert die komplette Garderobe inkl. Details und Stueckzahl."""
    if not wardrobe:
        return "(Garderobe ist leer)"

    # Nach Kategorie gruppieren, damit die KI Mengenverhaeltnisse erkennt
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for it in wardrobe:
        by_cat.setdefault(it["category"], []).append(it)

    lines = []
    for cat, items in by_cat.items():
        total = sum(int(i.get("quantity") or 1) for i in items)
        lines.append(f"\n{cat} ({total} Stück):")
        for it in items:
            qty = int(it.get("quantity") or 1)
            qty_txt = f" ×{qty}" if qty > 1 else ""
            parts = [
                it.get("name") or cat,
                it.get("color", ""),
                it.get("material", ""),
                it.get("pattern", ""),
                it.get("style", ""),
            ]
            desc = ", ".join(p for p in parts if p)
            if it.get("brand"):
                desc += f", Marke: {it['brand']}"
            details = it.get("details") or {}
            if details:
                det = ", ".join(f"{k}: {v}" for k, v in details.items() if v)
                if det:
                    desc += f" [{det}]"
            lines.append(f"  - ID {it['id']}{qty_txt}: {desc}")

    return "\n".join(lines)


def shopping_suggestions(
    wardrobe: list[dict[str, Any]],
    profile: dict[str, Any],
    direction: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Schlaegt sinnvolle Ergaenzungen zur Garderobe vor."""
    history_block = ""
    if history:
        turns = []
        for msg in history[-8:]:  # nur die letzten Runden mitschicken
            role = "Nutzer" if msg.get("role") == "user" else "Du"
            turns.append(f"{role}: {msg.get('content', '')}")
        history_block = "\n\nBisheriger Verlauf:\n" + "\n".join(turns)

    prompt = f"""Du bist ein erfahrener Personal Shopper und Stilberater.

Profil des Nutzers:
{_profile_block(profile)}

Aktuelle Garderobe (mit Stückzahlen):
{_wardrobe_block(wardrobe)}

Wunsch / Richtung des Nutzers: {direction or 'keine besondere Vorgabe'}{history_block}

Analysiere die Garderobe: Was fehlt? Wo gibt es Lücken? Wovon hat der Nutzer schon zu viel?
Achte auf die Stückzahlen – wenn jemand acht schwarze T-Shirts hat, braucht er kein neuntes.
Schlage genau 5 konkrete Kleidungsstücke vor, die die Garderobe sinnvoll ergänzen.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "intro": "1-2 Sätze auf Deutsch: was dir an der Garderobe auffällt",
  "suggestions": [
    {{
      "title": "konkreter Vorschlag, z.B. 'Beige Chino, regular fit'",
      "category": "einer aus: {', '.join(CATEGORIES[:30])}...",
      "color": "empfohlene Farbe",
      "material": "empfohlenes Material",
      "reason": "2-3 Sätze auf Deutsch: warum genau das fehlt und was es ermöglicht",
      "combines_with": ["Namen vorhandener Teile aus der Garderobe, die dazu passen"]
    }}
  ]
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[prompt])
    data = _extract_json(response.text or "{}")

    raw = data.get("suggestions", [])
    suggestions = []
    for s in raw[:5]:
        if not isinstance(s, dict):
            continue
        combines = s.get("combines_with", [])
        suggestions.append(
            {
                "title": str(s.get("title", "")),
                "category": str(s.get("category", "")),
                "color": str(s.get("color", "")),
                "material": str(s.get("material", "")),
                "reason": str(s.get("reason", "")),
                "combines_with": [str(c) for c in combines] if isinstance(combines, list) else [],
            }
        )

    return {"intro": str(data.get("intro", "")), "suggestions": suggestions}


def fit_check(
    product_text: str,
    wardrobe: list[dict[str, Any]],
    profile: dict[str, Any],
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict[str, Any]:
    """Prueft ein Produkt aus einem Online-Shop gegen Garderobe und Profil."""
    prompt = f"""Du bist ein kritischer Personal Shopper. Der Nutzer überlegt, dieses Produkt zu kaufen.

Produktbeschreibung aus dem Shop:
\"\"\"
{product_text.strip()}
\"\"\"

Profil des Nutzers:
{_profile_block(profile)}

Aktuelle Garderobe (mit Stückzahlen):
{_wardrobe_block(wardrobe)}

Bewerte, wie gut dieses Produkt zur bestehenden Garderobe und zum Nutzer passt.
Berücksichtige dabei:
- Passt es farblich und stilistisch zu vorhandenen Teilen?
- Hat der Nutzer schon etwas Ähnliches (Stückzahlen beachten)?
- Material und Qualität: ist das sinnvoll für seine Garderobe?
- Größe: passt die angegebene Größe zu seinen Körpermaßen? Fällt das Teil groß oder klein aus?
- Schließt es eine echte Lücke oder ist es ein Duplikat?

Sei ehrlich und kritisch. Wenn es nicht passt, sag das klar.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "score": Zahl von 0 bis 100 (wie gut es passt),
  "verdict": "kurzes Urteil in einem Satz, z.B. 'Sinnvolle Ergänzung' oder 'Hast du schon ähnlich'",
  "explanation": "ausführliche deutsche Begründung (4-6 Sätze), gehe konkret auf Material, Farbe, Stil und Kombinierbarkeit ein",
  "pros": ["kurze Pluspunkte"],
  "cons": ["kurze Minuspunkte"],
  "size_advice": "Empfehlung zur Größe basierend auf den Körpermaßen, oder leer wenn keine Maße vorhanden",
  "combines_with": ["Namen vorhandener Teile, mit denen es gut kombinierbar ist"]
}}"""

    contents: list[Any] = []
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
    contents.append(prompt)

    response = _call_with_retry(model=settings.gemini_model, contents=contents)
    data = _extract_json(response.text or "{}")

    try:
        score = max(0, min(100, int(float(data.get("score", 0)))))
    except (ValueError, TypeError):
        score = 0

    def _str_list(key: str) -> list[str]:
        val = data.get(key, [])
        return [str(x) for x in val] if isinstance(val, list) else []

    return {
        "score": score,
        "verdict": str(data.get("verdict", "")),
        "explanation": str(data.get("explanation", "")),
        "pros": _str_list("pros"),
        "cons": _str_list("cons"),
        "size_advice": str(data.get("size_advice", "")),
        "combines_with": _str_list("combines_with"),
    }
