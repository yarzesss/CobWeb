"""PnL and wallet stats calculation for Cobweb."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client


def _normalize_amount(amount: Any, decimals: Optional[int] = None) -> float:
    try:
        a = float(amount or 0)
        if decimals:
            return a / (10 ** int(decimals))
        return a
    except Exception:
        return 0.0


def _lamports_to_sol(lamports: Any) -> float:
    try:
        return float(lamports or 0) / 1e9
    except Exception:
        return 0.0


async def calculate_wallet_pnl(
    wallet_address: str,
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Calculate wallet PnL from Helius Enhanced Transaction history.

    Parses swap events (events.swap) and token transfers to build
    per-token buy/sell history, then calculates realized PnL via FIFO.

    Returns:
    {
        "summary": {
            "total_realized_usd": float,
            "total_trades": int,
            "win_trades": int,
            "winrate": float,
            "avg_hold_time_minutes": float,
            "avg_position_size_usd": float,
        },
        "per_token": {
            "mint_address": {
                "realized_pnl": float,
                "unrealized_usd": float | None,
                "buys": int,
                "sells": int,
            }
        }
    }
    """
    cache_key = f"wallet:{wallet_address}:pnl"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(wallet_address, limit=limit)

    # per-token state: {mint: {buy_queue: [{amount, usd, timestamp}], realized, sells}}
    token_state: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "buy_queue": [],
        "realized_pnl": 0.0,
        "buy_count": 0,
        "sell_count": 0,
        "win_trades": 0,
        "hold_times": [],
    })

    total_position_usd = 0.0
    trade_count = 0

    for tx in sorted(txs, key=lambda t: t.get("timestamp") or 0):
        timestamp = tx.get("timestamp") or 0

        # ── Try swap event first (most accurate for DEX trades) ───────────────
        swap = (tx.get("events") or {}).get("swap") or {}

        if swap:
            # Determine what wallet received (output) and sent (input)
            token_outputs = swap.get("tokenOutputs") or []
            token_inputs = swap.get("tokenInputs") or []
            native_input = swap.get("nativeInput") or {}
            native_output = swap.get("nativeOutput") or {}

            # SOL spent (buy) → token received
            for output in token_outputs:
                if output.get("userAccount") != wallet_address:
                    continue
                mint = output.get("mint")
                if not mint:
                    continue
                amount = _normalize_amount(output.get("rawTokenAmount", {}).get("tokenAmount"), output.get("rawTokenAmount", {}).get("decimals"))
                usd = output.get("tokenAmount")  # Helius sometimes provides USD value

                state = token_state[mint]
                state["buy_queue"].append({"amount": amount, "usd": usd, "timestamp": timestamp})
                state["buy_count"] += 1
                if usd:
                    total_position_usd += float(usd)
                    trade_count += 1

            # Token sold → SOL received
            for inp in token_inputs:
                if inp.get("userAccount") != wallet_address:
                    continue
                mint = inp.get("mint")
                if not mint:
                    continue
                amount = _normalize_amount(inp.get("rawTokenAmount", {}).get("tokenAmount"), inp.get("rawTokenAmount", {}).get("decimals"))
                sell_usd = inp.get("tokenAmount")

                state = token_state[mint]
                state["sell_count"] += 1
                trade_count += 1

                # FIFO PnL matching
                realized = _fifo_match(
                    state["buy_queue"],
                    amount=amount,
                    sell_usd=sell_usd,
                    sell_timestamp=timestamp,
                    hold_times=state["hold_times"],
                )
                state["realized_pnl"] += realized
                if realized > 0:
                    state["win_trades"] += 1

        else:
            # ── Fallback: parse tokenTransfers directly ───────────────────────
            for transfer in tx.get("tokenTransfers") or []:
                mint = transfer.get("mint")
                if not mint:
                    continue

                from_acc = transfer.get("fromUserAccount")
                to_acc = transfer.get("toUserAccount")
                amount = float(transfer.get("tokenAmount") or 0)

                state = token_state[mint]

                if to_acc == wallet_address:
                    # Incoming = buy
                    state["buy_queue"].append({"amount": amount, "usd": None, "timestamp": timestamp})
                    state["buy_count"] += 1

                elif from_acc == wallet_address:
                    # Outgoing = sell
                    state["sell_count"] += 1
                    _fifo_match(
                        state["buy_queue"],
                        amount=amount,
                        sell_usd=None,
                        sell_timestamp=timestamp,
                        hold_times=state["hold_times"],
                    )

    # ── Build summary ─────────────────────────────────────────────────────────
    total_realized = sum(s["realized_pnl"] for s in token_state.values())
    total_wins = sum(s["win_trades"] for s in token_state.values())
    all_hold_times = [h for s in token_state.values() for h in s["hold_times"]]

    winrate = (total_wins / trade_count) if trade_count > 0 else 0.0
    avg_hold = (sum(all_hold_times) / len(all_hold_times)) if all_hold_times else 0.0
    avg_position = (total_position_usd / trade_count) if trade_count > 0 else 0.0

    per_token = {
        mint: {
            "realized_pnl": round(s["realized_pnl"], 4),
            "unrealized_usd": None,
            "buys": s["buy_count"],
            "sells": s["sell_count"],
        }
        for mint, s in token_state.items()
        if s["buy_count"] > 0 or s["sell_count"] > 0
    }

    result = {
        "summary": {
            "total_realized_usd": round(total_realized, 2),
            "total_trades": trade_count,
            "win_trades": total_wins,
            "winrate": round(winrate, 4),
            "avg_hold_time_minutes": round(avg_hold, 2),
            "avg_position_size_usd": round(avg_position, 2),
        },
        "per_token": per_token,
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
    return result


def _fifo_match(
    buy_queue: List[Dict[str, Any]],
    *,
    amount: float,
    sell_usd: Optional[float],
    sell_timestamp: int,
    hold_times: List[float],
) -> float:
    """
    Match a sell against the buy queue (FIFO).
    Returns realized PnL for this sell.
    Records hold time (minutes) for each matched lot.
    """
    realized = 0.0
    remaining = amount

    while remaining > 0 and buy_queue:
        buy = buy_queue[0]
        take = min(remaining, buy["amount"])

        # Record hold time in minutes
        if buy.get("timestamp") and sell_timestamp:
            hold_minutes = (sell_timestamp - buy["timestamp"]) / 60
            if hold_minutes > 0:
                hold_times.append(hold_minutes)

        # PnL only if we have USD values for both sides
        if sell_usd is not None and buy.get("usd") is not None:
            buy_price_per_unit = buy["usd"] / buy["amount"] if buy["amount"] else 0
            sell_price_per_unit = sell_usd / amount if amount else 0
            realized += take * (sell_price_per_unit - buy_price_per_unit)

        buy["amount"] -= take
        remaining -= take

        if buy["amount"] <= 1e-9:
            buy_queue.pop(0)

    return realized