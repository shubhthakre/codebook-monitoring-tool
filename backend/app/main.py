from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import health, monitors, settings
from .services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


def _init_oracle_client() -> None:
    try:
        from .checkers.database import _ensure_oracle_client

        mode = _ensure_oracle_client()
        logger.info("Oracle client mode: %s", mode)
    except Exception as exc:
        logger.warning("Oracle client init skipped/failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _init_oracle_client()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Codebook Monitoring Tool",
    description="Lightweight health checks for servers, databases, and systemd services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(monitors.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
