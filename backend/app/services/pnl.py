"""PnL calculation for Cobweb — SOL-based (no external price data needed)."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client


async def calculate_wallet_pnl(wallet_address: str, limit: int = 500) -> Dict[str, Any]:
    """
    Calculate wallet PnL from Helius Enhanced Transactions.

    Uses SOL amounts (no USD price data needed):
    - BUY:  wallet sends SOL → receives tokens  (nativeInput + tokenOutputs)
    - SELL: wallet sends tokens → receives SOL  (tokenInputs + nativeOutput)

    Returns SOL-based PnL per token + summary stats.
    """
    cache_key = f"wallet:{wallet_address}:pnl"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(wallet_address, limit=limit)

    # Per-token state
    per_token: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "sol_spent": 0.0,
        "sol_received": 0.0,
        "token_bought": 0.0,
        "token_sold": 0.0,
        "buy_count": 0,
        "sell_count": 0,
        "first_buy_ts": None,
        "hold_times_minutes": [],
    })

    total_trades = 0
    dex_counter: Counter = Counter()

    for tx in sorted(txs, key=lambda t: t.get("timestamp") or 0):
        ts = tx.get("timestamp") or 0
        source = tx.get("source") or ""
        if source:
            dex_counter[source] += 1

        swap = (tx.get("events") or {}).get("swap") or {}
        if not swap:
            continue

        ni = swap.get("nativeInput")    # SOL sent by wallet (buy)
        no = swap.get("nativeOutput")   # SOL received by wallet (sell)
        token_inputs = swap.get("tokenInputs") or []    # tokens sent (sell)
        token_outputs = swap.get("tokenOutputs") or []  # tokens received (buy)

        # ── BUY: wallet sends SOL, receives tokens ──────────────────────────
        if ni and ni.get("account") == wallet_address and token_outputs:
            sol_amount = int(ni.get("amount") or 0) / 1e9
            for out in token_outputs:
                if out.get("userAccount") != wallet_address:
                    continue
                mint = out.get("mint")
                if not mint:
                    continue
                raw = out.get("rawTokenAmount") or {}
                token_amt = float(raw.get("tokenAmount") or 0)
                decimals = int(raw.get("decimals") or 0)
                if decimals > 0:
                    token_amt = token_amt / (10 ** decimals)

                state = per_token[mint]
                state["sol_spent"] += sol_amount
                state["token_bought"] += token_amt
                state["buy_count"] += 1
                if state["first_buy_ts"] is None:
                    state["first_buy_ts"] = ts
                total_trades += 1

        # ── SELL: wallet receives SOL, sends tokens ──────────────────────────
        elif no and no.get("account") == wallet_address and token_inputs:
            sol_amount = int(no.get("amount") or 0) / 1e9
            for inp in token_inputs:
                if inp.get("userAccount") != wallet_address:
                    continue
                mint = inp.get("mint")
                if not mint:
                    continue
                raw = inp.get("rawTokenAmount") or {}
                token_amt = float(raw.get("tokenAmount") or 0)
                decimals = int(raw.get("decimals") or 0)
                if decimals > 0:
                    token_amt = token_amt / (10 ** decimals)

                state = per_token[mint]
                state["sol_received"] += sol_amount
                state["token_sold"] += token_amt
                state["sell_count"] += 1
                total_trades += 1

                # Hold time
                if state["first_buy_ts"] and ts > state["first_buy_ts"]:
                    hold_minutes = (ts - state["first_buy_ts"]) / 60
                    state["hold_times_minutes"].append(hold_minutes)

    # ── Build summary ─────────────────────────────────────────────────────────
    total_sol_pnl = 0.0
    win_trades = 0
    completed_trades = 0
    all_hold_times: List[float] = []
    per_token_out: Dict[str, Any] = {}

    for mint, state in per_token.items():
        sol_pnl = state["sol_received"] - state["sol_spent"]
        total_sol_pnl += sol_pnl

        if state["sell_count"] > 0:
            completed_trades += 1
            if sol_pnl > 0:
                win_trades += 1

        all_hold_times.extend(state["hold_times_minutes"])

        per_token_out[mint] = {
            "sol_spent": round(state["sol_spent"], 4),
            "sol_received": round(state["sol_received"], 4),
            "sol_pnl": round(sol_pnl, 4),
            "token_bought": round(state["token_bought"], 2),
            "token_sold": round(state["token_sold"], 2),
            "buys": state["buy_count"],
            "sells": state["sell_count"],
        }

    winrate = win_trades / completed_trades if completed_trades > 0 else 0.0
    avg_hold = sum(all_hold_times) / len(all_hold_times) if all_hold_times else 0.0
    favorite_dex = dex_counter.most_common(1)[0][0] if dex_counter else None

    result = {
        "summary": {
            "total_sol_pnl": round(total_sol_pnl, 4),
            "total_realized_usd": round(total_sol_pnl, 4),  # Frontend compat alias
            "total_trades": total_trades,
            "completed_trades": completed_trades,
            "win_trades": win_trades,
            "winrate": round(winrate, 4),
            "avg_hold_time_minutes": round(avg_hold, 2),
            "avg_position_size_usd": 0.0,
            "favorite_dex": favorite_dex,
            "currency": "SOL",
        },
        "per_token": per_token_out,
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
    return result