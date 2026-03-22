from crewai_tools import MCPTool

from config import settings


# This file wires up the official Google Ads MCP server for MonitorAgent.
#
# The MCP server is READ-ONLY — it can only fetch data, never change anything.
# That's exactly what MonitorAgent needs: read campaign performance data.
#
# How it works:
# - The MCP server is NOT a network service you connect to via URL
# - It runs as a local subprocess on your machine, launched by MCPTool
# - MCPTool starts it automatically when MonitorAgent calls a tool
# - It communicates via stdio (standard input/output), not HTTP
#
# The MCP server exposes two tools to the agent:
#   1. list_accessible_customers — lists all Google Ads accounts you have access to
#   2. search — runs a GAQL query and returns performance data
#
# MonitorAgent uses "search" to ask things like:
# "Give me CTR, CPC, impressions and spend for campaign X this week"
# and gets back real data from the Google Ads API.


def get_mcp_reader() -> MCPTool:
    return MCPTool(
        command="pipx",
        args=[
            "run",
            "--spec",
            "git+https://github.com/googleads/google-ads-mcp.git",
            "google-ads-mcp",
        ],
        env=settings.google_ads_mcp_env,
    )


mcp_reader = get_mcp_reader()