export type Archetype =
  | 'sniper'
  | 'insider'
  | 'swing'
  | 'swing_trader'
  | 'accumulator'
  | 'flipper'
  | 'bot'
  | 'unknown';

export type DevRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type LifecycleStage =
  | 'accumulation'
  | 'markup'
  | 'distribution'
  | 'dump'
  | 'unknown';

export type BuyerCategory = 'smart_money' | 'bot' | 'cluster' | 'regular';

export interface EarlyBuyer {
  wallet: string;
  timestamp?: number;
  tx_signature?: string;
  slot?: number;
  /** Tokens bought (decimals-adjusted) */
  amount?: number;
  amount_tokens?: number;
  /** Position size in USD at entry */
  amount_usd?: number | null;
  sol_spent?: number;
  entry_price_sol?: number | null;
  /** Market cap at the moment of entry */
  entry_market_cap_usd?: number | null;
  market_cap_usd?: number | null;
  blocks_after_launch?: number;
  bot_score?: number;
  smart_money_score?: number;
  archetype?: Archetype;
  category?: BuyerCategory;
  in_cluster?: boolean;
  cluster_id?: number | null;
  suspicion_score?: number | null;
  cluster_type?: string | null;
}

export interface CabalConnection {
  from: string;
  to: string;
  type: 'funding' | 'direct_transfer' | string;
  amount_sol?: number;
}

export interface CabalCluster {
  wallets: string[];
  connections: CabalConnection[];
  common_funder: string | null;
  suspicion_score: number;
  co_traded_tokens?: string[];
}

export interface CabalData {
  clusters: CabalCluster[];
  independent_wallets: string[];
}

export interface DevRisk {
  score: number;
  level: DevRiskLevel;
  dev_wallet: string | null;
  dev_prev_tokens?: number;
  quick_sell_signal?: boolean;
}

export interface TokenAnalysis {
  ca: string;
  name: string | null;
  symbol: string | null;
  token_supply?: number;
  sol_price_usd?: number;
  early_buyers_count: number;
  buyer_counts?: {
    smart_money: number;
    bots: number;
    cluster_members: number;
    regular: number;
  };
  early_buyers: EarlyBuyer[];
  cabal: CabalData;
  dev_risk: DevRisk;
}

export interface WalletProfile {
  wallet_address: string;
  archetype: Archetype;
  bot_score: number;
  smart_money_score: number;
  winrate: number;
  total_trades: number;
  total_pnl_usd: number;
  avg_position_size_usd: number;
  avg_hold_time_minutes: number;
  favorite_dex: string | null;
  first_seen: string | null;
  last_active: string | null;
  updated_at: string;
}

export interface WalletPnl {
  wallet_address: string;
  summary: {
    total_sol_pnl?: number;
    total_realized_usd: number;
    total_unrealized_usd?: number;
    winrate: number;
    total_trades: number;
    completed_trades?: number;
    win_trades?: number;
    avg_hold_time_minutes: number;
    avg_position_size_usd: number;
    avg_position_size_sol?: number;
    favorite_dex?: string | null;
    sol_price_usd?: number;
  };
  by_token?: Array<{
    mint: string;
    symbol?: string;
    realized_usd: number;
    sol_pnl?: number;
    sol_spent?: number;
    sol_received?: number;
    buys?: number;
    sells?: number;
    trades: number;
  }>;
}

export interface TradeRecord {
  signature?: string;
  timestamp?: number;
  type?: string;
  source?: string;
  description?: string;
  tokenTransfers?: Array<Record<string, unknown>>;
}

export interface WatchlistItem {
  wallet_address: string;
  label: string | null;
  added_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  group: 'funder' | 'member' | 'independent';
  suspicionScore?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  amount_sol?: number;
}
