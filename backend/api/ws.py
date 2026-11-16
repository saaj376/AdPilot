import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.event_bus import event_bus
from services.redis_store import load_context

router = APIRouter()
TERMINAL_STATUSES = {"DONE", "FAILED", "PAUSED"}


@router.websocket("/{campaign_id}")
async def campaign_live_stream(websocket: WebSocket, campaign_id: str):
    await websocket.accept()
    # Subscribe before reading the snapshot so transitions cannot fall in a gap.
    queue = event_bus.subscribe(campaign_id)
    disconnected = asyncio.create_task(websocket.receive())
    pending = None
    try:
        context = await load_context(campaign_id)
        if context is None:
            await websocket.close(code=1008, reason="Campaign not found")
            return
        snapshot = context.model_dump(mode="json")
        await websocket.send_json({
            "type": "catch_up",
            "campaign_id": campaign_id,
            "campaign_status": snapshot["campaign_status"],
            "agent_states": snapshot["agent_states"],
        })
        if context.campaign_status in TERMINAL_STATUSES:
            await websocket.send_json({"type": "pipeline_done", "campaign_id": campaign_id,
                                       "campaign_status": context.campaign_status})
            return
        while True:
            pending = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait({pending, disconnected}, return_when=asyncio.FIRST_COMPLETED)
            if disconnected in done:
                message = disconnected.result()
                if message["type"] == "websocket.disconnect":
                    break
                disconnected = asyncio.create_task(websocket.receive())
                if pending not in done:
                    pending.cancel()
                    continue
            event = pending.result()
            if event is None:
                context = await load_context(campaign_id)
                await websocket.send_json({"type": "pipeline_done", "campaign_id": campaign_id,
                                           "campaign_status": context.campaign_status if context else "FAILED"})
                break
            await websocket.send_json({"type": "agent_update", **event.model_dump(mode="json")})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        for task in (pending, disconnected):
            if task is not None:
                task.cancel()
        await asyncio.gather(*(task for task in (pending, disconnected) if task is not None),
                             return_exceptions=True)
        event_bus.unsubscribe(campaign_id, queue)
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError):
            pass
