"""知识库上传与入库桩逻辑。"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import BadRequestError
from src.core.settings import BACKEND_ROOT, get_settings
from src.db.models import KbChunk, KbDocument, KbIngestJob
from src.integrations import llm_http


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sanitize_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1] or "upload.md"
    base = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", base)
    if not base or base == ".md":
        base = "upload.md"
    elif not base.lower().endswith(".md"):
        base = f"{base}.md"
    return base[:200]


def _chunk_markdown(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks


async def index_kb_document_for_rag(session: AsyncSession, doc: KbDocument) -> None:
    """为文档写入 kb_chunks；若已配置 LLM 则写入向量 JSON。"""
    await session.execute(delete(KbChunk).where(KbChunk.document_id == doc.id))
    path = (BACKEND_ROOT / doc.stored_relative_path).resolve()
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    parts = _chunk_markdown(text)
    use_emb = llm_http.llm_is_configured()
    for i, part in enumerate(parts):
        emb_json: str | None = None
        if use_emb:
            try:
                vec = await llm_http.embed_one(part[:8000])
                emb_json = json.dumps(vec)
            except Exception:
                emb_json = None
        session.add(
            KbChunk(
                document_id=doc.id,
                chunk_index=i,
                content_text=part,
                embedding_json=emb_json,
            )
        )
    await session.flush()


async def ingest_stub(session: AsyncSession, job: KbIngestJob) -> None:
    """B3：同步桩——校验文件可读即标记三栏成功；B4 替换为真实向量/关键词/元数据流水线。"""
    job.status = "processing"
    job.updated_at = _now()
    await session.flush()

    doc = await session.get(KbDocument, job.document_id)
    if doc is None:
        job.status = "failed"
        job.last_error = "文档记录不存在"
        job.updated_at = _now()
        return

    path = (BACKEND_ROOT / doc.stored_relative_path).resolve()

    if not path.is_file():
        job.status = "failed"
        job.last_error = "磁盘文件不存在"
        job.updated_at = _now()
        return

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        job.status = "failed"
        job.last_error = f"读取失败: {e}"
        job.updated_at = _now()
        return

    if not text.strip():
        job.status = "failed"
        job.last_error = "文件为空"
        job.updated_at = _now()
        return

    _ = text.split("\n", 1)[0][:120]
    job.status = "success"
    job.vector_ok = True
    job.keyword_ok = True
    job.metadata_ok = True
    job.last_error = None
    job.updated_at = _now()


async def save_markdown_upload(
    session: AsyncSession,
    user_id: int,
    original_name: str,
    raw: bytes,
) -> tuple[KbDocument, KbIngestJob]:
    s = get_settings()
    if len(raw) > s.kb_max_upload_bytes:
        raise BadRequestError(f"文件超过上限 {s.kb_max_upload_bytes} 字节")

    safe = sanitize_filename(original_name)
    if not safe.lower().endswith(".md"):
        raise BadRequestError("仅支持 .md 文件")

    doc = KbDocument(
        original_filename=safe,
        stored_relative_path="",
        byte_size=0,
        created_by_user_id=user_id,
        created_at=_now(),
    )
    session.add(doc)
    await session.flush()

    sub = Path(s.kb_storage_dir) / f"{doc.id}_{safe}"
    doc.stored_relative_path = sub.as_posix()
    dest = (BACKEND_ROOT / sub).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    doc.byte_size = len(raw)

    job = KbIngestJob(
        document_id=doc.id,
        status="pending",
        vector_ok=False,
        keyword_ok=False,
        metadata_ok=False,
        last_error=None,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(job)
    await session.flush()

    await ingest_stub(session, job)
    await index_kb_document_for_rag(session, doc)
    await session.commit()
    await session.refresh(doc)
    await session.refresh(job)
    return doc, job


async def list_documents(session: AsyncSession) -> list[KbDocument]:
    r = await session.execute(select(KbDocument).order_by(KbDocument.created_at.desc()))
    return list(r.scalars().all())


async def list_jobs_with_filename(session: AsyncSession) -> list[tuple[KbIngestJob, str]]:
    r = await session.execute(
        select(KbIngestJob, KbDocument.original_filename)
        .join(KbDocument, KbIngestJob.document_id == KbDocument.id)
        .order_by(KbIngestJob.created_at.desc())
    )
    rows = r.all()
    return [(job, fn) for job, fn in rows]


async def get_job(session: AsyncSession, job_id: int) -> KbIngestJob | None:
    return await session.get(KbIngestJob, job_id)


async def retry_job(session: AsyncSession, job: KbIngestJob) -> KbIngestJob:
    job.vector_ok = False
    job.keyword_ok = False
    job.metadata_ok = False
    job.last_error = None
    await ingest_stub(session, job)
    doc = await session.get(KbDocument, job.document_id)
    if doc:
        await index_kb_document_for_rag(session, doc)
    await session.commit()
    await session.refresh(job)
    return job
