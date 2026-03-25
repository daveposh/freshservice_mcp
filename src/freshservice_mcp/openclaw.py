"""Minimal OpenClaw integration helper.

This module provides a thin async wrapper to call an OpenClaw-compatible
inference endpoint. It is intentionally small — the project should adapt the
payload/endpoint to match your OpenClaw deployment.

Environment variables:
- `OPENCLAW_API_BASE` (required): base URL, e.g. http://localhost:11434
- `OPENCLAW_API_KEY` (optional): Bearer token for the OpenClaw service
- `OPENCLAW_GENERATE_PATH` (optional): path to the generate endpoint (default: /api/generate)

Return value: parsed JSON response from OpenClaw, or a minimal error dict.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import os

import httpx


DEFAULT_TIMEOUT = 10.0


async def generate(
    prompt: str, *, model: Optional[str] = None, max_tokens: int = 512
) -> Dict[str, Any]:
    """Send a generation request to an OpenClaw endpoint.

    Keep the function small so callers can adapt payload or headers as needed.
    """
    base = os.getenv("OPENCLAW_API_BASE")
    if not base:
        raise RuntimeError("OPENCLAW_API_BASE environment variable is not set")

    path = os.getenv("OPENCLAW_GENERATE_PATH", "/api/generate")
    url = f"{base.rstrip('/')}{path}"

    payload: Dict[str, Any] = {"prompt": prompt, "max_tokens": max_tokens}
    if model:
        payload["model"] = model

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    api_key = os.getenv("OPENCLAW_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, verify=True, follow_redirects=False) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            # return a minimal sanitized error
            return {
                "error": "openclaw_request_failed",
                "status_code": e.response.status_code if e.response is not None else None,
                "message": e.response.text if e.response is not None else str(e),
            }
        except httpx.HTTPError as e:
            return {"error": "openclaw_request_failed", "message": str(e)}
