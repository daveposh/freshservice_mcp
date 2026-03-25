import os
import asyncio
from unittest.mock import patch

import pytest

import importlib

# Import server inside tests after setting env to ensure module-level env reads pick up monkeypatch


class MockResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise server.httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


class DummyClient:
    def __init__(self, response: MockResponse):
        self._resp = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self._resp

    async def get(self, *args, **kwargs):
        return self._resp


@pytest.mark.asyncio
async def test_create_ticket_success(monkeypatch):
    # Provide required envs
    monkeypatch.setenv("FRESHSERVICE_DOMAIN", "example.freshservice.test")
    monkeypatch.setenv("FRESHSERVICE_APIKEY", "fakekey")

    # (re)import server so module-level env reads pick up monkeypatched env
    server = importlib.reload(importlib.import_module("freshservice_mcp.server"))

    resp = {"id": 123, "subject": "Test"}
    mock_resp = MockResponse(status_code=201, json_data=resp)

    def client_factory(*args, **kwargs):
        return DummyClient(mock_resp)

    # Patch the AsyncClient used in the server module
    with patch.object(server.httpx, "AsyncClient", client_factory):
        result = await server.create_ticket(
            subject="Test", description="desc", source=1, priority=1, status=2, email="a@b.com"
        )

    assert isinstance(result, str)
    assert "Ticket created successfully" in result


@pytest.mark.asyncio
async def test_get_ticket_fields(monkeypatch):
    monkeypatch.setenv("FRESHSERVICE_DOMAIN", "example.freshservice.test")
    monkeypatch.setenv("FRESHSERVICE_APIKEY", "fakekey")

    server = importlib.reload(importlib.import_module("freshservice_mcp.server"))

    fields = {"fields": ["a", "b"]}
    mock_resp = MockResponse(status_code=200, json_data=fields)

    def client_factory(*args, **kwargs):
        return DummyClient(mock_resp)

    with patch.object(server.httpx, "AsyncClient", client_factory):
        result = await server.get_ticket_fields()

    assert isinstance(result, dict)
    assert result == fields
