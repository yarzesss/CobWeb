"""Watchlist endpoints — requires JWT auth."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import TokenData, get_current_user
from app.core.cache import get_json, set_json

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


class WatchlistItemIn(BaseModel):
    wallet_address: str
    label: Optional[str] = None


class WatchlistItemOut(BaseModel):
    wallet_address: str
    label: Optional[str]
    added_at: str


def _user_key(user: TokenData) -> str:
    return f"watchlist:{user.wallet}"


@router.get("", response_model=List[WatchlistItemOut])
async def get_watchlist(
    current_user: TokenData = Depends(get_current_user),
) -> Any:
    data = await get_json(_user_key(current_user))
    return data or []


@router.post("", response_model=WatchlistItemOut)
async def add_to_watchlist(
    item: WatchlistItemIn,
    current_user: TokenData = Depends(get_current_user),
) -> Any:
    key = _user_key(current_user)
    data: List[Dict[str, Any]] = await get_json(key) or []

    if any(e.get("wallet_address") == item.wallet_address for e in data):
        raise HTTPException(status_code=400, detail="Wallet already in watchlist")

    entry = {
        "wallet_address": item.wallet_address,
        "label": item.label,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    data.append(entry)
    await set_json(key, data)  # без TTL — watchlist постійний
    return entry


@router.delete("/{wallet_address}")
async def remove_from_watchlist(
    wallet_address: str,
    current_user: TokenData = Depends(get_current_user),
) -> Any:
    key = _user_key(current_user)
    data: List[Dict[str, Any]] = await get_json(key) or []

    filtered = [e for e in data if e.get("wallet_address") != wallet_address]
    if len(filtered) == len(data):
        raise HTTPException(status_code=404, detail="Wallet not in watchlist")

    await set_json(key, filtered)
    return {"deleted": True, "wallet_address": wallet_address}