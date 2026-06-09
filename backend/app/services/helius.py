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

    async def get_early_buyers(
        self, ca: str, max_mcap_usd: int = None
    ) -> List[Dict[str, Any]]:
        """
        Find wallets that bought the token very early (near launch).

        Strategy:
        - Fetch all transactions for the token CA sorted by time
        - Extract unique buyers from token transfer events (toUserAccount)
        - The first N unique buyers are considered "early" — bought at lowest mcap
        - Returns list of dicts: {wallet, tx_signature, slot, timestamp}
        """
        if max_mcap_usd is None:
            max_mcap_usd = settings.EARLY_BUY_MARKET_CAP_USD

        cache_key = f"token:{ca}:early_buyers"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        txs = await self._fetch_all_transactions(ca, limit=1000)
        if not txs:
            await set_json(cache_key, [], ttl=settings.CACHE_TTL_TOKEN)
            return []

        # Sort by timestamp ascending — earliest first
        txs.sort(key=lambda t: t.get("timestamp", 0))

        seen_wallets: set[str] = set()
        early_buyers: List[Dict[str, Any]] = []

        for tx in txs:
            # Parse token transfers — we want buyers (toUserAccount)
            for transfer in tx.get("tokenTransfers", []):
                if transfer.get("mint") != ca:
                    continue
                buyer = transfer.get("toUserAccount")
                if not buyer or buyer in seen_wallets:
                    continue
                # Skip if it's the token's own CA or a known DEX vault
                if buyer == ca:
                    continue
                seen_wallets.add(buyer)
                early_buyers.append({
                    "wallet": buyer,
                    "tx_signature": tx.get("signature"),
                    "slot": tx.get("slot"),
                    "timestamp": tx.get("timestamp"),
                    "amount": transfer.get("tokenAmount", 0),
                })

        await set_json(cache_key, early_buyers, ttl=settings.CACHE_TTL_TOKEN)
        return early_buyers

    # ─── Wallet ───────────────────────────────────────────────────────────────

    async def get_wallet_transactions(
        self, wallet_address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch parsed transaction history for a wallet via Helius Enhanced Transactions."""
        cache_key = f"wallet:{wallet_address}:transactions"
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