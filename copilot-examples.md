Copilot Examples (Microsoft 365 Copilot)
======================================

Purpose
-------
Ready-to-use, redacted examples you can index for Microsoft 365 Copilot so teams can ask Copilot how to run and interact with the FreshService MCP server safely.

Run server (redacted)
---------------------
Set environment variables securely (example shows placeholders):

```bash
export FRESHSERVICE_APIKEY="<REDACTED_FRESHSERVICE_APIKEY>"
export FRESHSERVICE_DOMAIN="yourcompany.freshservice.com"

# Run via console script (after `pip install -e .`)
uvx freshservice-mcp --env FRESHSERVICE_APIKEY=$FRESHSERVICE_APIKEY --env FRESHSERVICE_DOMAIN=$FRESHSERVICE_DOMAIN
```

Quick `curl` — create a ticket via MCP (redacted payload)
----------------------------------------------------
Example REST call that your MCP server might expose (adjust endpoints to match your MCP routing):

```bash
curl -s -X POST "http://localhost:8000/tools/create_ticket" \
  -H "Content-Type: application/json" \
  -d '{"subject":"Network outage","description":"Users cannot reach the VPN","priority":1, "auth": {"api_key":"<REDACTED>"}}'
```

Python (async) — call the project's OpenClaw helper (redacted)
-----------------------------------------------------------
```py
import asyncio
from freshservice_mcp.openclaw import generate

async def main():
    resp = await generate("Summarize ticket #12345", model="claw-1", max_tokens=128)
    if resp.get("error"):
        print("OpenClaw error:", resp)
    else:
        print(resp)

asyncio.run(main())
```

Ollama / OpenAI example (curl) — generate a JSON response
---------------------------------------------------------
```bash
curl -sX POST "$OLLAMA_API_BASE/api/generate?model=$OLLAMA_MODEL" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Summarize ticket #12345 in JSON with fields summary,suggested_assignee,priority","max_tokens":256}' | jq .
```

Copilot prompt examples (for users)
----------------------------------
Include these prompt templates in indexed docs so Copilot returns consistent, safe answers.

- System-like instruction (tenant doc snippet):

  "You are an assistant that helps operators interact with the FreshService MCP server. Use examples in this repository. Never request or print API keys — use `<REDACTED>` for secrets. Provide exact commands and a short explanation."

- User prompt examples:
  - "How do I start the MCP server locally? Show the `uvx` command and required environment variables (redact secrets)."
  - "Show a Python example that calls `generate()` in `src/freshservice_mcp/openclaw.py` and handles errors." 
  - "Provide a `curl` example to create a ticket using the MCP server and a JSON payload schema for the `create_ticket` tool."

Admin / tenant prompts (for Copilot Studio)
-----------------------------------------
- "Index the README and `copilot-instructions.md` into the tenant semantic store and verify Copilot can answer: 'How do I run the MCP server locally?'."
- "Test privacy: query 'Where is the API key?' and ensure Copilot returns guidance to use tenant secrets and placeholders, not values."

Indexing guidance (short)
------------------------
- Include `README.md`, `copilot-instructions.md`, and `copilot-examples.md` in your tenant knowledge source (SharePoint or semantic index).
- Exclude `.env`, any `*.pem`/`*.key` files, and `pyproject.toml` if it contains local-only paths.

Testing tips
------------
- After indexing, ask Copilot a test question like: "How do I run the FreshService MCP server?" Confirm the response shows redacted placeholders and exact commands.
- If Copilot returns sensitive data, remove the offending doc from the index and re-index.

If you'd like, I can expand these examples into a `copilot-playbook.md` with step-by-step screenshots and test queries for your security team.
