import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext
from app.core.config import ALGORITHM, SECRET_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str):
    return pwd_context.hash(password.strip())


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password.strip(), hashed_password)


def hash_otp(code: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(code: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return hmac.compare_digest(hash_otp(code), hashed)


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)