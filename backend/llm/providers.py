from __future__ import annotations

from typing import Any

import httpx

from config import get_settings


async def groq_chat_completion(*, prompt: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("groq_key_missing")

    payload = {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "max_tokens": 1800,
        "messages": [
            {
                "role": "system",
                "content": "You are a municipal planning advisor. Use only provided values. Do not invent numeric values.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds * 2) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        res.raise_for_status()
        body = res.json()
    return str(body["choices"][0]["message"]["content"])


async def bitnet_chat_completion(*, prompt: str) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "model": settings.bitnet_model,
        "temperature": 0.3,
        "max_tokens": 1800,
        "messages": [
            {
                "role": "system",
                "content": "You are a municipal planning advisor. Use only provided values. Do not invent numeric values.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    base = settings.bitnet_api_base.rstrip("/")
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds * 2) as client:
        res = await client.post(
            f"{base}/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        res.raise_for_status()
        body = res.json()
    return str(body["choices"][0]["message"]["content"])


async def check_bitnet_health(settings=None) -> dict[str, Any]:
    local_settings = settings or get_settings()
    base = local_settings.bitnet_api_base.rstrip("/")
    if not base:
        return {"reachable": False, "models": [], "error": "bitnet_api_base_missing"}

    headers = {"Content-Type": "application/json"}
    if (local_settings.bitnet_api_key or "").strip():
        headers["Authorization"] = f"Bearer {local_settings.bitnet_api_key}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{base}/models", headers=headers)
            res.raise_for_status()
            body = res.json()

        model_ids: list[str] = []
        for item in body.get("data", []):
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                model_ids.append(model_id)

        return {"reachable": True, "models": model_ids, "error": None}
    except Exception as exc:
        return {"reachable": False, "models": [], "error": str(exc)}
