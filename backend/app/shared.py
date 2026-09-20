"""Gemeinsame Helfer fuer alle Router.

Liegt bewusst in einem eigenen Modul, damit main.py und die Sammlungs-Router
(collections_api.py) dieselben Bausteine nutzen koennen, ohne sich gegenseitig
zu importieren.
"""

import base64
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import Response

from . import gemini_service, models

# Cache-Header fuer Bilder: 7 Tage im Browser, 30 Tage im CDN
IMAGE_CACHE = "public, max-age=604800, s-maxage=2592000, immutable"

LOCATION_HINT = (
    "Das 'In Szene setzen' ist leider im Europäischen Wirtschaftsraum nicht verfügbar — "
    "Google hat die Nano-Banana-Bildgenerierung in der EU aus regulatorischen Gründen gesperrt. "
    "Das Backend müsste dafür in einer US-Region laufen (Railway-Region auf us-west1 wechseln)."
)


def raise_image_error(exc: Exception) -> None:
    """Wandelt einen Bildgenerierungs-Fehler in eine verstaendliche HTTP-Antwort um."""
    if gemini_service._is_location_error(exc):
        raise HTTPException(status_code=451, detail=LOCATION_HINT)
    raise HTTPException(status_code=502, detail=f"Bildgenerierung fehlgeschlagen: {exc}")


def img_response(data: bytes, mime: str) -> Response:
    return Response(content=data, media_type=mime, headers={"Cache-Control": IMAGE_CACHE})


def api_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def decode_b64(value: str, label: str = "Bilddaten") -> bytes:
    """Dekodiert base64 und wirft bei Fehlern eine saubere HTTP-Antwort."""
    try:
        return base64.b64decode(value)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"{label} ungueltig.")


def decode_image_payload(payload: dict[str, Any]) -> list[tuple[bytes, str]]:
    """Liest `images: [{image_base64, image_mime}]` aus einem Payload.

    Faellt auf die Einzelbild-Felder zurueck, damit aeltere Clients weiter funktionieren.
    """
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
        images.append((decode_b64(b64), entry.get("image_mime") or "image/jpeg"))

    if not images:
        raise HTTPException(status_code=400, detail="Keine Bilddaten empfangen.")
    return images


def profile_dict(user: models.User) -> dict[str, Any]:
    return {
        "measurements": user.measurements or {},
        "sizes": user.sizes or {},
        "fit_preference": user.fit_preference,
        "body_type": user.body_type,
        "style_notes": user.style_notes,
    }


def wrist_cm(user: models.User) -> float | None:
    """Handgelenkumfang aus dem Profil, falls hinterlegt."""
    raw = (user.measurements or {}).get("wrist")
    if not raw:
        return None
    try:
        return float(str(raw).replace(",", "."))
    except (ValueError, TypeError):
        return None
