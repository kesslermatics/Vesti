"""Authentifizierung: Passwort-Hashing (PBKDF2) und JWT-Tokens."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .models import ApiKey  # noqa: F401 – re-exported for mcp_api
from .config import get_settings
from .database import get_db

settings = get_settings()
_bearer = HTTPBearer(auto_error=True)

_PBKDF2_ROUNDS = 240_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        rounds = int(rounds)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AttributeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return hmac.compare_digest(dk.hex(), hash_hex)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_user_by_api_key(
    api_key: str,
    db: Session,
) -> models.User:
    """Gibt den User zu einem API-Key zurück. Wirft 401 wenn ungültig."""
    from sqlalchemy import select

    key_obj = db.scalars(
        select(models.ApiKey).where(models.ApiKey.key == api_key)
    ).first()
    if not key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger API-Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(models.User, key_obj.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger API-Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungueltiges oder abgelaufenes Token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise invalid

    user = db.get(models.User, user_id)
    if not user:
        raise invalid
    return user
