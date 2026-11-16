from agents.base_agent import BaseAgent, load_prompt

creative_agent=BaseAgent.build(
    role="Google Ads Copywriter",
    goal=(
        "Write compelling, policy-compliant Google Ads headlines and descriptions "
        "for every ad group. Copy must be specific to the business, "
        "match the brand tone, and stay within Google's character limits."
    ),
    backstory=load_prompt("creative.txt"),
    tools=[],
    # Pure LLM agent — no tools. Disabling the ReAct system prompt so the LLM
    # can write Final Answer directly without hitting the Action/Observation
    # format parser and triggering unnecessary retry loops.
    use_system_prompt=False,
)
# CreativeAgent writes the actual ad copy —
# headlines, descriptions and CTAs for every ad group.
#
# It is a pure LLM agent — no tools needed.
# It reads business_profile and keyword_strategy from the
# CampaignContext (passed via CrewAI task context) and
# uses the creative.txt prompt to write Google-policy-compliant copy.
#
# Output goes into CampaignContext.ad_creatives
# and is then reviewed by QAAgent before export.