"""路由依赖：鉴权与当前用户。"""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import get_settings
from src.db.models import User
from src.db.session import get_session

security = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        s = get_settings()
        payload = jwt.decode(
            creds.credentials,
            s.jwt_secret_key,
            algorithms=[s.jwt_algorithm],
        )
        uid = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效或过期令牌") from None

    r = await session.execute(select(User).where(User.id == uid))
    user = r.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_agent(user: User) -> None:
    if user.role not in ("agent", "both"):
        raise HTTPException(status_code=403, detail="需要坐席权限")


def require_employee(user: User) -> None:
    if user.role not in ("employee", "both"):
        raise HTTPException(status_code=403, detail="需要员工权限")
