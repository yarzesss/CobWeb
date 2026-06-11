"""Token analysis endpoints."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.helius import get_helius_client
from app.services.cabal import analyze_cabal
from app.services.classifier import compute_dev_risk, classify_dev_risk

router = APIRouter(prefix="/token", tags=["Token"])


def _validate_ca(ca: str) -> None:
    if not (32 <= len(ca) <= 44) or not ca.isalnum():
        raise HTTPException(status_code=400, detail="Invalid contract address")


async def _get_dev_risk(
    dev_wallet: Optional[str],
    ca: Optional[str] = None,
    launch_ts: Optional[int] = None,
) -> Dict[str, Any]:
    if not dev_wallet:
        return {"score": 0, "level": "LOW", "dev_wallet": None}

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(dev_wallet, limit=300)
    txs = sorted(txs, key=lambda t: t.get("timestamp") or 0)

    # Distinct tokens the deployer has touched (rough serial-deployer proxy)
    seen_tokens: set[str] = set()
    for tx in txs:
        for transfer in tx.get("tokenTransfers") or []:
            mint = transfer.get("mint")
            if mint:
                seen_tokens.add(mint)
    dev_prev_tokens = len(seen_tokens)

    # Did the dev SELL this specific token within 24h of its launch?
    quick_sell = False
    if ca and launch_ts:
        deadline = launch_ts + 24 * 3600
        for tx in txs:
            ts = tx.get("timestamp") or 0
            if ts > deadline:
                break
            for transfer in tx.get("tokenTransfers") or []:
                if (
                    transfer.get("mint") == ca
                    and transfer.get("fromUserAccount") == dev_wallet
                ):
                    quick_sell = True
                    break
            if quick_sell:
                break

    score = compute_dev_risk(
        dev_rug_count=0,  # TODO: rug DB integration
        dev_sells_within_hours=1.0 if quick_sell else None,
        dev_prev_tokens=dev_prev_tokens,
        connected_to_known_scammers=False,
    )
    return {
        "score": score,
        "level": classify_dev_risk(score),
        "dev_wallet": dev_wallet,
        "dev_prev_tokens": dev_prev_tokens,
        "quick_sell_signal": quick_sell,
    }


def _enrich_buyers(
    early_buyers: List[Dict[str, Any]],
    cabal: Dict[str, Any],
    launch_slot: Optional[int] = None,
    launch_ts: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Enrich early buyers with computed signals:
    - blocks/seconds after launch
    - bot_score (timing-based)
    - archetype (sniper / insider / unknown)
    - smart_money_score and cluster membership
    """
    if not early_buyers:
        return []

    valid_slots = [b.get("slot") for b in early_buyers if b.get("slot")]
    if launch_slot is None:
        launch_slot = min(valid_slots) if valid_slots else None
    valid_ts = [b.get("timestamp") for b in early_buyers if b.get("timestamp")]
    if launch_ts is None:
        launch_ts = min(valid_ts) if valid_ts else None

    cluster_wallet_map: Dict[str, Dict[str, Any]] = {}
    for i, cluster in enumerate(cabal.get("clusters") or []):
        for w in cluster.get("wallets") or []:
            cluster_wallet_map[w] = {
                "cluster_id": i,
                "suspicion_score": cluster.get("suspicion_score"),
                "cluster_type": cluster.get("cluster_type", "unknown"),
            }

    enriched = []
    for buyer in early_buyers:
        wallet = buyer.get("wallet")
        slot = buyer.get("slot")
        ts = buyer.get("timestamp")

        blocks_after = (slot - launch_slot) if (slot and launch_slot) else None
        seconds_after = (ts - launch_ts) if (ts and launch_ts) else None

        in_cluster = wallet in cluster_wallet_map
        cluster_info = cluster_wallet_map.get(wallet, {})
        cluster_suspicion = cluster_info.get("suspicion_score") or 0

        # Bot score from entry timing (block-level beats second-level)
        if (blocks_after is not None and blocks_after < 3) or (
            seconds_after is not None and seconds_after < 2
        ):
            bot_score = 85
        elif (blocks_after is not None and blocks_after < 10) or (
            seconds_after is not None and seconds_after < 10
        ):
            bot_score = 65
        elif (blocks_after is not None and blocks_after < 30) or (
            seconds_after is not None and seconds_after < 60
        ):
            bot_score = 35
        else:
            bot_score = 12

        # Archetype
        if bot_score >= 60:
            archetype = "bot"
        elif blocks_after is not None and blocks_after < 5:
            archetype = "sniper"
        elif in_cluster and cluster_suspicion >= 70:
            archetype = "insider"
        elif in_cluster:
            archetype = "swing_trader"
        else:
            archetype = "unknown"

        # Smart money: not a bot, not part of a suspicious cluster
        if bot_score >= 60:
            smart_money_score = 0
        elif in_cluster and cluster_suspicion >= 70:
            smart_money_score = 15
        else:
            smart_money_score = max(0, 60 - bot_score)

        enriched.append({
            **buyer,
            "blocks_after_launch": blocks_after,
            "seconds_after_launch": seconds_after,
            "bot_score": bot_score,
            "archetype": archetype,
            "smart_money_score": smart_money_score,
            "cluster_id": cluster_info.get("cluster_id"),
            "suspicion_score": cluster_info.get("suspicion_score"),
            "cluster_type": cluster_info.get("cluster_type"),
            "in_cluster": in_cluster,
        })

    enriched.sort(key=lambda b: (
        0 if b.get("in_cluster") else 1,
        b.get("blocks_after_launch") if b.get("blocks_after_launch") is not None else 9999,
    ))

    return enriched


@router.get("/{ca}", summary="Full token analysis")
async def token_analysis(ca: str) -> Dict[str, Any]:
    _validate_ca(ca)
    helius = get_helius_client()

    token_info, early_full = await asyncio.gather(
        helius.get_token_info(ca),
        helius.get_early_buyers_full(ca),
    )

    early_buyers = early_full.get("buyers", [])
    launch_ts = early_full.get("launch_timestamp")
    launch_slot = early_full.get("launch_slot")
    dev_wallet = token_info.get("update_authority")

    cabal, dev_risk = await asyncio.gather(
        analyze_cabal(ca, early_buyers),
        _get_dev_risk(dev_wallet, ca=ca, launch_ts=launch_ts),
    )

    enriched = _enrich_buyers(early_buyers, cabal, launch_slot, launch_ts)

    return {
        "ca": ca,
        "name": token_info.get("name"),
        "symbol": token_info.get("symbol"),
        "supply": token_info.get("supply_ui"),
        "decimals": token_info.get("decimals"),
        "sol_price_usd": early_full.get("sol_price_usd"),
        "launch_timestamp": launch_ts,
        "history_complete": early_full.get("history_complete", False),
        "early_buyers_count": len(early_buyers),
        "early_buyers": enriched[:100],
        "cabal": cabal,
        "dev_risk": dev_risk,
    }


@router.get("/{ca}/early-buyers", summary="Paginated early buyers list")
async def token_early_buyers(ca: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    _validate_ca(ca)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    helius = get_helius_client()
    early_full = await helius.get_early_buyers_full(ca)
    early_buyers = early_full.get("buyers", [])
    cabal = await analyze_cabal(ca, early_buyers)
    enriched = _enrich_buyers(
        early_buyers, cabal,
        early_full.get("launch_slot"), early_full.get("launch_timestamp"),
    )
    page = enriched[offset: offset + limit]
    return {
        "ca": ca,
        "total": len(early_buyers),
        "limit": limit,
        "offset": offset,
        "history_complete": early_full.get("history_complete", False),
        "buyers": page,
    }


@router.get("/{ca}/cabal", summary="Cabal cluster analysis")
async def token_cabal(ca: str) -> Dict[str, Any]:
    _validate_ca(ca)
    helius = get_helius_client()
    early_buyers = await helius.get_early_buyers(ca)
    return await analyze_cabal(ca, early_buyers)


@router.get("/{ca}/dev-risk", summary="Dev wallet risk score")
async def token_dev_risk(ca: str) -> Dict[str, Any]:
    _validate_ca(ca)
    helius = get_helius_client()
    token_info, early_full = await asyncio.gather(
        helius.get_token_info(ca),
        helius.get_early_buyers_full(ca),
    )
    return await _get_dev_risk(
        token_info.get("update_authority"),
        ca=ca,
        launch_ts=early_full.get("launch_timestamp"),
    )