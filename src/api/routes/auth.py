from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from src.db.session import get_db
from src.db.models import User
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.api.deps import get_current_user
from src.core.rate_limit import rl_auth
import os, asyncio
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
LOGIN_MAX_FAIL = int(os.getenv("LOGIN_MAX_FAIL", "5"))
LOGIN_LOCK_MIN = int(os.getenv("LOGIN_LOCK_MIN", "15"))


router = APIRouter()

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    public_alias: str | None = None
    opt_in_public_analysis: bool = False

class AuthOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/register", dependencies=[Depends(rl_auth())], response_model=AuthOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        public_alias=data.public_alias,
        opt_in_public_analysis=data.opt_in_public_analysis,
        password_hash=hash_password(data.password),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()

    return AuthOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )

class LoginIn(BaseModel):
    email: EmailStr
    password: str

async def _get_redis():
    return redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

@router.post("/login", response_model=AuthOut, dependencies=[Depends(rl_auth())])
async def login(data: LoginIn, db: Session = Depends(get_db)):
    r = await _get_redis()
    key = f"login:fail:{data.email.lower()}"
    lock_key = f"login:lock:{data.email.lower()}"

    if await r.get(lock_key):
        raise HTTPException(status_code=429, detail="Too many attempts. Try later.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        fails = await r.incr(key)
        if fails == 1:
            await r.expire(key, LOGIN_LOCK_MIN * 60)  # window
        if fails >= LOGIN_MAX_FAIL:
            await r.set(lock_key, "1", ex=LOGIN_LOCK_MIN * 60)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # success → reset counters
    await r.delete(key)
    await r.delete(lock_key)

    user.last_login = datetime.utcnow()
    db.add(user); db.commit()
    return AuthOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


class RefreshIn(BaseModel):
    refresh_token: str

@router.post("/refresh", dependencies=[Depends(rl_auth())], response_model=AuthOut)
def refresh_tokens(body: RefreshIn = Body(...)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    sub = payload["sub"]
    return AuthOut(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "public_alias": user.public_alias,
        "opt_in_public_analysis": user.opt_in_public_analysis,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }
