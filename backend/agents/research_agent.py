from agents.base_agent import BaseAgent, load_prompt
from tools.scraper_tools import scrape_website, search_competitors

research_agent = BaseAgent.build(
    role="Business Research Specialist",
 
    goal=(
        "Analyse the business description and scrape competitor websites "
        "to build a detailed business profile. "
        "Extract the target audience, USP, brand tone, competitors, "
        "buying intent signals, and ad themes."
    ),
 
    backstory=load_prompt("research.txt"),
 
    # Two scraping tools — scrape the business's own site and competitor sites
    tools=[scrape_website, search_competitors],
)

# ResearchAgent is the first agent in the pipeline.
# Everything downstream depends on what it finds here —
# KeywordAgent uses its buying_intent_signals as seed keywords,
# CreativeAgent uses its tone and USP to write ad copy,
# ReportAgent uses its business_name in the weekly summary.
#
# Input:
#   - business_description (from CampaignContext) — the raw text the user typed
#
# Output it writes to CampaignContext:
#   - business_profile — structured analysis of the business and competitors