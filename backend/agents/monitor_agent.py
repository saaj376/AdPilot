from agents.base_agent import BaseAgent
from tools.google_ads_mcp_reader import mcp_reader

monitor_agent = BaseAgent.build(
    role="Campaign Performance Analyst",
 
    goal=(
        "Fetch this week's performance data for the campaign using GAQL queries. "
        "Get impressions, clicks, CTR, average CPC, total spend, and conversions "
        "at both campaign and keyword level. "
        "Identify the top 3 performing keywords and the bottom 3 by CTR. "
        "Return all numbers in plain units — convert micros to USD."
    ),
 
    backstory=(
        "You are a Google Ads performance analyst with expert knowledge of GAQL. "
        "You use the search tool to query the Google Ads API for campaign metrics. "
        "You always query LAST_7_DAYS for the weekly report cycle. "
        "You convert all money values from micros to USD by dividing by 1,000,000. "
        "You identify which keywords are driving results and which are wasting budget. "
        "You structure your findings clearly so OptimizeAgent knows exactly what to act on. "
        "You always respond with valid JSON only. No markdown, no explanation."
    ),
 
    # mcp_reader is the official Google Ads MCP server — read-only
    # Exposes: list_accessible_customers, search (GAQL)
    tools=[mcp_reader],
)

# MonitorAgent reads live campaign performance from Google Ads.
# It is the only agent that uses the official Google Ads MCP server.
# The MCP server is read-only — MonitorAgent can only fetch data, never change it.
#
# It queries performance data using GAQL (Google Ads Query Language)
# via the MCP server's "search" tool.
#
# Example GAQL query it might run:
#   SELECT campaign.id, metrics.impressions, metrics.clicks,
#          metrics.ctr, metrics.average_cpc, metrics.cost_micros,
#          metrics.conversions
#   FROM campaign
#   WHERE segments.date DURING LAST_7_DAYS
#
# Input it reads from previous agents:
#   - campaign_ids (from LaunchAgent) — the real campaign_id to query
#
# Output it writes to CampaignContext:
#   - performance_data — impressions, clicks, CTR, CPC, spend, conversions, top keywords, low performers