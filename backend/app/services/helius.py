from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.core.cache import get_json, set_json

WSOL_MINT = "So11111111111111111111111111111111111111112"

# Addresses that must never be counted as "buyers" — programs, DEX
# authorities, fee vaults. tokenTransfers.toUserAccount can resolve to
# these for pool-side legs of a swap.
NON_BUYER_ADDRESSES: set[str] = {
    "11111111111111111111111111111111",                  # System Program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",       # SPL Token
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",       # Token-2022
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",      # Associated Token
    "ComputeBudget111111111111111111111111111111",        # Compute Budget
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",       # pump.fun program
    "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM",      # pump.fun fee
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",       # pump.fun AMM
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",      # Raydium authority v4
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",      # Raydium AMM v4
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",      # Raydium CLMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",       # Orca Whirlpool
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",       # Jupiter v6
}


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

    # ─── SOL price (USD) ─────────────────────────────────────────────────────

    async def get_sol_price_usd(self) -> Optional[float]:
        """Current SOL/USD price. Jupiter → CoinGecko fallback, 60s cache."""
        cache_key = "price:sol_usd"
        cached = await get_json(cache_key)
        if cached is not None:
            return float(cached)

        price: Optional[float] = None

        # 1) Jupiter price API
        data = await self._get(
            "https://lite-api.jup.ag/price/v2",
            params={"ids": WSOL_MINT},
        )
        try:
            if isinstance(data, dict) and not data.get("error"):
                entry = (data.get("data") or {}).get(WSOL_MINT) or {}
                raw = entry.get("price") or entry.get("usdPrice")
                if raw is not None:
                    price = float(raw)
        except (TypeError, ValueError):
            price = None

        # 2) CoinGecko fallback
        if price is None:
            data = await self._get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"},
            )
            try:
                if isinstance(data, dict) and not data.get("error"):
                    raw = (data.get("solana") or {}).get("usd")
                    if raw is not None:
                        price = float(raw)
            except (TypeError, ValueError):
                price = None

        if price is not None and price > 0:
            await set_json(cache_key, price, ttl=settings.SOL_PRICE_CACHE_TTL)
        return price

    # ─── Token ───────────────────────────────────────────────────────────────

    async def get_token_metadata(self, ca: str) -> Dict[str, Any]:
        """Raw token metadata via Helius token-metadata endpoint."""
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

    async def get_token_info(self, ca: str) -> Dict[str, Any]:
        """
        Normalized token info parsed from Helius metadata:
        { ca, name, symbol, decimals, supply_ui, update_authority }
        """
        meta = await self.get_token_metadata(ca)
        info: Dict[str, Any] = {
            "ca": ca,
            "name": None,
            "symbol": None,
            "decimals": None,
            "supply_ui": None,
            "update_authority": None,
        }
        if not isinstance(meta, dict) or meta.get("error"):
            return info

        on_chain_meta = (meta.get("onChainMetadata") or {}).get("metadata") or {}
        meta_data = on_chain_meta.get("data") or {}
        off_chain = (meta.get("offChainMetadata") or {}).get("metadata") or {}
        legacy = meta.get("legacyMetadata") or {}

        info["name"] = (
            (meta_data.get("name") or "").strip()
            or (off_chain.get("name") or "").strip()
            or (legacy.get("name") or "").strip()
            or None
        )
        info["symbol"] = (
            (meta_data.get("symbol") or "").strip()
            or (off_chain.get("symbol") or "").strip()
            or (legacy.get("symbol") or "").strip()
            or None
        )
        info["update_authority"] = on_chain_meta.get("updateAuthority")

        parsed_info = (
            ((meta.get("onChainAccountInfo") or {}).get("accountInfo") or {})
            .get("data", {})
            .get("parsed", {})
            .get("info", {})
        )
        try:
            decimals = int(parsed_info.get("decimals"))
            supply_raw = int(parsed_info.get("supply"))
            info["decimals"] = decimals
            info["supply_ui"] = supply_raw / (10 ** decimals) if decimals >= 0 else None
        except (TypeError, ValueError):
            pass

        return info

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

        result = data.get("result", {}).get("value", []) if isinstance(data, dict) else []
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_TOKEN)
        return result

    # ─── Early buyers ─────────────────────────────────────────────────────────

    @staticmethod
    def _wallet_sol_spent_in_tx(tx: Dict[str, Any], wallet: str) -> float:
        """How much SOL the wallet paid in this tx (positive number, in SOL)."""
        # 1) Parsed swap event — most accurate
        swap = (tx.get("events") or {}).get("swap") or {}
        ni = swap.get("nativeInput") or {}
        if ni.get("account") == wallet:
            try:
                return int(ni.get("amount") or 0) / 1e9
            except (TypeError, ValueError):
                pass

        # 2) Account-level native balance change
        for acc in tx.get("accountData") or []:
            if acc.get("account") == wallet:
                change = acc.get("nativeBalanceChange") or 0
                if change < 0:
                    return -change / 1e9
                break

        # 3) Native transfers fallback
        spent = 0
        for nt in tx.get("nativeTransfers") or []:
            if nt.get("fromUserAccount") == wallet:
                spent += nt.get("amount") or 0
            if nt.get("toUserAccount") == wallet:
                spent -= nt.get("amount") or 0
        return max(0.0, spent / 1e9)

    async def get_early_buyers_full(
        self, ca: str, max_mcap_usd: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find wallets that genuinely BOUGHT the token early (paid SOL,
        received the token), with entry market cap and amounts.

        Returns:
        {
          "buyers": [
            { wallet, tx_signature, slot, timestamp,
              token_amount, sol_spent, amount_usd,
              entry_mcap_usd, entry_price_sol }
          ],
          "launch_timestamp": int | None,
          "launch_slot": int | None,
          "history_complete": bool,   # did we reach the token's first tx
          "sol_price_usd": float | None,
        }
        """
        if max_mcap_usd is None:
            max_mcap_usd = settings.EARLY_BUY_MARKET_CAP_USD

        cache_key = f"token:{ca}:early_buyers:v2"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        token_info, sol_price = await asyncio.gather(
            self.get_token_info(ca),
            self.get_sol_price_usd(),
        )
        supply_ui = token_info.get("supply_ui")

        txs, reached_genesis = await self._fetch_transaction_history(
            ca, max_pages=settings.HELIUS_MAX_TX_PAGES
        )

        empty = {
            "buyers": [],
            "launch_timestamp": None,
            "launch_slot": None,
            "history_complete": reached_genesis,
            "sol_price_usd": sol_price,
        }
        if not txs:
            await set_json(cache_key, empty, ttl=settings.CACHE_TTL_TOKEN)
            return empty

        # Oldest first — these are the earliest available transactions.
        txs.sort(key=lambda t: (t.get("timestamp") or 0, t.get("slot") or 0))

        launch_ts = next((t.get("timestamp") for t in txs if t.get("timestamp")), None)
        launch_slot = next((t.get("slot") for t in txs if t.get("slot")), None)

        seen_wallets: set[str] = set()
        buyers: List[Dict[str, Any]] = []
        consecutive_above_cap = 0

        for tx in txs:
            if len(buyers) >= settings.MAX_EARLY_BUYERS:
                break
            if consecutive_above_cap >= 25:
                break  # price has clearly moved past the early-buy window

            for transfer in tx.get("tokenTransfers") or []:
                if transfer.get("mint") != ca:
                    continue
                buyer = transfer.get("toUserAccount")
                if (
                    not buyer
                    or buyer in seen_wallets
                    or buyer == ca
                    or buyer in NON_BUYER_ADDRESSES
                ):
                    continue

                try:
                    token_amount = float(transfer.get("tokenAmount") or 0)
                except (TypeError, ValueError):
                    token_amount = 0.0
                if token_amount <= 0:
                    continue

                sol_spent = self._wallet_sol_spent_in_tx(tx, buyer)
                if sol_spent <= 0.0005:
                    # No SOL paid → airdrop / internal transfer, not a buy
                    continue

                entry_price_sol = sol_spent / token_amount
                entry_mcap_usd: Optional[float] = None
                amount_usd: Optional[float] = None
                if sol_price:
                    amount_usd = sol_spent * sol_price
                    if supply_ui:
                        entry_mcap_usd = entry_price_sol * supply_ui * sol_price

                if entry_mcap_usd is not None and entry_mcap_usd > max_mcap_usd:
                    consecutive_above_cap += 1
                    continue
                consecutive_above_cap = 0

                seen_wallets.add(buyer)
                buyers.append({
                    "wallet": buyer,
                    "tx_signature": tx.get("signature"),
                    "slot": tx.get("slot"),
                    "timestamp": tx.get("timestamp"),
                    "token_amount": token_amount,
                    "sol_spent": round(sol_spent, 6),
                    "amount_usd": round(amount_usd, 2) if amount_usd is not None else None,
                    "entry_price_sol": entry_price_sol,
                    "entry_mcap_usd": round(entry_mcap_usd, 2) if entry_mcap_usd is not None else None,
                })

        result = {
            "buyers": buyers,
            "launch_timestamp": launch_ts,
            "launch_slot": launch_slot,
            "history_complete": reached_genesis,
            "sol_price_usd": sol_price,
        }
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_TOKEN)
        return result

    async def get_early_buyers(
        self, ca: str, max_mcap_usd: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Back-compat helper returning only the buyers list."""
        full = await self.get_early_buyers_full(ca, max_mcap_usd)
        return full.get("buyers", [])

    # ─── Wallet ───────────────────────────────────────────────────────────────

    async def get_wallet_transactions(
        self, wallet_address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Parsed transaction history for a wallet (newest first)."""
        cache_key = f"wallet:{wallet_address}:transactions:{limit}"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        max_pages = max(1, (limit + 99) // 100)
        txs, _ = await self._fetch_transaction_history(wallet_address, max_pages=max_pages)
        result = txs[:limit]
        await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
        return result

    async def get_wallet_sol_transfers(
        self, wallet_address: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Native SOL transfers touching this wallet."""
        cache_key = f"wallet:{wallet_address}:sol_transfers"
        cached = await get_json(cache_key)
        if cached is not None:
            return cached

        txs = await self.get_wallet_transactions(wallet_address, limit=limit)
        sol_transfers: List[Dict[str, Any]] = []

        for tx in txs:
            for transfer in tx.get("nativeTransfers") or []:
                from_acc = transfer.get("fromUserAccount")
                to_acc = transfer.get("toUserAccount")
                amount = transfer.get("amount", 0)
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
        """Full detail of a single transaction."""
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

    async def _fetch_transaction_history(
        self, address: str, max_pages: int = 10
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Paginate Helius Enhanced Transactions (newest → oldest, `before` cursor).

        Returns (transactions, reached_genesis). reached_genesis=True means we
        walked all the way back to the address's first transaction, so the
        oldest items in the list really are the earliest on-chain activity.
        """
        url = (
            f"{settings.HELIUS_API_URL}/addresses/{address}/transactions"
            f"?api-key={settings.HELIUS_API_KEY}"
        )
        all_txs: List[Dict[str, Any]] = []
        before: Optional[str] = None
        reached_genesis = False

        for _ in range(max_pages):
            params: Dict[str, Any] = {"limit": 100}
            if before:
                params["before"] = before

            data = await self._get(url, params=params)

            if isinstance(data, dict) and data.get("error"):
                break
            if not isinstance(data, list) or not data:
                reached_genesis = True
                break

            all_txs.extend(data)

            if len(data) < 100:
                reached_genesis = True
                break

            before = data[-1].get("signature")

        return all_txs, reached_genesis


# ─── Singleton ────────────────────────────────────────────────────────────────

_client: Optional[HeliusClient] = None


def get_helius_client() -> HeliusClient:
    global _client
    if _client is None:
        _client = HeliusClient()
    return _client