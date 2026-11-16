from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.campaigns import router as campaigns_router
from api.reports import router as reports_router
from api.ws import router as ws_router
from api.research import router as research_router

app.include_router(research_router, prefix="/research", tags=["research"])
app.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
app.include_router(reports_router,   prefix="/reports",   tags=["reports"])
app.include_router(ws_router,        prefix="/live",      tags=["websocket"])


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {
        "status":  "ok",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "model":   settings.OLLAMA_MODEL,
    }

async def startup():
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    from services.llm_client import check_ollama_health
    await check_ollama_health()

    from services.redis_store import check_redis_health
    await check_redis_health()

    from core.scheduler import start_scheduler
    start_scheduler()

    print("All systems ready.")


async def shutdown():
    print("Shutting down...")

    from core.scheduler import stop_scheduler
    stop_scheduler()

    from services.redis_store import close_redis
    await close_redis()
