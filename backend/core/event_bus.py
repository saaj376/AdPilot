import asyncio
from collections import defaultdict
from models.agent_run import PipelineEvent

# The event bus is the bridge between crew.py and the WebSocket endpoint.
#
# How it works:
#   - crew.py's on_step() calls event_bus.publish() after each agent completes
#   - ws.py's WebSocket handler calls event_bus.subscribe() when a client connects
#   - The WebSocket loop reads from the queue and streams events to the browser
#
# It is entirely in-memory — no Redis, no persistence.
# If the server restarts, live connections drop and reconnect.
# Historical events are not replayed — clients get live events only.
# Past state is available via GET /campaigns/:id/status (reads from Redis).
#
# One asyncio.Queue per campaign_id — multiple browser tabs can subscribe
# to the same campaign and all receive the same events.

class EventBus:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
    def subscribe(self, campaign_id: str) -> asyncio.Queue:
        """
        Creates a new queue for a WebSocket client and registers it.
        Called by ws.py when a browser connects to /live/{campaign_id}.
 
        Returns the queue — the WebSocket reads from it in a loop.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[campaign_id].append(queue)
        return queue
    
    def unsubscribe(self, campaign_id: str, queue: asyncio.Queue):
        """
        removes a queue when the websocket client disconnects
        called by ws.py when a browser disconnects from /live/{campaign_id}
        cleans up the queue list so we don't accumulate dead queues.
        """
        if campaign_id in self._queues:
            self._queues[campaign_id].remove(queue)
            if not self._queues[campaign_id]:  # If the list is empty, remove
                del self._queues[campaign_id]
    
    async def publish(self, campaign_id: str, event: PipelineEvent) -> None:
        """
        Pushes an event to all subscribers for a campaign.
        Called by crew.py's on_step() after each agent completes.
 
        If no subscribers are connected (e.g. browser tab is closed),
        the event is silently dropped — that's fine, context is in Redis.
        """
        for queue in self._queues.get(campaign_id, []):
            await queue.put(event)
    
    async def publish_done(self, campaign_id: str) -> None:
        """
        Special method to signal that a campaign has completed.
        Called by crew.py when the entire pipeline finishes.
 
        It sends a "done" event to all subscribers, which can trigger cleanup
        or UI updates in the browser.
        """
        for queue in self._queues.get(campaign_id, []):
            await queue.put(None)

event_bus = EventBus()