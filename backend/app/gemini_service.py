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
from .fragrances import (
    FRAGRANCE_AUDIENCES,
    FRAGRANCE_CONCENTRATIONS,
    FRAGRANCE_FAMILIES,
    FRAGRANCE_LONGEVITIES,
    FRAGRANCE_NOTES,
    FRAGRANCE_OCCASIONS,
    FRAGRANCE_SEASONS,
    FRAGRANCE_SILLAGES,
    FRAGRANCE_TIMES,
)
from .watches import (
    WATCH_BAND_MATERIALS,
    WATCH_BAND_TYPES,
    WATCH_CASE_MATERIALS,
    WATCH_CLASPS,
    WATCH_COMPLICATIONS,
    WATCH_CONDITIONS,
    WATCH_CRYSTALS,
    WATCH_MOVEMENTS,
    WATCH_OCCASIONS,
    WATCH_SETS,
    WATCH_STYLES,
)

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
    watches: list[dict[str, Any]] | None = None,
    fragrances: list[dict[str, Any]] | None = None,
    weather: str = "",
) -> dict[str, Any]:
    """Empfiehlt passende Teile aus der Garderobe und urteilt ehrlich, ob das Outfit taugt.

    Uhren und Duefte werden mitempfohlen, sofern der Nutzer welche erfasst hat.
    """
    watches = watches or []
    fragrances = fragrances or []

    wardrobe_lines = []
    for idx, it in enumerate(wardrobe):
        wardrobe_lines.append(
            f"{idx}. {it.get('name') or it['category']} "
            f"({it['category']}, Farbe: {it.get('color', '?')}, "
            f"Stil: {it.get('style', '?')}, Material: {it.get('material', '?')})"
        )
    wardrobe_text = "\n".join(wardrobe_lines) if wardrobe_lines else "(keine weiteren Teile)"

    base_text = (
        f"{base_item.get('name') or base_item['category']} "
        f"({base_item['category']}, Farbe: {base_item.get('color', '?')}, "
        f"Stil: {base_item.get('style', '?')})"
    )

    # Uhren und Duefte nur anfragen, wenn welche vorhanden sind
    watch_section = ""
    watch_json = ""
    if watches:
        watch_section = f"\nUhren des Nutzers (nummeriert):\n{_watches_block(watches)}\n"
        watch_json = """
  "watch_index": Index der passenden Uhr als Zahl, oder null wenn keine passt,
  "watch_reason": "ein Satz: warum diese Uhr zum Look und Anlass passt","""

    fragrance_section = ""
    fragrance_json = ""
    if fragrances:
        fragrance_section = f"\nDüfte des Nutzers (nummeriert):\n{_fragrances_block(fragrances)}\n"
        fragrance_json = """
  "fragrance_index": Index des passenden Dufts als Zahl, oder null wenn keiner passt,
  "fragrance_reason": "ein Satz: warum dieser Duft zum Anlass und zur Tageszeit passt","""

    extras_hint = ""
    if watches or fragrances:
        extras_hint = (
            "\n- Wähle zusätzlich eine passende Uhr und einen passenden Duft aus den unten "
            "gelisteten Sammlungen. Begründe beides kurz über Stil, Anlass und Wirkung – "
            "nicht über den Preis.\n"
            "- Wenn nichts davon zum Look passt, setze den jeweiligen Index auf null. "
            "Eine unpassende Empfehlung ist schlechter als keine."
        )

    weather_block_hint = ""
    if weather and weather.strip():
        weather_block_hint = (
            f"\n- Wetter: {weather.strip()}. Verbindlich für die Auswahl. "
            "Leichte, offene oder kurze Teile gehören nicht in einen Regentag, "
            "dicke Lagen nicht in Hitze."
        )

    # Wetter-Kontext: beeinflusst Layering, Stoffwahl und ob Schuhe nass werden dürfen
    weather_block = f"\nWetter: {weather.strip()}" if weather and weather.strip() else ""

    prompt = f"""Du bist ein ehrlicher, direkter Stilberater. Der Nutzer möchte ein Outfit für folgenden Anlass zusammenstellen.

Basis-Teil: {base_text}
Anlass: {occasion or 'nicht angegeben'}{weather_block}
Zusatzwunsch: {note or 'keiner'}

Verfügbare Teile in der Garderobe (nummeriert):
{wardrobe_text}
{watch_section}{fragrance_section}
WICHTIG:
- Sei ehrlich. Wenn das Basis-Teil oder die verfügbaren Kombinationen für den Anlass nicht wirklich geeignet sind, sag das klar.
- Berücksichtige ALLE Kategorien: Oberteile, Hosen, Schuhe, Jacken, Gürtel, Accessoires, etc.
- Ein komplettes Outfit sollte mindestens Oberteil + Unterteil enthalten, idealerweise auch Schuhe und ggf. Jacke/Accessoires.
- Nenne in deiner Erklärung die Teile NUR beim Namen (z.B. "schwarze Chino"), KEINE IDs oder Nummern!{weather_block_hint}{extras_hint}

Wähle die am besten passenden Teile aus der Garderobe (Basis-Teil nicht nochmal nennen).

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "item_indices": [Liste der Indizes als Zahlen, 0-basiert],{watch_json}{fragrance_json}
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

    watch_pos = _pick_index(data.get("watch_index"), watches)
    fragrance_pos = _pick_index(data.get("fragrance_index"), fragrances)

    return {
        "item_ids": item_ids,
        "suitability": suitability,
        "suitability_reason": str(data.get("suitability_reason", "")),
        "explanation": str(data.get("explanation", "")),
        "watch_id": watches[watch_pos]["id"] if watch_pos is not None else None,
        "watch_reason": str(data.get("watch_reason", "")) if watch_pos is not None else "",
        "fragrance_id": fragrances[fragrance_pos]["id"] if fragrance_pos is not None else None,
        "fragrance_reason": (
            str(data.get("fragrance_reason", "")) if fragrance_pos is not None else ""
        ),
    }


def generate_outfits(
    wardrobe: list[dict[str, Any]],
    occasion: str,
    note: str,
    count: int = 5,
    watches: list[dict[str, Any]] | None = None,
    fragrances: list[dict[str, Any]] | None = None,
    weather: str = "",
) -> dict[str, Any]:
    """Generiert mehrere komplette Outfit-Vorschläge aus der Garderobe.

    Jedes Outfit enthaelt zusaetzlich eine passende Uhr und einen passenden Duft,
    sofern der Nutzer welche erfasst hat.
    """
    if not wardrobe:
        return {"outfits": [], "message": "Deine Garderobe ist noch leer."}

    watches = watches or []
    fragrances = fragrances or []

    wardrobe_lines = []
    for idx, it in enumerate(wardrobe):
        qty_txt = f" ×{it['quantity']}" if it.get('quantity', 1) > 1 else ""
        wardrobe_lines.append(
            f"{idx}. {it.get('name') or it['category']}{qty_txt} "
            f"({it['category']}, Farbe: {it.get('color', '?')}, "
            f"Stil: {it.get('style', '?')}, Material: {it.get('material', '?')})"
        )
    wardrobe_text = "\n".join(wardrobe_lines)

    watch_section = ""
    watch_json = ""
    if watches:
        watch_section = f"\nUhren des Nutzers (nummeriert):\n{_watches_block(watches)}\n"
        watch_json = """
      "watch_index": Index der passenden Uhr als Zahl, oder null,
      "watch_reason": "ein kurzer Satz: warum diese Uhr zum Look passt","""

    fragrance_section = ""
    fragrance_json = ""
    if fragrances:
        fragrance_section = f"\nDüfte des Nutzers (nummeriert):\n{_fragrances_block(fragrances)}\n"
        fragrance_json = """
      "fragrance_index": Index des passenden Dufts als Zahl, oder null,
      "fragrance_reason": "ein kurzer Satz: warum dieser Duft zum Look passt","""

    extras_hint = ""
    if watches or fragrances:
        extras_hint = (
            "\n- Ergänze jedes Outfit um eine passende Uhr und einen passenden Duft aus den "
            "unten gelisteten Sammlungen. Eine Taucheruhr gehört nicht zum Anzug, ein "
            "schwerer Abendduft nicht ins Büro – achte darauf.\n"
            "- Variiere auch hier: nicht bei jedem Outfit dieselbe Uhr und derselbe Duft.\n"
            "- Passt nichts, setze den jeweiligen Index auf null."
        )

    weather_hint = ""
    if weather and weather.strip():
        weather_hint = (
            f"\n- Wetter: {weather.strip()}. Das ist verbindlich. "
            "Kurze Hosen, leichte Stoffe oder offene Schuhe haben bei Regen oder Kälte "
            "in keinem Outfit etwas verloren, egal wie schön sie aussehen. "
            "Umgekehrt wirken dicke Lagen und schwere Stoffe bei Hitze deplatziert."
        )

    weather_block = f"\nWetter: {weather.strip()}" if weather and weather.strip() else ""

    prompt = f"""Du bist ein kreativer Stilberater. Der Nutzer möchte Outfit-Vorschläge aus seiner Garderobe.

Anlass: {occasion or 'Alltag / keine Vorgabe'}{weather_block}
Zusatzwunsch: {note or 'keiner'}

Verfügbare Teile in der Garderobe (nummeriert):
{wardrobe_text}
{watch_section}{fragrance_section}
Erstelle {count} verschiedene, komplette Outfits aus dieser Garderobe.

WICHTIG:
- Jedes Outfit sollte KOMPLETT sein: Oberteil + Unterteil + idealerweise Schuhe, Jacke/Blazer wenn vorhanden, Gürtel/Accessoires wo passend
- Variiere die Kombinationen - keine Duplikate!
- Sei ehrlich: wenn die Garderobe nicht viel hergibt oder für den Anlass ungeeignet ist, sag das
- Berücksichtige ALLE Kategorien: T-Shirts, Hemden, Hosen, Jeans, Schuhe, Jacken, Gürtel, Accessoires, etc.
- Verwende die NUMMERN (0, 1, 2, ...) aus der jeweiligen Liste oben um etwas zu referenzieren
- In deiner Begründung nenne die Teile NUR beim Namen (z.B. "blaues Hemd"), KEINE Nummern oder IDs!{weather_hint}{extras_hint}

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "outfits": [
    {{
      "item_indices": [Liste von Indizes als Zahlen - mindestens 2, besser 3-5 Teile pro Outfit],{watch_json}{fragrance_json}
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

        watch_pos = _pick_index(outfit.get("watch_index"), watches)
        fragrance_pos = _pick_index(outfit.get("fragrance_index"), fragrances)

        outfits.append({
            "item_ids": item_ids,
            "title": str(outfit.get("title", "Outfit")),
            "why": str(outfit.get("why", "")),
            "watch_id": watches[watch_pos]["id"] if watch_pos is not None else None,
            "watch_reason": (
                str(outfit.get("watch_reason", "")) if watch_pos is not None else ""
            ),
            "fragrance_id": (
                fragrances[fragrance_pos]["id"] if fragrance_pos is not None else None
            ),
            "fragrance_reason": (
                str(outfit.get("fragrance_reason", "")) if fragrance_pos is not None else ""
            ),
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
    watches: list[dict[str, Any]] | None = None,
    fragrances: list[dict[str, Any]] | None = None,
    domain: str = "",
) -> dict[str, Any]:
    """Schlaegt sinnvolle Ergaenzungen vor – Kleidung, Uhren und Duefte.

    `domain` beschraenkt die Vorschlaege optional auf "Kleidung", "Uhr" oder "Duft".
    """
    watches = watches or []
    fragrances = fragrances or []

    history_block = ""
    if history:
        turns = []
        for msg in history[-8:]:  # nur die letzten Runden mitschicken
            role = "Nutzer" if msg.get("role") == "user" else "Du"
            turns.append(f"{role}: {msg.get('content', '')}")
        history_block = "\n\nBisheriger Verlauf:\n" + "\n".join(turns)

    if domain == "Uhr":
        domain_hint = (
            "Beschränke dich AUSSCHLIESSLICH auf Uhren. Setze bei jedem Vorschlag "
            '"domain" auf "Uhr" und in "category" den Uhrentyp (z.B. "Dress / Elegant").'
        )
    elif domain == "Duft":
        domain_hint = (
            "Beschränke dich AUSSCHLIESSLICH auf Düfte. Setze bei jedem Vorschlag "
            '"domain" auf "Duft" und in "category" die Duftfamilie (z.B. "Holzig").'
        )
    elif domain == "Kleidung":
        domain_hint = (
            "Beschränke dich AUSSCHLIESSLICH auf Kleidung. Setze bei jedem Vorschlag "
            '"domain" auf "Kleidung".'
        )
    else:
        domain_hint = (
            "Du darfst Kleidung, Uhren und Düfte vorschlagen – gewichte danach, wo die "
            "größte Lücke ist. Setze bei jedem Vorschlag das Feld \"domain\" passend auf "
            '"Kleidung", "Uhr" oder "Duft". Wenn eine Sammlung noch leer ist, ist ein '
            "solider Grundstein dort oft wertvoller als das fünfte ähnliche Kleidungsstück."
        )

    prompt = f"""Du bist ein erfahrener Personal Shopper – für Mode, Uhren und Düfte.

Profil des Nutzers:
{_profile_block(profile)}

Aktuelle Garderobe (mit Stückzahlen):
{_wardrobe_block(wardrobe)}

Uhrensammlung:
{_watches_block(watches, with_ids=False)}

Duftsammlung:
{_fragrances_block(fragrances, with_ids=False)}

Wunsch / Richtung des Nutzers: {direction or 'keine besondere Vorgabe'}{history_block}

Analysiere den gesamten Besitz: Was fehlt? Wo gibt es Lücken? Wovon hat der Nutzer schon zu viel?
Achte auf die Stückzahlen – wenn jemand acht schwarze T-Shirts hat, braucht er kein neuntes.
Bei Uhren gilt dasselbe für Redundanz im Stil, bei Düften für Redundanz in Familie und Basisnoten.

{domain_hint}

Schlage genau 5 konkrete Anschaffungen vor.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "intro": "1-2 Sätze auf Deutsch: was dir am Gesamtbild auffällt",
  "suggestions": [
    {{
      "title": "konkreter Vorschlag, z.B. 'Beige Chino, regular fit' oder 'Frischer Zitrus-EdT für den Sommer'",
      "domain": "Kleidung" | "Uhr" | "Duft",
      "category": "bei Kleidung eine aus: {', '.join(CATEGORIES[:25])}... / bei Uhren der Uhrentyp / bei Düften die Duftfamilie",
      "color": "bei Kleidung und Uhren die empfohlene Farbe, bei Düften leer",
      "material": "bei Kleidung und Uhren das empfohlene Material, bei Düften die Konzentration",
      "reason": "2-3 Sätze auf Deutsch: warum genau das fehlt und was es ermöglicht",
      "combines_with": ["Namen vorhandener Teile, Uhren oder Düfte, die dazu passen"]
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
        raw_domain = str(s.get("domain", "")).strip()
        suggestions.append(
            {
                "title": str(s.get("title", "")),
                "category": str(s.get("category", "")),
                "color": str(s.get("color", "")),
                "material": str(s.get("material", "")),
                "reason": str(s.get("reason", "")),
                "combines_with": [str(c) for c in combines] if isinstance(combines, list) else [],
                "domain": raw_domain if raw_domain in {"Kleidung", "Uhr", "Duft"} else "Kleidung",
            }
        )

    return {"intro": str(data.get("intro", "")), "suggestions": suggestions}


def fit_check(
    product_text: str,
    wardrobe: list[dict[str, Any]],
    profile: dict[str, Any],
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
    watches: list[dict[str, Any]] | None = None,
    fragrances: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prueft ein Produkt aus einem Online-Shop gegen Besitz und Profil.

    Erkennt selbst, ob es um ein Kleidungsstueck, eine Uhr oder einen Duft geht,
    und bewertet entsprechend.
    """
    watches = watches or []
    fragrances = fragrances or []

    wrist = (profile.get("measurements") or {}).get("wrist")
    wrist_block = (
        f"\nHandgelenkumfang des Nutzers: {wrist} cm"
        if wrist
        else "\nHandgelenkumfang: nicht hinterlegt"
    )

    prompt = f"""Du bist ein kritischer Personal Shopper für Mode, Uhren und Düfte.
Der Nutzer überlegt, dieses Produkt zu kaufen.

Produktbeschreibung aus dem Shop:
\"\"\"
{product_text.strip()}
\"\"\"

Profil des Nutzers:
{_profile_block(profile)}{wrist_block}

Aktuelle Garderobe (mit Stückzahlen):
{_wardrobe_block(wardrobe)}

Uhrensammlung:
{_watches_block(watches, with_ids=False)}

Duftsammlung:
{_fragrances_block(fragrances, with_ids=False)}

Erkenne zuerst, um welche Art Produkt es sich handelt: Kleidungsstück, Uhr oder Duft.
Bewerte dann, wie gut es zum bestehenden Besitz und zum Nutzer passt.

Bei einem KLEIDUNGSSTÜCK berücksichtige:
- Passt es farblich und stilistisch zu vorhandenen Teilen?
- Hat der Nutzer schon etwas Ähnliches (Stückzahlen beachten)?
- Material und Qualität: ist das sinnvoll für seine Garderobe?
- Größe: passt die angegebene Größe zu seinen Körpermaßen? Fällt das Teil groß oder klein aus?

Bei einer UHR berücksichtige:
- Gehäusedurchmesser gegen den Handgelenkumfang: als Faustregel liegt der Durchmesser
  angenehm bei etwa 22 bis 27 Prozent des Handgelenkumfangs. Rechne das konkret nach und
  schreibe das Ergebnis in "size_advice".
- Deckt die Uhr einen Anlass ab, für den noch nichts da ist, oder doppelt sie einen
  vorhandenen Stil?
- Passt Werk, Material und Wasserdichtigkeit zum tatsächlichen Einsatz?
- Passt das Armband farblich zu den Schuhen und Gürteln in der Garderobe?

Bei einem DUFT berücksichtige:
- Duftfamilie und Noten gegen die Sammlung: riecht das für Außenstehende wie etwas,
  das der Nutzer schon hat? Dann sag das deutlich.
- Deckt er eine fehlende Jahreszeit, Tageszeit oder einen fehlenden Anlass ab?
- Passt Sillage und Konzentration zum genannten Einsatzzweck?
- Warne bei blindem Kauf ohne Testen, wenn der Duft polarisiert.

Sei ehrlich und kritisch. Wenn es nicht passt, sag das klar.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "score": Zahl von 0 bis 100 (wie gut es passt),
  "verdict": "kurzes Urteil in einem Satz, z.B. 'Sinnvolle Ergänzung' oder 'Hast du schon ähnlich'",
  "explanation": "ausführliche deutsche Begründung (4-6 Sätze), gehe konkret auf die für diese Produktart relevanten Punkte ein",
  "pros": ["kurze Pluspunkte"],
  "cons": ["kurze Minuspunkte"],
  "size_advice": "bei Kleidung die Größenempfehlung anhand der Körpermaße, bei Uhren die Durchmesser-Einschätzung anhand des Handgelenks, bei Düften die Empfehlung zur Flakongröße – oder leer wenn die Daten fehlen",
  "combines_with": ["Namen vorhandener Teile, Uhren oder Düfte, mit denen es gut zusammengeht"]
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
    watches: list[dict[str, Any]] | None = None,
    fragrances: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Freier Chat mit dem Style-Assistenten.

    Der Assistent kennt Garderobe, Uhrensammlung und Duftsammlung und kann
    dadurch konkret aus dem tatsaechlichen Besitz beraten.
    """
    watches = watches or []
    fragrances = fragrances or []
    
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

    prompt = f"""Du bist Vesti, ein freundlicher und kompetenter persönlicher Berater für Stil,
Uhren und Düfte. Der Nutzer chattet mit dir über seine Garderobe, seine Uhren und seine Düfte.

Profil des Nutzers:
{_profile_block(profile)}

Garderobe des Nutzers:
{wardrobe_text}

Uhren des Nutzers:
{_watches_block(watches, with_ids=False)}

Düfte des Nutzers:
{_fragrances_block(fragrances, with_ids=False)}

{history_block}

Aktuelle Nachricht des Nutzers: {message}

Antworte natürlich, freundlich und hilfreich auf Deutsch. Du kannst:
- Outfit-Vorschläge aus der Garderobe machen (nenne Teile beim Namen, z.B. "dein blaues Hemd")
- Styling-Tipps geben
- Fragen zu Kleidungsstücken beantworten
- Zu Uhren beraten: welche Uhr zu welchem Anlass oder Outfit passt, wie ein Durchmesser
  am Handgelenk wirkt, ob eine Kombination stilistisch stimmt
- Zu Düften beraten: welcher Duft zu Anlass, Jahreszeit und Tageszeit passt, wie sich
  Duftfamilien und Noten unterscheiden, ob die Sammlung Lücken oder Dopplungen hat,
  wie man dosiert und was sinnvoll layert
- Bei hochgeladenen Bildern: Outfit, Uhr oder Flakon bewerten und Feedback geben
- Allgemeine Fragen zu Mode, Uhrmacherei und Parfümerie beantworten

WICHTIG:
- Beziehe dich bevorzugt auf das, was der Nutzer WIRKLICH besitzt. Nenne alles beim Namen
  (z.B. "blaues Hemd", "deine Speedmaster", "dein Sauvage"), NIEMALS mit IDs oder Nummern.
- Wenn eine Sammlung leer ist, erfinde nichts hinein. Dann berate allgemein und sag,
  dass du mit erfassten Uhren oder Düften konkreter helfen könntest.
- Bei Düften: erfinde keine Duftnoten. Wenn du einen Duft nicht kennst, sag das.

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


# ══════════════════════════════════════════════════════════════════════
#  Uhren
# ══════════════════════════════════════════════════════════════════════

def _num(value: Any) -> float | None:
    """Parst eine Zahl tolerant aus KI-Antworten ('42 mm' -> 42.0)."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip().replace(",", ".")
    digits = ""
    for ch in cleaned:
        if ch.isdigit() or (ch == "." and "." not in digits):
            digits += ch
        elif digits:
            break
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _int_or_none(value: Any) -> int | None:
    parsed = _num(value)
    return int(parsed) if parsed is not None else None


def _str_list_from(value: Any, allowed: list[str] | None = None) -> list[str]:
    """Normalisiert eine Listen-Antwort der KI, optional gegen erlaubte Werte."""
    if isinstance(value, str):
        raw = [v.strip() for v in value.split(",")]
    elif isinstance(value, list):
        raw = [str(v).strip() for v in value]
    else:
        return []

    items = [v for v in raw if v]
    if allowed is None:
        return items

    lookup = {a.lower(): a for a in allowed}
    result: list[str] = []
    for entry in items:
        canonical = lookup.get(entry.lower())
        if canonical and canonical not in result:
            result.append(canonical)
    return result


def analyze_watch_image(
    images: list[tuple[bytes, str]] | bytes,
    filename: str = "upload.jpg",
    hint: str = "",
    known_brands: list[str] | None = None,
) -> dict[str, Any]:
    """Erkennt eine Uhr anhand der Aufnahmen.

    Anders als bei Kleidung ist hier die *Identifikation* der Schluessel: sobald
    Marke, Modell oder Referenznummer lesbar sind, kann das Modell die technischen
    Daten aus seinem Wissen ergaenzen, statt sie zu schaetzen.
    """
    parts = _image_parts(images, filename)

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}" if hint and hint.strip() else ""
    )
    multi_block = (
        f"\nDir liegen {len(parts)} Aufnahmen derselben Uhr vor (z.B. Zifferblatt, "
        "Gehäuseboden, Armband, Box). Der Gehäuseboden und die Papiere tragen oft die "
        "Referenznummer – lies sie unbedingt aus, wenn sie sichtbar ist."
        if len(parts) > 1
        else ""
    )
    brands_block = ""
    if known_brands:
        brands_list = ", ".join(f'"{b}"' for b in known_brands[:30])
        brands_block = (
            f"\nBereits bekannte Marken des Nutzers: [{brands_list}]"
            "\nBevorzuge bei gleicher Marke die dort verwendete Schreibweise."
        )

    prompt = f"""Du bist ein erfahrener Uhrmacher und Uhrenexperte. Analysiere die Aufnahme(n) dieser Armbanduhr.{multi_block}{hint_block}{brands_block}

VORGEHEN – in dieser Reihenfolge:
1. Lies alles Geschriebene: Markenname und Modellbezeichnung auf dem Zifferblatt, Gravuren
   auf dem Gehäuseboden, Referenz- und Seriennummer, Angaben auf Box oder Papieren.
2. Wenn du das Modell dadurch eindeutig identifizierst, ergänze die technischen Daten
   aus deinem Wissen über dieses Modell (Werk, Durchmesser, Glas, Wasserdichtigkeit).
   Das ist ausdrücklich erwünscht und genauer als Schätzen.
3. Nur was du weder lesen noch aus dem identifizierten Modell ableiten kannst, schätzt du
   optisch. Wenn du etwas nicht bestimmen kannst, lass das Feld leer statt zu raten.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "identified": true wenn du das konkrete Modell erkannt hast, sonst false,
  "confidence": "hoch" | "mittel" | "niedrig",
  "name": "sprechender Name, z.B. 'Omega Speedmaster Professional'",
  "brand": "Markenname, sonst leer",
  "model": "Modellbezeichnung ohne Marke, z.B. 'Speedmaster Professional Moonwatch'",
  "reference": "Referenznummer wenn lesbar oder aus dem Modell bekannt, sonst leer",
  "year": Herstellungsjahr als Zahl wenn bestimmbar, sonst null,
  "movement": "einer aus: {', '.join(WATCH_MOVEMENTS)}",
  "case_material": "einer aus: {', '.join(WATCH_CASE_MATERIALS)}",
  "case_diameter": Gehäusedurchmesser in mm als Zahl, sonst null,
  "case_thickness": Gehäusehöhe in mm als Zahl, sonst null,
  "lug_width": Bandanstoßbreite in mm als Zahl, sonst null,
  "crystal": "einer aus: {', '.join(WATCH_CRYSTALS)}",
  "water_resistance": Wasserdichtigkeit in Metern als Zahl, sonst null,
  "complications": ["passende aus: {', '.join(WATCH_COMPLICATIONS)}"],
  "dial_color": "Farbe des Zifferblatts auf Deutsch",
  "band_type": "einer aus: {', '.join(WATCH_BAND_TYPES)}",
  "band_material": "einer aus: {', '.join(WATCH_BAND_MATERIALS)}",
  "band_color": "Farbe des Armbands auf Deutsch",
  "clasp": "einer aus: {', '.join(WATCH_CLASPS)}",
  "style": "einer aus: {', '.join(WATCH_STYLES)}",
  "occasions": ["2-4 passende aus: {', '.join(WATCH_OCCASIONS)}"],
  "condition": "einer aus: {', '.join(WATCH_CONDITIONS)} – nach sichtbarem Zustand",
  "box_papers": "einer aus: {', '.join(WATCH_SETS)} – nur wenn auf den Bildern zu sehen",
  "description": "2-3 Sätze auf Deutsch: was diese Uhr charakterisiert, wozu sie gedacht ist"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[*parts, prompt])
    data = _extract_json(response.text or "{}")

    return {
        "identified": bool(data.get("identified")),
        "confidence": str(data.get("confidence", "")),
        "name": str(data.get("name", "")),
        "brand": str(data.get("brand", "")),
        "model": str(data.get("model", "")),
        "reference": str(data.get("reference", "")),
        "year": _int_or_none(data.get("year")),
        "movement": str(data.get("movement", "")),
        "case_material": str(data.get("case_material", "")),
        "case_diameter": _num(data.get("case_diameter")),
        "case_thickness": _num(data.get("case_thickness")),
        "lug_width": _num(data.get("lug_width")),
        "crystal": str(data.get("crystal", "")),
        "water_resistance": _int_or_none(data.get("water_resistance")),
        "complications": _str_list_from(data.get("complications"), WATCH_COMPLICATIONS),
        "dial_color": str(data.get("dial_color", "")),
        "band_type": str(data.get("band_type", "")),
        "band_material": str(data.get("band_material", "")),
        "band_color": str(data.get("band_color", "")),
        "clasp": str(data.get("clasp", "")),
        "style": str(data.get("style", "")),
        "occasions": _str_list_from(data.get("occasions"), WATCH_OCCASIONS),
        "condition": str(data.get("condition", "")),
        "box_papers": str(data.get("box_papers", "")),
        "description": str(data.get("description", "")),
    }


def generate_watch_shot(
    images: list[tuple[bytes, str]] | bytes,
    brand: str = "",
    model: str = "",
    dial_color: str = "",
    case_material: str = "",
    band_material: str = "",
    filename: str = "upload.jpg",
) -> tuple[bytes, str] | None:
    """Erzeugt ein sauberes Studio-Produktfoto einer Uhr.

    Uhren brauchen eine andere Bildsprache als Kleidung: leicht angewinkelte
    Dreiviertelansicht, kontrollierte Reflexe auf Glas und Gehaeuse, Zeiger und
    Zifferblatt exakt wie im Original.
    """
    if isinstance(images, (bytes, bytearray)):
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        raw_images: list[tuple[bytes, str]] = [(bytes(images), mime)]
    else:
        raw_images = [(d, m or "image/jpeg") for d, m in images if d]

    if not raw_images:
        return None

    subject = " ".join(p for p in (brand, model) if p) or "Armbanduhr"
    dial_hint = f", Zifferblatt in {dial_color}" if dial_color else ""
    case_hint = f", Gehäuse aus {case_material}" if case_material else ""
    band_hint = f", Armband aus {band_material}" if band_material else ""

    prompt = (
        f"Erstelle ein professionelles Studio-Produktfoto dieser Armbanduhr "
        f"({subject}{dial_hint}{case_hint}{band_hint}).\n\n"
        "ABSOLUT WICHTIG – nichts verfälschen:\n"
        "- Zeige EXAKT dieselbe Uhr wie auf den Referenzfotos: identisches Zifferblatt, "
        "identische Indizes, Zeigerform, Logo- und Schriftplatzierung, Lünette, Krone, "
        "Drücker, Armband und Schließe.\n"
        "- Übernimm die Zeigerstellung und alle Anzeigen (Datum, Hilfszifferblätter) "
        "unverändert vom Original.\n"
        "- Erfinde keine Beschriftung, keine Komplikation und kein Logo dazu. "
        "Ändere weder Farbe noch Proportionen. Es muss zweifelsfrei dieselbe Uhr sein.\n"
        "- Vorhandene Gebrauchsspuren dezent beibehalten, keine neuen hinzufügen.\n\n"
        "Bildgestaltung (nur Szene, nicht die Uhr):\n"
        "- Leicht angewinkelte Dreiviertelansicht, Zifferblatt gut lesbar, komplette Uhr im Bild.\n"
        "- Armband elegant geöffnet oder sanft geschwungen präsentiert, freistehend.\n"
        "- KEIN Handgelenk, KEIN Mensch, KEINE Hand im Bild.\n"
        "- Gleichmäßiger, neutraler, sehr heller Hintergrund (weiß bis leicht warmweiß).\n"
        "- Weiches Studiolicht mit kontrollierten Reflexen auf Glas und Gehäuse, "
        "keine Blendflecken die das Zifferblatt verdecken.\n"
        "- Zentrierte Komposition, quadratischer Bildausschnitt, hochwertig und minimalistisch.\n"
        "Gib nur das fertige Bild zurück."
    )

    return _generate_image_http(raw_images, prompt)


# ══════════════════════════════════════════════════════════════════════
#  Duefte
# ══════════════════════════════════════════════════════════════════════

def analyze_fragrance_image(
    images: list[tuple[bytes, str]] | bytes,
    filename: str = "upload.jpg",
    hint: str = "",
    known_brands: list[str] | None = None,
) -> dict[str, Any]:
    """Erkennt einen Duft anhand der Aufnahmen.

    Ein Duft laesst sich nicht sehen. Der Weg fuehrt deshalb ueber das Etikett:
    ist der Duft identifiziert, liefert das Modell Duftpyramide, Familie und
    Charakter aus seinem Wissen.
    """
    parts = _image_parts(images, filename)

    hint_block = (
        f"\nZusatzinfo vom Nutzer: {hint.strip()}" if hint and hint.strip() else ""
    )
    multi_block = (
        f"\nDir liegen {len(parts)} Aufnahmen desselben Dufts vor (z.B. Flakon, Etikett, "
        "Umverpackung, Batch-Code). Nutze alle, um Name, Linie und Konzentration sicher zu lesen."
        if len(parts) > 1
        else ""
    )
    brands_block = ""
    if known_brands:
        brands_list = ", ".join(f'"{b}"' for b in known_brands[:30])
        brands_block = (
            f"\nBereits bekannte Häuser des Nutzers: [{brands_list}]"
            "\nBevorzuge bei gleichem Haus die dort verwendete Schreibweise."
        )

    prompt = f"""Du bist ein erfahrener Parfum-Experte. Analysiere die Aufnahme(n) dieses Duftes.{multi_block}{hint_block}{brands_block}

VORGEHEN – in dieser Reihenfolge:
1. Lies alles Geschriebene: Haus/Marke, Duftname, Linie oder Kollektion, Konzentration
   (EdT, EdP, Parfum), Füllmenge in ml, Batch-Code.
2. Ein Duft ist auf einem Foto nicht riechbar. Sobald du ihn über das Etikett aber
   eindeutig identifizierst, gib Duftpyramide, Duftfamilie, Sillage und Haltbarkeit
   aus deinem Wissen über diesen konkreten Duft an. Das ist ausdrücklich erwünscht.
3. Wenn du den Duft NICHT sicher identifizieren kannst, setze "identified" auf false und
   lass die Duftnoten leer, statt sie zu erfinden. Erfundene Noten sind schlimmer als
   keine Angabe.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "identified": true wenn du den konkreten Duft erkannt hast, sonst false,
  "confidence": "hoch" | "mittel" | "niedrig",
  "name": "Duftname ohne Haus, z.B. 'Sauvage Elixir'",
  "brand": "Haus / Marke, z.B. 'Dior'",
  "line": "Linie oder Kollektion wenn vorhanden, sonst leer",
  "concentration": "einer aus: {', '.join(FRAGRANCE_CONCENTRATIONS)}",
  "year": Erscheinungsjahr als Zahl wenn bekannt, sonst null,
  "perfumer": "Name des Parfumeurs wenn bekannt, sonst leer",
  "audience": "einer aus: {', '.join(FRAGRANCE_AUDIENCES)}",
  "family": "die dominante Duftfamilie, einer aus: {', '.join(FRAGRANCE_FAMILIES)}",
  "secondary_family": "zweite Duftfamilie falls zutreffend, sonst leer",
  "top_notes": ["Kopfnoten, nur bekannte Noten aus: {', '.join(FRAGRANCE_NOTES[:40])} usw."],
  "heart_notes": ["Herznoten"],
  "base_notes": ["Basisnoten"],
  "sillage": "einer aus: {', '.join(FRAGRANCE_SILLAGES)}",
  "longevity": "einer aus: {', '.join(FRAGRANCE_LONGEVITIES)}",
  "occasions": ["2-4 passende aus: {', '.join(FRAGRANCE_OCCASIONS)}"],
  "seasons": ["passende aus: {', '.join(FRAGRANCE_SEASONS)}"],
  "time_of_day": "einer aus: {', '.join(FRAGRANCE_TIMES)}",
  "bottle_size": Füllmenge in ml als Zahl wenn lesbar, sonst null,
  "batch_code": "Batch-Code wenn lesbar, sonst leer",
  "description": "2-3 Sätze auf Deutsch: wie der Duft wirkt und wozu er passt"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[*parts, prompt])
    data = _extract_json(response.text or "{}")

    return {
        "identified": bool(data.get("identified")),
        "confidence": str(data.get("confidence", "")),
        "name": str(data.get("name", "")),
        "brand": str(data.get("brand", "")),
        "line": str(data.get("line", "")),
        "concentration": str(data.get("concentration", "")),
        "year": _int_or_none(data.get("year")),
        "perfumer": str(data.get("perfumer", "")),
        "audience": str(data.get("audience", "")),
        "family": str(data.get("family", "")),
        "secondary_family": str(data.get("secondary_family", "")),
        # Noten bewusst NICHT gegen die Liste filtern: die Auswahl ist bekannt
        # unvollstaendig und eine korrekt gelesene, seltene Note ist wertvoller
        # als eine weggeworfene.
        "top_notes": _str_list_from(data.get("top_notes")),
        "heart_notes": _str_list_from(data.get("heart_notes")),
        "base_notes": _str_list_from(data.get("base_notes")),
        "sillage": str(data.get("sillage", "")),
        "longevity": str(data.get("longevity", "")),
        "occasions": _str_list_from(data.get("occasions"), FRAGRANCE_OCCASIONS),
        "seasons": _str_list_from(data.get("seasons"), FRAGRANCE_SEASONS),
        "time_of_day": str(data.get("time_of_day", "")),
        "bottle_size": _int_or_none(data.get("bottle_size")),
        "batch_code": str(data.get("batch_code", "")),
        "description": str(data.get("description", "")),
    }


def generate_fragrance_shot(
    images: list[tuple[bytes, str]] | bytes,
    brand: str = "",
    name: str = "",
    family: str = "",
    filename: str = "upload.jpg",
) -> tuple[bytes, str] | None:
    """Erzeugt ein sauberes Studio-Produktfoto eines Flakons.

    Glas ist der schwierige Teil: Form, Farbe des Saftes und die Etikettenschrift
    muessen exakt bleiben, waehrend Reflexe und Hintergrund neu gestaltet werden.
    """
    if isinstance(images, (bytes, bytearray)):
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        raw_images: list[tuple[bytes, str]] = [(bytes(images), mime)]
    else:
        raw_images = [(d, m or "image/jpeg") for d, m in images if d]

    if not raw_images:
        return None

    subject = " ".join(p for p in (brand, name) if p) or "Parfumflakon"
    family_hint = f" Der Duft ist {family}." if family else ""

    prompt = (
        f"Erstelle ein professionelles Studio-Produktfoto dieses Parfumflakons "
        f"({subject}).{family_hint}\n\n"
        "ABSOLUT WICHTIG – nichts verfälschen:\n"
        "- Zeige EXAKT denselben Flakon wie auf den Referenzfotos: identische Flaschenform, "
        "identischer Verschluss, gleiche Farbe des Glases und der Flüssigkeit darin, "
        "gleicher Füllstand.\n"
        "- Das Etikett muss zeichengenau übernommen werden: gleiche Schriftzüge, gleiche "
        "Schriftart, gleiche Anordnung, gleiche Farben. Erfinde KEINEN Text und ändere "
        "keine Buchstaben.\n"
        "- Keine zusätzlichen Gravuren, Siegel oder Verzierungen hinzufügen.\n\n"
        "Bildgestaltung (nur Szene, nicht der Flakon):\n"
        "- Flakon aufrecht, frontal bis ganz leicht angewinkelt, komplett im Bild, "
        "Etikett vollständig lesbar.\n"
        "- Eleganter, ruhiger Hintergrund: neutral hell (weiß bis warmweiß) mit sanftem "
        "Verlauf, hochwertig und minimalistisch.\n"
        "- Weiches Studiolicht, kontrollierte Glanzlichter auf dem Glas, eine dezente "
        "Reflexion oder ein weicher Schatten auf der Standfläche.\n"
        "- Keine Menschen, keine Hände, keine Blüten oder Deko-Requisiten.\n"
        "- Zentrierte Komposition, quadratischer Bildausschnitt.\n"
        "Gib nur das fertige Bild zurück."
    )

    return _generate_image_http(raw_images, prompt)


# ══════════════════════════════════════════════════════════════════════
#  Prompt-Bausteine fuer die Sammlungen
# ══════════════════════════════════════════════════════════════════════

def _watches_block(watches: list[dict[str, Any]], with_ids: bool = True) -> str:
    """Formatiert die Uhrensammlung fuer den Prompt."""
    if not watches:
        return "(keine Uhren erfasst)"

    lines = []
    for idx, w in enumerate(watches):
        label = w.get("name") or " ".join(
            p for p in (w.get("brand", ""), w.get("model", "")) if p
        ) or "Uhr"
        bits = []
        if w.get("style"):
            bits.append(w["style"])
        if w.get("case_material"):
            bits.append(f"Gehäuse {w['case_material']}")
        if w.get("case_diameter"):
            bits.append(f"{w['case_diameter']:g} mm")
        if w.get("dial_color"):
            bits.append(f"Zifferblatt {w['dial_color']}")
        if w.get("band_material"):
            bits.append(f"Band {w['band_material']}")
        if w.get("band_color"):
            bits.append(w["band_color"])
        if w.get("movement"):
            bits.append(w["movement"])
        if w.get("water_resistance"):
            bits.append(f"{w['water_resistance']} m WR")
        occ = w.get("occasions") or []
        if occ:
            bits.append("für " + ", ".join(occ))
        prefix = f"  {idx}. " if with_ids else "  - "
        lines.append(f"{prefix}{label} ({', '.join(bits) if bits else 'keine Details'})")

    return "\n".join(lines)


def _fragrances_block(fragrances: list[dict[str, Any]], with_ids: bool = True) -> str:
    """Formatiert die Duftsammlung fuer den Prompt."""
    if not fragrances:
        return "(keine Düfte erfasst)"

    lines = []
    for idx, f in enumerate(fragrances):
        label = f.get("name") or "Duft"
        if f.get("brand"):
            label = f"{f['brand']} {label}"
        bits = []
        if f.get("concentration"):
            bits.append(f["concentration"])
        if f.get("family"):
            bits.append(f["family"])
        if f.get("secondary_family"):
            bits.append(f["secondary_family"])

        pyramid = []
        for key, prefix in (
            ("top_notes", "Kopf"),
            ("heart_notes", "Herz"),
            ("base_notes", "Basis"),
        ):
            notes = f.get(key) or []
            if notes:
                pyramid.append(f"{prefix}: {', '.join(notes[:5])}")
        if pyramid:
            bits.append(" | ".join(pyramid))

        if f.get("sillage"):
            bits.append(f"Sillage {f['sillage']}")
        if f.get("longevity"):
            bits.append(f"Haltbarkeit {f['longevity']}")
        if f.get("time_of_day"):
            bits.append(f["time_of_day"])
        seasons = f.get("seasons") or []
        if seasons:
            bits.append("Saison: " + ", ".join(seasons))
        occ = f.get("occasions") or []
        if occ:
            bits.append("für " + ", ".join(occ))
        if f.get("fill_level") is not None:
            bits.append(f"Flakon {f['fill_level']}% voll")

        prefix = f"  {idx}. " if with_ids else "  - "
        lines.append(f"{prefix}{label} ({'; '.join(bits) if bits else 'keine Details'})")

    return "\n".join(lines)


def _pick_index(value: Any, pool: list[dict[str, Any]]) -> int | None:
    """Wandelt einen von der KI gelieferten Index in eine gueltige Listenposition."""
    if value is None or value == "":
        return None
    try:
        idx = int(value)
    except (ValueError, TypeError):
        return None
    return idx if 0 <= idx < len(pool) else None


# ══════════════════════════════════════════════════════════════════════
#  Sammlungs-Auswertung durch die KI
# ══════════════════════════════════════════════════════════════════════

def analyze_watch_collection(
    watches: list[dict[str, Any]],
    profile: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Ehrliche KI-Einschaetzung der Uhrensammlung."""
    def _top(key: str, n: int = 5) -> str:
        entries = stats.get(key) or []
        return ", ".join(f"{e['label']} ({e['count']})" for e in entries[:n]) or "–"

    prompt = f"""Du bist ein erfahrener Uhrenberater und analysierst die Sammlung eines Nutzers.

Profil:
{_profile_block(profile)}

Uhrensammlung:
{_watches_block(watches, with_ids=False)}

Berechnete Kennzahlen:
- Uhren insgesamt: {stats.get('total')}
- Stile: {_top('styles')}
- Marken: {_top('brands')}
- Gehäusematerialien: {_top('case_materials')}
- Armbänder: {_top('band_materials')}
- Werke: {_top('movements')}
- Abgedeckte Anlässe: {_top('occasions')}
- Durchschnittlicher Durchmesser: {stats.get('avg_diameter') or '–'} mm

Sei ehrlich und konkret. Keine Floskeln. Eine Sammlung aus fünf ähnlichen Taucheruhren
ist keine Sammlung, sondern eine Wiederholung – wenn das so ist, sag es.
Achte besonders darauf, ob die Sammlung die Anlässe des Nutzers abdeckt: eine elegante Uhr
für formelle Termine, eine robuste für den Alltag, eventuell eine sportliche.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "headline": "ein prägnanter Satz, der die Sammlung charakterisiert",
  "score": Zahl von 0 bis 100 – wie ausgewogen und vielseitig die Sammlung ist,
  "summary": "3-5 Sätze auf Deutsch: ehrliche Gesamteinschätzung",
  "strengths": ["2-4 konkrete Stärken"],
  "weaknesses": ["2-4 konkrete Lücken oder Redundanzen"],
  "next_steps": ["2-4 konkrete nächste Schritte, priorisiert"],
  "collection_profile": "in 2-4 Worten der Charakter der Sammlung, z.B. 'sportlich-klassisch'"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[prompt])
    return _parse_collection_insight(response.text or "{}", "collection_profile")


def analyze_fragrance_collection(
    fragrances: list[dict[str, Any]],
    profile: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Ehrliche KI-Einschaetzung der Duftsammlung."""
    def _top(key: str, n: int = 5) -> str:
        entries = stats.get(key) or []
        return ", ".join(f"{e['label']} ({e['count']})" for e in entries[:n]) or "–"

    prompt = f"""Du bist ein erfahrener Duftberater und analysierst die Sammlung eines Nutzers.

Profil:
{_profile_block(profile)}

Duftsammlung:
{_fragrances_block(fragrances, with_ids=False)}

Berechnete Kennzahlen:
- Düfte insgesamt: {stats.get('total')}
- Duftfamilien: {_top('families')}
- Häufigste Noten: {_top('notes', 8)}
- Konzentrationen: {_top('concentrations')}
- Häuser: {_top('brands')}
- Saison-Abdeckung: {_top('seasons', 5)}
- Abgedeckte Anlässe: {_top('occasions')}
- Tageszeiten: {_top('times')}

Sei ehrlich und konkret. Keine Floskeln.
Achte auf zwei Dinge besonders:
1. Redundanz – mehrere Düfte derselben Familie mit denselben Basisnoten riechen für
   Außenstehende gleich, egal wie unterschiedlich sie für den Träger sind. Sag das klar.
2. Abdeckung – fehlt etwas Frisches für den Sommer, etwas Wärmeres für den Winter,
   etwas Zurückhaltendes fürs Büro oder etwas Markantes für den Abend?

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "headline": "ein prägnanter Satz, der die Sammlung charakterisiert",
  "score": Zahl von 0 bis 100 – wie ausgewogen und vielseitig die Sammlung ist,
  "summary": "3-5 Sätze auf Deutsch: ehrliche Gesamteinschätzung",
  "strengths": ["2-4 konkrete Stärken"],
  "weaknesses": ["2-4 konkrete Lücken oder Redundanzen"],
  "next_steps": ["2-4 konkrete nächste Schritte, priorisiert"],
  "collection_profile": "in 2-4 Worten das Duftprofil, z.B. 'holzig-orientalisch'"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[prompt])
    return _parse_collection_insight(response.text or "{}", "collection_profile")


def _parse_collection_insight(raw: str, profile_key: str) -> dict[str, Any]:
    """Gemeinsames Parsen der Sammlungs-Einschaetzungen."""
    data = _extract_json(raw)

    try:
        score = max(0, min(100, int(float(data.get("score", 0)))))
    except (ValueError, TypeError):
        score = 0

    def _list(key: str) -> list[str]:
        val = data.get(key, [])
        return [str(x) for x in val] if isinstance(val, list) else []

    return {
        "headline": str(data.get("headline", "")),
        "score": score,
        "summary": str(data.get("summary", "")),
        "strengths": _list("strengths"),
        "weaknesses": _list("weaknesses"),
        "next_steps": _list("next_steps"),
        "collection_profile": str(data.get(profile_key, "")),
    }


def fragrance_advice(
    question: str,
    fragrances: list[dict[str, Any]],
    profile: dict[str, Any],
    occasion: str = "",
    season: str = "",
) -> dict[str, Any]:
    """Gezielte Duftberatung aus dem eigenen Bestand.

    Beantwortet Fragen wie "welchen Duft nehme ich zum Vorstellungsgespraech"
    und nennt eine konkrete Empfehlung plus Alternative.
    """
    prompt = f"""Du bist ein erfahrener Duftberater. Der Nutzer möchte wissen, welchen Duft aus
seiner eigenen Sammlung er nehmen soll.

Profil:
{_profile_block(profile)}

Seine Duftsammlung (nummeriert):
{_fragrances_block(fragrances)}

Frage des Nutzers: {question or 'Welcher Duft passt heute?'}
Anlass: {occasion or 'nicht angegeben'}
Jahreszeit: {season or 'nicht angegeben'}

Empfehle genau einen Duft aus der Sammlung und eine Alternative.
Begründe über Duftfamilie, Noten, Sillage und Anlass – nicht über Marketing.
Wenn kein Duft der Sammlung wirklich passt, sag das offen und erkläre, was fehlen würde.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein Markdown):
{{
  "pick_index": Index des empfohlenen Dufts als Zahl, oder null wenn keiner passt,
  "alternative_index": Index der Alternative als Zahl, oder null,
  "reason": "2-4 Sätze auf Deutsch: warum dieser Duft. Nenne ihn beim Namen, nicht per Nummer.",
  "application": "kurzer Hinweis zur Dosierung, z.B. 'zwei Sprüher, Hals und Handgelenk'",
  "gap": "was in der Sammlung für diesen Anlass fehlt, oder leer"
}}"""

    response = _call_with_retry(model=settings.gemini_model, contents=[prompt])
    data = _extract_json(response.text or "{}")

    pick = _pick_index(data.get("pick_index"), fragrances)
    alt = _pick_index(data.get("alternative_index"), fragrances)

    return {
        "fragrance_id": fragrances[pick]["id"] if pick is not None else None,
        "alternative_id": fragrances[alt]["id"] if alt is not None else None,
        "reason": str(data.get("reason", "")),
        "application": str(data.get("application", "")),
        "gap": str(data.get("gap", "")),
    }
