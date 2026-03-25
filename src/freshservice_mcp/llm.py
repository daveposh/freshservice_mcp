"""Small LLM adapter that selects OpenClaw, Ollama or OpenAI at runtime.

Usage:
  from freshservice_mcp.llm import generate
  resp = await generate("Summarize this ticket...", model="gpt-4", max_tokens=256)

The function returns a dict with either `{'text': <str>}` on success or an
`{'error': ...}` dict on failure.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from . import openclaw

DEFAULT_TIMEOUT = 15.0


async def _openai_call(prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "missing_openai_api_key"}

    base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    url = f"{base.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, verify=True) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # prefer chat-style message
            text = None
            choices = data.get("choices") or []
            if choices:
                first = choices[0]
                # chat completion
                msg = first.get("message")
                if isinstance(msg, dict):
                    text = msg.get("content")
                else:
                    text = first.get("text")

            if text is None:
                return {"error": "no_text_in_response", "response": data}
            return {"text": text}
        except httpx.HTTPStatusError as e:
            return {
                "error": "openai_http_error",
                "status_code": e.response.status_code,
                "body": e.response.text,
            }
        except Exception as e:
            return {"error": "openai_error", "message": str(e)}


async def _ollama_call(prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
    base = os.getenv("OLLAMA_API_BASE")
    if not base:
        return {"error": "missing_ollama_base"}

    url = f"{base.rstrip('/')}/api/generate?model={model}"
    payload = {"prompt": prompt, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json"}

    api_key = os.getenv("OLLAMA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, verify=True) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Ollama's response shape can vary; try common keys
            if "generations" in data and data["generations"]:
                return {"text": data["generations"][0].get("text")}
            if "text" in data:
                return {"text": data["text"]}
            return {"text": str(data)}
        except httpx.HTTPStatusError as e:
            return {
                "error": "ollama_http_error",
                "status_code": e.response.status_code,
                "body": e.response.text,
            }
        except Exception as e:
            return {"error": "ollama_error", "message": str(e)}


async def generate(
    prompt: str, model: str = "gpt-4", max_tokens: int = 256
) -> Dict[str, Any]:
    """Generate text using the first available provider in order:
    1. OpenClaw (OPENCLAW_API_BASE)
    2. Ollama (OLLAMA_API_BASE)
    3. OpenAI (OPENAI_API_KEY)
    """
    # 1) OpenClaw
    if os.getenv("OPENCLAW_API_BASE"):
        try:
            return await openclaw.generate(prompt, model=model, max_tokens=max_tokens)
        except Exception as e:
            return {"error": "openclaw_integration_failed", "message": str(e)}

    # 2) Ollama
    if os.getenv("OLLAMA_API_BASE"):
        return await _ollama_call(prompt, model, max_tokens)

    # 3) OpenAI
    return await _openai_call(prompt, model, max_tokens)
