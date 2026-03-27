from agents.base_agent import BaseAgent, load_prompt

qa_agent = BaseAgent.build(
    role="Google Ads Policy Compliance Reviewer",

    goal=(
        "Review every headline and description against Google Ads editorial policies. "
        "Flag automatic failures and fix them. "
        "Note warnings but do not block launch for warnings alone. "
        "Return the corrected copy in fixed_copy so LaunchAgent can use it directly."
    ),

    backstory=load_prompt("qa_policy.txt"),
    tools=[],
    # Pure LLM agent — no tools. Disabling the ReAct system prompt so the LLM
    # can write Final Answer directly without triggering parse-error retry loops.
    use_system_prompt=False,
)


# QAAgent reviews ad copy before it goes live.
# It is a pure LLM agent — no tools needed.
# It reads CreativeAgent's output and checks it against
# Google Ads editorial policies.
#
# If it finds issues it fixes them automatically and returns
# the corrected copy in fixed_copy — LaunchAgent uses the
# fixed version, not the original.
#
# Input it reads from previous agents:
#   - ad_creatives (from CreativeAgent) — headlines and descriptions per ad group
#
# Output it writes to CampaignContext:
#   - qa_result — approved status, issues, warnings, and fixed copy per ad group
