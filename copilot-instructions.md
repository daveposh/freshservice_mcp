Copilot for Microsoft 365 (Copilot for Business)
===============================================

Purpose
-------
This file contains guidance and ready-to-use instructions to help your organization configure Microsoft 365 Copilot for Business (Office Copilot) to work productively with this repository and the FreshService MCP server.

How Copilot ingests this repo
------------------------------
- Microsoft 365 Copilot uses tenant-configured content connectors and knowledge sources (OneDrive, SharePoint, Exchange, Teams, Dataverse, or a custom semantic index).
- To allow Copilot to use repository content, expose the repository (or selected docs) via an approved knowledge source your tenant admin can index (for example a SharePoint docs library or a semantic store that contains the README and `copilot-instructions.md`).
- Do NOT store secrets (API keys, credentials) in repository files — keep them in tenant secrets or environment variables.

Recommended tenant-admin steps
------------------------------
1. Create a curated knowledge set that includes the repository README and `copilot-instructions.md` (recommended).
2. Configure the Microsoft 365 admin connector or semantic index to include that content and refresh the index.
3. Ensure Copilot usage policies and data handling settings meet your compliance needs (data retention and redaction).

Usage guidance for Copilot prompts
---------------------------------
Use focused prompts that tell Copilot the intent and the safe operational boundaries. Example system/instruction snippet you can include in the indexed docs:

"You are an assistant that helps operators interact with the FreshService MCP server. Use the documented tools and examples in this repository. Never attempt to reveal or request API keys. When explaining operations, provide exact CLI commands and environment variable names but mark secrets as `<REDACTED>`."

Suggested user prompts (examples)
---------------------------------
- "Using the `freshservice-mcp` server in this repo, show how to create a new ticket by calling the MCP tool. Provide the exact `curl` and Python `httpx` steps and environment variables required (redact actual secrets)."
- "Summarize what `src/freshservice_mcp/openclaw.py` does and give an example of how to call its `generate()` helper safely from an async script."
- "List required environment variables to run this server and explain where to store them securely in Microsoft 365 (e.g., Azure Key Vault or tenant secrets)."

Privacy & safety notes
----------------------
- Never index files that contain secrets (for example `.env` files); exclude them from the tenant index.
- When Copilot generates code or commands that reference secrets, instruct it to use placeholders such as `<YOUR_OPENAI_KEY>` and include a short note on how and where to set them securely.
- If your tenant uses conditional access / DLP, work with your security team to ensure the MCP server documentation is allowed in the knowledge sources used by Copilot.

Repository-level suggestions
---------------------------
- Keep `copilot-instructions.md` and `README.md` up-to-date with run instructions and environment variables so Copilot's answers stay accurate.
- Add short, focused examples (CLI and Python) illustrating common tasks — Copilot uses these as authoritative examples when present in the knowledge set.

Admin checklist (short)
----------------------
- [ ] Curate README and `copilot-instructions.md` into tenant knowledge source
- [ ] Verify indexing completed and test queries in Copilot Studio
- [ ] Add a policy that prevents accidental exposure of secrets in responses

Contact / Next steps
--------------------
If you want, I can add a few short, curated example prompts and CLI snippets into `README.md` as well, or create a `copilot-examples.md` with runnable, redacted snippets.
