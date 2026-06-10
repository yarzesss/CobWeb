"""Token analysis endpoints."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.helius import get_helius_client
from app.services.cabal import analyze_cabal
from app.services.classifier import compute_dev_risk, classify_dev_risk

router = APIRouter(prefix="/token", tags=["Token"])


async def _get_dev_risk(dev_wallet: str | None) -> Dict[str, Any]:
    if not dev_wallet:
        return {"score": 0, "level": "LOW", "dev_wallet": None}

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(dev_wallet, limit=200)
    seen_tokens: set[str] = set()
    quick_sells = 0
    sorted_txs = sorted(txs, key=lambda t: t.get("timestamp") or 0)

    for tx in sorted_txs:
        for transfer in tx.get("tokenTransfers") or []:
            mint = transfer.get("mint")
            if mint:
                seen_tokens.add(mint)

    dev_prev_tokens = len(seen_tokens)
    for tx in sorted_txs[:20]:
        for transfer in tx.get("tokenTransfers") or []:
            if transfer.get("fromUserAccount") == dev_wallet:
                quick_sells += 1

    dev_sells_within_hours = 1.0 if quick_sells > 3 else None
    score = compute_dev_risk(
        dev_rug_count=0,
        dev_sells_within_hours=dev_sells_within_hours,
        dev_prev_tokens=dev_prev_tokens,
        connected_to_known_scammers=False,
    )
    return {
        "score": score,
        "level": classify_dev_risk(score),
        "dev_wallet": dev_wallet,
        "dev_prev_tokens": dev_prev_tokens,
        "quick_sell_signal": quick_sells > 3,
    }


def _enrich_buyers(
    early_buyers: List[Dict[str, Any]],
    cabal: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Enrich early buyers with real computed data:
    - bot_score: based on how many blocks after launch they bought
    - archetype: SNIPER (first blocks) | INSIDER (cluster) | UNKNOWN
    - blocks_after_launch: how early they got in
    - cluster membership
    """
    if not early_buyers:
        return []

    # Find launch slot = the very first buyer's slot
    valid_slots = [b.get("slot") for b in early_buyers if b.get("slot")]
    launch_slot = min(valid_slots) if valid_slots else 0

    # Build cluster lookup
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
        slot = buyer.get("slot") or 0
        blocks_after = max(0, slot - launch_slot) if launch_slot else 0
        in_cluster = wallet in cluster_wallet_map
        cluster_info = cluster_wallet_map.get(wallet, {})

        # Bot score: the earlier relative to launch, the more likely it's a bot
        if blocks_after < 3:
            bot_score = 85
        elif blocks_after < 10:
            bot_score = 65
        elif blocks_after < 30:
            bot_score = 35
        else:
            bot_score = 12

        # Archetype
        if blocks_after < 5:
            archetype = "sniper"
        elif in_cluster and (cluster_info.get("suspicion_score") or 0) >= 70:
            archetype = "insider"
        elif in_cluster:
            archetype = "swing_trader"
        else:
            archetype = "unknown"

        # Smart money: high if NOT a bot AND NOT in suspicious cluster
        if bot_score >= 60:
            smart_money_score = 0
        elif in_cluster and (cluster_info.get("suspicion_score") or 0) >= 70:
            smart_money_score = 15  # Cluster member = coordinated, not "smart" independent
        else:
            smart_money_score = max(0, 55 - bot_score)

        enriched.append({
            **buyer,
            "blocks_after_launch": blocks_after,
            "bot_score": bot_score,
            "archetype": archetype,
            "smart_money_score": smart_money_score,
            "cluster_id": cluster_info.get("cluster_id"),
            "suspicion_score": cluster_info.get("suspicion_score"),
            "cluster_type": cluster_info.get("cluster_type"),
            "in_cluster": in_cluster,
        })

    # Sort: cluster members first, then by blocks_after_launch ascending
    enriched.sort(key=lambda b: (
        0 if b.get("in_cluster") else 1,
        b.get("blocks_after_launch", 9999),
    ))

    return enriched


@router.get("/{ca}", summary="Full token analysis")
async def token_analysis(ca: str) -> Dict[str, Any]:
    helius = get_helius_client()

    meta, early_buyers = await asyncio.gather(
        helius.get_token_metadata(ca),
        helius.get_early_buyers(ca),
    )

    dev_wallet = None
    if isinstance(meta, dict):
        on_chain = meta.get("onChainMetadata") or {}
        dev_wallet = (
            on_chain.get("updateAuthority")
            or meta.get("owner")
            or meta.get("developer")
        )

    cabal, dev_risk = await asyncio.gather(
        analyze_cabal(ca, early_buyers),
        _get_dev_risk(dev_wallet),
    )

    enriched = _enrich_buyers(early_buyers, cabal)

    return {
        "ca": ca,
        "name": (meta.get("onChainMetadata") or {}).get("name") if isinstance(meta, dict) else None,
        "symbol": (meta.get("onChainMetadata") or {}).get("symbol") if isinstance(meta, dict) else None,
        "early_buyers_count": len(early_buyers),
        "early_buyers": enriched[:50],
        "cabal": cabal,
        "dev_risk": dev_risk,
    }


@router.get("/{ca}/early-buyers", summary="Paginated early buyers list")
async def token_early_buyers(ca: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    helius = get_helius_client()
    early_buyers = await helius.get_early_buyers(ca)
    cabal = await analyze_cabal(ca, early_buyers)
    enriched = _enrich_buyers(early_buyers, cabal)
    page = enriched[offset: offset + limit]
    return {
        "ca": ca,
        "total": len(early_buyers),
        "limit": limit,
        "offset": offset,
        "buyers": page,
    }


@router.get("/{ca}/cabal", summary="Cabal cluster analysis")
async def token_cabal(ca: str) -> Dict[str, Any]:
    helius = get_helius_client()
    early_buyers = await helius.get_early_buyers(ca)
    return await analyze_cabal(ca, early_buyers)


@router.get("/{ca}/dev-risk", summary="Dev wallet risk score")
async def token_dev_risk(ca: str) -> Dict[str, Any]:
    helius = get_helius_client()
    meta = await helius.get_token_metadata(ca)
    dev_wallet = None
    if isinstance(meta, dict):
        on_chain = meta.get("onChainMetadata") or {}
        dev_wallet = on_chain.get("updateAuthority") or meta.get("owner")
    return await _get_dev_risk(dev_wallet)