"""Cabal / cluster detection for Cobweb backend."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client


async def analyze_cabal(
    ca: str,
    early_buyers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Analyze early buyers for cluster/insider signals.

    Three-layer detection:
    1. Common funder — wallets funded from the same source
    2. Direct transfers — wallets that sent SOL directly to each other
    3. Suspicion score — based on cluster size and connection type

    Returns:
    {
        "clusters": [{
            "wallets": [...],
            "connections": [{from, to, type, amount_sol?}],
            "common_funder": "addr" | None,
            "suspicion_score": 0-100,
        }],
        "independent_wallets": [...]
    }
    """
    cache_key = f"cabal:{ca}:clusters"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()

    if early_buyers is None:
        early_buyers = await helius.get_early_buyers(ca)

    wallets: List[str] = [
        e["wallet"] for e in early_buyers if e.get("wallet")
    ][: settings.MAX_WALLETS_PER_CABAL_SCAN]

    if not wallets:
        result = {"clusters": [], "independent_wallets": []}
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_CABAL)
        return result

    # ── Fetch SOL transfers for all wallets in parallel ──────────────────────
    transfers_map: Dict[str, List[Dict[str, Any]]] = {}

    async def fetch_transfers(wallet: str) -> None:
        try:
            transfers_map[wallet] = await helius.get_wallet_sol_transfers(wallet)
        except Exception:
            transfers_map[wallet] = []

    await asyncio.gather(*(fetch_transfers(w) for w in wallets))

    # ── Layer 1: Common funder detection ─────────────────────────────────────
    # First incoming SOL transfer = who funded this wallet
    funder_map: Dict[str, str] = {}

    for wallet, transfers in transfers_map.items():
        sorted_txs = sorted(transfers, key=lambda t: t.get("timestamp") or 0)
        for t in sorted_txs:
            to_acc = t.get("toUserAccount")
            from_acc = t.get("fromUserAccount")
            if to_acc == wallet and from_acc and from_acc != wallet:
                funder_map[wallet] = from_acc
                break

    # Group wallets by common funder
    funder_groups: Dict[str, List[str]] = {}
    for wallet, funder in funder_map.items():
        funder_groups.setdefault(funder, []).append(wallet)

    clusters: List[Dict[str, Any]] = []
    used_wallets: Set[str] = set()

    for funder, members in funder_groups.items():
        if len(members) < 2:
            continue
        connections = [
            {"from": funder, "to": m, "type": "funding"}
            for m in members
        ]
        suspicion_score = min(95, 40 + len(members) * 10)
        clusters.append({
            "wallets": list(members),
            "connections": connections,
            "common_funder": funder,
            "suspicion_score": suspicion_score,
        })
        used_wallets.update(members)

    # ── Layer 2: Direct transfers between early buyers ────────────────────────
    wallet_set = set(wallets)

    for wallet, transfers in transfers_map.items():
        for t in transfers:
            from_acc = t.get("fromUserAccount")
            to_acc = t.get("toUserAccount")
            amount_sol = t.get("amount_sol", 0)

            if not from_acc or not to_acc:
                continue
            if from_acc != wallet:
                continue
            if to_acc not in wallet_set or to_acc == wallet:
                continue

            edge = {
                "from": from_acc,
                "to": to_acc,
                "type": "direct_transfer",
                "amount_sol": amount_sol,
            }

            # Add to existing cluster if either wallet is already in one
            placed = False
            for cluster in clusters:
                members_set = set(cluster["wallets"])
                if from_acc in members_set or to_acc in members_set:
                    cluster["connections"].append(edge)
                    # Merge the other wallet into this cluster
                    other = to_acc if from_acc in members_set else from_acc
                    if other not in members_set:
                        cluster["wallets"].append(other)
                    cluster["suspicion_score"] = min(100, cluster["suspicion_score"] + 10)
                    used_wallets.update([from_acc, to_acc])
                    placed = True
                    break

            if not placed:
                clusters.append({
                    "wallets": [from_acc, to_acc],
                    "connections": [edge],
                    "common_funder": None,
                    "suspicion_score": 55,
                })
                used_wallets.update([from_acc, to_acc])

    independent_wallets = [w for w in wallets if w not in used_wallets]

    result = {
        "clusters": clusters,
        "independent_wallets": independent_wallets,
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_CABAL)
    return result