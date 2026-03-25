#!/usr/bin/env python3
"""Tiny example script demonstrating the OpenClaw adapter.

Run locally after setting `OPENCLAW_API_BASE` (and optionally `OPENCLAW_API_KEY`).
"""

import asyncio

from freshservice_mcp.openclaw import generate


async def main():
    prompt = "Summarize ticket #12345 in one paragraph"
    resp = await generate(prompt, model="claw-1", max_tokens=128)
    if resp.get("error"):
        print("OpenClaw error:", resp)
    else:
        print("OpenClaw response:", resp)


if __name__ == "__main__":
    asyncio.run(main())
