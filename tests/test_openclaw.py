import pytest

import httpx


@pytest.mark.asyncio
async def test_openclaw_success(monkeypatch):
    # Patch httpx.AsyncClient with a dummy that returns a successful response
    class DummyResponse:
        def __init__(self, data, status=200, text=""):
            self._data = data
            self.status_code = status
            self.text = text

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("error", request=None, response=self)

        def json(self):
            return self._data

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            # Simulate a typical gateway response that contains 'text'
            return DummyResponse({"text": "This is a summary"}, status=200)

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    monkeypatch.setenv("OPENCLAW_API_BASE", "http://localhost:11434")

    from freshservice_mcp.openclaw import generate

    resp = await generate("test prompt", model="claw-1", max_tokens=32)
    assert isinstance(resp, dict)
    assert resp.get("text") == "This is a summary"


@pytest.mark.asyncio
async def test_openclaw_http_error(monkeypatch):
    class DummyResponse:
        def __init__(self, data=None, status=500, text="server error"):
            self._data = data or {}
            self.status_code = status
            self.text = text

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("error", request=None, response=self)

        def json(self):
            return self._data

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            return DummyResponse(status=500, text="internal")

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    monkeypatch.setenv("OPENCLAW_API_BASE", "http://localhost:11434")

    from freshservice_mcp.openclaw import generate

    resp = await generate("test prompt", model="claw-1", max_tokens=32)
    assert isinstance(resp, dict)
    assert resp.get("error") == "openclaw_request_failed"
