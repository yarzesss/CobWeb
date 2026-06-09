"""Wallet and token classification logic for Cobweb."""
from __future__ import annotations

from typing import Any, Dict, Optional


# ── Bot Score ─────────────────────────────────────────────────────────────────

def compute_bot_score(
    *,
    avg_blocks_after_deploy: Optional[float] = None,
    min_tx_interval_ms: Optional[float] = None,
    daily_tx_count: Optional[int] = None,
    position_size_variance: Optional[float] = None,
) -> int:
    """
    Compute bot-likelihood score 0-100.
    >60 = BOT, <30 = HUMAN, between = UNKNOWN
    """
    score = 0
    if avg_blocks_after_deploy is not None and avg_blocks_after_deploy < 3:
        score += 40
    if min_tx_interval_ms is not None and min_tx_interval_ms < 500:
        score += 25
    if daily_tx_count is not None and daily_tx_count > 50:
        score += 20
    if position_size_variance is not None and position_size_variance < 0.05:
        score += 15
    return min(score, 100)


def classify_bot(score: int) -> str:
    if score > 60:
        return "BOT"
    if score < 30:
        return "HUMAN"
    return "UNKNOWN"


# ── Dev Risk Score ─────────────────────────────────────────────────────────────

def compute_dev_risk(
    *,
    dev_rug_count: int = 0,
    dev_sells_within_hours: Optional[float] = None,
    dev_prev_tokens: int = 0,
    connected_to_known_scammers: bool = False,
) -> int:
    """
    Compute dev risk score 0-100.
    >70 = HIGH RISK, 40-70 = MEDIUM, <40 = LOW
    """
    score = 0
    score += min(dev_rug_count * 25, 75)  # cap rug contribution at 75
    if dev_sells_within_hours is not None and dev_sells_within_hours < 24:
        score += 30
    if dev_prev_tokens > 5:
        score += 10
    if connected_to_known_scammers:
        score += 35
    return min(score, 100)


def classify_dev_risk(score: int) -> str:
    if score > 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


# ── Smart Money Score ─────────────────────────────────────────────────────────

def compute_smart_money_score(
    *,
    winrate: float = 0.0,                      # 0.0 - 1.0
    total_trades: int = 0,
    avg_hold_time_minutes: float = 0.0,
    avg_position_size_usd: float = 0.0,
    bot_score: int = 0,
) -> int:
    """
    Compute Smart Money score 0-100.
    Rewards: high winrate, consistent trading, reasonable hold time.
    Penalizes: bots, too few trades, very short holds.
    """
    if bot_score > 60:
        return 0  # bots are not Smart Money

    score = 0

    # Winrate — most important factor (max 50 points)
    score += int(winrate * 50)

    # Trade consistency — need at least 20 trades to be meaningful
    if total_trades >= 100:
        score += 20
    elif total_trades >= 50:
        score += 15
    elif total_trades >= 20:
        score += 10
    elif total_trades >= 5:
        score += 5

    # Hold time — not too short (scalper) not too long (holder)
    # Sweet spot: 30min - 7 days
    if 30 <= avg_hold_time_minutes <= 7 * 24 * 60:
        score += 15
    elif avg_hold_time_minutes < 5:
        score -= 10  # too fast, likely bot-like

    # Position size — larger = more conviction
    if avg_position_size_usd >= 10000:
        score += 15
    elif avg_position_size_usd >= 1000:
        score += 10
    elif avg_position_size_usd >= 100:
        score += 5

    return max(0, min(score, 100))


# ── Wallet Archetype ──────────────────────────────────────────────────────────

def classify_wallet_archetype(profile: Dict[str, Any]) -> str:
    """
    Classify wallet into one of:
    bot / sniper / insider / flipper / swing_trader / accumulator / unknown

    Priority order matters — check bot first, then specific behaviors.
    """
    bot_score = int(profile.get("bot_score") or 0)
    winrate = float(profile.get("winrate") or 0.0)
    total_trades = int(profile.get("total_trades") or 0)
    avg_hold = profile.get("avg_hold_time_minutes")
    avg_pos = float(profile.get("avg_position_size_usd") or 0.0)
    avg_blocks = profile.get("avg_blocks_after_deploy")
    smart_money = int(profile.get("smart_money_score") or 0)

    # 1. Bot — automated trading, filter out first
    if bot_score > 60:
        return "bot"

    # 2. Sniper — buys in first 3 blocks after deploy (human sniper)
    if avg_blocks is not None and float(avg_blocks) < 3:
        return "sniper"

    if avg_hold is None:
        return "unknown"

    avg_hold = float(avg_hold)

    # 3. Flipper — holds less than 24h, high trade frequency
    if avg_hold < 24 * 60 and total_trades > 30:
        return "flipper"

    # 4. Insider — high winrate + enters consistently before pumps
    # Smart money score >70 with good winrate = insider behavior
    if smart_money >= 70 and winrate >= 0.65 and total_trades >= 20:
        return "insider"

    # 5. Swing Trader — holds days, moderate frequency
    if avg_hold < 7 * 24 * 60:
        return "swing_trader"

    # 6. Accumulator — large positions, long holds
    if avg_pos >= 5000:
        return "accumulator"

    return "unknown"