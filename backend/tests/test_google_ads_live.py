import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google.api_core.exceptions import MethodNotImplemented

from config import settings
from services.google_ads_client import check_sdk_credentials, get_client
from tools.google_ads_mcp_reader import (
    MCP_COMMAND,
    mcp_list_accessible_customers,
    mcp_reader,
)
from tools.google_ads_sdk_tools import get_keyword_ideas


@pytest.fixture(scope="module", autouse=True)
def load_backend_env():
    backend_dir = Path(__file__).resolve().parents[1]
    env_path = backend_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


@pytest.fixture(scope="module", autouse=True)
def require_live_flag_or_skip():
    if os.getenv("RUN_GOOGLE_ADS_LIVE_TESTS") != "1":
        pytest.skip("Set RUN_GOOGLE_ADS_LIVE_TESTS=1 to run real Google Ads tests.")


@pytest.mark.integration
def test_google_ads_sdk_accessible_customers_live():
    """Call real Google Ads SDK and print accessible customer resource names."""
    check_sdk_credentials()

    client = get_client()
    customer_service = client.get_service("CustomerService")
    try:
        response = customer_service.list_accessible_customers()
    except MethodNotImplemented as exc:
        pytest.skip(
            "Google Ads API version configured in the client appears sunset on the server side. "
            f"Details: {exc}"
        )

    customers = list(response.resource_names)
    print("\n=== Google Ads SDK accessible customers ===")
    print(json.dumps(customers, indent=2))

    assert isinstance(customers, list)
    assert len(customers) > 0


@pytest.mark.integration
def test_google_ads_keyword_planner_live():
    """Call real Keyword Planner through the SDK tool wrapper and print output."""
    try:
        keywords = get_keyword_ideas.run(
            seed_keywords=["pizza delivery", "wood fired pizza"],
            location="Austin, TX",
        )
    except MethodNotImplemented as exc:
        pytest.skip(
            "Keyword Planner endpoint appears unavailable for the configured SDK/API version. "
            f"Details: {exc}"
        )

    print("\n=== Google Ads Keyword Planner sample ===")
    print(json.dumps(keywords[:10], indent=2))

    assert isinstance(keywords, list)
    assert len(keywords) > 0
    if isinstance(keywords[0], dict) and "error" in keywords[0]:
        err = str(keywords[0]["error"])
        if "DEVELOPER_TOKEN_NOT_APPROVED" in err:
            pytest.skip(
                "Developer token is test-only and not approved for non-test accounts. "
                "Apply for Basic/Standard Google Ads API access."
            )
        pytest.fail(f"Keyword Planner returned API error: {err}")
    assert "text" in keywords[0]


@pytest.mark.integration
def test_google_ads_mcp_is_not_fallback():
    """Ensure MCP bridge is wired and performs a real list_accessible_customers call."""
    name = str(getattr(mcp_reader, "name", ""))
    print("\n=== MCP tool name ===")
    print(name)

    print("\n=== MCP command ===")
    print(MCP_COMMAND)

    assert name == "google_ads_mcp_search"
    assert MCP_COMMAND

    # This ensures MCP credentials were picked from settings/.env.
    assert settings.GOOGLE_APPLICATION_CREDENTIALS
    assert settings.GOOGLE_PROJECT_ID

    out = mcp_list_accessible_customers.run()
    print("\n=== MCP list_accessible_customers output ===")
    print(out)

    if "DefaultCredentialsError" in out or "must be ADC JSON" in out:
        pytest.fail(
            "GOOGLE_APPLICATION_CREDENTIALS is not valid ADC JSON for MCP. "
            "Use authorized_user/service_account credentials, not OAuth client_secret JSON."
        )
    assert "failed:" not in out.lower(), out
