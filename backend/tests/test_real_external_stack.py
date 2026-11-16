import json
import os
import shutil

import pytest
from crewai import Crew, Process, Task

from agents.monitor_agent import monitor_agent
from tools.google_ads_mcp_reader import mcp_reader
from tools.scraper_tools import scrape_website, search_competitors


def _require_real_flag() -> None:
    if os.getenv("RUN_REAL_EXTERNAL_TESTS") != "1":
        pytest.skip("Set RUN_REAL_EXTERNAL_TESTS=1 to run real external service tests.")


def _require_mcp_env() -> None:
    required = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_PROJECT_ID",
        "GOOGLE_ADS_DEVELOPER_TOKEN",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        pytest.skip(f"Missing MCP env vars: {', '.join(missing)}")


def test_real_scraping_tools_output():
    _require_real_flag()

    scrape_url = os.getenv("REAL_SCRAPE_URL", "http://neverssl.com")
    page_text = scrape_website.run(url=scrape_url)
    print("\n=== scrape_website response (first 800 chars) ===")
    print(str(page_text)[:800])

    competitors = search_competitors.run(
        business_type=os.getenv("REAL_BUSINESS_TYPE", "pizza restaurant"),
        location=os.getenv("REAL_LOCATION", "Austin, TX"),
    )
    print("\n=== search_competitors response (first 3 items) ===")
    print(json.dumps(competitors[:3], indent=2))

    assert isinstance(page_text, str)
    assert isinstance(competitors, list)


def test_real_google_ads_mcp_path():
    _require_real_flag()
    _require_mcp_env()

    if "fallback" in str(getattr(mcp_reader, "name", "")).lower():
        pytest.fail(
            "MCP is still running in fallback mode. "
            "Fix crewai/crewai-tools compatibility first to use actual Google Ads MCP."
        )

    cli_path = shutil.which("google-ads-mcp")
    if not cli_path:
        pytest.fail("google-ads-mcp command not found in PATH.")

    task = Task(
        description=(
            "Use the MCP tool to list accessible Google Ads customers and return valid JSON with the result."
        ),
        expected_output="Valid JSON only.",
        agent=monitor_agent,
    )

    crew = Crew(
        agents=[monitor_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    output = crew.kickoff(inputs={})
    raw = output.raw if hasattr(output, "raw") else str(output)

    print("\n=== MonitorAgent MCP output ===")
    print(raw)

    assert str(raw).strip()
