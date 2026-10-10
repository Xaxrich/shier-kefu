"""B4：QA 向量 / 意图 / 改写 / RAG（RRF）/ 生成。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import BadRequestError, LlmNotConfiguredError
from src.core.settings import get_settings
from src.db.models import KbChunk, QaPair, Ticket, User
from src.integrations import llm_http
from src.services import ticket_service


def _parse_json_loose(text: str) -> dict[str, Any]:
    t = text.strip()
    if "```" in t:
        for part in t.split("```"):
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                t = p
                break
    return json.loads(t)


def _keyword_score(query: str, chunk: str) -> float:
    if not query or not chunk:
        return 0.0
    q = query.strip()
    if len(q) >= 2 and q in chunk:
        return 1000.0
    overlap = len(set(q) & set(chunk))
    return float(overlap)


def _rrf_merge(rank_lists: list[list[int]], k: int) -> list[int]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, cid in enumerate(ranks, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


async def _load_all_chunks(session: AsyncSession) -> list[KbChunk]:
    r = await session.execute(select(KbChunk))
    return list(r.scalars().all())


async def _load_qa_pairs(session: AsyncSession) -> list[QaPair]:
    r = await session.execute(select(QaPair))
    return list(r.scalars().all())


async def run_ai_reply(session: AsyncSession, ticket: Ticket, user: User) -> dict[str, Any]:
    if not llm_http.llm_is_configured():
        raise LlmNotConfiguredError()

    if ticket.status == "closed":
        raise BadRequestError("会话已结束")

    if not ticket_service.can_access_ticket(user, ticket):
        raise BadRequestError("无权操作此工单")

    t2 = await session.execute(
        select(Ticket)
        .options(selectinload(Ticket.messages))
        .where(Ticket.id == ticket.id)
    )
    ticket = t2.scalar_one()
    msgs = sorted(ticket.messages, key=lambda m: (m.created_at, m.id))
    user_msgs = [m for m in msgs if m.sender_role == "user"]
    if not user_msgs:
        raise BadRequestError("请先发送一条消息")
    query = user_msgs[-1].body.strip()
    if not query:
        raise BadRequestError("问题内容为空")

    s = get_settings()
    meta: dict[str, Any] = {"query": query}

    qa_rows = await _load_qa_pairs(session)
    for qa in qa_rows:
        if qa.question_text in query or query in qa.question_text:
            await ticket_service.append_ai_message(session, ticket, qa.answer_text)
            meta["route"] = "qa_substring"
            return {"answer": qa.answer_text, "intent": "clear", "meta": meta}

    q_emb: list[float] | None = None
    try:
        q_emb = await llm_http.embed_one(query)
    except Exception as e:
        meta["embedding_error"] = str(e)

    best_sim = -1.0
    best_answer: str | None = None
    if q_emb is not None:
        for qa in qa_rows:
            if not qa.question_embedding_json:
                continue
            try:
                qv = json.loads(qa.question_embedding_json)
                sim = llm_http.cosine_similarity(q_emb, qv)
            except (json.JSONDecodeError, TypeError):
                continue
            if sim > best_sim:
                best_sim = sim
                best_answer = qa.answer_text
        if best_answer is not None and best_sim >= s.qa_similarity_threshold:
            await ticket_service.append_ai_message(session, ticket, best_answer)
            meta["route"] = "qa_vector"
            meta["qa_similarity"] = best_sim
            return {"answer": best_answer, "intent": "clear", "meta": meta}

    intent_raw = await llm_http.chat_completion(
        [
            {
                "role": "system",
                "content": "你是意图分类器，只输出 JSON，不要其他文字。",
            },
            {
                "role": "user",
                "content": (
                    '判断用户问题是否信息足够给出知识库检索。输出格式：{"intent":"clear"|"vague"|"other",'
                    '"confidence":0.0,"reason":""}。vague 表示需要用户补充关键信息。'
                    f"\n用户问题：{query}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=256,
    )
    try:
        intent_obj = _parse_json_loose(intent_raw)
    except (json.JSONDecodeError, ValueError):
        intent_obj = {"intent": "clear", "confidence": 0.5, "reason": "parse_fallback"}
    intent = str(intent_obj.get("intent", "clear")).lower()
    meta["intent_json"] = intent_obj

    if intent == "vague":
        follow = await llm_http.chat_completion(
            [
                {"role": "system", "content": "你是企业内部客服，用一句中文礼貌反问以澄清用户需求。"},
                {"role": "user", "content": query},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        text = follow.strip() or "能否补充更多背景信息？"
        await ticket_service.append_ai_message(session, ticket, text)
        meta["route"] = "intent_vague"
        return {"answer": text, "intent": "vague", "meta": meta}

    short_mem = [m.body for m in user_msgs[-3:]]
    rewrite_prompt = (
        "根据下列「近期用户原话」压缩成适合知识检索的一句中文查询，不要解释，只输出一行：\n"
        f"近期用户原话：{chr(10).join(short_mem)}"
    )
    rewritten = await llm_http.chat_completion(
        [
            {"role": "system", "content": "你是查询改写助手。"},
            {"role": "user", "content": rewrite_prompt},
        ],
        temperature=0.2,
        max_tokens=200,
    )
    rewritten_q = rewritten.strip().split("\n")[0].strip() or query
    meta["rewritten_query"] = rewritten_q

    chunks = await _load_all_chunks(session)
    vec_ids: list[int] = []
    if q_emb is not None:
        scored: list[tuple[int, float]] = []
        for ch in chunks:
            if not ch.embedding_json:
                continue
            try:
                ev = json.loads(ch.embedding_json)
                sim = llm_http.cosine_similarity(q_emb, ev)
            except (json.JSONDecodeError, TypeError):
                continue
            scored.append((ch.id, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        vec_ids = [cid for cid, _ in scored[: s.vector_top_k]]

    kw_scored: list[tuple[int, float]] = []
    for ch in chunks:
        sc = _keyword_score(rewritten_q, ch.content_text)
        if sc > 0:
            kw_scored.append((ch.id, sc))
    kw_scored.sort(key=lambda x: x[1], reverse=True)
    kw_ids = [cid for cid, _ in kw_scored[: s.keyword_top_k]]

    fused = _rrf_merge([vec_ids, kw_ids], s.rrf_k) if (vec_ids or kw_ids) else []
    top_ids = fused[: s.rerank_top_k]
    id_to_chunk = {c.id: c for c in chunks}
    context_parts: list[str] = []
    for cid in top_ids:
        ch = id_to_chunk.get(cid)
        if ch:
            context_parts.append(f"[片段#{ch.chunk_index}]\n{ch.content_text}")
    context = "\n\n".join(context_parts) if context_parts else "（当前知识库无匹配片段，请基于常识简要说明并建议联系人工。）"
    meta["chunk_ids"] = top_ids

    answer = await llm_http.chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "你是企业内部智能客服。请仅结合「知识片段」作答；若片段不足以得出结论，请明确说明并建议用户联系人工或补充材料。"
                    "回答简洁、专业，使用中文。"
                ),
            },
            {
                "role": "user",
                "content": f"知识片段：\n{context}\n\n用户问题：{rewritten_q}",
            },
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    out = answer.strip() or "抱歉，暂时无法生成回答。"
    await ticket_service.append_ai_message(session, ticket, out)
    meta["route"] = "rag_generate"
    return {"answer": out, "intent": intent, "meta": meta}
