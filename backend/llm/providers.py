from __future__ import annotations

from typing import Any

import httpx

from config import get_settings


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
