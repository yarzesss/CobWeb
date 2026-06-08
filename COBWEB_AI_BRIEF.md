# COBWEB — Project Brief for AI Assistant

## What is Cobweb?

Cobweb is a Solana blockchain analytics platform. The core idea: a user enters a token's Contract Address (CA), and the platform finds all wallets that bought that token at an early market cap (5k–10k USD). It then analyzes connections between those wallets — shared funders, direct SOL transfers between them, and coordinated buying patterns across multiple tokens.

The goal is to answer one question: **"Are these early buyers independent Smart Money traders, or a coordinated insider group?"**

If it's a group — show the connection graph, their common funder wallet, and every other token they acted on together.
If they're independent — show each wallet's profile, trading archetype, winrate, and Dev Risk Score of the token.

Target users: retail traders on Solana who want to make decisions based on on-chain data instead of Telegram alpha calls.

---

## What Makes It Different From Competitors

Competitors (Birdeye, Gmgn.ai, Cielo Finance) show numbers. Cobweb shows **behavioral patterns and hidden connections**.

Unique features that don't exist elsewhere:

1. **Cabal / Cluster Detector** — finds groups of wallets that coordinate trades. Builds a graph of connections (shared funder, direct transfers, co-trading history). Gives each cluster a "suspicion score" 0–100.

2. **Wallet Archetype Classifier** — classifies every wallet as: Sniper / Insider / Swing Trader / Accumulator / Flipper / Bot. Based on behavior, not just PnL.

3. **Bot Filter** — sniper bots are excluded from Smart Money leaderboards. They appear in a separate "Bot Activity" tab. Calculated via Bot Score (0–100).

4. **Dev Risk Score** — analyzes the token deployer's history: how many tokens they've deployed, how many rugged, how fast they sold their allocation.

5. **Token Lifecycle Stage** — automatically determines current phase: Accumulation / Markup / Distribution / Dump (based on Wyckoff method applied to on-chain holder behavior).

6. **Multi-wallet Attribution** — detects if multiple wallets are controlled by one person (same funder, same behavioral fingerprint) and shows their combined real PnL.

7. **Narrative Tracker** — tracks which token categories (AI, DeSci, meme, RWA) Smart Money wallets are currently buying.

8. **Copy-trade Simulator** — backtest: "If you had copied this wallet for the last 30 days, your result would be +/- X%".

---

## Tech Stack

### Backend
- **Python 3.12** + **FastAPI** (async)
- **PostgreSQL** (via SQLAlchemy async + asyncpg)
- **Redis** (caching + pub/sub)
- **Alembic** (database migrations)
- **Helius API** (Solana RPC provider — all blockchain data comes from here)
- **httpx** (async HTTP client for Helius)
- **python-jose** + **PyNaCl** (JWT auth + Solana message signature verification)

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Solana wallet-adapter** (Phantom / Solflare login via message signing — no access to funds)
- **React Query** (data fetching + caching)

### Design Style
- Dark pixel art aesthetic
- Primary colors: dark pink (#C2185B range) and dark gray (#1a1a2e range)
- Pixel/retro font for headings
- Clean data-dense UI (think trading terminal meets pixel art)

---

## Project File Structure

```
cobweb/
│
├── docker-compose.yml              ← needs to be created
├── .env.example                    ← needs to be created
├── README.md                       ← needs to be created
│
├── backend/
│   ├── Dockerfile                  ← needs to be created
│   ├── requirements.txt            ← needs to be created
│   ├── alembic.ini                 ← needs to be created
│   ├── alembic/
│   │   └── versions/               ← migration files go here
│   │
│   └── app/
│       ├── main.py                 ← needs to be created
│       ├── config.py               ← needs to be created
│       ├── database.py             ← needs to be created
│       │
│       ├── models/
│       │   ├── __init__.py         ← needs to be created
│       │   ├── user.py             ← needs to be created
│       │   ├── watchlist.py        ← needs to be created
│       │   ├── wallet_profile.py   ← needs to be created
│       │   └── token_analysis.py   ← needs to be created
│       │
│       ├── routers/
│       │   ├── __init__.py         ← needs to be created
│       │   ├── auth.py             ← Web3 sign/verify → JWT
│       │   ├── tokens.py           ← Token dashboard endpoints
│       │   ├── wallets.py          ← Wallet profiler endpoints
│       │   └── watchlist.py        ← Watchlist CRUD
│       │
│       ├── services/
│       │   ├── __init__.py         ← needs to be created
│       │   ├── helius.py           ← Helius RPC API client (MOST IMPORTANT)
│       │   ├── pnl.py              ← PnL calculation logic
│       │   ├── classifier.py       ← Bot Score + Wallet Archetype logic
│       │   └── cabal.py            ← Cluster/connection detection (CORE FEATURE)
│       │
│       └── core/
│           ├── __init__.py         ← needs to be created
│           ├── auth.py             ← JWT creation/verification helpers
│           └── cache.py            ← Redis helper wrappers
│
└── frontend/
    ├── Dockerfile                  ← needs to be created
    ├── package.json                ← needs to be created
    ├── next.config.js
    ├── tailwind.config.js          ← pixel art theme config
    ├── tsconfig.json
    │
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx                    ← homepage with CA search input
        │   ├── token/[ca]/page.tsx         ← Token Dashboard
        │   └── wallet/[address]/page.tsx   ← Wallet Profiler
        │
        ├── components/
        │   ├── ui/                         ← base components (button, input, card)
        │   ├── token/                      ← EarlyBuyersTable, CabalGraph, DevRiskCard
        │   └── wallet/                     ← WalletStats, TradeHistory, ArchetypeBadge
        │
        ├── lib/
        │   ├── api.ts                      ← axios/fetch client to backend
        │   └── wallet.ts                   ← web3 auth helpers
        │
        └── providers/
            └── index.tsx                   ← WalletAdapter + ReactQuery providers
```

---

## Database Models (Already Created)

### User
```python
id, wallet_address (unique), telegram_chat_id, subscription_tier (free/premium), last_seen, created_at
```

### Watchlist
```python
id, user_id (FK), wallet_address, label, added_at
```

### WalletProfile
```python
id, wallet_address (unique),
archetype (sniper/insider/swing/accumulator/flipper/bot/unknown),
bot_score (0-100), smart_money_score (0-100),
winrate (0.0-1.0), total_trades, total_pnl_usd,
avg_position_size_usd, avg_hold_time_minutes, favorite_dex,
first_seen, last_active, updated_at
```

### TokenAnalysis
```python
id, ca (unique), name, symbol, dev_wallet,
dev_risk_score (0-100), dev_prev_tokens, dev_rug_count,
lifecycle_stage (accumulation/markup/distribution/dump/unknown),
is_bundled (bool), sniper_count,
early_buyers (JSON), cabal_data (JSON),
total_early_buyers, analyzed_at, updated_at
```

---

## Key Config Variables (config.py)

```python
HELIUS_API_KEY          # Helius RPC key
HELIUS_RPC_URL          # https://mainnet.helius-rpc.com
HELIUS_API_URL          # https://api.helius.xyz/v0
DATABASE_URL            # postgresql+asyncpg://...
REDIS_URL               # redis://localhost:6379/0
JWT_SECRET
TELEGRAM_BOT_TOKEN
CACHE_TTL_TOKEN         # 300s — token data cache
CACHE_TTL_WALLET        # 600s — wallet profile cache
CACHE_TTL_CABAL         # 1800s — cabal analysis cache
HELIUS_REQUESTS_PER_SECOND  # 10 — rate limiting
MAX_WALLETS_PER_CABAL_SCAN  # 50
EARLY_BUY_MARKET_CAP_USD    # 10000 — threshold for "early buyer"
```

---

## Core Business Logic to Implement

### 1. Helius Service (services/helius.py)
The most critical service. Must implement:
- `get_token_metadata(ca)` — name, symbol, decimals, supply
- `get_early_buyers(ca, max_mcap_usd)` — all wallets that bought before market cap hit `max_mcap_usd`
- `get_wallet_transactions(wallet_address, limit)` — full transaction history
- `get_wallet_sol_transfers(wallet_address)` — only SOL transfer history (for cabal detection)
- `get_token_largest_accounts(ca)` — current top holders
- `get_transaction_detail(signature)` — full detail of a single transaction

Use Helius Enhanced Transactions API (`/v0/addresses/{address}/transactions`) for parsed data.
Always implement rate limiting (max 10 req/sec) and Redis caching.

### 2. Cabal Detection (services/cabal.py)
Three-layer connection analysis:
- **Layer 1 — Common Funder**: Check if multiple early buyer wallets received their first SOL from the same source wallet. Strongest signal.
- **Layer 2 — Direct Transfers**: Check if wallets sent SOL directly to each other (even via intermediary). Build a directed graph.
- **Layer 3 — Co-trading Pattern**: Check if wallets repeatedly appear together as early buyers on other tokens (even without direct transfers).

Output format:
```python
{
  "clusters": [
    {
      "wallets": ["addr1", "addr2", "addr3"],
      "connections": [
        {"from": "addr1", "to": "addr2", "type": "funding", "amount_sol": 1.5},
        {"from": "addr2", "to": "addr3", "type": "direct_transfer"}
      ],
      "common_funder": "funder_addr",
      "suspicion_score": 87,
      "co_traded_tokens": ["ca1", "ca2"]
    }
  ],
  "independent_wallets": ["addr4", "addr5"]
}
```

### 3. Bot Score (services/classifier.py)
```python
score = 0
if avg_blocks_after_deploy < 3: score += 40    # bought in first 3 blocks
if min_tx_interval_ms < 500: score += 25        # transactions faster than 500ms
if daily_tx_count > 50: score += 20             # too many trades per day
if position_size_variance < 0.05: score += 15   # robotically consistent position sizes
# score > 60 = BOT, score < 30 = HUMAN, between = UNKNOWN
```

### 4. Dev Risk Score (services/classifier.py)
```python
score = 0
if dev_rug_count > 0: score += (dev_rug_count * 25)   # 25 points per rug
if dev_sells_within_hours < 24: score += 30             # sold within 24h of launch
if dev_prev_tokens > 5: score += 10                     # serial deployer
if connected_to_known_scammers: score += 35             # blacklisted connections
# score > 70 = HIGH RISK, 40-70 = MEDIUM, <40 = LOW
```

### 5. Web3 Auth Flow (routers/auth.py)
```
1. Frontend requests a nonce from backend: GET /auth/nonce?wallet=ADDRESS
2. Backend generates nonce, stores in Redis for 5 minutes
3. User signs the message with their wallet (Phantom/Solflare)
4. Frontend sends: POST /auth/verify { wallet, signature, nonce }
5. Backend verifies signature using PyNaCl (Ed25519)
6. If valid → create/update User in DB → return JWT
7. All protected routes use JWT Bearer token
```

---

## API Endpoints to Build

```
GET  /auth/nonce?wallet={address}
POST /auth/verify                    { wallet, signature, nonce }

GET  /token/{ca}                     → full token analysis (early buyers + cabal + dev risk)
GET  /token/{ca}/early-buyers        → paginated list of early buyers
GET  /token/{ca}/cabal               → cabal cluster analysis
GET  /token/{ca}/dev-risk            → dev wallet risk score

GET  /wallet/{address}               → full wallet profile
GET  /wallet/{address}/trades        → trade history
GET  /wallet/{address}/pnl           → PnL breakdown

GET  /watchlist                      → get user's saved wallets (auth required)
POST /watchlist                      → add wallet (auth required)
DELETE /watchlist/{wallet_address}   → remove wallet (auth required)
```

---

## Coding Standards

- **Python**: async/await everywhere, type hints on all functions, Pydantic schemas for all request/response bodies
- **Error handling**: never let Helius errors crash the API — always return partial data with error flags
- **Caching strategy**: Redis cache before every Helius call. Key format: `token:{ca}:early_buyers`, `wallet:{address}:profile`, `cabal:{ca}:clusters`
- **TypeScript**: strict mode, no `any` types
- **Components**: keep components small and focused, one responsibility each

---

## What To Build Next (Priority Order)

## Instructions for AI Assistant

Create ALL files from scratch. Do not skip any file, 
do not assume anything is already done. 
Start with priority order below and create every 
single file completely before moving to the next.

1. `backend/app/core/auth.py` — JWT helpers
2. `backend/app/core/cache.py` — Redis helpers
3. `backend/app/services/helius.py` — Helius API client ← START HERE, everything depends on this
4. `backend/app/services/classifier.py` — Bot score + Archetype + Dev risk
5. `backend/app/services/cabal.py` — Cluster detection
6. `backend/app/services/pnl.py` — PnL calculation
7. `backend/app/routers/auth.py` — Web3 auth
8. `backend/app/routers/tokens.py` — Token endpoints
9. `backend/app/routers/wallets.py` — Wallet endpoints
10. `backend/app/routers/watchlist.py` — Watchlist endpoints
11. `backend/app/main.py` — FastAPI app entry point
12. `backend/Dockerfile`
13. `frontend/` — Next.js app (after backend is solid)

---

## Important Notes

- Sniper bots must be **filtered out** from Smart Money leaderboards. They appear in a separate section.
- All Helius calls must go through Redis cache first — check cache, if miss → call Helius → store result.
- The `cabal_data` and `early_buyers` fields in TokenAnalysis are JSON — store the full structured result there so we don't re-compute on every request.
- Market cap threshold for "early buyer" is configurable via `EARLY_BUY_MARKET_CAP_USD` in config (default 10,000 USD).
- When calculating PnL, account for Jupiter routing, wrapped tokens, and multi-hop swaps on Solana — it's non-trivial.
- The project name is **Cobweb**. The visual metaphor is a spider web — wallets are nodes, connections are threads.
