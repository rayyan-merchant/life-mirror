import os, datetime, jwt, hashlib, hmac
from typing import Optional

# ── ENV ─────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

# ── Password hashing (pbkdf2) ───────────────────────────────────────
# (keeps deps light; if you prefer bcrypt, swap it in requirements + here)
PWD_SALT = os.getenv("PWD_SALT", "lm_salt").encode()

def hash_password(password: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), PWD_SALT, 120_000)
    return dk.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    test = hash_password(password)
    return hmac.compare_digest(test, stored_hash or "")

# ── JWT helpers ─────────────────────────────────────────────────────
def _exp(minutes: int = 30) -> int:
    return int((datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)).timestamp())

def _exp_days(days: int) -> int:
    return int((datetime.datetime.utcnow() + datetime.timedelta(days=days)).timestamp())

def create_access_token(sub: str, extra: Optional[dict] = None) -> str:
    payload = {"sub": sub, "type": "access", "exp": _exp(ACCESS_MIN)}
    if extra: payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token(sub: str) -> str:
    payload = {"sub": sub, "type": "refresh", "exp": _exp_days(REFRESH_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
