from agents.base_agent import BaseAgent
from tools.keyword_tools import get_keyword_ideas

keyword_agent=BaseAgent.build(
    role="Google Ads Keyword Strategist",
 
    goal=(
        "Build a focused keyword strategy using high-intent keyword expansions. "
        "Group keywords into themes that map to ad groups. "
        "Prioritise high-intent keywords with reasonable CPC for the budget."
    ),
 
    backstory=(
        "You are an expert Google Ads keyword strategist with deep knowledge "
        "of search intent and keyword planning. "
        "You use keyword expansion patterns and intent modifiers to find the best keywords "
        "for a business based on its profile and target audience. "
        "You group keywords by intent and theme — not just by topic — "
        "so each ad group has tightly related keywords that share the same ad copy. "
        "You always consider the monthly budget when recommending bids "
        "and filter out keywords with very high CPC relative to the budget. "
        "You return structured JSON so the creative and reporting agents "
        "can use your output directly without interpretation. "
        "Respond only with valid JSON. No markdown, no explanation, no code blocks."
    ),
    tools=[get_keyword_ideas],
)

# KeywordAgent builds the keyword strategy for the campaign.
#
# It uses get_keyword_ideas (heuristic expansion tool) to generate
# keyword ideas with estimated search volume and CPC.
#
# It reads business_profile from the task context (written by ResearchAgent)
# and uses the buying_intent_signals and ad_themes from that profile
# as seed keywords for expansion.
#
# Output goes into CampaignContext.keyword_strategy and is used by:
#   - CreativeAgent  → to write headlines around the top keywords
#   - the campaign planner    → to add keywords to each ad group