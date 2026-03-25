# FreshService MCP Server

## Overview

A powerful MCP (Model Context Protocol) server implementation that seamlessly integrates with Freshservice, enabling AI models to interact with Freshservice modules and perform various IT service management operations. This integration bridge empowers your AI assistants to manage and resolve IT service tickets, streamlining your support workflow.

## Key Features

- **Enterprise-Grade Freshservice Integration**: Direct, secure communication with Freshservice API endpoints
- **AI Model Compatibility**: Enables Claude and other AI models to execute service desk operations through Freshservice
- **Automated ITSM Management**: Efficiently handle ticket creation, updates, responses, and asset management
- **Workflow Acceleration**: Reduce manual intervention in routine IT service tasks

## Supported Freshservice Modules

**This MCP server currently supports operations across a wide range of Freshservice modules:**

- Tickets
- Changes
- Conversations
- Products
- Requesters
- Agents
- Agent Groups
- Requester Groups
- Canned Responses
- Canned Response Folders
- Workspaces
- Solution Categories
- Solution Folders
- Solution Articles

## Components & Tools

### Ticket Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_ticket` | Create new service tickets | `subject`, `description`, `source`, `priority`, `status`, `email` |
| `update_ticket` | Update existing tickets | `ticket_id`, `updates` |
| `delete_ticket` | Remove tickets | `ticket_id` |
| `filter_tickets` | Find tickets matching criteria | `query` |
| `get_ticket_fields` | Retrieve ticket field definitions | None |
| `get_tickets` | List all tickets with pagination | `page`, `per_page` |
| `get_ticket_by_id` | Retrieve single ticket details | `ticket_id` |

### Change Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_changes` | List all changes with pagination | `page`, `per_page`, `query` |
| `filter_changes` | Filter changes with advanced queries | `query`, `page`, `per_page` |
| `get_change_by_id` | Retrieve single change details | `change_id` |
| `create_change` | Create new change request | `requester_id`, `subject`, `description`, `priority`, `impact`, `status`, `risk`, `change_type` |
| `update_change` | Update existing change | `change_id`, `change_fields` |
| `close_change` | Close change with result explanation | `change_id`, `change_result_explanation` |
| `delete_change` | Remove change | `change_id` |
| `get_change_tasks` | Get tasks for a change | `change_id` |
| `create_change_note` | Add note to change | `change_id`, `body` |

#### 🚨 Important: Query Syntax for Filtering

When using `get_changes` or `filter_changes` with the `query` parameter, the query string must be wrapped in double quotes for the Freshservice API to work correctly:

✅ **CORRECT**: `"status:3"`, `"approval_status:1 AND status:<6"`  
❌ **WRONG**: `status:3` (will cause 500 Internal Server Error)

**Common Query Examples:**

- `"status:3"` - Changes awaiting approval
- `"approval_status:1"` - Approved changes
- `"approval_status:1 AND status:<6"` - Approved changes that are not closed
- `"planned_start_date:>'2025-07-14'"` - Changes starting after specific date
- `"status:3 AND priority:1"` - High priority changes awaiting approval

### Conversation Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_ticket_note` | Add a note to a ticket | `ticket_id`, `body` |
| `send_ticket_reply` | Send a reply to a ticket | `ticket_id`, `body`, `from_email` |
| `list_all_ticket_conversation` | List all conversations for a ticket | `ticket_id` |
| `update_ticket_conversation` | Update a conversation | `conversation_id`, `updates` |

### Product Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_all_products` | List all products | None |
| `get_products_by_id` | Get product by ID | `id` |
| `create_product` | Create a new product | `name`, `asset_type_id`, `manufacturer`, `status`, `mode_of_procurement`, `description` |
| `update_product` | Update an existing product | `id`, `product_fields` |

### Requester Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_requester` | Create a new requester | `first_name`, `primary_email` |
| `get_requester_id` | Get requester by ID | `id` |
| `update_requester` | Update an existing requester | `requester_id`, `updates` |
| `list_all_requester_fields` | List all requester fields | None |
| `filter_requesters` | Filter requesters based on query | `query` |

### Agent Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_agent` | Create a new agent | `first_name`, `email` |
| `get_agent` | Get agent by ID | `agent_id` |
| `get_all_agents` | List all agents | `page`, `per_page` |
| `update_agent` | Update an existing agent | `agent_id`, `updates` |
| `get_agent_fields` | Retrieve agent field definitions | None |
| `filter_agents` | Filter agents based on query | `query` |

### Agent Groups Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_all_agent_groups` | List all agent groups | None |
| `getAgentGroupById` | Get agent group by ID | `id` |
| `create_group` | Create a new agent group | `group_fields` |
| `update_group` | Update an existing agent group | `group_id`, `group_fields` |

### Requester Groups Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_requester_groups` | List all requester groups | None |
| `get_requester_groups_by_id` | Get requester group by ID | `id` |
| `create_requester_group` | Create a new requester group | `name`, `description` |
| `update_requester_group` | Update an existing requester group | `id`, `updates` |
| `list_requester_group_members` | List members of a requester group | `group_id` |
| `add_requester_to_group` | Add a requester to a group | `group_id`, `requester_id` |

### Canned Responses Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_all_canned_response` | List all canned responses | None |
| `get_canned_response` | Get canned response by ID | `id` |

### Canned Response Folders Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_all_canned_response_folder` | List all canned response folders | None |
| `list_canned_response_folder` | List canned response folder by ID | `id` |

### Workspace Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_all_workspaces` | List all workspaces | None |
| `get_workspace` | Get workspace by ID | `id` |

### Solution Categories Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_all_solution_category` | List all solution categories | None |
| `get_solution_category` | Get solution category by ID | `id` |
| `create_solution_category` | Create a new solution category | `name`, `description`, `workspace_id` |
| `update_solution_category` | Update an existing solution category | `category_id`, `updates` |

### Solution Folders Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_list_of_solution_folder` | List folders under a solution category | `category_id` |
| `create_solution_folder` | Create a new folder | `name`, `category_id`, `department_ids`, `visibility`, `description` |
| `update_solution_folder` | Update an existing folder | `id`, `updates` |

### Solution Articles Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_list_of_solution_article` | List articles in a solution folder | `folder_id` |
| `create_solution_article` | Create a new article | `title`, `description`, `folder_id`, `article_type`, `status`, `tags`, `keywords`, `review_date` |
| `update_solution_article` | Update an existing article | `article_id`, `updates` |
| `get_solution_article` | Get article by ID | `id` |
| `publish_solution_article` | Publish a solution article | `article_id` |

## Getting Started

## LLM Integration (OpenAI & Ollama)

This project does not require an LLM by default, but if you integrate components that call an LLM you can point them to OpenAI (recommended) or an Ollama server.

- OpenAI (recommended):

  - Set your API key and optional base URL:

    ```bash
    export OPENAI_API_KEY="sk-..."
    # Optional: point to a proxy or custom base
    export OPENAI_API_BASE="https://api.openai.com/v1"
    ```

  - Quick curl test:

    ```bash
    curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
      "$OPENAI_API_BASE/models" | jq .
    ```

- Ollama (alternative):

  - For a local Ollama daemon or Ollama Cloud, set the base URL and model name used by your client:

    ```bash
    export OLLAMA_API_BASE="http://localhost:11434"
    export OLLAMA_MODEL="gpt4all"   # replace with your model name
    ```

  - Quick curl test (example generate endpoint):

    ```bash
    curl -sX POST "$OLLAMA_API_BASE/api/generate?model=$OLLAMA_MODEL" \
      -H "Content-Type: application/json" \
      -d '{"prompt":"Hello from Ollama","max_tokens":128}' | jq .
    ```

Notes:

- Use `OPENAI_API_BASE` when you need to point OpenAI SDKs to a proxy, Azure OpenAI endpoint, or private gateway.
- Ollama compatibility varies; prefer OpenAI-hosted endpoints if you need the broadest SDK support.

- OpenClaw (internal / alternative LLM gateway):

  - If you use an OpenClaw-compatible gateway, the project includes a tiny
    helper at `src/freshservice_mcp/openclaw.py` which calls a configurable
    generate endpoint. Configure the environment variables below:

    ```bash
    export OPENCLAW_API_BASE="http://localhost:11434"
    export OPENCLAW_API_KEY="<your_key>"           # optional
    export OPENCLAW_GENERATE_PATH="/api/generate" # optional
    ```

  - Example usage (python async):

    ```py
    from freshservice_mcp.openclaw import generate

    result = await generate("Summarize the ticket: ...", model="claw-1", max_tokens=256)
    print(result)
    ```

  - The helper returns the parsed JSON response or a minimal error dict on failure.


See the full deployment checklist and secrets guidance in [DEPLOYMENT.md](DEPLOYMENT.md).

### Prerequisites

- A Freshservice account (sign up at [freshservice.com](https://www.freshservice.com))
- Freshservice API key
- `uvx` installed (`pip install uv` or `brew install uv`)
- Python 3.10 or higher

### Configuration

1. **Generate your Freshservice API key from the admin panel:**
   - Navigate to Profile Settings → API Settings
   - Copy your API key for configuration

2. **Set up your domain and authentication details as shown below**

### Usage with Claude Desktop

1. Install Claude Desktop from the [official website](https://claude.ai/desktop)
2. Add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "freshservice-mcp": {
      "command": "uvx",
      "args": [
        "freshservice-mcp"
      ],
      "env": {
        "FRESHSERVICE_APIKEY": "<YOUR_FRESHSERVICE_APIKEY>",
        "FRESHSERVICE_DOMAIN": "<YOUR_FRESHSERVICE_DOMAIN>"
      }
    }
  }
}
```

**Important**: Replace `<YOUR_FRESHSERVICE_APIKEY>` with your actual API key and `<YOUR_FRESHSERVICE_DOMAIN>` with your domain (e.g., `yourcompany.freshservice.com`)

### Usage with uvx

```bash
# Install dependencies
pip install uv

# Run the server
uvx freshservice-mcp --env FRESHSERVICE_APIKEY=<your_api_key> --env FRESHSERVICE_DOMAIN=<your_domain>
```

### Running in VS Code

To run and debug the MCP server from VS Code using the project's virtual environment:

1. Select the project's Python interpreter (Command Palette → **Python: Select Interpreter**) and pick the virtualenv Python (for example: `${workspaceFolder}/.venv311/bin/python`).

2. Create a `.env` file at the repository root or set environment variables in your system. Example `.env`:

```
FRESHSERVICE_APIKEY=<your_api_key>
FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
```

3. Add a VS Code debug configuration at `.vscode/launch.json` (create the file if it doesn't exist):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run MCP server",
      "type": "python",
      "request": "launch",
      "module": "freshservice_mcp.server",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

4. Start the configuration `Run MCP server` from the Run view. Your server will start in the integrated terminal and use the environment variables from `.env`.

Notes:
- The project defines a console script `freshservice-mcp` (see `pyproject.toml`) but running via the module (`freshservice_mcp.server`) works reliably from the VS Code debugger.
- If you prefer to run the packaged entry point, install the package into your venv (`pip install -e .`) and run the `freshservice-mcp` command from the terminal.

## Example Operations

Once configured, you can ask Claude to perform operations like:

**Tickets:**
- "Create a new incident ticket with subject 'Network connectivity issue in Marketing department' and description 'Users unable to connect to Wi-Fi in Marketing area', set priority to high"
- "List all critical incidents reported in the last 24 hours"
- "Update ticket #12345 status to resolved"

**Changes:**
- "Create a change request for scheduled server maintenance next Tuesday at 2 AM"
- "Update the status of change request #45678 to 'Approved'"
- "Close change #5092 with result explanation 'Successfully deployed to production. All tests passed.'"
- "List all pending changes"

**Other Operations:**
- "Show asset details for laptop with asset tag 'LT-2023-087'"
- "Create a solution article about password reset procedures"

## Testing

For testing purposes, you can start the server manually:

```bash
uvx freshservice-mcp --env FRESHSERVICE_APIKEY=<your_api_key> --env FRESHSERVICE_DOMAIN=<your_domain>
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Using with Ollama (examples)

If you are running a local Ollama daemon (or Ollama Cloud), set the base URL and model name and then call the generate endpoint.

1) Environment variables

```bash
export OLLAMA_API_BASE="http://localhost:11434"
export OLLAMA_MODEL="gpt4all"  # replace with your model
# Optional: if your Ollama instance expects an API key
export OLLAMA_API_KEY="<your_key>"
```

2) Quick curl example

```bash
curl -sX POST "$OLLAMA_API_BASE/api/generate?model=$OLLAMA_MODEL" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Summarize the ticket: ...","max_tokens":128}' | jq .
```

3) Python (async) example — use the project's adapter:

```py
import asyncio
from freshservice_mcp.llm import generate

async def main():
    # Ensure OLLAMA_API_BASE and OLLAMA_MODEL are set in your environment
    resp = await generate("Summarize this ticket...", model="gpt4all", max_tokens=128)
    print(resp)

asyncio.run(main())
```

Notes:
- The project's `generate()` helper will prefer OpenClaw if `OPENCLAW_API_BASE` is set, then Ollama if `OLLAMA_API_BASE` is set, otherwise OpenAI.
- When debugging in VS Code, add `OLLAMA_API_BASE` and `OLLAMA_MODEL` to your `.env` (or `envFile`) so the debugger picks them up.

## Example Operations — Ollama

If you are driving the MCP server with an Ollama model, here are concise prompt examples that work well with the project's adapters. Send these as the model prompt (or include them inside a structured system/instruction message):

- "Summarize ticket #12345 in one paragraph and propose a short, actionable resolution and assignee. Include estimated priority."
- "Create an incident ticket: subject 'Email outage in Sales', description 'Several users cannot access email; steps tried: restart client, cleared cache', suggest priority and tags, and provide the JSON payload for the `create_ticket` tool."
- "List all open high-priority incidents and provide a one-line suggested owner for each. Respond in JSON array format with fields: ticket_id, subject, suggested_owner."

Tip: Ollama models often respond more reliably when you explicitly request machine-readable output (JSON) and show a short example of the expected schema in the prompt.

### Prompt templates and JSON output (Ollama)

Below are compact prompt patterns that work well with Ollama models and the project's adapters. They encourage consistent, machine-readable replies that your MCP tools can consume directly.

- Simple system + user template:

```text
System: You are an assistant that outputs a single JSON object describing the result.
User: Summarize ticket #12345 in one paragraph, propose an assignee, and include an estimated priority.

Expected JSON schema:
{
  "summary": "<one-paragraph-summary>",
  "suggested_assignee": "<email_or_name>",
  "estimated_priority": <1|2|3|4>
}
```

- JSON-array response example (when listing items):

```text
User: List all open high-priority incidents and return a JSON array with fields: ticket_id, subject, suggested_owner

Expected output example:
[
  {"ticket_id":12345, "subject":"Email outage", "suggested_owner":"ops@example.com"},
  {"ticket_id":12346, "subject":"VPN failure", "suggested_owner":"netadmin@example.com"}
]
```

- Curl example (explicitly request JSON):

```bash
curl -sX POST "$OLLAMA_API_BASE/api/generate?model=$OLLAMA_MODEL" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"System: You are an assistant that outputs JSON.\nUser: Summarize ticket #12345 as JSON.","max_tokens":256}' | jq .
```

Notes:
- If your Ollama instance requires authentication, include the `OLLAMA_API_KEY` in the `Authorization: Bearer <key>` header.
- When integrating into the MCP flow, validate the model output against the expected schema before calling tool functions (defensive parsing avoids accidental malformed calls).

## Using with GitHub Copilot

You can ask GitHub Copilot (or Copilot Chat) to generate helper code snippets that interact with Freshservice or the MCP server. Below are example Copilot prompts and a minimal starter snippet you can store in your repo for quick edits.

Copilot prompt (example):

"Write an async Python function `create_incident(subject, description)` that uses `httpx` to call Freshservice's REST API to create a ticket. Use `FRESHSERVICE_APIKEY` and `FRESHSERVICE_DOMAIN` from environment variables and return the created ticket JSON. Include proper error handling and a short docstring."

Expected minimal generated snippet (edit as needed):

```py
import os
import httpx

async def create_incident(subject: str, description: str) -> dict:
  """Create an incident ticket in Freshservice and return the response JSON."""
  api_key = os.environ["FRESHSERVICE_APIKEY"]
  domain = os.environ["FRESHSERVICE_DOMAIN"]
  url = f"https://{domain}/api/v2/tickets"
  headers = {"Content-Type": "application/json"}
  auth = (api_key, "X")
  payload = {"subject": subject, "description": description, "status": 2}
  async with httpx.AsyncClient() as client:
    r = await client.post(url, json={"helpdesk_ticket": payload}, auth=auth, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()
```

You can prompt Copilot to adapt this snippet to call MCP tools directly (for example, by wrapping it to send the JSON payload to your local MCP server or by generating an MCP-based client). Copilot excels at producing these adapters quickly — provide the package/module names and a one-line example of the call you expect.

## Troubleshooting

- **Verify your Freshservice API key and domain are correct**
- **Ensure proper network connectivity to Freshservice servers**
- **Check API rate limits and quotas**
- **Verify the `uvx` command is available in your PATH**
- **Query syntax for filtering must be wrapped in double quotes** (see Change Management section above)

## License

This MCP server is licensed under the MIT License. See the [LICENSE](LICENSE) file in the project repository for full details.

## Additional Resources

- [Freshservice API Documentation](https://api.freshservice.com/)
- [Claude Desktop Integration Guide](https://docs.anthropic.com/claude/docs/claude-desktop)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

---

<!-- Footer removed -->
