from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from src.db.session import get_db
from src.db.models import User
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.api.deps import get_current_user

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

@router.post("/login", dependencies=[Depends(rl_auth())], response_model=AuthOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

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
