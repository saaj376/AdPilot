import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import core.crew as pipeline
import api.ws as ws_api
import main
from core.campaign_context import AgentName, CampaignContext
from models.campaign import CampaignCreateRequest, CampaignStatus


def context():
    return CampaignContext(campaign_id="regression", business_description="A local bakery serving Austin", monthly_budget=500)


@pytest.mark.parametrize("raw", [
    '{"ad_groups":{"Bakery":{"headlines":["Fresh {bread}"]}}}',
    'Final Answer: ```json\n{"ad_groups":{"Bakery":{"headlines":["Fresh {bread}"]}}}\n```',
])
def test_json_parser_keeps_outer_structure(raw):
    assert pipeline._parse_agent_output(SimpleNamespace(raw=raw)) == {
        "ad_groups": {"Bakery": {"headlines": ["Fresh {bread}"]}}
    }


def test_invalid_output_is_not_success():
    with pytest.raises(ValueError):
        pipeline._parse_agent_output(SimpleNamespace(raw="Sorry, the service failed"))


@pytest.mark.parametrize("changes", [
    {"business_description": " " * 30}, {"monthly_budget": float("inf")},
    {"geo_targets": []}, {"geo_targets": ["   "]},
])
def test_reject_invalid_campaign_inputs(changes):
    payload = dict(business_description="A local bakery serving Austin", monthly_budget=500)
    with pytest.raises(ValueError):
        CampaignCreateRequest(**{**payload, **changes})


@pytest.mark.asyncio
async def test_task_callback_isolated_and_persisted(monkeypatch):
    saved = []

    async def save(_id, value):
        saved.append(value.model_dump(mode="json"))

    monkeypatch.setattr(pipeline, "save_context", save)
    first, second = context(), context()
    crew = pipeline.build_crew(first, asyncio.get_running_loop())
    other = pipeline.build_crew(second, asyncio.get_running_loop())
    assert crew.step_callback is None
    assert crew.agents[0] is not other.agents[0]
    assert crew.tasks[0] is not other.tasks[0]
    assert crew.tasks[1].context[0] is crew.tasks[0]
    first.set_agent_running(AgentName.RESEARCH)
    await asyncio.to_thread(crew.task_callback, SimpleNamespace(
        agent="Business Research Specialist", raw='{"business_name":"Bakery"}'))
    assert first.business_profile == {"business_name": "Bakery"}
    assert second.business_profile == {}
    assert saved[-1]["agent_states"][AgentName.KEYWORD]["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_qa_rejection_stops_plan(monkeypatch):
    value = context()
    value.set_agent_running(AgentName.QA)
    crew = pipeline.build_crew(value, asyncio.get_running_loop())
    with pytest.raises(ValueError, match="plan stopped"):
        await asyncio.to_thread(crew.task_callback, SimpleNamespace(
            agent="Google Ads Policy Compliance Reviewer", raw='{"overall_approved":false}'))
    assert value.agent_states[AgentName.REPORT].status == "IDLE"


@pytest.mark.asyncio
async def test_failed_worker_marks_running_agent_and_finishes_stream(monkeypatch):
    saved = []
    async def save(_id, value):
        saved.append(value.model_dump(mode="json"))
    class BrokenCrew:
        def kickoff(self, **kwargs):
            raise RuntimeError("Ollama unavailable")
    monkeypatch.setattr(pipeline, "save_context", save)
    monkeypatch.setattr(pipeline, "build_crew", lambda *_: BrokenCrew())
    result = await pipeline.run_crew("regression", "A local bakery serving Austin", 500, ["Austin"])
    assert result.campaign_status == "FAILED"
    assert result.agent_states[AgentName.RESEARCH].status == "FAILED"
    assert "Ollama unavailable" in result.agent_states[AgentName.RESEARCH].logs[-1].message
    assert saved[-1]["campaign_status"] == "FAILED"


@pytest.mark.parametrize("status", [CampaignStatus.DONE, CampaignStatus.FAILED])
def test_late_websocket_gets_terminal_status(monkeypatch, status):
    value = context()
    value.campaign_status = status
    async def load(_id):
        assert "regression" in ws_api.event_bus._queues
        return value
    async def noop():
        pass
    monkeypatch.setattr(main, "startup", noop)
    monkeypatch.setattr(main, "shutdown", noop)
    monkeypatch.setattr(ws_api, "load_context", load)
    with TestClient(main.app) as client:
        with client.websocket_connect("/live/regression") as socket:
            assert socket.receive_json()["type"] == "catch_up"
            assert socket.receive_json()["campaign_status"] == status
    assert "regression" not in ws_api.event_bus._queues


@pytest.mark.asyncio
async def test_all_eight_planning_tasks_complete_through_real_crew(monkeypatch):
    import json
    from crewai import Agent

    outputs = [
        {"business_name": "Bakery"}, {"ad_groups": {"Bread": []}},
        {"ad_groups": {"Bread": {"headlines": ["Bread"]}}},
        {"overall_approved": True}, {"published": False, "ad_groups": {}},
        {"data_available": False, "metrics": None}, {"applied": False, "experiments": []},
        {"week_summary": "Campaign plan ready for review."},
    ]
    by_role = dict(zip(pipeline._ROLE_TO_AGENT_NAME, outputs))
    calls = []
    def execute(agent, task, context=None, tools=None):
        calls.append(agent.role)
        assert "{landing_page_url}" not in task.description
        return json.dumps(by_role[agent.role])
    snapshots = []
    async def save(_id, value):
        snapshots.append(value.model_dump(mode="json"))
    monkeypatch.setattr(Agent, "execute_task", execute)
    monkeypatch.setattr(pipeline, "save_context", save)
    result = await pipeline.run_crew("flow", "A local bakery serving Austin", 500, ["Austin"], "https://bakery.example")
    assert result.campaign_status == "DONE"
    assert result.is_complete()
    assert len(calls) == 8
    assert result.weekly_report == "Campaign plan ready for review."
    assert snapshots[-1]["campaign_status"] == "DONE"


@pytest.mark.asyncio
@pytest.mark.parametrize('role,output,message', [
    ('Google Ads Campaign Launch Specialist', {'published': True}, 'published=false'),
    ('Campaign Performance Analyst', {'data_available': True, 'metrics': {'clicks': 10}}, 'unavailable'),
    ('Google Ads Bid and Budget Optimizer', {'applied': True}, 'applied=false'),
])
async def test_planning_agents_reject_claims_of_live_actions(role, output, message):
    import json
    value = context()
    crew = pipeline.build_crew(value, asyncio.get_running_loop())
    with pytest.raises(ValueError, match=message):
        await asyncio.to_thread(crew.task_callback, SimpleNamespace(agent=role, raw=json.dumps(output)))
    for agent in crew.agents[4:7]:
        assert agent.tools == []
