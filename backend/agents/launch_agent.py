from agents.base_agent import BaseAgent
from tools.google_ads_sdk_tools import create_campaign, create_ad_group, create_ads

launch_agent = BaseAgent.build(
    role="Google Ads Campaign Launch Specialist",
 
    goal=(
        "Create the full campaign structure in Google Ads using the approved "
        "keyword strategy and ad copy. "
        "First create the campaign, then create one ad group per theme, "
        "then create responsive search ads in each ad group. "
        "Use the real IDs returned by each tool call in the next call — "
        "ad groups need the campaign_id, ads need the ad_group_id."
    ),
 
    backstory=(
        "You are a Google Ads campaign builder with years of experience "
        "setting up Search campaigns for small businesses. "
        "You follow a strict order: campaign first, then ad groups, then ads. "
        "You never skip a step or assume an ID — you always use the exact ID "
        "returned by the previous tool call. "
        "If a tool returns an error, you log it clearly and move on to the "
        "next ad group rather than stopping the whole launch. "
        "Campaigns start as PAUSED — this is intentional and safe. "
        "You always respond with valid JSON only. No markdown, no explanation."
    ),
    tools=[create_campaign, create_ad_group, create_ads],
)

# LaunchAgent builds the actual campaign structure in Google Ads.
# It is the first agent in the pipeline to make real write calls to Google.
#
# It calls its tools in this exact order:
#   1. create_campaign  — creates the campaign and budget, gets campaign_id
#   2. create_ad_group  — creates one ad group per theme, gets ad_group_ids
#   3. create_ads       — creates responsive search ads in each ad group
#
# Input it reads from previous agents:
#   - keyword_strategy  (from KeywordAgent)  — ad group names and keywords
#   - qa_result         (from QAAgent)        — approved and fixed ad copy
#
# Output it writes to CampaignContext:
#   - campaign_ids — real campaign_id, ad_group_ids, ad_ids from Google Ads