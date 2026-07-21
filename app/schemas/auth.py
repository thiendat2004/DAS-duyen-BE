from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserBrief(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str


class TokenResponse(BaseModel):
    accessToken: str
    user: UserBrief


class TokenRefreshResponse(BaseModel):
    accessToken: str
    user: UserBrief


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: str
    status: str
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
