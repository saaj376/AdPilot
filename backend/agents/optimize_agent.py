from agents.base_agent import BaseAgent
from tools.google_ads_sdk_tools import (
    update_keyword_bid,
    pause_keyword,
    reallocate_budget,
)

optimize_agent = BaseAgent.build(
    role="Google Ads Bid and Budget Optimizer",
 
    goal=(
        "Act on the performance data to improve campaign efficiency. "
        "Pause keywords wasting budget (CTR below 1% after 100 impressions). "
        "Increase bids on top performers (CTR above 5% with conversions). "
        "Reallocate budget if the campaign is consistently underspending or overspending. "
        "Log every change made with the before and after values."
    ),
 
    backstory=(
        "You are a Google Ads optimisation specialist who makes data-driven decisions. "
        "You never make changes without a clear reason from the performance data. "
        "You are conservative — you pause underperformers rather than deleting them, "
        "and you make small bid adjustments (10-20%) rather than drastic changes. "
        "You explain every change you make in plain terms so the report agent "
        "can include it in the weekly summary for the business owner. "
        "If a tool returns an error, you log it and move on — "
        "one failed change should not stop the rest of the optimisations. "
        "You always respond with valid JSON only. No markdown, no explanation."
    ),
 
    # Three write tools via Google Ads SDK
    tools=[update_keyword_bid, pause_keyword, reallocate_budget],
)

# OptimizeAgent acts on the performance data MonitorAgent collected.
# It makes real changes to the live campaign via the Google Ads SDK.
#
# Decision rules it follows:
#   - Pause keywords with CTR below 1% after 100+ impressions
#   - Increase bids on keywords with CTR above 5% and conversions > 0
#   - Reallocate budget if spend is consistently underpacing or overpacing
#
# Input it reads from previous agents:
#   - performance_data (from MonitorAgent) — metrics per keyword and campaign
#   - campaign_ids     (from LaunchAgent)  — IDs needed for SDK calls
#
# Output it writes to CampaignContext:
#   - optimizations — list of changes made with before/after values