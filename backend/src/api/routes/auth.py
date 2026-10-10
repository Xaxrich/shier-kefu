"""登录接口。"""

from fastapi import Depends, HTTPException
from pycore.api import APIRouter, success_response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.models.auth import LoginRequest, LoginResult, UserBrief
from src.services.auth_service import authenticate, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await authenticate(session, body.username.strip(), body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = create_access_token(user.id, user.username, user.role)
    data = LoginResult(
        access_token=token,
        token_type="bearer",
        user=UserBrief(username=user.username, role=user.role),
    )
    return success_response(data.model_dump())
