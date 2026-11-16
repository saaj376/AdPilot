import json
from uuid import uuid4
from fastapi.responses import Response
from services.video_research import load_brief

from fastapi import APIRouter, BackgroundTasks, HTTPException

from core.crew import run_crew
from core.campaign_context import CampaignContext
from models.campaign import (
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignStatus,
)
from services.redis_store import (
    add_active_campaign,
    get_all_campaign_ids,
    load_context,
    save_context,
)
router = APIRouter()

@router.post("", response_model=CampaignCreateResponse, status_code=202)
async def create_campaign(
    request: CampaignCreateRequest,
    background_tasks: BackgroundTasks,
):
    """
    POST /campaigns

    Starts a new campaign pipeline run.

    Returns immediately with a campaign_id — the pipeline runs in the background.
    The frontend connects to WS /live/{campaign_id} to get live agent updates.

    Status 202 means "accepted" — the request was valid and work has started,
    but it's not finished yet. This is the correct HTTP status for async jobs.
    """
    research_brief = None
    if request.research_brief_id:
        research_brief = await load_brief(request.research_brief_id)
        if research_brief is None or research_brief['status'] != 'ready':
            raise HTTPException(422, 'Select a completed research brief before creating the campaign')

    # Generate a unique ID for this campaign
    campaign_id = str(uuid4())

    await save_context(campaign_id, CampaignContext(
        campaign_id=campaign_id,
        landing_page_url=str(request.landing_page_url or ""),
        research_brief=research_brief,
        business_description=request.business_description,
        monthly_budget=request.monthly_budget,
        geo_targets=request.geo_targets,
    ))

    # Register it in the active campaigns set in Redis
    await add_active_campaign(campaign_id)

    # Run the pipeline in the background — don't wait for it to finish
    # BackgroundTasks runs after the response is sent to the client
    background_tasks.add_task(
        run_crew,
        campaign_id=campaign_id,
        landing_page_url=str(request.landing_page_url or ""),
        research_brief=research_brief,
        business_description=request.business_description,
        monthly_budget=request.monthly_budget,
        geo_targets=request.geo_targets,
    )

    return CampaignCreateResponse(
        campaign_id=campaign_id,
        status=CampaignStatus.PENDING,
        message=f"Pipeline started. Connect to /live/{campaign_id} for live updates.",
    )


@router.get("")
async def list_campaigns():
    """
    GET /campaigns

    Returns all campaign IDs stored in Redis.
    The frontend uses this to populate the campaign list on the Home page.
    """
    ids = await get_all_campaign_ids()
    return {"campaign_ids": ids, "count": len(ids)}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """
    GET /campaigns/{campaign_id}

    Returns the full CampaignContext for a campaign.
    Used by the CampaignDetail page to show all agent outputs.
    """
    context = await load_context(campaign_id)
    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Campaign '{campaign_id}' not found. It may have expired.",
        )
    return context.model_dump()


@router.get("/{campaign_id}/status")
async def get_campaign_status(campaign_id: str):
    """
    GET /campaigns/{campaign_id}/status

    Returns only the agent_states and campaign_status.
    Lightweight polling fallback for clients that can't use WebSocket.
    Much faster than loading the full context.
    """
    context = await load_context(campaign_id)
    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Campaign '{campaign_id}' not found.",
        )
    return {
        "campaign_id":     campaign_id,
        "campaign_status": context.campaign_status,
        "agent_states":    {
            name: {
                "status":      state.status,
                "started_at":  state.started_at,
                "finished_at": state.finished_at,
            }
            for name, state in context.agent_states.items()
        },
    }

@router.get("/{campaign_id}/export")
async def export_campaign(campaign_id: str):
    context = await load_context(campaign_id)
    if context is None:
        raise HTTPException(404, "Campaign plan not found")
    if context.campaign_status != CampaignStatus.DONE:
        raise HTTPException(409, "Campaign plan is not ready for export")
    payload = {
        "campaign_id": campaign_id, "published": False,
        "business_description": context.business_description,
        "landing_page_url": context.landing_page_url,
        "monthly_budget": context.monthly_budget, "geo_targets": context.geo_targets,
        "research_brief": context.research_brief, "business_profile": context.business_profile,
        "keyword_strategy": context.keyword_strategy, "ad_creatives": context.ad_creatives,
        "qa_result": context.qa_result, "campaign_plan": context.weekly_report,
        "launch_package": context.launch_package, "measurement_plan": context.performance_data,
        "optimization_recommendations": context.optimizations,
    }
    return Response(json.dumps(payload, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="campaign-plan.json"'})
