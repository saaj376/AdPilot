"""Opt-in planning integration test using the configured local model."""
import asyncio
import os
import pytest
from core.campaign_context import CampaignContext
from core.crew import build_crew
from services.llm_client import check_ollama_health

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_planning_flow(monkeypatch):
    if os.getenv("RUN_FULL_AGENT_FLOW_TEST") != "1":
        pytest.skip("Set RUN_FULL_AGENT_FLOW_TEST=1 to run the planning model integration")
    await check_ollama_health()
    async def save(*args):
        pass
    monkeypatch.setattr("core.crew.save_context", save)
    context = CampaignContext(campaign_id="integration-plan", business_description="A bakery selling fresh bread in Austin", monthly_budget=500)
    crew = build_crew(context, asyncio.get_running_loop())
    await asyncio.to_thread(crew.kickoff, inputs={
        "business_description": context.business_description, "monthly_budget": 500,
        "geo_targets": "Austin, TX", "landing_page_url": "https://example.com",
        "video_research": "No video research supplied.",
    })
    assert context.is_complete()
    assert context.weekly_report
