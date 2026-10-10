"""工单与消息接口。"""

from fastapi import Depends, HTTPException
from pycore.api import APIRouter, success_response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_agent, require_employee
from src.core.errors import BadRequestError, ForbiddenError, LlmNotConfiguredError
from src.db.models import User
from src.db.session import get_session
from src.models.ai import AiReplyResult
from src.models.ticket import MessageCreate, MessageRead, TicketCreate, TicketDetail, TicketPatch, TicketSummary
from src.services import rag_pipeline, ticket_service
from src.services.ticket_service import can_access_ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("/")
async def create_ticket(
    body: TicketCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_employee(user)
    t = await ticket_service.create_ticket(session, user.id, body.title)
    return success_response(TicketSummary.model_validate(t).model_dump())


@router.get("/mine")
async def list_my_tickets(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_employee(user)
    rows = await ticket_service.list_mine(session, user.id)
    data = [TicketSummary.model_validate(t).model_dump() for t in rows]
    return success_response(data)


@router.get("/queue")
async def list_queue(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_agent(user)
    rows = await ticket_service.list_queue(session)
    data = [TicketSummary.model_validate(t).model_dump() for t in rows]
    return success_response(data)


@router.post("/{ticket_id}/ai-reply")
async def ai_reply(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ticket = await ticket_service.get_ticket_detail(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="无权操作此工单")
    try:
        result = await rag_pipeline.run_ai_reply(session, ticket, user)
    except LlmNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=e.message) from e
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    data = AiReplyResult(
        answer=result["answer"],
        intent=result.get("intent"),
        meta=result.get("meta") or {},
    )
    return success_response(data.model_dump())


@router.get("/{ticket_id}")
async def read_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ticket = await ticket_service.get_ticket_detail(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="无权查看此工单")
    msgs = sorted(ticket.messages, key=lambda m: (m.created_at, m.id))
    detail = TicketDetail(
        ticket=TicketSummary.model_validate(ticket),
        messages=[MessageRead.model_validate(m) for m in msgs],
    )
    return success_response(detail.model_dump())


@router.post("/{ticket_id}/messages")
async def post_message(
    ticket_id: int,
    body: MessageCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ticket = await ticket_service.get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not can_access_ticket(user, ticket):
        raise HTTPException(status_code=403, detail="无权操作此工单")
    try:
        msg = await ticket_service.add_message(session, ticket, user, body.content)
        return success_response(MessageRead.model_validate(msg).model_dump())
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message) from e


@router.post("/{ticket_id}/transfer")
async def transfer(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ticket = await ticket_service.get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    try:
        t = await ticket_service.transfer_to_human(session, ticket, user)
        return success_response(TicketSummary.model_validate(t).model_dump())
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message) from e


@router.patch("/{ticket_id}")
async def patch_ticket(
    ticket_id: int,
    body: TicketPatch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_agent(user)
    ticket = await ticket_service.get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    try:
        t = await ticket_service.patch_ticket(
            session,
            ticket,
            category=body.category,
            close=body.close is True,
        )
        return success_response(TicketSummary.model_validate(t).model_dump())
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
