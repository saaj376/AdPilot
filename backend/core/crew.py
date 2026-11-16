import asyncio
import json
import concurrent.futures
from collections.abc import Coroutine
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
    Rejects invalid output so a failed task cannot appear successful.
    """
    import json
    import re

    if isinstance(raw_output, dict):
        return raw_output
    structured = getattr(raw_output, "json_dict", None)
    if isinstance(structured, dict):
        return structured
    model = getattr(raw_output, "pydantic", None)
    if hasattr(model, "model_dump"):
        return model.model_dump()
    value = getattr(raw_output, "raw", raw_output)
    if not isinstance(value, str):
        value = str(value)
    # Decode from the outside in; starting at the last brace loses parent keys.
    marker = re.search(r"final answer\s*:\s*", value, re.IGNORECASE)
    if marker:
        value = value[marker.end():]
    decoder = json.JSONDecoder()
    for index, char in enumerate(value):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        except json.JSONDecodeError:
            continue
    raise ValueError("Agent returned no valid JSON output")

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

_STEP_ORDER = [
    AgentName.RESEARCH,
    AgentName.KEYWORD,
    AgentName.CREATIVE,
    AgentName.QA,
    AgentName.LAUNCH,
    AgentName.MONITOR,
    AgentName.OPTIMIZE,
    AgentName.REPORT,
]


def _resolve_agent_name(step_output, fallback_index: int) -> str:
    """Resolve agent name from CrewAI callback payload with safe fallbacks."""
    # CrewAI can provide either a role string or an Agent object with .role.
    raw_agent = getattr(step_output, "agent", None)

    role_candidates: list[str] = []
    if isinstance(raw_agent, str):
        role_candidates.append(raw_agent)
    else:
        role_value = getattr(raw_agent, "role", None)
        if isinstance(role_value, str):
            role_candidates.append(role_value)

        stringified = str(raw_agent) if raw_agent is not None else ""
        if stringified:
            role_candidates.append(stringified)

    for candidate in role_candidates:
        if candidate in _ROLE_TO_AGENT_NAME:
            return _ROLE_TO_AGENT_NAME[candidate]

        normalized = candidate.strip().lower()
        for role, agent_name in _ROLE_TO_AGENT_NAME.items():
            if role.lower() in normalized:
                return agent_name

    # Final fallback: trust sequential task order for Process.sequential.
    if 0 <= fallback_index < len(_STEP_ORDER):
        return _STEP_ORDER[fallback_index]

    return ""


def _normalize_field_value(field: str, output: dict) -> dict | str:
    """Coerce agent output into the destination CampaignContext field shape."""
    if field != "weekly_report":
        return output

    if isinstance(output, dict):
        week_summary = output.get("week_summary")
        if isinstance(week_summary, str) and week_summary.strip():
            return week_summary

        raw_value = output.get("raw")
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value

    return str(output)

def build_crew(context: CampaignContext, event_loop: asyncio.AbstractEventLoop) -> Crew:
    """
    Assembles the CrewAI Crew for a full pipeline run.
    Called once per campaign by run_crew().
 
    Process.sequential means agents run one after another
    in the exact order listed — never in parallel.
    """
 
    # Callbacks run in kickoff's worker thread. Wait for persistence and event
    # delivery before allowing the next task or terminal state to proceed.
    def _schedule(coro: Coroutine) -> None:
        asyncio.run_coroutine_threadsafe(coro, event_loop).result()

    step_index = 0

    def on_step(step_output):
        nonlocal step_index
        if context.campaign_status == CampaignStatus.FAILED:
            raise RuntimeError("Pipeline has already failed")
        agent_name = _resolve_agent_name(step_output, step_index)
 
        if not agent_name:
            return

        previous_status = str(context.agent_states[agent_name].status)
        agent_order_index = _STEP_ORDER.index(agent_name) if agent_name in _STEP_ORDER else -1

        output = _parse_agent_output(step_output)
        if output.get("error"):
            raise ValueError(f"{agent_name}: {output['error']}")
        if agent_name == AgentName.QA and output.get("overall_approved") is not True:
            raise ValueError("Policy review did not approve the campaign; launch stopped")
        if agent_name == AgentName.LAUNCH and not output.get("campaign_id"):
            raise ValueError("Launch returned no campaign ID")
        field = _AGENT_OUTPUT_FIELD.get(agent_name)
        if field and hasattr(context, field):
            setattr(context, field, _normalize_field_value(field, output))
        context.set_agent_done(agent_name, output=output)

        just_completed = previous_status != "DONE"
        if just_completed and agent_order_index >= 0 and agent_order_index >= step_index:
            step_index = agent_order_index + 1
 
        # Log a completion message
        context.add_log(
            agent_name,
            f"{agent_name} completed successfully.",
            level="INFO",
        )
 
        # Save updated context to Redis after every agent
        # This means progress is never lost if the server restarts mid-pipeline
        _schedule(save_context(context.campaign_id, context))
 
        # Push live event to WebSocket
        # Import here to avoid circular imports at module level
        from core.event_bus import event_bus
        from models.agent_run import PipelineEvent
 
        event = PipelineEvent(
            campaign_id=context.campaign_id,
            agent_name=agent_name,
            status=context.agent_states[agent_name].status,
            output=context.agent_states[agent_name].output,
            log=context.agent_states[agent_name].logs[-1]
            if context.agent_states[agent_name].logs else None,
        )
        _schedule(event_bus.publish(context.campaign_id, event))

        # In sequential mode, immediately move the next agent to RUNNING so
        # the UI reflects progress even while the next step is in-flight.
        if just_completed and step_index < len(_STEP_ORDER):
            next_agent = _STEP_ORDER[step_index]
            next_state = context.agent_states.get(next_agent)
            if next_state and next_state.status == "IDLE":
                context.set_agent_running(next_agent)
                context.add_log(next_agent, f"{next_agent} started.", level="INFO")

                _schedule(save_context(context.campaign_id, context))

                next_event = PipelineEvent(
                    campaign_id=context.campaign_id,
                    agent_name=next_agent,
                    status=context.agent_states[next_agent].status,
                    output=context.agent_states[next_agent].output,
                    log=context.agent_states[next_agent].logs[-1]
                    if context.agent_states[next_agent].logs else None,
                )
                _schedule(event_bus.publish(context.campaign_id, next_event))
 
    crew = Crew(
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
        task_callback=on_step,        # only completed tasks, never tool actions
        verbose=True,                 # prints agent thinking to console
    )
    # CrewAI mutates tasks and agents during execution. Copy the graph together
    # so task.context references stay linked while concurrent campaigns isolate.
    return crew.copy()



async def run_crew(
    campaign_id: str,
    business_description: str,
    monthly_budget: float,
    geo_targets: list[str],
    landing_page_url: str = "",
    research_brief: dict | None = None,
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
        landing_page_url=landing_page_url,
        research_brief=research_brief,
        business_description=business_description,
        monthly_budget=monthly_budget,
        geo_targets=geo_targets,
    )
 
    # Save immediately so the status endpoint returns something straight away
    await save_context(campaign_id, context)
 
    try:
        # Mark campaign as running
        context.campaign_status = CampaignStatus.RUNNING
        context.set_agent_running(AgentName.RESEARCH)
        context.add_log(AgentName.RESEARCH, f"{AgentName.RESEARCH} started.", level="INFO")
        await save_context(campaign_id, context)

        from core.event_bus import event_bus
        from models.agent_run import PipelineEvent

        await event_bus.publish(
            campaign_id,
            PipelineEvent(
                campaign_id=campaign_id,
                agent_name=AgentName.RESEARCH,
                status=context.agent_states[AgentName.RESEARCH].status,
                output=context.agent_states[AgentName.RESEARCH].output,
                log=context.agent_states[AgentName.RESEARCH].logs[-1],
            ),
        )
 
        # Build the crew and kick it off
        # inputs dict is available to tasks via {variable_name} placeholders
        loop = asyncio.get_running_loop()
        crew = build_crew(context, loop)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    crew.kickoff,
                    inputs={
                        "landing_page_url": landing_page_url,
                        "video_research": json.dumps({
                            'input': research_brief.get('input'), 'analysis': research_brief.get('analysis')
                        }) if research_brief else 'No video research supplied.',
                        "business_description": business_description,
                        "monthly_budget":       monthly_budget,
                        "geo_targets":          str(geo_targets),
                    },
                ),
                timeout=600,
            )
        except TimeoutError as exc:
            raise RuntimeError(
                "Pipeline exceeded 10 minutes while executing an agent step. "
                "Check Ollama responsiveness and external tool latency."
            ) from exc
        except concurrent.futures.TimeoutError as exc:
            raise RuntimeError(
                "Pipeline worker thread timed out while executing Crew kickoff."
            ) from exc
 
        if not context.is_complete():
            raise RuntimeError("Pipeline ended before all agent tasks completed")
        # All agents completed — mark as done
        context.campaign_status = CampaignStatus.DONE
        await save_context(campaign_id, context)
 
    except Exception as e:
        # Something failed — mark campaign as failed and save
        for name, state in context.agent_states.items():
            if state.status == "RUNNING":
                context.set_agent_failed(name, str(e))
                context.add_log(name, str(e), level="ERROR")
        context.campaign_status = CampaignStatus.FAILED
        context.add_log("pipeline", f"Pipeline failed: {str(e)}", level="ERROR")
        await save_context(campaign_id, context)

    finally:
        # Always signal WebSocket listeners that this run reached a terminal state.
        from core.event_bus import event_bus
        await event_bus.publish_done(campaign_id)
 
    return context