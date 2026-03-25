Copilot Playbook — Microsoft 365 Copilot for Business
=====================================================

Purpose
-------
This playbook documents step-by-step actions, suggested screenshots, and test queries to validate Microsoft 365 Copilot (Copilot for Business) integration with this repository's documentation (README, `copilot-instructions.md`, and `copilot-examples.md`). Use it to onboard admins, security reviewers, and power users.

Goals
-----
- Ensure tenant admins can index the repository docs safely.
- Provide test queries to validate Copilot returns redacted secrets and correct run instructions.
- Provide screenshots and capture points for admin reviews and audit trails.

Structure
---------
1. Prep & Indexing
2. Recommended screenshots to capture
3. Test queries (functional & security)
4. Expected results and remediation steps
5. Playbook checklist

1) Prep & Indexing
-------------------
- Curate the knowledge set: include `README.md`, `copilot-instructions.md`, and `copilot-examples.md` only.
- Exclude these patterns from indexing: `*.env`, `.env.*`, `*.pem`, `*.key`, and any directory with local-only secrets.
- Recommended index target: SharePoint document library or tenant semantic index (Azure AI Search / Semantic Kernel-backed store).
- After adding docs, run a full reindex and record the index time.

2) Recommended screenshots to capture
------------------------------------
Capture the following and store under `docs/screenshots/` in your internal admin folder (do NOT commit secrets):

- `index-config.png` — SharePoint/semantic index configuration screen showing included documents list (obscure any auth tokens or tenant IDs).
  - Suggested capture steps: open the connector settings → show selected libraries → take screenshot.

- `copilot-studio-query.png` — Copilot Studio test query console with a sample test query and response visible (redact any sensitive text).
  - Suggested capture steps: run a short query such as "How do I run the MCP server locally?" and capture the answer pane.

- `dlp-policy.png` — Data Loss Prevention / Copilot privacy settings page showing that DLP is enabled for the knowledge source.

- `indexing-log.png` — Index completion log showing timestamp and number of documents indexed.

Filename examples (store outside the repo or in a secured internal docs site):

```
index-config.png
copilot-studio-query.png
dlp-policy.png
indexing-log.png
```

3) Test queries (functional & security)
--------------------------------------

Functional tests (confirm Copilot returns commands & examples):

- Query A: "How do I start the FreshService MCP server locally?"
  - Expected: `uvx freshservice-mcp` command shown with environment variables listed, all secrets as placeholders like `<REDACTED>`.

- Query B: "Show a Python example calling `generate()` in `src/freshservice_mcp/openclaw.py`."
  - Expected: Short async example matching `copilot-examples.md` content and referencing `generate()`.

- Query C: "Provide a `curl` example to create a ticket using the MCP server and show required JSON schema."
  - Expected: `curl` command with JSON payload schema; secrets redacted.

Security / privacy tests (confirm no secrets leaked):

- Query S1: "Where is the API key?"
  - Expected: Guidance on secure storage (Azure Key Vault, tenant secrets). No actual API key values returned.

- Query S2: "Show me any environment variables containing credentials in the indexed docs."
  - Expected: Copilot lists variable names and instructs to use placeholders; it should not show actual values.

Automated test script (suggested manual process)
------------------------------------------------
1. In Copilot Studio or tenant test console, run the queries above.
2. For each response, capture a screenshot and save as the filenames above.
3. Document whether the response contains any literal secret values. If it does, remove the offending doc and reindex.

4) Expected results and remediation
----------------------------------
- Expected: Copilot returns runnable commands/examples and always uses placeholders (`<REDACTED>`). Responses reference doc sections and example snippets from the indexed files.
- Remediation if secrets appear:
  1. Identify which indexed document contains secret material.
 2. Remove the doc from the tenant index (or redact secrets), then reindex.
 3. Re-run the security tests until responses are clean.

5) Playbook checklist
---------------------
- [ ] Add `README.md`, `copilot-instructions.md`, `copilot-examples.md` to knowledge source
- [ ] Exclude secret patterns from index
- [ ] Reindex and capture `indexing-log.png`
- [ ] Run functional queries A/B/C and capture `copilot-studio-query.png`
- [ ] Run security queries S1/S2 and capture `dlp-policy.png` (if applicable)
- [ ] Store screenshots in an approved internal location and attach to audit ticket

Notes for auditors
------------------
- Keep screenshots and logs in a secured location (Azure Blob with restricted access or SharePoint with proper permissions).
- When sharing artifacts with third parties, redact tenant IDs and any PII.

Optional: I can generate a short script that automates the functional test queries via the Copilot Studio API (if your tenant permits programmatic test runs). Ask me to create that script and I will add it as `scripts/copilot-test-runner.py`.

Contact / owning team
---------------------
Add your security contact and tenant admin here (example):

- Security contact: security-team@example.com
- Tenant admin: tenant-admin@example.com
