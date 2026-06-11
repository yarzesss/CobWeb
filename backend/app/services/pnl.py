from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import WSOL_MINT, get_helius_client

DUST_SOL = 0.0005  # ignore SOL deltas below this (fees / rent noise)


def _wallet_sol_delta(tx: Dict[str, Any], wallet: str) -> float:
    """Net SOL change for the wallet in this tx (SOL, signed)."""
    for acc in tx.get("accountData") or []:
        if acc.get("account") == wallet:
            return (acc.get("nativeBalanceChange") or 0) / 1e9

    delta = 0
    for nt in tx.get("nativeTransfers") or []:
        if nt.get("toUserAccount") == wallet:
            delta += nt.get("amount") or 0
        if nt.get("fromUserAccount") == wallet:
            delta -= nt.get("amount") or 0
    return delta / 1e9


def _wallet_token_deltas(tx: Dict[str, Any], wallet: str) -> Dict[str, float]:
    """Net token amount change per mint for the wallet (UI units)."""
    deltas: Dict[str, float] = defaultdict(float)
    for tt in tx.get("tokenTransfers") or []:
        mint = tt.get("mint")
        if not mint or mint == WSOL_MINT:
            continue
        try:
            amount = float(tt.get("tokenAmount") or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        if tt.get("toUserAccount") == wallet:
            deltas[mint] += amount
        if tt.get("fromUserAccount") == wallet:
            deltas[mint] -= amount
    return {m: a for m, a in deltas.items() if abs(a) > 1e-12}


def _parse_swap_event(
    tx: Dict[str, Any], wallet: str
) -> Optional[Tuple[str, str, float, float]]:
    """
    Parse Helius parsed swap event for the wallet.
    Returns (side, mint, sol_amount, token_amount) or None.
    side ∈ {"buy", "sell"}.
    """
    swap = (tx.get("events") or {}).get("swap") or {}
    if not swap:
        return None

    ni = swap.get("nativeInput") or {}
    no = swap.get("nativeOutput") or {}

    def _token_amt(entry: Dict[str, Any]) -> Tuple[Optional[str], float]:
        mint = entry.get("mint")
        raw = entry.get("rawTokenAmount") or {}
        try:
            amount = float(raw.get("tokenAmount") or 0)
            decimals = int(raw.get("decimals") or 0)
        except (TypeError, ValueError):
            return mint, 0.0
        if decimals > 0:
            amount = amount / (10 ** decimals)
        return mint, amount

    # BUY: wallet sends SOL, receives tokens
    if ni.get("account") == wallet:
        sol_amount = int(ni.get("amount") or 0) / 1e9
        for out in swap.get("tokenOutputs") or []:
            if out.get("userAccount") != wallet:
                continue
            mint, amount = _token_amt(out)
            if mint and mint != WSOL_MINT and amount > 0 and sol_amount > 0:
                return ("buy", mint, sol_amount, amount)

    # SELL: wallet sends tokens, receives SOL
    if no.get("account") == wallet:
        sol_amount = int(no.get("amount") or 0) / 1e9
        for inp in swap.get("tokenInputs") or []:
            if inp.get("userAccount") != wallet:
                continue
            mint, amount = _token_amt(inp)
            if mint and mint != WSOL_MINT and amount > 0 and sol_amount > 0:
                return ("sell", mint, sol_amount, amount)

    return None


async def calculate_wallet_pnl(wallet_address: str, limit: int = 500) -> Dict[str, Any]:
    """SOL-based realized PnL per token + summary stats (USD derived)."""
    cache_key = f"wallet:{wallet_address}:pnl:v2"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(wallet_address, limit=limit)
    sol_price = await helius.get_sol_price_usd()

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
    buy_sizes_sol: List[float] = []
    dex_counter: Counter = Counter()

    def _record(side: str, mint: str, sol_amount: float, token_amount: float, ts: int) -> None:
        nonlocal total_trades
        state = per_token[mint]
        if side == "buy":
            state["sol_spent"] += sol_amount
            state["token_bought"] += token_amount
            state["buy_count"] += 1
            buy_sizes_sol.append(sol_amount)
            if state["first_buy_ts"] is None:
                state["first_buy_ts"] = ts
        else:
            state["sol_received"] += sol_amount
            state["token_sold"] += token_amount
            state["sell_count"] += 1
            if state["first_buy_ts"] and ts > state["first_buy_ts"]:
                state["hold_times_minutes"].append((ts - state["first_buy_ts"]) / 60)
        total_trades += 1

    for tx in sorted(txs, key=lambda t: t.get("timestamp") or 0):
        ts = tx.get("timestamp") or 0
        source = tx.get("source") or ""
        if source and source != "UNKNOWN":
            dex_counter[source] += 1

        # 1) Parsed swap event
        parsed = _parse_swap_event(tx, wallet_address)
        if parsed:
            side, mint, sol_amount, token_amount = parsed
            _record(side, mint, sol_amount, token_amount, ts)
            continue

        # 2) Fallback: balance deltas (pump.fun & friends)
        token_deltas = _wallet_token_deltas(tx, wallet_address)
        if not token_deltas:
            continue
        sol_delta = _wallet_sol_delta(tx, wallet_address)

        for mint, token_delta in token_deltas.items():
            if token_delta > 0 and sol_delta < -DUST_SOL:
                _record("buy", mint, -sol_delta, token_delta, ts)
            elif token_delta < 0 and sol_delta > DUST_SOL:
                _record("sell", mint, sol_delta, -token_delta, ts)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_sol_pnl = 0.0
    win_trades = 0
    completed_trades = 0
    all_hold_times: List[float] = []
    by_token: List[Dict[str, Any]] = []

    for mint, state in per_token.items():
        sol_pnl = state["sol_received"] - state["sol_spent"]
        total_sol_pnl += sol_pnl

        if state["sell_count"] > 0:
            completed_trades += 1
            if sol_pnl > 0:
                win_trades += 1

        all_hold_times.extend(state["hold_times_minutes"])

        by_token.append({
            "mint": mint,
            "sol_spent": round(state["sol_spent"], 4),
            "sol_received": round(state["sol_received"], 4),
            "sol_pnl": round(sol_pnl, 4),
            "realized_usd": round(sol_pnl * sol_price, 2) if sol_price else None,
            "token_bought": round(state["token_bought"], 2),
            "token_sold": round(state["token_sold"], 2),
            "buys": state["buy_count"],
            "sells": state["sell_count"],
            "trades": state["buy_count"] + state["sell_count"],
        })

    by_token.sort(key=lambda t: abs(t["sol_pnl"]), reverse=True)

    winrate = win_trades / completed_trades if completed_trades > 0 else 0.0
    avg_hold = sum(all_hold_times) / len(all_hold_times) if all_hold_times else 0.0
    avg_position_sol = sum(buy_sizes_sol) / len(buy_sizes_sol) if buy_sizes_sol else 0.0
    favorite_dex = dex_counter.most_common(1)[0][0] if dex_counter else None

    result = {
        "wallet_address": wallet_address,
        "summary": {
            "total_sol_pnl": round(total_sol_pnl, 4),
            "total_realized_usd": round(total_sol_pnl * sol_price, 2) if sol_price else round(total_sol_pnl, 4),
            "usd_is_estimate": True,  # USD uses current SOL price, not historical
            "sol_price_usd": sol_price,
            "total_trades": total_trades,
            "completed_trades": completed_trades,
            "win_trades": win_trades,
            "winrate": round(winrate, 4),
            "avg_hold_time_minutes": round(avg_hold, 2),
            "avg_position_size_sol": round(avg_position_sol, 4),
            "avg_position_size_usd": round(avg_position_sol * sol_price, 2) if sol_price else 0.0,
            "favorite_dex": favorite_dex,
            "currency": "SOL",
        },
        "by_token": by_token[:100],
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
    return result