"""S3-kompatibler Bildspeicher (Cloudflare R2, AWS S3, MinIO ...).

Idee: Die Bild-Spalten der Modelle bleiben BYTEA, bekommen aber den Typ
`S3Blob`. Beim Schreiben wird das Bild nach S3 hochgeladen und in der DB nur
ein kurzer Marker (`s3:<key>`) abgelegt. Beim Lesen wird der Marker
transparent aufgeloest, sodass der restliche Code weiterhin mit `bytes`
arbeitet. Bestehende Zeilen mit echten Bilddaten bleiben lesbar (Legacy);
`migrate_images_to_s3.py` verschiebt sie nachtraeglich.

Ist S3 nicht konfiguriert, werden Bilder wie bisher direkt in der DB gespeichert.
"""

import logging
import threading
import uuid
from collections import OrderedDict
from functools import lru_cache

from sqlalchemy import LargeBinary, event, inspect, select, type_coerce
from sqlalchemy.orm import Session, object_session
from sqlalchemy.types import TypeDecorator

from .config import get_settings

logger = logging.getLogger("vesti.storage")

MARKER = b"s3:"
_MAX_MARKER_LEN = 512


class S3Bytes(bytes):
    """Bilddaten, die aus S3 geladen wurden. `key` verweist auf das S3-Objekt."""

    key: str | None = None

    def __new__(cls, data: bytes, key: str | None = None):
        obj = super().__new__(cls, data)
        obj.key = key
        return obj


# ── Konfiguration / Client ─────────────────────────────────────────────

def s3_enabled() -> bool:
    s = get_settings()
    return bool(s.s3_bucket and s.s3_access_key_id and s.s3_secret_access_key)


@lru_cache
def _client():
    import boto3
    from botocore.config import Config

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url or None,
        region_name=s.s3_region or "auto",
        aws_access_key_id=s.s3_access_key_id,
        aws_secret_access_key=s.s3_secret_access_key,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": "path"},
        ),
    )


# ── Marker ─────────────────────────────────────────────────────────────

def encode_marker(key: str) -> bytes:
    return MARKER + key.encode("utf-8")


def decode_marker(raw: bytes | None) -> str | None:
    """Gibt den S3-Key zurueck, falls `raw` ein Marker ist (sonst None)."""
    if not raw or len(raw) > _MAX_MARKER_LEN or not raw.startswith(MARKER):
        return None
    try:
        return raw[len(MARKER):].decode("utf-8")
    except UnicodeDecodeError:
        return None


# ── Kleiner Byte-begrenzter LRU-Cache (Keys sind unveraenderlich) ───────

class _BlobCache:
    def __init__(self, max_bytes: int):
        self._max = max_bytes
        self._size = 0
        self._data: OrderedDict[str, bytes] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            value = self._data.get(key)
            if value is not None:
                self._data.move_to_end(key)
            return value

    def put(self, key: str, value: bytes) -> None:
        if len(value) > self._max // 4:
            return
        with self._lock:
            old = self._data.pop(key, None)
            if old is not None:
                self._size -= len(old)
            self._data[key] = value
            self._size += len(value)
            while self._size > self._max and self._data:
                _, evicted = self._data.popitem(last=False)
                self._size -= len(evicted)

    def drop(self, key: str) -> None:
        with self._lock:
            old = self._data.pop(key, None)
            if old is not None:
                self._size -= len(old)


_cache = _BlobCache(max_bytes=64 * 1024 * 1024)


# ── Low-level Operationen ───────────────────────────────────────────────

def _sniff(data: bytes) -> tuple[str, str]:
    """(Dateiendung, Content-Type) anhand der Magic Bytes."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    return ".bin", "application/octet-stream"


def put_blob(folder: str, data: bytes) -> str:
    """Laedt `data` nach S3 und liefert den Key (`<prefix><folder>/<uuid><ext>`)."""
    s = get_settings()
    prefix = s.s3_key_prefix or ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    ext, content_type = _sniff(data)
    key = f"{prefix}{folder}/{uuid.uuid4().hex}{ext}"
    _client().put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)
    _cache.put(key, data)
    return key


def get_blob(key: str) -> bytes:
    cached = _cache.get(key)
    if cached is not None:
        return cached
    resp = _client().get_object(Bucket=get_settings().s3_bucket, Key=key)
    data = resp["Body"].read()
    _cache.put(key, data)
    return data


def delete_blob(key: str) -> None:
    _cache.drop(key)
    _client().delete_object(Bucket=get_settings().s3_bucket, Key=key)


# ── SQLAlchemy-Typ ──────────────────────────────────────────────────────

class S3Blob(TypeDecorator):
    """BYTEA-Spalte, die Bilder in S3 ablegt und nur einen Marker speichert."""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, folder: str = "misc"):
        super().__init__()
        self.folder = folder

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        raw = bytes(value)
        if not raw or not s3_enabled():
            return raw
        # Immer ein neues Objekt anlegen: dieselben Bytes koennen in mehreren
        # Zeilen landen (z. B. bei Migrationen) und jede Zeile besitzt ihr Objekt.
        return encode_marker(put_blob(self.folder, raw))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        raw = bytes(value)
        key = decode_marker(raw)
        if key is None:
            return raw
        return S3Bytes(get_blob(key), key)

    def copy(self, **kw):
        return S3Blob(self.folder)


# ── Aufraeumen verwaister S3-Objekte ───────────────────────────────────
# Beim Loeschen/Ersetzen eines Bildes wird der alte Key gemerkt und erst nach
# erfolgreichem Commit aus S3 entfernt.

_PENDING = "s3_pending_delete"


def _blob_attrs(mapper) -> list[str]:
    return [
        attr.key
        for attr in mapper.column_attrs
        if isinstance(attr.columns[0].type, S3Blob)
    ]


def _raw_keys(connection, mapper, target, attr_names: list[str]) -> set[str]:
    """Liest die aktuell gespeicherten Marker der Zeile (ohne S3-Download)."""
    if not attr_names:
        return set()
    table = mapper.local_table
    pk_col = list(table.primary_key.columns)[0]
    pk_val = mapper.primary_key_from_instance(target)[0]
    cols = [type_coerce(table.c[mapper.get_property(n).columns[0].key], LargeBinary) for n in attr_names]
    row = connection.execute(select(*cols).where(pk_col == pk_val)).first()
    keys: set[str] = set()
    if row:
        for raw in row:
            key = decode_marker(bytes(raw)) if raw is not None else None
            if key:
                keys.add(key)
    return keys


def _queue(target, keys: set[str]) -> None:
    if not keys:
        return
    session = object_session(target)
    if session is not None:
        session.info.setdefault(_PENDING, set()).update(keys)


def _before_delete(mapper, connection, target):
    if not s3_enabled():
        return
    _queue(target, _raw_keys(connection, mapper, target, _blob_attrs(mapper)))


def _before_update(mapper, connection, target):
    if not s3_enabled():
        return
    state = inspect(target)
    changed = [n for n in _blob_attrs(mapper) if state.attrs[n].history.has_changes()]
    _queue(target, _raw_keys(connection, mapper, target, changed))


def register_cleanup(model_classes) -> None:
    for cls in model_classes:
        event.listen(cls, "before_delete", _before_delete)
        event.listen(cls, "before_update", _before_update)


@event.listens_for(Session, "after_commit")
def _purge_after_commit(session):
    keys = session.info.pop(_PENDING, None)
    for key in keys or ():
        try:
            delete_blob(key)
        except Exception:  # noqa: BLE001
            logger.warning("S3-Objekt %s konnte nicht geloescht werden", key, exc_info=True)


@event.listens_for(Session, "after_rollback")
def _discard_after_rollback(session):
    session.info.pop(_PENDING, None)
