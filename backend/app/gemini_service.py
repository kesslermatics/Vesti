"""Kapselt die gesamte Gemini-Kommunikation (Bildanalyse + Outfit-Empfehlung)."""

import base64
import json
import mimetypes
import time
import urllib.request
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


class ImageGenerationUnavailable(Exception):
    """Bildgenerierung ist am Server-Standort (Region) nicht verfügbar."""


def _generate_image_http(
    image_parts: list[tuple[bytes, str]],
    prompt: str,
) -> tuple[bytes, str] | None:
    """Bildgenerierung per direktem HTTP-Call statt SDK.

    Das SDK fuehrt serverseitige Regionspruefungen durch die im EWR scheitern.
    Der direkte v1beta-Endpunkt umgeht diese Pruefung.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY ist nicht gesetzt.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_image_model}:generateContent?key={settings.gemini_api_key}"
    )

    # Parts: erst Bilder als inlineData, dann Prompt-Text
    parts_payload: list[dict] = []
    for data, mime in image_parts:
        parts_payload.append({
            "inlineData": {
                "mimeType": mime or "image/jpeg",
                "data": base64.b64encode(data).decode("utf-8"),
            }
        })
    parts_payload.append({"text": prompt})

    body = json.dumps({
        "contents": [{"parts": parts_payload}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }).encode("utf-8")

    last_exc: Exception | None = None
    delay = _BASE_DELAY

    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            for candidate in result.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    inline = part.get("inlineData")
                    if inline and inline.get("data"):
                        mime_out = inline.get("mimeType") or "image/png"
                        return base64.b64decode(inline["data"]), mime_out
            return None

        except urllib.error.HTTPError as exc:
            last_exc = exc
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass
            is_retryable = exc.code in (429, 500, 503)
            if not is_retryable or attempt == _MAX_RETRIES - 1:
                raise RuntimeError(
                    f"Gemini Bildgenerierung HTTP {exc.code}: {body_text[:300]}"
                ) from exc
            time.sleep(delay)
            delay *= 2

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            msg = str(exc).lower()
            is_retryable = (
                "503" in msg or "429" in msg or "500" in msg
                or "unavailable" in msg or "overloaded" in msg
                or "timeout" in msg
            )
            if not is_retryable or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= 2

    if last_exc:
        raise last_exc
    return None


def _is_location_error(exc: Exception) -> bool:
    """Erkennt geografische Beschränkungen der Bildgenerierung."""
    msg = str(exc).lower()
    return (
        "not available in your country" in msg
        or "user location is not supported" in msg
        or "location is not supported" in msg
        or ("failed_precondition" in msg and "location" in msg)
    )


def _extract_response_parts(response: Any) -> list[Any]:
    """Extrahiert Parts robust aus einer Gemini-Antwort (SDK-versionsunabhaengig)."""
    # Neuere SDKs: response.parts direkt
    if getattr(response, "parts", None):
        return list(response.parts)
    # Aeltere SDKs: response.candidates[0].content.parts
    candidates = getattr(response, "candidates", None)
    if candidates:
        cand = candidates[0]
        content = getattr(cand, "content", None)
        if content is not None:
            return list(getattr(content, "parts", None) or [])
    return []


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


def _image_parts(
    images: list[tuple[bytes, str]] | bytes,
    filename: str = "upload.jpg",
) -> list[Any]:
    """Normalisiert Bild-Input zu einer Liste von Gemini-Parts."""
    if isinstance(images, (bytes, bytearray)):
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        images = [(bytes(images), mime)]

    parts = []
    for data, mime in images:
        if not data:
            continue
        parts.append(types.Part.from_bytes(data=data, mime_type=mime or "image/jpeg"))
    return parts


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


def quick_analyze_image(
    images: list[tuple[bytes, str]] | bytes,
    filename: str = "upload.jpg",
    hint: str = "",
) -> dict[str, Any]:
    """Schritt 1: Schnelle Erkennung von Kategorie und Farbe.

    `images` ist eine Liste von (bytes, mime). Einzelne bytes werden aus
    Rueckwaertskompatibilitaet weiterhin akzeptiert.
    """
    parts = _image_parts(images, filename)

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}"
        if hint and hint.strip()
        else ""
    )
    multi_block = (
        f"\nEs sind {len(parts)} Aufnahmen desselben Kleidungsstücks (z.B. Vorderseite, "
        "Futter, Etikett). Nutze alle, um sicher zu bestimmen."
        if len(parts) > 1
        else ""
    )

    prompt = f"""Du bist ein Mode-Experte. Analysiere die Aufnahme(n) und erkenne NUR die Kategorie und die dominante Farbe.{multi_block}{hint_block}

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "category": "einer aus: {', '.join(CATEGORIES[:20])}...",
  "color": "dominante Farbe(n) auf Deutsch"
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[*parts, prompt],
    )

    data = _extract_json(response.text or "{}")
    return {
        "category": str(data.get("category", "")),
        "color": str(data.get("color", "")),
    }


def detail_analyze_image(
    images: list[tuple[bytes, str]] | bytes,
    filename: str = "upload.jpg",
    category: str = "",
    hint: str = "",
    known_brands: list[str] | None = None,
) -> dict[str, Any]:
    """Schritt 2: Detaillierte Analyse aller Metadaten basierend auf der Kategorie."""
    parts = _image_parts(images, filename)

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}"
        if hint and hint.strip()
        else ""
    )
    multi_block = (
        f"\nDir liegen {len(parts)} Aufnahmen desselben Teils vor (z.B. Außenseite, Futter, "
        "Pflege-Etikett, Detail). Wenn auf einem Etikett Material- oder Pflegeangaben zu lesen "
        "sind, nutze diese bevorzugt gegenüber einer optischen Schätzung."
        if len(parts) > 1
        else ""
    )

    # Kategorienspezifische Detail-Felder holen
    detail_fields = CATEGORY_DETAILS.get(category, [])
    detail_prompt = ""
    if detail_fields:
        detail_prompt = f"""  "details": {{
    {', '.join(f'"{field}": "Wert"' for field in detail_fields)}
  }},"""

    # Bekannte Marken als Kontext mitgeben
    brands_block = ""
    if known_brands:
        brands_list = ", ".join(f'"{b}"' for b in known_brands[:30])
        brands_block = f"""
Bereits bekannte Marken des Nutzers: [{brands_list}]
Wenn die Marke auf dem Bild oder im Hinweis eindeutig erkennbar ist (Logo, Etikett, Aufdruck, oder explizit im Hinweis genannt), trage sie ein.
Bevorzuge dabei die exakte Schreibweise einer bereits bekannten Marke.
Wenn die Marke nicht eindeutig erkennbar ist, lasse das Feld leer."""

    prompt = f"""Du bist ein Mode-Experte. Analysiere dieses {category} im Detail.{multi_block}{hint_block}{brands_block}

WICHTIG: Wenn ein Pflege-Etikett sichtbar ist, lies ALLE Informationen darauf:
- Exakte Material-Zusammensetzung (z.B. "100% Baumwolle" oder "80% Wolle, 20% Polyester")
- Waschtemperatur (z.B. "30°C", "40°C")
- Pflegesymbole und Anweisungen (nicht bügeln, nicht bleichen, Handwäsche, etc.)
- Bei Schuhen: Ledertyp, Obermaterial, Futtermaterial, Sohlenmaterial
- Herstellungsland, wenn angegeben
- Größenangaben auf dem Etikett

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "name": "kurzer sprechender Name, z.B. 'Blaues Leinenhemd'",
  "brand": "Markenname wenn eindeutig erkennbar, sonst leer",
  "material": "exakte Material-Zusammensetzung vom Etikett oder geschätzt, z.B. '100% Baumwolle' oder 'Leder'",
  "pattern": "Muster/Textur, z.B. 'uni', 'gestreift', 'kariert'",
  "style": "einer aus: {', '.join(STYLES)}",
  "occasion": "einer aus: {', '.join(OCCASIONS[:10])}...",
  "season": "einer aus: {', '.join(SEASONS)}",
  "description": "ein kurzer deutscher Satz zum Stueck",
{detail_prompt}
  "care_instructions": {{
    "wash_temp": "Waschtemperatur z.B. '30°C', '40°C', 'Handwäsche', 'nicht waschen', oder leer",
    "dry": "Trockner-Anweisung z.B. 'Trockner niedrig', 'nicht Trockner', 'lufttrocknen', oder leer",
    "iron": "Bügel-Anweisung z.B. 'niedrige Temperatur', 'mittlere Temperatur', 'nicht bügeln', oder leer",
    "bleach": "'nicht bleichen' oder leer",
    "dry_clean": "'chemische Reinigung' oder 'professionelle Reinigung' oder leer",
    "special": "besondere Hinweise wie 'separat waschen', 'auf links waschen', etc. oder leer"
  }},
  "material_details": {{
    "composition": "exakte Zusammensetzung vom Etikett z.B. '80% Wolle, 20% Polyamid' oder leer",
    "leather_type": "bei Leder/Schuhen: Typ z.B. 'Glattleder', 'Wildleder', 'Nubukleder' oder leer",
    "lining": "Futtermaterial z.B. '100% Polyester', 'Lederfutter' oder leer",
    "sole": "bei Schuhen: Sohlenmaterial z.B. 'Gummisohle', 'Ledersohle' oder leer",
    "origin": "Herstellungsland z.B. 'Made in Italy', 'Made in China' oder leer"
  }}
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[*parts, prompt],
    )

    data = _extract_json(response.text or "{}")
    details = data.pop("details", {}) if "details" in data else {}
    care_instructions = data.pop("care_instructions", {}) if "care_instructions" in data else {}
    material_details = data.pop("material_details", {}) if "material_details" in data else {}
    
    # Merge care and material details into details dict
    if care_instructions and any(care_instructions.values()):
        details["care_instructions"] = care_instructions
    if material_details and any(material_details.values()):
        details["material_details"] = material_details

    return {
        "name": str(data.get("name", "")),
        "brand": str(data.get("brand", "")),
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


def generate_product_shot(
    images: list[tuple[bytes, str]] | bytes,
    category: str = "",
    color: str = "",
    material: str = "",
    filename: str = "upload.jpg",
) -> tuple[bytes, str] | None:
    """Erzeugt aus den (oft schlampigen) Nutzerfotos ein sauberes, einheitliches
    Studio-Produktfoto. Das Kleidungsstück wird NICHT verändert – nur die Szene,
    Beleuchtung und der Hintergrund werden professionell gestaltet.

    Gibt (bytes, mime) des generierten Bildes zurück oder None bei Fehler.
    """
    # Rohe (bytes, mime) Liste normalisieren – _image_parts() nicht benutzen da
    # wir hier direkt HTTP aufrufen und keine SDK-Part-Objekte brauchen
    if isinstance(images, (bytes, bytearray)):
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        raw_images: list[tuple[bytes, str]] = [(bytes(images), mime)]
    else:
        raw_images = [(d, m or "image/jpeg") for d, m in images if d]

    if not raw_images:
        return None

    subject = category or "Kleidungsstück"
    color_hint = f" in {color}" if color else ""
    material_hint = f", Material: {material}" if material else ""

    # Prompt: beschreibende, narrative Anweisung. Kernregel: Original exakt bewahren.
    prompt = (
        f"Erstelle ein professionelles, sauberes E-Commerce-Produktfoto dieses "
        f"Kleidungsstücks ({subject}{color_hint}{material_hint}).\n\n"
        "ABSOLUT WICHTIG – nichts verfälschen:\n"
        "- Zeige EXAKT dasselbe Kleidungsstück wie auf den Referenzfotos: identische "
        "Farbe, identisches Muster, identischer Schnitt, gleiche Knöpfe, Nähte, "
        "Prints, Logos, Waschung und alle Details.\n"
        "- Erfinde nichts dazu und lasse nichts weg. Verändere weder Farbton noch "
        "Proportionen. Es muss zweifelsfrei dasselbe Teil sein.\n"
        "- Behalte sichtbare Gebrauchsspuren nur dezent; keine neuen hinzufügen.\n\n"
        "Bildgestaltung (nur Szene, nicht das Teil):\n"
        "- Das Kleidungsstück sauber und faltenfrei präsentiert, mittig, komplett im Bild.\n"
        "- Ghost-Mannequin / freigestellt schwebend, ODER flach sauber ausgelegt "
        "(je nachdem was besser passt), KEIN Mensch, KEIN Gesicht.\n"
        "- Gleichmäßiger, neutraler, sehr heller Hintergrund (weiß bis ganz leicht warmweiß).\n"
        "- Weiches, professionelles Studiolicht, sanfte Schatten, keine harten Reflexe.\n"
        "- Zentrierte Komposition, quadratischer Bildausschnitt, hochwertig und minimalistisch.\n"
        "Gib nur das fertige Bild zurück."
    )

    return _generate_image_http(raw_images, prompt)


def generate_outfit_tryon(
    item_images: list[tuple[bytes, str]],
    piece_labels: list[str],
    occasion: str = "",
) -> tuple[bytes, str] | None:
    """Erzeugt ein realistisches Foto einer Person, die das komplette Outfit trägt.

    `item_images` sind die Referenzbilder der einzelnen Teile (je 1 pro Teil).
    Gibt (bytes, mime) zurück oder None.
    """
    raw_images = [(d, m or "image/jpeg") for d, m in item_images if d]
    if not raw_images:
        return None

    pieces_text = ", ".join(piece_labels) if piece_labels else "die gezeigten Teile"
    occ = f" für folgenden Anlass: {occasion}" if occasion else ""

    prompt = (
        "Erstelle ein realistisches, hochwertiges Ganzkörper-Modefoto einer Person, "
        f"die dieses komplette Outfit trägt{occ}.\n\n"
        f"Das Outfit besteht aus diesen Teilen (siehe Referenzbilder): {pieces_text}.\n\n"
        "WICHTIG – Teile originalgetreu übernehmen:\n"
        "- Jedes Kleidungsstück muss exakt so aussehen wie auf seinem Referenzbild: "
        "gleiche Farbe, gleiches Muster, gleicher Schnitt, gleiche Details.\n"
        "- Kombiniere alle gezeigten Teile zu einem stimmigen Look an einer Person.\n"
        "- Erfinde keine zusätzlichen auffälligen Kleidungsstücke dazu.\n\n"
        "Bildgestaltung:\n"
        "- Natürlich wirkende Person in entspannter, selbstbewusster Pose, Ganzkörper.\n"
        "- Neutrales, aufgeräumtes Studio- oder Lifestyle-Setting, weiches Licht.\n"
        "- Modern, clean, wie ein Lookbook-Foto. Hochformat.\n"
        "- Neutrales, freundliches Gesicht; keine bekannte reale Person darstellen.\n"
        "Gib nur das fertige Bild zurück."
    )

    return _generate_image_http(raw_images, prompt)


def recommend_outfit(
    base_item: dict[str, Any],
    wardrobe: list[dict[str, Any]],
    occasion: str,
    note: str,
) -> dict[str, Any]:
    """Empfiehlt passende Teile aus der Garderobe und urteilt ehrlich, ob das Outfit taugt."""
    wardrobe_lines = []
    for it in wardrobe:
        wardrobe_lines.append(
            f"- {it.get('name') or it['category']} "
            f"({it['category']}, Farbe: {it.get('color', '?')}, "
            f"Stil: {it.get('style', '?')}, Material: {it.get('material', '?')})"
        )
    wardrobe_text = "\n".join(wardrobe_lines) if wardrobe_lines else "(keine weiteren Teile)"

    base_text = (
        f"{base_item.get('name') or base_item['category']} "
        f"({base_item['category']}, Farbe: {base_item.get('color', '?')}, "
        f"Stil: {base_item.get('style', '?')})"
    )

    prompt = f"""Du bist ein ehrlicher, direkter Stilberater. Der Nutzer möchte ein Outfit für folgenden Anlass zusammenstellen.

Basis-Teil: {base_text}
Anlass: {occasion or 'nicht angegeben'}
Zusatzwunsch: {note or 'keiner'}

Verfügbare Teile in der Garderobe:
{wardrobe_text}

WICHTIG: 
- Sei ehrlich. Wenn das Basis-Teil oder die verfügbaren Kombinationen für den Anlass nicht wirklich geeignet sind, sag das klar.
- Berücksichtige ALLE Kategorien: Oberteile, Hosen, Schuhe, Jacken, Gürtel, Accessoires, etc.
- Ein komplettes Outfit sollte mindestens Oberteil + Unterteil enthalten, idealerweise auch Schuhe und ggf. Jacke/Accessoires.
- Nenne in deiner Erklärung die Teile NUR beim Namen (z.B. "schwarze Chino"), KEINE IDs oder Nummern!

Wähle die am besten passenden Teile aus der Garderobe (Basis-Teil nicht nochmal nennen).

ANTWORT-FORMAT:
Erstelle eine interne Liste der passenden Teil-Indizes (0-basiert, entsprechend der Reihenfolge oben).
In deiner Erklärung nenne die Teile NUR beim Namen.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "item_indices": [Liste der Indizes als Zahlen, 0-basiert],
  "suitability": "perfekt" | "geht" | "notlösung" | "ungeeignet",
  "suitability_reason": "ein ehrlicher Satz: warum das Outfit für den Anlass (nicht) passt",
  "explanation": "2-4 Sätze auf Deutsch: wie das Outfit wirkt, was gut passt, was fehlt oder stört, und welchen Tipp du für diesen Anlass noch hast. Nenne Teile nur beim Namen!"
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[prompt],
    )

    data = _extract_json(response.text or "{}")
    raw_indices = data.get("item_indices", [])
    
    # Convert indices to IDs
    item_ids: list[int] = []
    for idx in raw_indices:
        try:
            idx_int = int(idx)
            if 0 <= idx_int < len(wardrobe):
                item_ids.append(wardrobe[idx_int]["id"])
        except (ValueError, TypeError, IndexError):
            continue

    suitability = str(data.get("suitability", "geht"))
    if suitability not in {"perfekt", "geht", "notlösung", "ungeeignet"}:
        suitability = "geht"

    return {
        "item_ids": item_ids,
        "suitability": suitability,
        "suitability_reason": str(data.get("suitability_reason", "")),
        "explanation": str(data.get("explanation", "")),
    }


def generate_outfits(
    wardrobe: list[dict[str, Any]],
    occasion: str,
    note: str,
    count: int = 5,
) -> dict[str, Any]:
    """Generiert mehrere komplette Outfit-Vorschläge aus der Garderobe."""
    if not wardrobe:
        return {"outfits": [], "message": "Deine Garderobe ist noch leer."}
    
    wardrobe_lines = []
    for idx, it in enumerate(wardrobe):
        qty_txt = f" ×{it['quantity']}" if it.get('quantity', 1) > 1 else ""
        wardrobe_lines.append(
            f"{idx}. {it.get('name') or it['category']}{qty_txt} "
            f"({it['category']}, Farbe: {it.get('color', '?')}, "
            f"Stil: {it.get('style', '?')}, Material: {it.get('material', '?')})"
        )
    wardrobe_text = "\n".join(wardrobe_lines)

    prompt = f"""Du bist ein kreativer Stilberater. Der Nutzer möchte Outfit-Vorschläge aus seiner Garderobe.

Anlass: {occasion or 'Alltag / keine Vorgabe'}
Zusatzwunsch: {note or 'keiner'}

Verfügbare Teile in der Garderobe (nummeriert):
{wardrobe_text}

Erstelle {count} verschiedene, komplette Outfits aus dieser Garderobe.

WICHTIG:
- Jedes Outfit sollte KOMPLETT sein: Oberteil + Unterteil + idealerweise Schuhe, Jacke/Blazer wenn vorhanden, Gürtel/Accessoires wo passend
- Variiere die Kombinationen - keine Duplikate!
- Sei ehrlich: wenn die Garderobe nicht viel hergibt oder für den Anlass ungeeignet ist, sag das
- Berücksichtige ALLE Kategorien: T-Shirts, Hemden, Hosen, Jeans, Schuhe, Jacken, Gürtel, Accessoires, etc.
- Verwende die NUMMERN (0, 1, 2, ...) aus der Liste oben um Teile zu referenzieren
- In deiner Begründung nenne die Teile NUR beim Namen (z.B. "blaues Hemd"), KEINE Nummern oder IDs!

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "outfits": [
    {{
      "item_indices": [Liste von Indizes als Zahlen - mindestens 2, besser 3-5 Teile pro Outfit],
      "title": "kurzer Titel, z.B. 'Smart Casual Look' oder 'Relaxed Weekend'",
      "why": "1-2 Sätze: warum diese Kombination für den Anlass passt. Nenne Teile nur beim Namen!"
    }}
  ]
}}"""

    response = _call_with_retry(
        model=settings.gemini_model,
        contents=[prompt],
    )

    data = _extract_json(response.text or "{}")
    raw_outfits = data.get("outfits", [])
    
    outfits = []
    for outfit in raw_outfits[:count]:
        if not isinstance(outfit, dict):
            continue
        
        raw_indices = outfit.get("item_indices", [])
        item_ids: list[int] = []
        for idx in raw_indices:
            try:
                idx_int = int(idx)
                if 0 <= idx_int < len(wardrobe):
                    item_ids.append(wardrobe[idx_int]["id"])
            except (ValueError, TypeError, IndexError):
                continue
        
        if not item_ids:  # Skip empty outfits
            continue
            
        outfits.append({
            "item_ids": item_ids,
            "title": str(outfit.get("title", "Outfit")),
            "why": str(outfit.get("why", "")),
        })
    
    return {"outfits": outfits}



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


def analyze_wardrobe(
    wardrobe: list[dict[str, Any]],
    profile: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Erstellt eine ehrliche KI-Einschaetzung der gesamten Garderobe."""
    def _top(key: str, n: int = 5) -> str:
        entries = stats.get(key) or []
        return ", ".join(f"{e['label']} ({e['count']})" for e in entries[:n]) or "–"

    prompt = f"""Du bist ein erfahrener Stilberater und analysierst die Garderobe eines Nutzers.

Profil:
{_profile_block(profile)}

Garderobe im Detail:
{_wardrobe_block(wardrobe)}

Berechnete Kennzahlen:
- Einträge: {stats.get('total_entries')}, Teile insgesamt: {stats.get('total_pieces')}
- Verteilung nach Outfit-Rolle: {_top('slots')}
- Top-Kategorien: {_top('categories')}
- Farben: {_top('colors')} (Anteil neutraler Farben: {stats.get('neutral_share')}%)
- Materialien: {_top('materials')}
- Stile: {_top('styles')}
- Anlässe: {_top('occasions')}
- Saison-Abdeckung: {_top('seasons', 4)}
- Theoretische Outfit-Kombinationen: {stats.get('combinations')}

Sei ehrlich und konkret. Keine Floskeln, keine Schmeicheleien.
Wenn die Garderobe einseitig oder lückenhaft ist, sag das direkt.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "headline": "ein prägnanter Satz, der die Garderobe charakterisiert",
  "score": Zahl von 0 bis 100 – wie ausgewogen und vielseitig die Garderobe ist,
  "summary": "3-5 Sätze auf Deutsch: ehrliche Gesamteinschätzung",
  "strengths": ["2-4 konkrete Stärken"],
  "weaknesses": ["2-4 konkrete Schwächen oder Lücken"],
  "next_steps": ["2-4 konkrete nächste Anschaffungen oder Maßnahmen, priorisiert"],
  "style_profile": "in 2-4 Worten der dominante Stil, z.B. 'minimalistisch casual'"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[prompt])
    data = _extract_json(response.text or "{}")

    try:
        score = max(0, min(100, int(float(data.get("score", 0)))))
    except (ValueError, TypeError):
        score = 0

    def _str_list(key: str) -> list[str]:
        val = data.get(key, [])
        return [str(x) for x in val] if isinstance(val, list) else []

    return {
        "headline": str(data.get("headline", "")),
        "score": score,
        "summary": str(data.get("summary", "")),
        "strengths": _str_list("strengths"),
        "weaknesses": _str_list("weaknesses"),
        "next_steps": _str_list("next_steps"),
        "style_profile": str(data.get("style_profile", "")),
    }


def chat_with_stylist(
    message: str,
    wardrobe: list[dict[str, Any]],
    profile: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict[str, Any]:
    """Freier Chat mit dem Style-Assistenten, mit Zugriff auf Garderobe und optionalem Bild."""
    
    history_block = ""
    if history:
        turns = []
        for msg in history[-10:]:  # letzte 10 Nachrichten
            role = "Nutzer" if msg.get("role") == "user" else "Du (Vesti)"
            content = msg.get("content", "")
            turns.append(f"{role}: {content}")
        history_block = "\n\nBisheriger Chat-Verlauf:\n" + "\n".join(turns)
    
    # Format wardrobe without IDs
    wardrobe_lines = []
    for it in wardrobe:
        qty_txt = f" ×{it.get('quantity', 1)}" if it.get('quantity', 1) > 1 else ""
        parts = [
            it.get('name') or it['category'],
            it['category'],
            it.get('color', ''),
            it.get('material', ''),
        ]
        desc = ", ".join(p for p in parts if p)
        if it.get('brand'):
            desc += f", {it['brand']}"
        wardrobe_lines.append(f"- {desc}{qty_txt}")
    
    wardrobe_text = "\n".join(wardrobe_lines) if wardrobe_lines else "(Garderobe ist leer)"
    
    prompt = f"""Du bist Vesti, ein freundlicher und kompetenter persönlicher Stilberater. 
Der Nutzer chattet mit dir über Mode, Stil und seine Garderobe.

Profil des Nutzers:
{_profile_block(profile)}

Garderobe des Nutzers:
{wardrobe_text}

{history_block}

Aktuelle Nachricht des Nutzers: {message}

Antworte natürlich, freundlich und hilfreich auf Deutsch. Du kannst:
- Outfit-Vorschläge aus der Garderobe machen (nenne Teile beim Namen, z.B. "dein blaues Hemd")
- Styling-Tipps geben
- Fragen zu Kleidungsstücken beantworten
- Bei hochgeladenen Bildern: Outfit bewerten, Feedback geben
- Allgemeine Mode-Fragen beantworten

WICHTIG: Nenne Kleidungsstücke immer beim Namen oder Beschreibung (z.B. "blaues Hemd", "schwarze Chino"), 
NIEMALS mit IDs oder Nummern!

Sei ehrlich aber freundlich. Wenn etwas nicht passt, sag es konstruktiv.
Antworte in 2-5 Sätzen, es sei denn mehr Detail ist nötig."""

    contents: list[Any] = []
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
    contents.append(prompt)

    response = _call_with_retry(model=settings.gemini_model, contents=contents)
    
    return {
        "response": response.text.strip(),
    }
