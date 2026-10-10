"""知识库上传与入库任务。"""

from fastapi import Depends, File, HTTPException, UploadFile
from pycore.api import APIRouter, success_response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.errors import BadRequestError
from src.db.models import KbDocument, User
from src.db.session import get_session
from src.models.kb import IngestJobRead, KbDocumentRead
from src.services import kb_service

router = APIRouter(prefix="/api/kb", tags=["knowledge"])


@router.post("/upload")
async def upload_markdown(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    name = file.filename or "upload.md"
    try:
        doc, job = await kb_service.save_markdown_upload(session, user.id, name, raw)
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=e.message) from e

    payload = {
        "document": KbDocumentRead.model_validate(doc).model_dump(),
        "job": _job_to_read(job, doc.original_filename),
    }
    return success_response(payload)


def _job_to_read(job, filename: str) -> dict:
    return IngestJobRead(
        id=job.id,
        document_id=job.document_id,
        filename=filename,
        status=job.status,
        vector_ok=job.vector_ok,
        keyword_ok=job.keyword_ok,
        metadata_ok=job.metadata_ok,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    ).model_dump()


@router.get("/documents")
async def list_documents(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _ = user
    rows = await kb_service.list_documents(session)
    data = [KbDocumentRead.model_validate(d).model_dump() for d in rows]
    return success_response(data)


@router.get("/jobs")
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _ = user
    rows = await kb_service.list_jobs_with_filename(session)
    data = [_job_to_read(job, fn) for job, fn in rows]
    return success_response(data)


@router.post("/jobs/{job_id}/retry")
async def retry_ingest(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _ = user
    job = await kb_service.get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status == "success":
        raise HTTPException(status_code=400, detail="已成功入库，无需重试")
    job = await kb_service.retry_job(session, job)
    doc = await session.get(KbDocument, job.document_id)
    fn = doc.original_filename if doc else ""
    return success_response(_job_to_read(job, fn))
