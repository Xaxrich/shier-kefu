"""工单 / 消息 API 契约。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)


class TicketPatch(BaseModel):
    category: str | None = None
    close: bool | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_role: str
    body: str
    created_at: datetime


class TicketSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_no: str
    title: str
    status: str
    category: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(BaseModel):
    ticket: TicketSummary
    messages: list[MessageRead]
