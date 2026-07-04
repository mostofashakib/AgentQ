from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agentq.config import settings
from agentq.db.engine import create_tables, async_session
from agentq.api.routes import traces, violations, stream, intercept, graph
from agentq.api.routes import behaviors as behaviors_route
from agentq.api.routes import alerts as alerts_route
from agentq.api.routes import agents as agents_route
from agentq.api.routes import settings as settings_route
from agentq.ingest.receiver import router as ingest_router
from agentq.api.worker import guardrail_worker
from agentq.behaviors.worker import behavior_worker
from agentq.api.alerts.worker import alert_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    if settings.demo_mode:
        from agentq.demo.seed import seed_demo
        async with async_session() as session:
            await seed_demo(session)
    task = asyncio.create_task(guardrail_worker())
    behavior_task = asyncio.create_task(behavior_worker())
    alert_task = asyncio.create_task(alert_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    behavior_task.cancel()
    try:
        await behavior_task
    except asyncio.CancelledError:
        pass
    alert_task.cancel()
    try:
        await alert_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AgentQ", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(traces.router)
app.include_router(violations.router)
app.include_router(stream.router)
app.include_router(intercept.router)
app.include_router(graph.router)
app.include_router(behaviors_route.router)
app.include_router(alerts_route.router)
app.include_router(agents_route.router)
app.include_router(settings_route.router)

if settings.demo_mode:
    from agentq.api.routes import demo as demo_route
    app.include_router(demo_route.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
