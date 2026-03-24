import asyncio
import json
import os
from typing import Any

import pytest
from crewai import Crew, Process
from crewai.tools import tool

from agents.creative_agent import creative_agent
from agents.keyword_agent import keyword_agent
from agents.launch_agent import launch_agent
from agents.monitor_agent import monitor_agent
from agents.optimize_agent import optimize_agent
from agents.qa_agent import qa_agent
from agents.report_agent import report_agent
from agents.research_agent import research_agent
from core.tasks import (
    creative_task,
    keyword_task,
    launch_task,
    monitor_task,
    optimize_task,
    qa_task,
    report_task,
    research_task,
)
from services.llm_client import check_ollama_health
from tools.google_ads_mcp_reader import mcp_list_accessible_customers


@tool("Flow mock create campaign")
def _flow_mock_create_campaign(
    name: str | dict = "",
    monthly_budget: float | dict = 0.0,
    geo_targets: list[str] | str | dict = "",
) -> dict:
    """Safe mock for campaign creation during full flow tests."""
    if isinstance(name, dict):
        name = "Flow Campaign"
    if isinstance(monthly_budget, dict):
        monthly_budget = 1200.0
    if isinstance(geo_targets, dict):
        geo_targets = ["Austin, TX"]
    if isinstance(geo_targets, str):
        geo_targets = [geo_targets] if geo_targets else ["Austin, TX"]

    return {
        "campaign_id": "flow-111111",
        "campaign_name": name or "Flow Campaign",
        "status": "PAUSED",
        "daily_budget": monthly_budget / 30,
        "geo_targets": geo_targets,
    }


@tool("Flow mock create ad group")
def _flow_mock_create_ad_group(campaign_id: str | dict = "", name: str | dict = "") -> dict:
    """Safe mock for ad group creation during full flow tests."""
    if isinstance(campaign_id, dict):
        campaign_id = "flow-111111"
    if isinstance(name, dict):
        name = "Flow Ad Group"

    return {
        "ad_group_id": f"ag-{abs(hash(name or 'flow')) % 1000000}",
        "campaign_id": campaign_id or "flow-111111",
        "name": name or "Flow Ad Group",
        "status": "ENABLED",
    }


@tool("Flow mock create ads")
def _flow_mock_create_ads(
    ad_group_id: str | dict = "",
    headlines: list[str] | dict = None,
    descriptions: list[str] | dict = None,
    final_url: str | dict = "",
) -> dict:
    """Safe mock for ad creation during full flow tests."""
    if isinstance(ad_group_id, dict):
        ad_group_id = "ag-flow"
    if isinstance(headlines, dict) or headlines is None:
        headlines = ["Fresh Wood-Fired Pizza", "Delivered Fast", "Order Online Today"]
    if isinstance(descriptions, dict) or descriptions is None:
        descriptions = ["Family favorites delivered hot.", "Order in minutes."]
    if isinstance(final_url, dict) or not final_url:
        final_url = "https://example.com"

    return {
        "ad_id": f"ad-{abs(hash(ad_group_id or 'flow')) % 1000000}",
        "ad_group_id": ad_group_id or "ag-flow",
        "headline_count": len(headlines),
        "description_count": len(descriptions),
        "final_url": final_url,
        "status": "ENABLED",
    }


@tool("Flow mock update keyword bid")
def _flow_mock_update_keyword_bid(
    ad_group_id: str | dict = "",
    keyword_id: str | dict = "",
    new_bid_usd: float | dict = 0.0,
) -> dict:
    """Safe mock for bid updates during full flow tests."""
    if isinstance(ad_group_id, dict):
        ad_group_id = "ag-flow"
    if isinstance(keyword_id, dict):
        keyword_id = "kw-flow"
    if isinstance(new_bid_usd, dict):
        new_bid_usd = 1.5

    return {
        "ad_group_id": ad_group_id or "ag-flow",
        "keyword_id": keyword_id or "kw-flow",
        "new_bid": new_bid_usd,
        "status": "UPDATED",
    }


@tool("Flow mock pause keyword")
def _flow_mock_pause_keyword(ad_group_id: str | dict = "", keyword_id: str | dict = "") -> dict:
    """Safe mock for keyword pause during full flow tests."""
    if isinstance(ad_group_id, dict):
        ad_group_id = "ag-flow"
    if isinstance(keyword_id, dict):
        keyword_id = "kw-flow"

    return {
        "ad_group_id": ad_group_id or "ag-flow",
        "keyword_id": keyword_id or "kw-flow",
        "status": "PAUSED",
    }


@tool("Flow mock reallocate budget")
def _flow_mock_reallocate_budget(
    campaign_id: str | dict = "",
    new_monthly_budget: float | dict = 0.0,
) -> dict:
    """Safe mock for budget reallocation during full flow tests."""
    if isinstance(campaign_id, dict):
        campaign_id = "flow-111111"
    if isinstance(new_monthly_budget, dict):
        new_monthly_budget = 1200.0

    return {
        "campaign_id": campaign_id or "flow-111111",
        "new_daily_budget": new_monthly_budget / 30,
        "status": "UPDATED",
    }


@tool("Flow mock monitor search")
def _flow_mock_monitor_search(query: str | dict = "") -> dict:
    """Deterministic read-only performance payload for full flow tests."""
    if isinstance(query, dict):
        query = "LAST_7_DAYS"
    return {
        "query": query or "LAST_7_DAYS",
        "impressions": 12450,
        "clicks": 812,
        "ctr": 0.0652,
        "avg_cpc": 1.82,
        "spend": 1477.84,
        "conversions": 97,
        "top_keywords": [
            "pizza delivery austin",
            "wood fired pizza near me",
            "family pizza deals",
        ],
        "low_performers": [
            "cheap pizza",
            "pizza coupon",
            "free pizza",
        ],
    }


@pytest.fixture(scope="module", autouse=True)
def require_flow_flag_or_skip():
    if os.getenv("RUN_FULL_AGENT_FLOW_TEST") != "1":
        pytest.skip("Set RUN_FULL_AGENT_FLOW_TEST=1 to run the full 8-agent flow test.")


@pytest.fixture(scope="module", autouse=True)
def require_ollama_or_skip():
    asyncio.run(check_ollama_health())


@pytest.fixture(scope="module", autouse=True)
def require_mcp_or_skip():
    mcp_probe = mcp_list_accessible_customers.run()
    if "failed:" in str(mcp_probe).lower():
        pytest.skip(f"MCP is not ready for full flow test: {mcp_probe}")


@pytest.fixture(scope="module", autouse=True)
def safe_write_tools():
    """Avoid live write mutations unless explicitly requested."""
    if os.getenv("RUN_AGENT_FLOW_LIVE_WRITES") == "1":
        yield
        return

    original_launch_tools = list(launch_agent.tools)
    original_optimize_tools = list(optimize_agent.tools)
    original_monitor_tools = list(monitor_agent.tools)

    launch_agent.tools = [
        _flow_mock_create_campaign,
        _flow_mock_create_ad_group,
        _flow_mock_create_ads,
    ]
    optimize_agent.tools = [
        _flow_mock_update_keyword_bid,
        _flow_mock_pause_keyword,
        _flow_mock_reallocate_budget,
    ]
    monitor_agent.tools = [_flow_mock_monitor_search]

    yield

    launch_agent.tools = original_launch_tools
    optimize_agent.tools = original_optimize_tools
    monitor_agent.tools = original_monitor_tools


@pytest.fixture(scope="module", autouse=True)
def escape_backstory_braces_for_crewai_formatting():
    """Prevent CrewAI `.format(**inputs)` from treating JSON braces as placeholders."""
    agents = [
        research_agent,
        keyword_agent,
        creative_agent,
        qa_agent,
        launch_agent,
        monitor_agent,
        optimize_agent,
        report_agent,
    ]

    originals = {}
    for agent in agents:
        original = str(agent.backstory)
        originals[agent] = original
        escaped = original.replace("{", "{{").replace("}", "}}")
        agent.backstory = escaped
        # Keep CrewAI interpolation source in sync.
        if hasattr(agent, "_original_backstory"):
            agent._original_backstory = escaped

    yield

    for agent, original in originals.items():
        agent.backstory = original
        if hasattr(agent, "_original_backstory"):
            agent._original_backstory = original


def _output_to_text(task_output) -> str:
    if task_output is None:
        return ""
    raw = task_output.raw if hasattr(task_output, "raw") else str(task_output)
    return str(raw).strip()


def _print_flow(task_outputs: list) -> None:
    stage_names = [
        "RESEARCH",
        "KEYWORD",
        "CREATIVE",
        "QA",
        "LAUNCH",
        "MONITOR",
        "OPTIMIZE",
        "REPORT",
    ]

    print("\n================ FULL 8-AGENT FLOW OUTPUT ================")
    for idx, output in enumerate(task_outputs):
        stage = stage_names[idx] if idx < len(stage_names) else f"STAGE_{idx + 1}"
        text = _output_to_text(output)
        print(f"\n----- {stage} -----")
        print(text)


@pytest.mark.integration
def test_full_8_agent_flow_prints_end_to_end_outputs():
    """Run the complete 8-agent pipeline and print each stage output."""
    crew = Crew(
        agents=[
            research_agent,
            keyword_agent,
            creative_agent,
            qa_agent,
            launch_agent,
            monitor_agent,
            optimize_agent,
            report_agent,
        ],
        tasks=[
            research_task,
            keyword_task,
            creative_task,
            qa_task,
            launch_task,
            monitor_task,
            optimize_task,
            report_task,
        ],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(
        inputs={
            "business_description": (
                "Tony's Wood-Fired Pizza in Austin serves dine-in and delivery, "
                "with family meal deals and online ordering."
            ),
            "monthly_budget": 1200.0,
            "geo_targets": str(["Austin, TX"]),
        }
    )

    task_outputs = list(getattr(result, "tasks_output", []) or [])
    if not task_outputs:
        task_outputs = [getattr(task, "output", None) for task in crew.tasks]

    _print_flow(task_outputs)

    assert len(task_outputs) == 8
    assert all(_output_to_text(o) for o in task_outputs)

    final_text = _output_to_text(task_outputs[-1])
    # Ensure the report stage returns JSON-shaped output text.
    parsed = json.loads(final_text)
    assert isinstance(parsed, dict)
