import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from config import settings
from tools.google_ads_mcp_reader import (
    MCP_COMMAND,
    mcp_list_accessible_customers,
    mcp_reader,
)


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
