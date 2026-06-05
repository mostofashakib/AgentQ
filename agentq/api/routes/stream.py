import asyncio
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/stream", tags=["stream"])

# module-level set of subscriber queues
_subscribers: set[asyncio.Queue] = set()


def broadcast(event_type: str, data: dict) -> None:
    """Broadcast an event to all SSE subscribers. Call from background workers."""
    payload = json.dumps({"type": event_type, "data": data})
    dead = set()
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.add(q)
    _subscribers.difference_update(dead)


@router.get("")
async def stream_events():
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)

    async def event_generator():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {"data": payload}
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"type": "ping"})}
        finally:
            _subscribers.discard(queue)

    return EventSourceResponse(event_generator())
