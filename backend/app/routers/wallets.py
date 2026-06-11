"""Wallet profiler endpoints."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.services.helius import get_helius_client
from app.services.pnl import calculate_wallet_pnl
from app.services.classifier import (
    compute_bot_score,
    compute_smart_money_score,
    classify_wallet_archetype,
)

router = APIRouter(prefix="/wallet", tags=["Wallet"])


def _validate_address(address: str) -> None:
    if not (32 <= len(address) <= 44) or not address.isalnum():
        raise HTTPException(status_code=400, detail="Invalid wallet address")


def _extract_heuristics(txs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not txs:
        return {}

    timestamps = sorted([tx.get("timestamp") for tx in txs if tx.get("timestamp")])

    min_interval_ms = None
    if len(timestamps) > 1:
        intervals = [
            (timestamps[i + 1] - timestamps[i]) * 1000
            for i in range(len(timestamps) - 1)
        ]
        # Same-second tx pairs give 0ms — ignore exact duplicates from one bundle
        positive = [i for i in intervals if i > 0]
        min_interval_ms = min(positive) if positive else 0

    daily_count = 0
    if timestamps:
        day_ago = timestamps[-1] - 86400
        daily_count = sum(1 for t in timestamps if t >= day_ago)

    dex_counter: Counter = Counter()
    for tx in txs:
        source = tx.get("source") or ""
        if source and source != "UNKNOWN":
            dex_counter[source] += 1
    favorite_dex = dex_counter.most_common(1)[0][0] if dex_counter else None

    first_seen = datetime.fromtimestamp(timestamps[0], tz=timezone.utc).isoformat() if timestamps else None
    last_active = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).isoformat() if timestamps else None

    return {
        "min_tx_interval_ms": min_interval_ms,
        "daily_tx_count": daily_count,
        "favorite_dex": favorite_dex,
        "first_seen": first_seen,
        "last_active": last_active,
    }


@router.get("/{address}", summary="Full wallet profile")
async def wallet_profile(address: str) -> Dict[str, Any]:
    _validate_address(address)
    helius = get_helius_client()

    txs, pnl = await asyncio.gather(
        helius.get_wallet_transactions(address, limit=500),
        calculate_wallet_pnl(address, limit=500),
    )

    heuristics = _extract_heuristics(txs)
    summary = pnl.get("summary", {})

    winrate = summary.get("winrate", 0.0)
    total_trades = summary.get("total_trades", 0)
    avg_hold = summary.get("avg_hold_time_minutes", 0.0)
    avg_position_usd = summary.get("avg_position_size_usd", 0.0)
    avg_position_sol = summary.get("avg_position_size_sol", 0.0)
    total_sol_pnl = summary.get("total_sol_pnl", 0.0)
    total_usd_pnl = summary.get("total_realized_usd", 0.0)
    favorite_dex = summary.get("favorite_dex") or heuristics.get("favorite_dex")

    bot_score = compute_bot_score(
        min_tx_interval_ms=heuristics.get("min_tx_interval_ms"),
        daily_tx_count=heuristics.get("daily_tx_count"),
    )

    smart_money = compute_smart_money_score(
        winrate=winrate,
        total_trades=total_trades,
        avg_hold_time_minutes=avg_hold,
        avg_position_size_usd=avg_position_usd,
        bot_score=bot_score,
    )

    archetype = classify_wallet_archetype({
        "bot_score": bot_score,
        "smart_money_score": smart_money,
        "winrate": winrate,
        "total_trades": total_trades,
        "avg_hold_time_minutes": avg_hold,
        "avg_position_size_usd": avg_position_usd,
    })

    return {
        "wallet_address": address,
        "archetype": archetype,
        "bot_score": bot_score,
        "smart_money_score": smart_money,
        "winrate": winrate,
        "total_trades": total_trades,
        "completed_trades": summary.get("completed_trades", 0),
        "total_pnl_usd": total_usd_pnl,
        "total_pnl_sol": total_sol_pnl,
        "usd_is_estimate": summary.get("usd_is_estimate", True),
        "avg_position_size_usd": avg_position_usd,
        "avg_position_size_sol": avg_position_sol,
        "avg_hold_time_minutes": avg_hold,
        "favorite_dex": favorite_dex,
        "first_seen": heuristics.get("first_seen"),
        "last_active": heuristics.get("last_active"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{address}/trades", summary="Wallet trade history")
async def wallet_trades(address: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    _validate_address(address)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(address, limit=limit + offset)

    if isinstance(txs, dict) and txs.get("error"):
        raise HTTPException(status_code=502, detail="Failed to fetch transactions")

    page = txs[offset: offset + limit] if isinstance(txs, list) else []

    # Slim payload — frontend only renders these fields
    trades = [
        {
            "signature": tx.get("signature"),
            "timestamp": tx.get("timestamp"),
            "type": tx.get("type"),
            "source": tx.get("source"),
            "description": tx.get("description"),
        }
        for tx in page
    ]
    return {
        "wallet_address": address,
        "total": len(txs) if isinstance(txs, list) else 0,
        "limit": limit,
        "offset": offset,
        "trades": trades,
    }


@router.get("/{address}/pnl", summary="Wallet PnL breakdown")
async def wallet_pnl(address: str) -> Dict[str, Any]:
    _validate_address(address)
    return await calculate_wallet_pnl(address)