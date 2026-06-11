"""Helius API client for Cobweb backend."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.core.cache import get_json, set_json


class HeliusClient:
    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _rate_limit(self) -> None:
        async with self._lock:
            now = time.monotonic()
            min_interval = 1.0 / max(1, settings.HELIUS_REQUESTS_PER_SECOND)
            elapsed = now - self._last_request
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request = time.monotonic()

    async def _get(self, url: str, params: Optional[Dict] = None) -> Any:
        await self._rate_limit()
        client = await self._get_client()
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": True, "message": str(exc)}

    async def _post(self, url: str, body: Dict) -> Any:
        await self._rate_limit()
        client = await self._get_client()
        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": True, "message": str(exc)}

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()

    # ─── Token ───────────────────────────────────────────────────────────────

    async def get_token_metadata(self, ca: str) -> Dict[str, Any]:
        """Fetch token name, symbol, decimals, supply via Helius DAS API."""
        cache_key = f"token:{ca}:metadata"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        url = f"{settings.HELIUS_API_URL}/token-metadata?api-key={settings.HELIUS_API_KEY}"
        data = await self._post(url, {"mintAccounts": [ca], "includeOffChain": True})

        if isinstance(data, list) and data:
            result = data[0]
        else:
            result = {"error": True, "ca": ca}

        await set_json(cache_key, result, ttl=settings.CACHE_TTL_TOKEN)
        return result

    async def get_token_largest_accounts(self, ca: str) -> List[Dict[str, Any]]:
        """Top holders of a token via Helius RPC."""
        cache_key = f"token:{ca}:largest_accounts"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        url = f"{settings.HELIUS_RPC_URL}/?api-key={settings.HELIUS_API_KEY}"
        data = await self._post(url, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenLargestAccounts",
            "params": [ca],
        })

        result = data.get("result", {}).get("value", [])
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_TOKEN)
        return result

    async def get_token_supply(self, ca: str) -> float:
        """Total token supply (UI amount, decimals-adjusted). Cached."""
        cache_key = f"token:{ca}:supply"
        cached = await get_json(cache_key)
        if cached is not None:
            return float(cached)

        url = f"{settings.HELIUS_RPC_URL}/?api-key={settings.HELIUS_API_KEY}"
        data = await self._post(url, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenSupply",
            "params": [ca],
        })

        supply = 0.0
        if isinstance(data, dict):
            value = (data.get("result") or {}).get("value") or {}
            ui_amount = value.get("uiAmount")
            if ui_amount is not None:
                supply = float(ui_amount)
            else:
                amount = value.get("amount")
                decimals = value.get("decimals") or 0
                if amount is not None:
                    supply = float(amount) / (10 ** int(decimals))

        await set_json(cache_key, supply, ttl=settings.CACHE_TTL_TOKEN)
        return supply

    async def get_sol_price_usd(self) -> float:
        """Current SOL/USD price. Jupiter → CoinGecko → fallback constant. Cached 60s."""
        cache_key = "price:sol:usd"
        cached = await get_json(cache_key)
        if cached is not None:
            return float(cached)

        wsol = "So11111111111111111111111111111111111111112"
        price: Optional[float] = None

        # 1. Jupiter lite price API
        data = await self._get(f"https://lite-api.jup.ag/price/v3?ids={wsol}")
        if isinstance(data, dict) and not data.get("error"):
            entry = data.get(wsol) or (data.get("data") or {}).get(wsol) or {}
            raw = entry.get("usdPrice") or entry.get("price")
            try:
                if raw is not None:
                    price = float(raw)
            except (TypeError, ValueError):
                price = None

        # 2. CoinGecko fallback
        if price is None or price <= 0:
            data = await self._get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"},
            )
            if isinstance(data, dict) and not data.get("error"):
                raw = (data.get("solana") or {}).get("usd")
                try:
                    if raw is not None:
                        price = float(raw)
                except (TypeError, ValueError):
                    price = None

        # 3. Static fallback — better an approximate mcap than an empty column
        if price is None or price <= 0:
            price = settings.SOL_PRICE_FALLBACK_USD

        await set_json(cache_key, price, ttl=settings.CACHE_TTL_PRICE)
        return price

    @staticmethod
    def _sol_spent_by(wallet: str, tx: Dict[str, Any]) -> float:
        """How much SOL `wallet` spent inside a transaction (swap event or native transfers)."""
        swap = (tx.get("events") or {}).get("swap") or {}
        ni = swap.get("nativeInput") or {}
        if ni.get("account") == wallet:
            try:
                return int(ni.get("amount") or 0) / 1e9
            except (TypeError, ValueError):
                pass

        total = 0
        for nt in tx.get("nativeTransfers") or []:
            if nt.get("fromUserAccount") == wallet:
                try:
                    total += int(nt.get("amount") or 0)
                except (TypeError, ValueError):
                    continue
        return total / 1e9

    async def get_early_buyers(
        self, ca: str, max_mcap_usd: int = None
    ) -> List[Dict[str, Any]]:
        """
        Find wallets that bought the token earliest in its available history.

        Strategy:
        - Paginate as deep into the token's tx history as allowed
          (Helius returns newest-first, so we must go back far enough
          to actually reach launch — this was the old bug: only the
          latest 1000 txs were fetched, i.e. the *most recent* buyers).
        - Sort ascending, walk from the oldest tx forward.
        - A wallet counts as a buyer only if it RECEIVED the token AND
          SPENT SOL in the same transaction (filters out airdrops,
          plain transfers, and DEX vault accounts).
        - Capture sol_spent + token amount so the API layer can compute
          entry price / entry market cap / position size in USD.
        """
        if max_mcap_usd is None:
            max_mcap_usd = settings.EARLY_BUY_MARKET_CAP_USD

        cache_key = f"token:{ca}:early_buyers:v2"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        max_txs = settings.MAX_TX_PAGES_FOR_EARLY_BUYERS * 100
        txs = await self._fetch_all_transactions(ca, limit=max_txs)
        if not txs:
            await set_json(cache_key, [], ttl=settings.CACHE_TTL_TOKEN)
            return []

        # Sort by timestamp ascending — earliest first
        txs.sort(key=lambda t: t.get("timestamp") or 0)

        seen_wallets: set[str] = set()
        early_buyers: List[Dict[str, Any]] = []

        for tx in txs:
            if len(early_buyers) >= settings.MAX_EARLY_BUYERS:
                break
            for transfer in tx.get("tokenTransfers") or []:
                if transfer.get("mint") != ca:
                    continue
                buyer = transfer.get("toUserAccount")
                if not buyer or buyer in seen_wallets or buyer == ca:
                    continue

                sol_spent = self._sol_spent_by(buyer, tx)
                if sol_spent <= 0:
                    # Not a purchase: airdrop / LP seed / internal transfer / vault leg
                    continue

                token_amount = transfer.get("tokenAmount") or 0
                try:
                    token_amount = float(token_amount)
                except (TypeError, ValueError):
                    token_amount = 0.0

                seen_wallets.add(buyer)
                early_buyers.append({
                    "wallet": buyer,
                    "tx_signature": tx.get("signature"),
                    "slot": tx.get("slot"),
                    "timestamp": tx.get("timestamp"),
                    "amount": token_amount,        # tokens bought (decimals-adjusted)
                    "sol_spent": round(sol_spent, 6),
                })

        await set_json(cache_key, early_buyers, ttl=settings.CACHE_TTL_TOKEN)
        return early_buyers

    # ─── Wallet ───────────────────────────────────────────────────────────────

    async def get_wallet_transactions(
        self, wallet_address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch parsed transaction history for a wallet via Helius Enhanced Transactions."""
        cache_key = f"wallet:{wallet_address}:transactions:{limit}"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        result = await self._fetch_all_transactions(wallet_address, limit=limit)
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
        return result

    async def get_wallet_sol_transfers(
        self, wallet_address: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Extract only native SOL transfers from wallet history.
        Uses nativeTransfers field from Helius Enhanced Transactions.
        Returns: [{fromUserAccount, toUserAccount, amount (lamports), timestamp}]
        """
        cache_key = f"wallet:{wallet_address}:sol_transfers"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        txs = await self._fetch_all_transactions(wallet_address, limit=limit)
        sol_transfers: List[Dict[str, Any]] = []

        for tx in txs:
            for transfer in tx.get("nativeTransfers", []):
                from_acc = transfer.get("fromUserAccount")
                to_acc = transfer.get("toUserAccount")
                amount = transfer.get("amount", 0)
                # Only include transfers where our wallet is sender or receiver
                if wallet_address not in (from_acc, to_acc):
                    continue
                sol_transfers.append({
                    "fromUserAccount": from_acc,
                    "toUserAccount": to_acc,
                    "amount": amount,
                    "amount_sol": amount / 1e9,
                    "timestamp": tx.get("timestamp"),
                    "signature": tx.get("signature"),
                })

        await set_json(cache_key, sol_transfers, ttl=settings.CACHE_TTL_WALLET)
        return sol_transfers

    async def get_transaction_detail(self, signature: str) -> Dict[str, Any]:
        """Fetch full detail of a single transaction."""
        cache_key = f"tx:{signature}:detail"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        url = (
            f"{settings.HELIUS_API_URL}/transactions"
            f"?api-key={settings.HELIUS_API_KEY}"
        )
        data = await self._post(url, {"transactions": [signature]})

        result = data[0] if isinstance(data, list) and data else {}
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_TOKEN)
        return result

    # ─── Internal ─────────────────────────────────────────────────────────────

    async def _fetch_all_transactions(
        self, address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Paginate through Helius Enhanced Transactions API.
        Helius returns max 100 per page — uses `before` cursor for pagination.
        """
        url = (
            f"{settings.HELIUS_API_URL}/addresses/{address}/transactions"
            f"?api-key={settings.HELIUS_API_KEY}"
        )
        all_txs: List[Dict[str, Any]] = []
        before: Optional[str] = None
        page_size = min(100, limit)

        while len(all_txs) < limit:
            params: Dict[str, Any] = {"limit": page_size}
            if before:
                params["before"] = before

            data = await self._get(url, params=params)

            if isinstance(data, dict) and data.get("error"):
                break
            if not isinstance(data, list) or not data:
                break

            all_txs.extend(data)

            if len(data) < page_size:
                break  # no more pages

            before = data[-1].get("signature")

        return all_txs[:limit]


# ─── Singleton ────────────────────────────────────────────────────────────────

_client: Optional[HeliusClient] = None


def get_helius_client() -> HeliusClient:
    global _client
    if _client is None:
        _client = HeliusClient()
    return _client