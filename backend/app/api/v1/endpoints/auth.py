"""Authentication endpoints: login, register, language, profile."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_min_role
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.geo import Role, User
from app.schemas.auth import (
    ChangeLanguageRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter()

PUBLIC_REGISTER_ROLES = {"citizen", "field_official"}


@router.post("/login", response_model=TokenResponse,
             dependencies=[Depends(rate_limit("login", 10, 300))])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(
        subject=user.id, role=user.role.name if user.role else "citizen",
        extras={"district_id": user.district_id},
    )
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=201,
             dependencies=[Depends(rate_limit("register", 5, 3600))])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    requested_role = payload.role or "citizen"
    # First registered user becomes the platform super admin (no demo accounts).
    user_count = db.scalar(select(func.count(User.id))) or 0
    if user_count == 0:
        requested_role = "super_admin"
    elif requested_role not in PUBLIC_REGISTER_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Self-registration only allowed for roles: {', '.join(PUBLIC_REGISTER_ROLES)}",
        )
    role = db.scalar(select(Role).where(Role.name == requested_role))
    if role is None:
        role = db.scalar(select(Role).where(Role.name == "citizen"))
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role_id=role.id,
        district_id=payload.district_id,
        preferred_language=payload.preferred_language or "en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id, role=role.name)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/language", response_model=UserOut)
def change_language(payload: ChangeLanguageRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    from app.services.i18n import supported_languages

    if payload.language not in supported_languages():
        raise HTTPException(status_code=400, detail="Unsupported language")
    user.preferred_language = payload.language
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(role: str = "super_admin", user: User = Depends(require_min_role("district_admin")),
               db: Session = Depends(get_db)):
    rows = db.scalars(select(User)).all()
    return [UserOut.model_validate(u) for u in rows]
