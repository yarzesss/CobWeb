"""Cobweb FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core import cache
from app.services.helius import get_helius_client
from app.routers import auth as auth_router
from app.routers import tokens as tokens_router
from app.routers import wallets as wallets_router
from app.routers import watchlist as watchlist_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    await cache.get_redis()
    yield
    # ── Shutdown ──
    await cache.close()
    await get_helius_client().aclose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["https://cobweb.so"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(tokens_router.router)
app.include_router(wallets_router.router)
app.include_router(watchlist_router.router)


@app.get("/healthz", tags=["Health"])
async def healthz() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}