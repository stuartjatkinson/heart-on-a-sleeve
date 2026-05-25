import base64
import hashlib
from datetime import datetime, timedelta
from typing import Any
import bcrypt
from jose import jwt, JWTError
from .config import get_settings

settings = get_settings()

ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 30
REFRESH_EXPIRE_DAYS = 7


def _prehash(password: str) -> bytes:
    """SHA-256 → base64 (44 ASCII bytes) so bcrypt never sees > 72 bytes."""
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(plain), hashed.encode())


def create_access_token(user_id: int) -> str:
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp, "type": "access"}, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    exp = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": exp, "type": "refresh"}, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
