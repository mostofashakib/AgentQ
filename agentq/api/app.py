import logging
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agentq.api.mcp_auth import MCPAuthMiddleware
from agentq.api.rate_limit import RateLimitMiddleware
from agentq.config import settings
from agentq.db.engine import create_tables, async_session
from agentq.api.routes import traces, violations, stream, intercept, graph
from agentq.api.routes import behaviors as behaviors_route
from agentq.api.routes import alerts as alerts_route
from agentq.api.routes import agents as agents_route
from agentq.api.routes import settings as settings_route
from agentq.api.routes import report as report_route
from agentq.api.routes import monitoring as monitoring_route
from agentq.api.routes import approvals as approvals_route
from agentq.api.routes import product_analytics as product_analytics_route
from agentq.ingest.receiver import router as ingest_router
from agentq.api.worker import guardrail_worker
from agentq.behaviors.worker import behavior_worker
from agentq.api.alerts.worker import alert_worker
from agentq.mcp.server import mcp as mcp_server
from agentq.monitoring.retention import prune_expired_telemetry
from agentq.utils.tasks import BackgroundTaskGroup
from agentq.demo.startup import seed_demo_if_enabled

logger = logging.getLogger(__name__)

mcp_app = mcp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
        await create_tables()
        if settings.auth_required and not any(
            [settings.admin_api_key, settings.viewer_api_key, settings.ingest_api_key]
        ):
            logger.error(
                "AUTH_REQUIRED but no API keys are configured "
                "(ADMIN_API_KEY / VIEWER_API_KEY / INGEST_API_KEY). "
                "Every request will be rejected until at least one is set — see .env.example."
            )
        async with async_session() as session:
            await prune_expired_telemetry(session)
        await seed_demo_if_enabled(enabled=settings.demo_mode, session_factory=async_session)
        async with BackgroundTaskGroup() as workers:
            workers.start(guardrail_worker(), name="guardrail-worker")
            workers.start(behavior_worker(), name="behavior-worker")
            workers.start(alert_worker(), name="alert-worker")
            yield


app = FastAPI(title="AgentQ", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

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
app.include_router(report_route.router)
app.include_router(monitoring_route.router)
app.include_router(approvals_route.router)
app.include_router(product_analytics_route.router)

app.mount("/mcp", MCPAuthMiddleware(mcp_app))

if settings.demo_mode:
    from agentq.api.routes import demo as demo_route
    app.include_router(demo_route.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
