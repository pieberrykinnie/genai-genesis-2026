from __future__ import annotations

import argparse
import asyncio
import json
import os
import time

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_MODEL = "HF1BitLLM/Llama3-8B-1.58-100B-tokens"


async def _get_models(client: httpx.AsyncClient, base_url: str, headers: dict[str, str]) -> tuple[bool, list[str], str | None]:
    try:
        response = await client.get(f"{base_url}/models", headers=headers)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return False, [], str(exc)

    model_ids: list[str] = []
    for item in payload.get("data", []):
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id.strip():
            model_ids.append(model_id)
    return True, model_ids, None


async def _chat_completion(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    model: str,
    response_format: dict[str, object] | None = None,
) -> tuple[bool, dict[str, object] | None, str | None, float]:
    payload: dict[str, object] = {
        "model": model,
        "temperature": 0,
        "max_tokens": 64,
        "messages": [
            {"role": "system", "content": "Return concise answers."},
            {"role": "user", "content": "Return valid JSON with key hello and value world."},
        ],
    }
    if response_format is not None:
        payload["response_format"] = response_format

    start = time.perf_counter()
    try:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        body = response.json()
        return True, body, None, elapsed_ms
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return False, None, str(exc), elapsed_ms


def _extract_content(body: dict[str, object] | None) -> str:
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return str(content or "")


def _is_json_text(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except Exception:
        return False


async def run_probe(base_url: str, model: str, timeout_seconds: float, api_key: str) -> int:
    base_url = base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        models_ok, model_ids, models_error = await _get_models(client, base_url, headers)
        print(f"models_reachable={models_ok}")
        if model_ids:
            print(f"models={model_ids}")
        if models_error:
            print(f"models_error={models_error}")
        if not models_ok:
            return 1

        basic_ok, basic_body, basic_error, basic_ms = await _chat_completion(client, base_url, headers, model)
        print(f"basic_chat_ok={basic_ok} latency_ms={basic_ms:.1f}")
        if basic_error:
            print(f"basic_chat_error={basic_error}")
            return 1

        object_ok, object_body, object_error, object_ms = await _chat_completion(
            client,
            base_url,
            headers,
            model,
            response_format={"type": "json_object"},
        )
        object_content = _extract_content(object_body)
        object_is_json = _is_json_text(object_content)
        print(f"json_object_ok={object_ok and object_is_json} latency_ms={object_ms:.1f}")
        if object_error:
            print(f"json_object_error={object_error}")
        if not object_ok or not object_is_json:
            return 2

        schema_ok, _, schema_error, schema_ms = await _chat_completion(
            client,
            base_url,
            headers,
            model,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "hello_schema",
                    "schema": {
                        "type": "object",
                        "properties": {"hello": {"type": "string"}},
                        "required": ["hello"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        )
        print(f"json_schema_ok={schema_ok} latency_ms={schema_ms:.1f}")
        if schema_error:
            print(f"json_schema_error={schema_error}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe local BitNet OpenAI-compatible server capabilities.")
    parser.add_argument("--base-url", default=os.getenv("BITNET_API_BASE", DEFAULT_BASE_URL), help="OpenAI-compatible /v1 base URL")
    parser.add_argument("--model", default=os.getenv("BITNET_MODEL", DEFAULT_MODEL), help="Model identifier to use")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds")
    parser.add_argument("--api-key", default=os.getenv("BITNET_API_KEY", "bitnet-local"), help="Optional API key")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run_probe(args.base_url, args.model, args.timeout, args.api_key))


if __name__ == "__main__":
    raise SystemExit(main())
