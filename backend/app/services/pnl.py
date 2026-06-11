"""PnL calculation for Cobweb.

Computed in SOL from on-chain swaps, converted to USD with the live SOL price.

Why two parsers:
- Helius fills `events.swap` only for some sources (Jupiter, Raydium, …).
  Pump.fun and several AMMs often come through with an EMPTY swap event —
  this is exactly why wallet profiles used to show zeros everywhere.
- So we first try `events.swap`, and if it's absent we fall back to
  reconstructing the trade from tokenTransfers + nativeTransfers +
  accountData.nativeBalanceChange.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client

# Sources we treat as trades when falling back to raw transfers
_TRADE_TYPES = {"SWAP", "UNKNOWN", "TRANSFER"}


def _adjust(raw: Dict[str, Any]) -> float:
    """rawTokenAmount → decimals-adjusted float."""
    try:
        amt = float(raw.get("tokenAmount") or 0)
        decimals = int(raw.get("decimals") or 0)
        return amt / (10 ** decimals) if decimals > 0 else amt
    except (TypeError, ValueError):
        return 0.0


def _parse_swap_event(
    tx: Dict[str, Any], wallet: str
) -> Optional[Tuple[str, str, float, float]]:
    """Parse via events.swap. Returns (side, mint, token_amount, sol_amount) or None."""
    swap = (tx.get("events") or {}).get("swap") or {}
    if not swap:
        return None

    ni = swap.get("nativeInput") or {}
    no = swap.get("nativeOutput") or {}
    token_inputs = swap.get("tokenInputs") or []
    token_outputs = swap.get("tokenOutputs") or []

    # BUY: wallet sends SOL, receives tokens
    if ni.get("account") == wallet and token_outputs:
        sol_amount = int(ni.get("amount") or 0) / 1e9
        for out in token_outputs:
            if out.get("userAccount") != wallet or not out.get("mint"):
                continue
            return ("buy", out["mint"], _adjust(out.get("rawTokenAmount") or {}), sol_amount)

    # SELL: wallet sends tokens, receives SOL
    if no.get("account") == wallet and token_inputs:
        sol_amount = int(no.get("amount") or 0) / 1e9
        for inp in token_inputs:
            if inp.get("userAccount") != wallet or not inp.get("mint"):
                continue
            return ("sell", inp["mint"], _adjust(inp.get("rawTokenAmount") or {}), sol_amount)

    return None


def _parse_raw_transfers(
    tx: Dict[str, Any], wallet: str
) -> Optional[Tuple[str, str, float, float]]:
    """
    Fallback parser (pump.fun & friends): reconstruct the trade from
    tokenTransfers + the wallet's net SOL movement in the transaction.
    """
    if (tx.get("type") or "").upper() not in _TRADE_TYPES:
        return None

    token_in = 0.0   # tokens received by wallet
    token_out = 0.0  # tokens sent by wallet
    mint_in: Optional[str] = None
    mint_out: Optional[str] = None

    for t in tx.get("tokenTransfers") or []:
        mint = t.get("mint")
        if not mint:
            continue
        try:
            amount = float(t.get("tokenAmount") or 0)
        except (TypeError, ValueError):
            continue
        if t.get("toUserAccount") == wallet:
            token_in += amount
            mint_in = mint
        elif t.get("fromUserAccount") == wallet:
            token_out += amount
            mint_out = mint

    # Net SOL movement: prefer accountData (includes fees & AMM legs)
    sol_change = 0.0
    found_account_data = False
    for acc in tx.get("accountData") or []:
        if acc.get("account") == wallet:
            try:
                sol_change = int(acc.get("nativeBalanceChange") or 0) / 1e9
                found_account_data = True
            except (TypeError, ValueError):
                pass
            break

    if not found_account_data:
        lamports = 0
        for nt in tx.get("nativeTransfers") or []:
            try:
                amount = int(nt.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if nt.get("fromUserAccount") == wallet:
                lamports -= amount
            elif nt.get("toUserAccount") == wallet:
                lamports += amount
        sol_change = lamports / 1e9

    # BUY: received tokens, SOL went down
    if token_in > 0 and mint_in and sol_change < -0.0001:
        return ("buy", mint_in, token_in, abs(sol_change))
    # SELL: sent tokens, SOL went up
    if token_out > 0 and mint_out and sol_change > 0.0001:
        return ("sell", mint_out, token_out, sol_change)

    return None


async def calculate_wallet_pnl(wallet_address: str, limit: int = 500) -> Dict[str, Any]:
    """Realized SOL/USD PnL per token + summary stats for a wallet."""
    cache_key = f"wallet:{wallet_address}:pnl:v2"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(wallet_address, limit=limit)
    sol_price = await helius.get_sol_price_usd()

    if not isinstance(txs, list):
        txs = []

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

    for tx in sorted(txs, key=lambda t: t.get("timestamp") or 0):
        ts = tx.get("timestamp") or 0

        parsed = _parse_swap_event(tx, wallet_address) or _parse_raw_transfers(tx, wallet_address)
        if not parsed:
            continue

        side, mint, token_amt, sol_amt = parsed
        if token_amt <= 0 or sol_amt <= 0:
            continue

        source = tx.get("source") or ""
        if source and source != "UNKNOWN":
            dex_counter[source] += 1

        state = per_token[mint]
        total_trades += 1

        if side == "buy":
            state["sol_spent"] += sol_amt
            state["token_bought"] += token_amt
            state["buy_count"] += 1
            buy_sizes_sol.append(sol_amt)
            if state["first_buy_ts"] is None:
                state["first_buy_ts"] = ts
        else:
            state["sol_received"] += sol_amt
            state["token_sold"] += token_amt
            state["sell_count"] += 1
            if state["first_buy_ts"] and ts > state["first_buy_ts"]:
                state["hold_times_minutes"].append((ts - state["first_buy_ts"]) / 60)

    # ── Build summary ────────────────────────────────────────────────────────
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
            "realized_usd": round(sol_pnl * sol_price, 2),
            "token_bought": round(state["token_bought"], 2),
            "token_sold": round(state["token_sold"], 2),
            "buys": state["buy_count"],
            "sells": state["sell_count"],
            "trades": state["buy_count"] + state["sell_count"],
        })

    # Biggest winners/losers first
    by_token.sort(key=lambda t: abs(t["sol_pnl"]), reverse=True)

    winrate = win_trades / completed_trades if completed_trades > 0 else 0.0
    avg_hold = sum(all_hold_times) / len(all_hold_times) if all_hold_times else 0.0
    avg_buy_sol = sum(buy_sizes_sol) / len(buy_sizes_sol) if buy_sizes_sol else 0.0
    favorite_dex = dex_counter.most_common(1)[0][0] if dex_counter else None

    result = {
        "wallet_address": wallet_address,
        "summary": {
            "total_sol_pnl": round(total_sol_pnl, 4),
            "total_realized_usd": round(total_sol_pnl * sol_price, 2),
            "total_trades": total_trades,
            "completed_trades": completed_trades,
            "win_trades": win_trades,
            "winrate": round(winrate, 4),
            "avg_hold_time_minutes": round(avg_hold, 2),
            "avg_position_size_sol": round(avg_buy_sol, 4),
            "avg_position_size_usd": round(avg_buy_sol * sol_price, 2),
            "favorite_dex": favorite_dex,
            "sol_price_usd": round(sol_price, 2),
        },
        "by_token": by_token,
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
    return result
