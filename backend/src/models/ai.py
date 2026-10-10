"""智能回答接口契约。"""

from typing import Any

from pydantic import BaseModel, Field


class AiReplyResult(BaseModel):
    answer: str
    intent: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
