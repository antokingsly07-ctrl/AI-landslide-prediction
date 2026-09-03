"""Pydantic schemas for authentication and users."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    phone: Optional[str] = None
    role: str = "citizen"  # citizen|field_official|district_admin|disaster_mgmt|super_admin
    district_id: Optional[str] = None
    preferred_language: str = "en"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str | None = None
    role_id: Optional[str] = None
    district_id: Optional[str] = None
    is_active: bool
    preferred_language: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("role", mode="before")
    @classmethod
    def _role_name(cls, v):
        # Accept either a Role ORM object or a plain string
        if hasattr(v, "name"):
            return v.name
        return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    phone: Optional[str] = None
    role_id: Optional[str] = None
    district_id: Optional[str] = None
    preferred_language: str = "en"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[str] = None
    district_id: Optional[str] = None
    is_active: Optional[bool] = None
    preferred_language: Optional[str] = None


UserOut.model_rebuild()


class ChangeLanguageRequest(BaseModel):
    language: str
