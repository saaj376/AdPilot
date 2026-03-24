import asyncio
import os

import pytest
from crewai import Crew, Process, Task
from crewai.tools import tool

from agents.creative_agent import creative_agent
from agents.keyword_agent import keyword_agent
from agents.launch_agent import launch_agent
from agents.monitor_agent import monitor_agent
from agents.optimize_agent import optimize_agent
from agents.qa_agent import qa_agent
from agents.report_agent import report_agent
from agents.research_agent import research_agent
from services.llm_client import check_ollama_health


@tool("Mock scrape website")
def mock_scrape_website(url: str) -> str:
    """Return deterministic page text for integration tests."""
    return f"Sample scraped content from {url}. Family-focused pizza menu, delivery, dine-in."


@tool("Mock search competitors")
def mock_search_competitors(business_type: str, location: str) -> list[dict]:
    """Return deterministic competitors for integration tests."""
    return [
        {
            "name": "Homeslice Pizza",
            "url": "https://example.com/homeslice",
            "snippet": f"Top {business_type} in {location}",
            "scraped_text": "Known for dine-in experience and artisan pizza.",
        },
        {
            "name": "Little Deli",
            "url": "https://example.com/littledeli",
            "snippet": f"Local favorite in {location}",
            "scraped_text": "Strong lunch traffic and quick delivery service.",
        },
    ]


@tool("Mock keyword ideas")
def mock_get_keyword_ideas(seed_keywords: list[str], location: str) -> list[dict]:
    """Return deterministic keyword planner output for integration tests."""
    base = seed_keywords[0] if seed_keywords else "pizza"
    return [
        {"text": f"{base} near me", "avg_monthly_searches": 880, "cpc": 1.9, "competition": "HIGH"},
        {"text": f"best {base} {location}", "avg_monthly_searches": 540, "cpc": 2.2, "competition": "MEDIUM"},
        {"text": f"{base} delivery {location}", "avg_monthly_searches": 430, "cpc": 1.7, "competition": "MEDIUM"},
    ]


@tool("Mock create campaign")
def mock_create_campaign(name: str, monthly_budget: float, geo_targets: list[str]) -> dict:
    """Return deterministic campaign creation payload for integration tests."""
    return {
        "campaign_id": "111111",
        "campaign_name": name,
        "status": "PAUSED",
        "daily_budget": monthly_budget / 30,
        "geo_targets": geo_targets,
    }


@tool("Mock create ad group")
def mock_create_ad_group(campaign_id: str, name: str) -> dict:
    """Return deterministic ad group payload for integration tests."""
    return {"ad_group_id": "222222", "campaign_id": campaign_id, "name": name, "status": "ENABLED"}


@tool("Mock create ads")
def mock_create_ads(ad_group_id: str, headlines: list[str], descriptions: list[str], final_url: str) -> dict:
    """Return deterministic ad creation payload for integration tests."""
    return {
        "ad_id": "333333",
        "ad_group_id": ad_group_id,
        "headline_count": len(headlines),
        "description_count": len(descriptions),
        "final_url": final_url,
        "status": "ENABLED",
    }


@tool("Mock monitor search")
def mock_monitor_search(query: str) -> dict:
    """Return deterministic performance metrics for integration tests."""
    return {
        "query": query,
        "impressions": 12000,
        "clicks": 760,
        "ctr": 0.0633,
        "avg_cpc": 1.95,
        "spend": 1482.0,
        "conversions": 84,
        "top_keywords": ["pizza near me", "wood fired pizza", "pizza delivery austin"],
        "low_performers": ["cheap pizza", "pizza coupon", "free pizza"],
    }


@tool("Mock update bid")
def mock_update_keyword_bid(ad_group_id: str, keyword_id: str, new_bid_usd: float) -> dict:
    """Return deterministic bid update result for integration tests."""
    return {
        "ad_group_id": ad_group_id,
        "keyword_id": keyword_id,
        "new_bid": new_bid_usd,
        "status": "UPDATED",
    }


@tool("Mock pause keyword")
def mock_pause_keyword(ad_group_id: str, keyword_id: str) -> dict:
    """Return deterministic pause result for integration tests."""
    return {"ad_group_id": ad_group_id, "keyword_id": keyword_id, "status": "PAUSED"}


@tool("Mock reallocate budget")
def mock_reallocate_budget(campaign_id: str, new_monthly_budget: float) -> dict:
    """Return deterministic budget reallocation result for integration tests."""
    return {
        "campaign_id": campaign_id,
        "new_daily_budget": new_monthly_budget / 30,
        "status": "UPDATED",
    }


@pytest.fixture(scope="module", autouse=True)
def enable_real_ollama_or_skip():
    if os.getenv("RUN_OLLAMA_AGENT_TESTS") != "1":
        pytest.skip("Set RUN_OLLAMA_AGENT_TESTS=1 to run real Ollama integration tests.")

    asyncio.run(check_ollama_health())


@pytest.fixture(scope="module", autouse=True)
def patch_external_tools():
    original_tools = {
        research_agent: list(research_agent.tools),
        keyword_agent: list(keyword_agent.tools),
        launch_agent: list(launch_agent.tools),
        monitor_agent: list(monitor_agent.tools),
        optimize_agent: list(optimize_agent.tools),
    }

    research_agent.tools = [mock_scrape_website, mock_search_competitors]
    keyword_agent.tools = [mock_get_keyword_ideas]
    launch_agent.tools = [mock_create_campaign, mock_create_ad_group, mock_create_ads]
    monitor_agent.tools = [mock_monitor_search]
    optimize_agent.tools = [mock_update_keyword_bid, mock_pause_keyword, mock_reallocate_budget]

    yield

    for agent, tools in original_tools.items():
        agent.tools = tools


def _run_single_agent(agent, title: str, description: str) -> str:
    task = Task(
        description=description,
        expected_output="Valid JSON only.",
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    output = crew.kickoff(inputs={})
    raw = output.raw if hasattr(output, "raw") else str(output)
    print(f"\n===== {title} =====")
    print(raw)
    return raw


def test_real_ollama_responses_from_all_8_agents():
    scenarios = [
        (
            "ResearchAgent",
            research_agent,
            "Analyse this business: 'Tony's Wood-Fired Pizza in Austin serving dine-in and delivery'. "
            "Use tools if needed. Return JSON with business profile, competitors, buying signals, and ad themes.",
        ),
        (
            "KeywordAgent",
            keyword_agent,
            "Using this profile: business_type='wood-fired pizza restaurant', location='Austin, TX', "
            "buying_intent_signals=['pizza delivery near me','best pizza austin'], ad_themes=['Delivery','Family Dining']. "
            "Return keyword strategy JSON grouped into ad groups.",
        ),
        (
            "CreativeAgent",
            creative_agent,
            "Write responsive search ad copy JSON for ad groups Delivery and Family Dining for a pizza brand in Austin.",
        ),
        (
            "QAAgent",
            qa_agent,
            "Review this sample ad copy and return corrected policy-compliant JSON: "
            "{'Delivery': {'headlines':['BEST!!! PIZZA EVER!!!!','Free pizza now'], 'descriptions':['Click now for insane deal!!!']}}",
        ),
        (
            "LaunchAgent",
            launch_agent,
            "Using approved ad groups and copy, create campaign structure with tools and return IDs as JSON.",
        ),
        (
            "MonitorAgent",
            monitor_agent,
            "Fetch LAST_7_DAYS campaign and keyword metrics for campaign_id=111111 and return JSON summary.",
        ),
        (
            "OptimizeAgent",
            optimize_agent,
            "Based on performance data with top and low keywords, apply bid updates/pause actions and return optimization JSON.",
        ),
        (
            "ReportAgent",
            report_agent,
            "Write a weekly owner-friendly summary JSON based on sample performance and optimizations.",
        ),
    ]

    collected = {}
    for title, agent, prompt in scenarios:
        raw = _run_single_agent(agent, title, prompt)
        collected[title] = raw

    assert len(collected) == 8
    assert all(str(v).strip() for v in collected.values())
