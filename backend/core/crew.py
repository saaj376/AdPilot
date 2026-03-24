import asyncio
from uuid import uuid4
from crewai import Crew, Process
from core.campaign_context import AgentName, CampaignContext
from core.tasks import (
    research_task,
    keyword_task,
    creative_task,
    qa_task,
    launch_task,
    monitor_task,
    optimize_task,
    report_task,
)
from agents.research_agent import research_agent
from agents.keyword_agent import keyword_agent
from agents.creative_agent import creative_agent
from agents.qa_agent import qa_agent
from agents.launch_agent import launch_agent
from agents.monitor_agent import monitor_agent
from agents.optimize_agent import optimize_agent
from agents.report_agent import report_agent
from models.campaign import CampaignStatus
from services.redis_store import save_context

# crew.py is the orchestrator — it wires everything together.
# It has two jobs:
#   1. build_crew()  — assembles agents + tasks into a CrewAI Crew
#   2. run_crew()    — entry point called by the API to start a pipeline run
#
# on_step() is the callback that fires after each agent completes.
# It updates CampaignContext, saves to Redis, and pushes a live event
# to the WebSocket so the frontend pipeline UI updates in real time.

def _parse_agent_output(raw_output) -> dict:
    """
    Extracts the output dict from a CrewAI TaskOutput object.
    CrewAI returns a TaskOutput — we pull the raw string and parse it.
    Falls back to empty dict if parsing fails — pipeline keeps moving.
    """
    import json
    import re
 
    try:
        text = raw_output.raw if hasattr(raw_output, "raw") else str(raw_output)
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
 
        return json.loads(text)
    except Exception:
        return {"raw": str(raw_output)}

_ROLE_TO_AGENT_NAME = {
    "Business Research Specialist":          AgentName.RESEARCH,
    "Google Ads Keyword Strategist":         AgentName.KEYWORD,
    "Google Ads Copywriter":                 AgentName.CREATIVE,
    "Google Ads Policy Compliance Reviewer": AgentName.QA,
    "Google Ads Campaign Launch Specialist": AgentName.LAUNCH,
    "Campaign Performance Analyst":          AgentName.MONITOR,
    "Google Ads Bid and Budget Optimizer":   AgentName.OPTIMIZE,
    "Campaign Reporting Analyst":            AgentName.REPORT,
}

_AGENT_OUTPUT_FIELD = {
    AgentName.RESEARCH:  "business_profile",
    AgentName.KEYWORD:   "keyword_strategy",
    AgentName.CREATIVE:  "ad_creatives",
    AgentName.QA:        "qa_result",
    AgentName.LAUNCH:    "campaign_ids",
    AgentName.MONITOR:   "performance_data",
    AgentName.OPTIMIZE:  "optimizations",
    AgentName.REPORT:    "weekly_report",
}

def build_crew(context: CampaignContext) -> Crew:
    """
    Assembles the CrewAI Crew for a full pipeline run.
    Called once per campaign by run_crew().
 
    Process.sequential means agents run one after another
    in the exact order listed — never in parallel.
    """
 
    # step_callback fires after each task completes
    # We use it to update context, save to Redis, and push WebSocket events
    def on_step(step_output):
        agent_role = step_output.agent if hasattr(step_output, "agent") else ""
        agent_name = _ROLE_TO_AGENT_NAME.get(agent_role, "")
 
        if not agent_name:
            return

        output = _parse_agent_output(step_output)
        field = _AGENT_OUTPUT_FIELD.get(agent_name)
        if field and hasattr(context, field):
            setattr(context, field, output)
        context.set_agent_done(agent_name, output=output)
 
        # Log a completion message
        context.add_log(
            agent_name,
            f"{agent_name} completed successfully.",
            level="INFO",
        )
 
        # Save updated context to Redis after every agent
        # This means progress is never lost if the server restarts mid-pipeline
        asyncio.create_task(save_context(context.campaign_id, context))
 
        # Push live event to WebSocket
        # Import here to avoid circular imports at module level
        from core.event_bus import event_bus
        from models.agent_run import PipelineEvent
 
        event = PipelineEvent(
            campaign_id=context.campaign_id,
            agent_name=agent_name,
            status=context.agent_states[agent_name].status,
            log=context.agent_states[agent_name].logs[-1]
            if context.agent_states[agent_name].logs else None,
        )
        asyncio.create_task(event_bus.publish(context.campaign_id, event))
 
    return Crew(
        agents=[
            research_agent,
            keyword_agent,
            creative_agent,
            qa_agent,
            launch_agent,
            monitor_agent,
            optimize_agent,
            report_agent,
        ],
        tasks=[
            research_task,
            keyword_task,
            creative_task,
            qa_task,
            launch_task,
            monitor_task,
            optimize_task,
            report_task,
        ],
        process=Process.sequential,   # one agent at a time, in order
        step_callback=on_step,        # fires after each task completes
        verbose=True,                 # prints agent thinking to console
    )


async def run_crew(
    campaign_id: str,
    business_description: str,
    monthly_budget: float,
    geo_targets: list[str],
) -> CampaignContext:
    """
    Main entry point called by POST /campaigns API endpoint.
    Runs the full 8-agent pipeline for a new campaign.
 
    1. Creates a fresh CampaignContext
    2. Saves it to Redis immediately (so /status endpoint works right away)
    3. Marks all agents as IDLE in the frontend
    4. Builds and kicks off the Crew
    5. Marks campaign as DONE when all agents complete
    6. Returns the final context
 
    Args:
        campaign_id:          UUID generated by the API
        business_description: raw text from the user
        monthly_budget:       monthly budget in USD
        geo_targets:          list of location strings
 
    Returns:
        The fully populated CampaignContext after all 8 agents complete.
    """
    # Create a fresh context for this campaign
    context = CampaignContext(
        campaign_id=campaign_id,
        business_description=business_description,
        monthly_budget=monthly_budget,
        geo_targets=geo_targets,
    )
 
    # Save immediately so the status endpoint returns something straight away
    await save_context(campaign_id, context)
 
    try:
        # Mark campaign as running
        context.campaign_status = CampaignStatus.RUNNING
        await save_context(campaign_id, context)
 
        # Build the crew and kick it off
        # inputs dict is available to tasks via {variable_name} placeholders
        crew = build_crew(context)
        crew.kickoff(inputs={
            "business_description": business_description,
            "monthly_budget":       monthly_budget,
            "geo_targets":          str(geo_targets),
        })
 
        # All agents completed — mark as done
        context.campaign_status = CampaignStatus.DONE
        await save_context(campaign_id, context)
 
    except Exception as e:
        # Something failed — mark campaign as failed and save
        context.campaign_status = CampaignStatus.FAILED
        context.add_log("pipeline", f"Pipeline failed: {str(e)}", level="ERROR")
        await save_context(campaign_id, context)
        raise
 
    return context