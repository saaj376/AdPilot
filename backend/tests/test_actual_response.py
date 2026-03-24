import json

from fastapi.testclient import TestClient

import main


async def _noop_async() -> None:
    return None


def test_actual_health_response(monkeypatch):
    """Print and assert the real /health JSON response from the FastAPI app."""
    monkeypatch.setattr(main, "startup", _noop_async)
    monkeypatch.setattr(main, "shutdown", _noop_async)

    with TestClient(main.app) as client:
        response = client.get("/health")

    print("\n/health status:", response.status_code)
    print("/health body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_actual_not_found_campaign_response(monkeypatch):
    """Print and assert a real 404 payload for a missing campaign."""
    monkeypatch.setattr(main, "startup", _noop_async)
    monkeypatch.setattr(main, "shutdown", _noop_async)

    with TestClient(main.app) as client:
        response = client.get("/campaigns/does-not-exist")

    print("\n/campaigns/does-not-exist status:", response.status_code)
    print("/campaigns/does-not-exist body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 404
    assert "detail" in response.json()
