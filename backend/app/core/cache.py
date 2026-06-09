"""Redis cache helpers for Cobweb."""
from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def get_json(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


async def set_json(key: str, value: Any, ttl: Optional[int] = None) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)


async def delete_key(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def close() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None