"""工单业务规则与状态流转。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import BadRequestError, ForbiddenError
from src.db.models import Message, Ticket, User

VALID_CATEGORIES = frozenset({"产品咨询", "账号问题", "故障报修", "其他"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Ticket | None:
    r = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
    return r.scalar_one_or_none()


async def create_ticket(session: AsyncSession, employee_user_id: int, title: str) -> Ticket:
    t = Ticket(
        ticket_no=f"tmp-{uuid.uuid4().hex}",
        employee_user_id=employee_user_id,
        status="processing",
        category=None,
        title=title.strip(),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(t)
    await session.flush()
    t.ticket_no = f"T-{_now().year}-{t.id:06d}"
    await session.commit()
    await session.refresh(t)
    return t


async def list_mine(session: AsyncSession, employee_user_id: int) -> list[Ticket]:
    r = await session.execute(
        select(Ticket)
        .where(Ticket.employee_user_id == employee_user_id)
        .order_by(Ticket.updated_at.desc())
    )
    return list(r.scalars().all())


async def list_queue(session: AsyncSession) -> list[Ticket]:
    r = await session.execute(
        select(Ticket).order_by(Ticket.updated_at.desc())
    )
    return list(r.scalars().all())


async def get_ticket_detail(session: AsyncSession, ticket_id: int) -> Ticket | None:
    r = await session.execute(
        select(Ticket)
        .options(selectinload(Ticket.messages))
        .where(Ticket.id == ticket_id)
    )
    return r.scalar_one_or_none()


def can_access_ticket(user: User, ticket: Ticket) -> bool:
    if user.role in ("agent", "both"):
        return True
    return ticket.employee_user_id == user.id


async def add_message(
    session: AsyncSession,
    ticket: Ticket,
    user: User,
    content: str,
) -> Message:
    """本人工单发 user；其余由坐席发 agent。"""
    if ticket.status == "closed":
        raise BadRequestError("会话已结束，无法发送")

    if user.id == ticket.employee_user_id:
        if user.role not in ("employee", "both"):
            raise ForbiddenError("无权操作此工单")
        role = "user"
    else:
        if user.role not in ("agent", "both"):
            raise ForbiddenError("需要坐席权限")
        role = "agent"

    if role == "agent" and ticket.status == "open":
        ticket.status = "processing"

    msg = Message(
        ticket_id=ticket.id,
        sender_role=role,
        body=content.strip(),
        created_at=_now(),
    )
    session.add(msg)
    ticket.updated_at = _now()
    await session.commit()
    await session.refresh(msg)
    await session.refresh(ticket)
    return msg


async def transfer_to_human(session: AsyncSession, ticket: Ticket, user: User) -> Ticket:
    if ticket.employee_user_id != user.id:
        raise ForbiddenError("无权操作此工单")
    if user.role not in ("employee", "both"):
        raise ForbiddenError("仅员工可转人工")
    ticket.status = "open"
    ticket.updated_at = _now()
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def append_ai_message(session: AsyncSession, ticket: Ticket, body: str) -> Message:
    """写入 AI 回复（管线内部使用）。"""
    if ticket.status == "closed":
        raise BadRequestError("会话已结束，无法发送")
    msg = Message(
        ticket_id=ticket.id,
        sender_role="ai",
        body=body.strip(),
        created_at=_now(),
    )
    session.add(msg)
    ticket.updated_at = _now()
    await session.commit()
    await session.refresh(msg)
    await session.refresh(ticket)
    return msg


async def patch_ticket(
    session: AsyncSession,
    ticket: Ticket,
    category: str | None,
    close: bool | None,
) -> Ticket:
    if category is not None:
        if category not in VALID_CATEGORIES:
            raise BadRequestError("分类不在允许列表中")
        ticket.category = category
    if close:
        ticket.status = "closed"
    ticket.updated_at = _now()
    await session.commit()
    await session.refresh(ticket)
    return ticket
