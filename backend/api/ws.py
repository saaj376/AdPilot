import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.event_bus import event_bus
from services.redis_store import load_context


router = APIRouter()


@router.websocket("/{campaign_id}")
async def campaign_live_stream(websocket: WebSocket, campaign_id: str):
    """
    WS /live/{campaign_id}

    Streams live agent events to the frontend as JSON.
    The frontend AgentPipeline component connects here when a campaign starts.

    How it works:
    1. Client connects to ws://localhost:8000/live/{campaign_id}
    2. We send any existing agent states immediately (catch-up for late joins)
    3. We subscribe to the event_bus for this campaign
    4. We loop — waiting for events and sending them as JSON
    5. When the pipeline finishes (None sentinel) or client disconnects, we close

    Each message sent to the client is a JSON object like:
    {
        "campaign_id":  "abc-123",
        "agent_name":   "ResearchAgent",
        "status":       "DONE",
        "log": {
            "agent_name": "ResearchAgent",
            "message":    "ResearchAgent completed successfully.",
            "level":      "INFO",
            "timestamp":  "2025-01-01T00:00:00"
        },
        "timestamp": "2025-01-01T00:00:00"
    }
    """
    await websocket.accept()

    async def _safe_send(payload: dict) -> bool:
        """Send payload, returning False if client disconnected mid-send."""
        try:
            await websocket.send_text(json.dumps(payload))
            return True
        except (WebSocketDisconnect, RuntimeError):
            return False

    queue = None

    # Send current state immediately so the client gets the full picture
    # even if it connects after some agents have already finished
    context = await load_context(campaign_id)
    if context:
        sent = await _safe_send({
            "type":          "catch_up",
            "campaign_id":   campaign_id,
            "campaign_status": context.campaign_status,
            "agent_states":  {
                name: {
                    "status":     state.status,
                    "started_at": str(state.started_at) if state.started_at else None,
                    "finished_at": str(state.finished_at) if state.finished_at else None,
                    "output":     state.output,
                    "logs": [
                        {"message": log.message, "level": log.level, "timestamp": str(log.timestamp)}
                        for log in state.logs
                    ],
                }
                for name, state in context.agent_states.items()
            },
        })
        if not sent:
            return

    # Subscribe to live events for this campaign
    queue = event_bus.subscribe(campaign_id)

    try:
        while True:
            # Wait for the next event from crew.py's on_step()
            event = await queue.get()

            # None is the sentinel value meaning the pipeline is done
            if event is None:
                sent = await _safe_send({
                    "type":        "pipeline_done",
                    "campaign_id": campaign_id,
                })
                if not sent:
                    break
                break

            # Send the event as JSON to the browser
            sent = await _safe_send({
                "type":        "agent_update",
                "campaign_id": event.campaign_id,
                "agent_name":  event.agent_name,
                "status":      event.status,
                "output":      event.output,
                "log": {
                    "message":   event.log.message,
                    "level":     event.log.level,
                    "timestamp": str(event.log.timestamp),
                } if event.log else None,
                "timestamp":   str(event.timestamp),
            })
            if not sent:
                break

    except WebSocketDisconnect:
        # Client closed the tab or navigated away — clean up silently
        pass

    finally:
        # Always unsubscribe when done — prevents memory leaks
        if queue is not None:
            event_bus.unsubscribe(campaign_id, queue)
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError):
            pass