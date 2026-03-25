# Deployment & Secrets Checklist

This checklist covers preparing the `freshservice_mcp` MCP server for deployment and handling secrets safely.

## Build & Packaging

- Pin dependencies in `pyproject.toml` for reproducible builds.
- Build a wheel for releases: `python -m build` (requires `build` package).
- Create a minimal container image (see `Dockerfile`) and scan the image for vulnerabilities.

## Configuration & Secrets

- Required environment variables:
  - `FRESHSERVICE_DOMAIN` (e.g. yourcompany.freshservice.com)
  - `FRESHSERVICE_APIKEY` — store in a secrets manager, never in repo.
  - `OPENAI_API_KEY` / `OPENAI_API_BASE` if using OpenAI.
  - `OLLAMA_API_BASE` / `OLLAMA_API_KEY` if using Ollama.
  - `OPENCLAW_API_BASE` / `OPENCLAW_API_KEY` if using OpenClaw.

- Recommended secret stores:
  - Cloud: Azure Key Vault, AWS Secrets Manager, Google Secret Manager
  - Kubernetes: ExternalSecrets or sealed-secrets
  - CI: repository secrets (GitHub Actions Secrets)

- Do NOT log secrets. Sanitize error messages and avoid printing full upstream responses.

## Runtime & Observability

- Run with a limited service account and network egress rules restricted to Freshservice and LLM endpoints.
- Configure timeouts and retries for all external calls (`httpx` timeout set in code).
- Add request/response sampling for debugging, but redact PII and secrets.

## Security Scans & Tests

- Run static checks and security tooling before release:
  - `ruff check .`
  - `black --check .`
  - `pytest` (unit tests)
  - `bandit -r src -ll`
  - `safety check` (may require pinned `packaging`/`safety` versions)

## Rollout

- Start with a single environment (staging) and monitor error rates and API usage.
- Add rate-limiting and exponential backoff for downstream API calls.

## Incident Response

- Ensure monitoring alerts for high error rates, increased latency, or rate-limit responses.
- Rotate keys immediately if leakage is suspected.

## Notes

- This project intentionally sanitizes upstream error bodies; keep that behavior when adapting code.

## Recent Security Remediation

- Resolved two low-severity static analyzer findings reported by the project security scan:
  - Replaced broad `except Exception:` blocks that swallowed errors with explicit handling and debug-level logging where appropriate.
  - Removed responses that returned raw exception strings to callers; endpoints now return a generic error message and log details at debug level.
- Added a small pytest harness with mocked `httpx.AsyncClient` to exercise create/list endpoints without real credentials.
- Updated CI to run unit tests as a blocking step.

If you prefer to accept any remaining low-risk findings as an exception (with rationale), we can add an entry here and a CI `bandit`/`ruff` ignore rule.
