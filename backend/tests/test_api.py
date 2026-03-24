import pytest
from fastapi.testclient import TestClient

import api.campaigns as campaigns_api
import api.reports as reports_api
import main
from core.campaign_context import AgentName, CampaignContext
from models.campaign import CampaignStatus


@pytest.fixture
def client(monkeypatch):
	async def _noop_async():
		return None

	monkeypatch.setattr(main, "startup", _noop_async)
	monkeypatch.setattr(main, "shutdown", _noop_async)

	with TestClient(main.app) as test_client:
		yield test_client


def test_health_endpoint(client):
	response = client.get("/health")

	assert response.status_code == 200
	body = response.json()
	assert body["status"] == "ok"
	assert "app" in body
	assert "version" in body
	assert "model" in body


def test_create_campaign_returns_202(client, monkeypatch, campaign_payload):
	called = {"added": False, "run": False}

	async def _fake_add_active_campaign(campaign_id: str):
		called["added"] = bool(campaign_id)

	async def _fake_run_crew(*args, **kwargs):
		called["run"] = True
		return None

	monkeypatch.setattr(campaigns_api, "add_active_campaign", _fake_add_active_campaign)
	monkeypatch.setattr(campaigns_api, "run_crew", _fake_run_crew)

	response = client.post("/campaigns", json=campaign_payload)

	assert response.status_code == 202
	body = response.json()
	assert "campaign_id" in body
	assert body["status"] == CampaignStatus.PENDING
	assert called["added"] is True
	assert called["run"] is True


def test_campaign_status_returns_404_for_unknown(client, monkeypatch):
	async def _fake_load_context(_campaign_id: str):
		return None

	monkeypatch.setattr(campaigns_api, "load_context", _fake_load_context)

	response = client.get("/campaigns/does-not-exist/status")

	assert response.status_code == 404


def test_report_returns_425_when_not_ready(client, monkeypatch):
	async def _fake_load_context(_campaign_id: str):
		return CampaignContext(
			campaign_id="abc123",
			business_description="A bakery in Austin with custom cakes and catering services.",
			monthly_budget=500.0,
			geo_targets=["Austin, TX"],
			campaign_status=CampaignStatus.RUNNING,
		)

	monkeypatch.setattr(reports_api, "load_context", _fake_load_context)

	response = client.get("/reports/abc123")

	assert response.status_code == 425


def test_report_returns_payload_when_ready(client, monkeypatch):
	async def _fake_load_context(_campaign_id: str):
		context = CampaignContext(
			campaign_id="abc123",
			business_description="A salon in Austin focused on hair and skincare services.",
			monthly_budget=800.0,
			geo_targets=["Austin, TX"],
			campaign_status=CampaignStatus.DONE,
		)
		context.business_profile = {"business_name": "Glow Salon"}
		context.weekly_report = "Week looked strong with CTR gains and better CPC."
		context.performance_data = {"clicks": 120, "ctr": 0.058}
		context.optimizations = {"paused_keywords": ["cheap haircut"]}
		context.set_agent_done(AgentName.REPORT, output={"ok": True})
		return context

	monkeypatch.setattr(reports_api, "load_context", _fake_load_context)

	response = client.get("/reports/abc123")

	assert response.status_code == 200
	body = response.json()
	assert body["campaign_id"] == "abc123"
	assert body["business_name"] == "Glow Salon"
	assert body["weekly_report"]
