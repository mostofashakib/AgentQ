from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agentq.db.engine import create_tables
from agentq.api.routes import traces, violations, evals, stream, intercept
from agentq.ingest.receiver import router as ingest_router
from agentq.api.worker import guardrail_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    task = asyncio.create_task(guardrail_worker())
    yield
    task.cancel()
    try:
        await task
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
app.include_router(evals.router)
app.include_router(stream.router)
app.include_router(intercept.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
