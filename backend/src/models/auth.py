"""认证相关 Pydantic 契约。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class UserBrief(BaseModel):
    username: str
    role: str


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief
