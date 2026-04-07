"""Tests for shared middleware."""

import uuid

from fastapi import FastAPI
from starlette.testclient import TestClient


def test_request_id_added_to_response():
    from shared.middleware import RequestIdMiddleware

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/test")
    assert "x-request-id" in resp.headers
    uuid.UUID(resp.headers["x-request-id"])


def test_request_id_preserved_if_sent():
    from shared.middleware import RequestIdMiddleware

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/test", headers={"x-request-id": "custom-id-123"})
    assert resp.headers["x-request-id"] == "custom-id-123"
