"""Token analysis endpoints."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.services.helius import get_helius_client
from app.services.cabal import analyze_cabal
from app.services.classifier import (
    compute_dev_risk,
    classify_dev_risk,
)

router = APIRouter(prefix="/token", tags=["Token"])


async def _get_dev_risk(dev_wallet: str | None) -> Dict[str, Any]:
    """
    Analyze dev wallet history to compute risk score.
    Looks at how many tokens this wallet deployed and sold quickly.
    """
    if not dev_wallet:
        return {"score": 0, "level": "LOW", "dev_wallet": None}

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(dev_wallet, limit=200)

    # Count unique tokens the dev deployed/interacted with
    seen_tokens: set[str] = set()
    quick_sells = 0

    sorted_txs = sorted(txs, key=lambda t: t.get("timestamp") or 0)

    for tx in sorted_txs:
        for transfer in tx.get("tokenTransfers") or []:
            mint = transfer.get("mint")
            if mint:
                seen_tokens.add(mint)

    dev_prev_tokens = len(seen_tokens)

    # Check if dev sold within 24h of first buy (quick dump signal)
    # Simplified: if dev has many sells in first transactions = suspicious
    early_txs = sorted_txs[:20]
    for tx in early_txs:
        for transfer in tx.get("tokenTransfers") or []:
            if transfer.get("fromUserAccount") == dev_wallet:
                quick_sells += 1

    dev_sells_within_hours = 1.0 if quick_sells > 3 else None

    score = compute_dev_risk(
        dev_rug_count=0,  # TODO: cross-reference with known rug database
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


@router.get("/{ca}", summary="Full token analysis")
async def token_analysis(ca: str) -> Dict[str, Any]:
    """
    Main endpoint — returns full analysis for a token:
    - Metadata (name, symbol)
    - Early buyers list
    - Cabal cluster analysis
    - Dev risk score
    """
    helius = get_helius_client()

    # Fetch metadata and early buyers in parallel
    meta, early_buyers = await asyncio.gather(
        helius.get_token_metadata(ca),
        helius.get_early_buyers(ca),
    )

    # Extract dev wallet from metadata
    dev_wallet = None
    if isinstance(meta, dict):
        on_chain = meta.get("onChainMetadata") or {}
        dev_wallet = (
            on_chain.get("updateAuthority")
            or meta.get("owner")
            or meta.get("developer")
        )

    # Cabal analysis and dev risk in parallel
    cabal, dev_risk = await asyncio.gather(
        analyze_cabal(ca, early_buyers),
        _get_dev_risk(dev_wallet),
    )

    return {
        "ca": ca,
        "name": (meta.get("onChainMetadata") or {}).get("name") if isinstance(meta, dict) else None,
        "symbol": (meta.get("onChainMetadata") or {}).get("symbol") if isinstance(meta, dict) else None,
        "early_buyers_count": len(early_buyers),
        "early_buyers": early_buyers[:50],  # top 50 in main response
        "cabal": cabal,
        "dev_risk": dev_risk,
    }


@router.get("/{ca}/early-buyers", summary="Paginated early buyers list")
async def token_early_buyers(
    ca: str,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    helius = get_helius_client()
    buyers = await helius.get_early_buyers(ca)
    page = buyers[offset: offset + limit]
    return {
        "ca": ca,
        "total": len(buyers),
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