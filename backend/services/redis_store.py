import json
import redis.asyncio as aioredis
from config import settings
from core.campaign_context import CampaignContext

_redis_client: aioredis.Redis | None = None

def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client

async def check_redis_health() -> None:
    try:
        client = get_redis()
        await client.ping()
        print("Redis healthy.")
    except Exception as e:
        raise RuntimeError(
            f"Redis is not reachable at '{settings.REDIS_URL}'. "
            f"Start it with: redis-server\n"
            f"Error: {e}"
        )
 
 
def _context_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}"
 
 
async def save_context(campaign_id: str, context: CampaignContext) -> None:
    """
    Serialises CampaignContext to JSON and stores it in Redis.
    Called by crew.py's on_step() after every agent completes.
    TTL is set from REDIS_TTL_SECONDS (default 7 days).
    """
    client = get_redis()
    await client.setex(
        name=_context_key(campaign_id),
        time=settings.REDIS_TTL_SECONDS,
        value=context.model_dump_json(),
    )
 
 
async def load_context(campaign_id: str) -> CampaignContext | None:
    """
    Loads and deserialises a CampaignContext from Redis.
    Returns None if the campaign doesn't exist or has expired.
    """
    client = get_redis()
    raw = await client.get(_context_key(campaign_id))
    if raw is None:
        return None
    return CampaignContext.model_validate_json(raw)
 
 
async def delete_context(campaign_id: str) -> None:
    """Removes a campaign context from Redis."""
    client = get_redis()
    await client.delete(_context_key(campaign_id))
 
_CAMPAIGN_IDS_KEY = "active_campaign_ids"
 
 
async def add_active_campaign(campaign_id: str) -> None:
    """
    Adds a campaign_id to the active campaigns set.
    Called when a new campaign is created via POST /campaigns.
    """
    client = get_redis()
    await client.sadd(_CAMPAIGN_IDS_KEY, campaign_id)
 
 
async def remove_active_campaign(campaign_id: str) -> None:
    """Removes a campaign_id from the active campaigns set."""
    client = get_redis()
    await client.srem(_CAMPAIGN_IDS_KEY, campaign_id)
 
 
async def get_all_campaign_ids() -> list[str]:
    """
    Returns all active campaign IDs.
    Used by GET /campaigns and the daily scheduler loop.
    """
    client = get_redis()
    ids = await client.smembers(_CAMPAIGN_IDS_KEY)
    return list(ids)
 
 
# ─── Scheduler state ──────────────────────────────────────────────────────────
 
_SCHEDULER_STATE_KEY = "scheduler_state"
 
 
async def save_scheduler_state(state: dict) -> None:
    """
    Persists scheduler state (last run times etc.) to Redis.
    Called by scheduler.py after each daily loop run.
    """
    client = get_redis()
    await client.set(_SCHEDULER_STATE_KEY, json.dumps(state))
 
 
async def load_scheduler_state() -> dict:
    """
    Loads scheduler state on server restart.
    Returns empty dict if no state exists yet.
    """
    client = get_redis()
    raw = await client.get(_SCHEDULER_STATE_KEY)
    if raw is None:
        return {}
    return json.loads(raw)