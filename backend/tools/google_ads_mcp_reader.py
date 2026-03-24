from crewai.tools import tool

try:
    from crewai_tools import MCPTool
except Exception:
    MCPTool = None

from config import settings


# The official Google Ads MCP server is now installed directly
# in your .venv via: pip install git+https://github.com/googleads/google-ads-mcp.git
#
# Because it's installed as a package (not run via pipx),
# we launch it using the installed command "google-ads-mcp"
# directly — no pipx needed.
#
# This tool is READ-ONLY — it can only fetch data, never change anything.
# That's exactly what MonitorAgent needs: read campaign performance via GAQL.
#
# Two tools exposed to the agent:
#   1. list_accessible_customers — lists all Google Ads accounts you can access
#   2. search — runs a GAQL query and returns performance data
#
# MonitorAgent uses "search" to ask things like:
# "Give me CTR, CPC, impressions and spend for campaign X this week"
# and gets back real data from the Google Ads API.


def get_mcp_reader() -> MCPTool:
    """
    Returns an MCPTool that launches the official Google Ads MCP server.

    Since google-ads-mcp is installed in your .venv via pip,
    we launch it using the installed "google-ads-mcp" command directly.

    MCPTool handles:
    - Starting the process
    - Passing credentials as environment variables
    - Sending tool calls (like "search") to the process
    - Returning results to the agent
    """
    return MCPTool(
        # Launch the installed command directly — no pipx needed
        command="google-ads-mcp",
        args=[],

        # Credentials passed as env vars to the subprocess
        # These come from your .env via settings.google_ads_mcp_env
        env=settings.google_ads_mcp_env,
    )


@tool("Google Ads MCP fallback")
def _mcp_unavailable_fallback(query: str = "") -> str:
    """Explain that crewai-tools is unavailable or incompatible in this environment."""
    return (
        "Google Ads MCP tool is unavailable because the installed 'crewai' and "
        "'crewai-tools' versions are incompatible in this environment. "
        "Install compatible versions, then restart the backend."
    )


# Module-level singleton — created once, imported by MonitorAgent only.
# Do NOT import this into LaunchAgent, OptimizeAgent etc.
# Those agents use the SDK tools in google_ads_sdk_tools.py instead.
mcp_reader = get_mcp_reader() if MCPTool is not None else _mcp_unavailable_fallback