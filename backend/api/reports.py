from fastapi import APIRouter, HTTPException
from services.redis_store import load_context

router = APIRouter()

@router.get("/{campaign_id}")
async def get_report(campaign_id: str):
    """
    GET /reports/{campaign_id}

    Returns the weekly report and performance data for a campaign.
    Used by the Reports page in the frontend.

    Returns 404 if the campaign doesn't exist or hasn't finished yet.
    Returns 425 (Too Early) if the campaign hasn't reached ReportAgent yet.
    """
    context = await load_context(campaign_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Campaign '{campaign_id}' not found.",
        )

    # ReportAgent hasn't run yet
    if not context.weekly_report:
        raise HTTPException(
            status_code=425,
            detail=(
                f"Report not ready yet for campaign '{campaign_id}'. "
                f"Current status: {context.campaign_status}. "
                f"Connect to /live/{campaign_id} to watch progress."
            ),
        )

    return {
        "campaign_id":      campaign_id,
        "campaign_status":  context.campaign_status,
        "weekly_report":    context.weekly_report,
        "performance_data": context.performance_data,
        "optimizations":    context.optimizations,
        "business_name":    context.business_profile.get("business_name", ""),
        "created_at":       str(context.created_at),
    }