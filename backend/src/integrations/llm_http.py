"""OpenAI 兼容 Embedding / Chat，httpx 显式 trust_env=False，不继承系统代理环境变量。"""

from __future__ import annotations

from typing import Any

import httpx

from src.core.settings import AppSettings, get_settings


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=120.0, trust_env=False)


def _headers(settings: AppSettings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }


def llm_is_configured() -> bool:
    s = get_settings()
    return bool(s.llm_api_key and s.llm_api_key.strip())


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    s = get_settings()
    url = f"{s.llm_base_url.rstrip('/')}/embeddings"
    payload = {"model": s.llm_embedding_model, "input": texts}
    async with _client() as client:
        r = await client.post(url, headers=_headers(s), json=payload)
        r.raise_for_status()
        data = r.json()
    out: list[list[float]] = []
    for item in sorted(data["data"], key=lambda x: x["index"]):
        out.append(item["embedding"])
    return out


async def embed_one(text: str) -> list[float]:
    vecs = await embed_texts([text])
    return vecs[0]


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
) -> str:
    s = get_settings()
    url = f"{s.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": s.llm_chat_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    async with _client() as client:
        r = await client.post(url, headers=_headers(s), json=payload)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"] or ""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
