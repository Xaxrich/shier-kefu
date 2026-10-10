"""知识库 API 契约。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KbDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    created_at: datetime


class IngestJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    filename: str
    status: str
    vector_ok: bool
    keyword_ok: bool
    metadata_ok: bool
    last_error: str | None
    created_at: datetime
    updated_at: datetime
