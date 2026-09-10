"""FastAPI dependencies for auth, roles and rate limiting."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.geo import User

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "citizen": 1,
    "field_official": 2,
    "district_admin": 3,
    "disaster_mgmt": 4,
    "super_admin": 5,
}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or missing")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role is None or user.role.name not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker


def require_min_role(min_role: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        user_role = user.role.name if user.role else "citizen"
        if ROLE_HIERARCHY.get(user_role, 1) < ROLE_HIERARCHY[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker


def get_current_district(user: User = Depends(get_current_user)) -> Optional[str]:
    return user.district_id
