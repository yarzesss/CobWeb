"""Wallet profiler endpoints."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.helius import get_helius_client
from app.services.pnl import calculate_wallet_pnl
from app.services.classifier import (
    compute_bot_score,
    compute_smart_money_score,
    classify_wallet_archetype,
)

router = APIRouter(prefix="/wallet", tags=["Wallet"])


def _extract_heuristics(txs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute bot-score inputs and behavioral stats from raw transactions.
    """
    if not txs:
        return {}

    timestamps = sorted([
        tx.get("timestamp") for tx in txs
        if tx.get("timestamp")
    ])

    # Min interval between transactions in ms
    min_interval_ms = None
    if len(timestamps) > 1:
        intervals = [
            (timestamps[i + 1] - timestamps[i]) * 1000
            for i in range(len(timestamps) - 1)
        ]
        min_interval_ms = min(intervals) if intervals else None

    # Daily tx count (last 24h)
    if timestamps:
        last_ts = timestamps[-1]
        day_ago = last_ts - 86400
        daily_count = sum(1 for t in timestamps if t >= day_ago)
    else:
        daily_count = 0

    # Favorite DEX — extract from source/program interactions
    dex_counter: Counter = Counter()
    for tx in txs:
        source = tx.get("source") or tx.get("program") or ""
        if source:
            dex_counter[source] += 1
    favorite_dex = dex_counter.most_common(1)[0][0] if dex_counter else None

    # First seen / last active
    first_seen = datetime.fromtimestamp(timestamps[0], tz=timezone.utc) if timestamps else None
    last_active = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc) if timestamps else None

    return {
        "min_tx_interval_ms": min_interval_ms,
        "daily_tx_count": daily_count,
        "favorite_dex": favorite_dex,
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_active": last_active.isoformat() if last_active else None,
    }


@router.get("/{address}", summary="Full wallet profile")
async def wallet_profile(address: str) -> Dict[str, Any]:
    """
    Returns full wallet profile:
    - Archetype classification
    - Bot score
    - Smart Money score
    - Winrate, PnL, avg hold time
    - Favorite DEX, first seen, last active
    """
    helius = get_helius_client()

    # Fetch transactions and PnL in parallel
    txs, pnl = await asyncio.gather(
        helius.get_wallet_transactions(address, limit=500),
        calculate_wallet_pnl(address, limit=500),
    )

    heuristics = _extract_heuristics(txs)
    summary = pnl.get("summary", {})

    winrate = summary.get("winrate", 0.0)
    total_trades = summary.get("total_trades", 0)
    avg_hold = summary.get("avg_hold_time_minutes", 0.0)
    avg_position = summary.get("avg_position_size_usd", 0.0)
    total_pnl = summary.get("total_realized_usd", 0.0)

    bot_score = compute_bot_score(
        min_tx_interval_ms=heuristics.get("min_tx_interval_ms"),
        daily_tx_count=heuristics.get("daily_tx_count"),
        avg_blocks_after_deploy=None,   # requires per-token analysis
        position_size_variance=None,    # requires per-token analysis
    )

    smart_money = compute_smart_money_score(
        winrate=winrate,
        total_trades=total_trades,
        avg_hold_time_minutes=avg_hold,
        avg_position_size_usd=avg_position,
        bot_score=bot_score,
    )

    archetype = classify_wallet_archetype({
        "bot_score": bot_score,
        "smart_money_score": smart_money,
        "winrate": winrate,
        "total_trades": total_trades,
        "avg_hold_time_minutes": avg_hold,
        "avg_position_size_usd": avg_position,
        "avg_blocks_after_deploy": None,
    })

    return {
        "wallet_address": address,
        "archetype": archetype,
        "bot_score": bot_score,
        "smart_money_score": smart_money,
        "winrate": winrate,
        "total_trades": total_trades,
        "total_pnl_usd": total_pnl,
        "avg_position_size_usd": avg_position,
        "avg_hold_time_minutes": avg_hold,
        "favorite_dex": heuristics.get("favorite_dex"),
        "first_seen": heuristics.get("first_seen"),
        "last_active": heuristics.get("last_active"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{address}/trades", summary="Wallet trade history")
async def wallet_trades(
    address: str,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(address, limit=limit + offset)

    if isinstance(txs, dict) and txs.get("error"):
        raise HTTPException(status_code=502, detail="Failed to fetch transactions")

    page = txs[offset: offset + limit] if isinstance(txs, list) else []
    return {
        "wallet_address": address,
        "total": len(txs) if isinstance(txs, list) else 0,
        "limit": limit,
        "offset": offset,
        "trades": page,
    }


@router.get("/{address}/pnl", summary="Wallet PnL breakdown")
async def wallet_pnl(address: str) -> Dict[str, Any]:
    return await calculate_wallet_pnl(address)