from agents.base_agent import BaseAgent, load_prompt
report_agent = BaseAgent.build(
    role="Campaign Reporting Analyst",

    goal=(
        "Write a clear, plain-English weekly performance summary for the business owner. "
        "No jargon — translate every metric into plain language. "
        "150 to 250 words. "
        "Open with the biggest win, explain what was optimised, end with one recommendation."
    ),

    backstory=load_prompt("report.txt"),

    # No tools — pure LLM writing task
    tools=[],
)

# ReportAgent is the last agent in the pipeline.
# It writes a plain-English weekly summary for the business owner.
# It has NO tools — it is a pure LLM agent.
#
# It reads everything that came before it —
# performance_data from MonitorAgent and optimizations from OptimizeAgent —
# and turns it into a short, jargon-free summary a non-technical person can understand.
#
# Input it reads from previous agents:
#   - business_profile  (from ResearchAgent)  — business name and context
#   - performance_data  (from MonitorAgent)   — this week's metrics
#   - optimizations     (from OptimizeAgent)  — changes made this week
#
# Output it writes to CampaignContext:
#   - weekly_report — plain English summary + key numbers dict

