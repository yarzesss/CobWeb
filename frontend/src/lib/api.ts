import type {
  CabalCluster,
  CabalData,
  DevRisk,
  GraphLink,
  GraphNode,
  TokenAnalysis,
  WalletPnl,
  WalletProfile,
  WatchlistItem,
  TradeRecord,
  EarlyBuyer,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAuthHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('cobweb_jwt');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/healthz'),

  getNonce: (wallet: string) =>
    request<{ wallet: string; nonce: string; expires_in: number }>(
      `/auth/nonce?wallet=${encodeURIComponent(wallet)}`,
    ),

  verifyAuth: (payload: { wallet: string; signature: string; nonce: string }) =>
    request<{ access_token: string; token_type: string }>('/auth/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getToken: (ca: string) => request<TokenAnalysis>(`/token/${ca}`),

  getTokenEarlyBuyers: (ca: string, limit = 100, offset = 0) =>
    request<{ ca: string; total: number; buyers: EarlyBuyer[] }>(
      `/token/${ca}/early-buyers?limit=${limit}&offset=${offset}`,
    ),

  getTokenCabal: (ca: string) =>
    request<CabalData>(`/token/${ca}/cabal`),

  getTokenDevRisk: (ca: string) =>
    request<DevRisk>(`/token/${ca}/dev-risk`),

  getWallet: (address: string) =>
    request<WalletProfile>(`/wallet/${address}`),

  getWalletTrades: (address: string, limit = 100, offset = 0) =>
    request<{
      wallet_address: string;
      total: number;
      trades: TradeRecord[];
    }>(`/wallet/${address}/trades?limit=${limit}&offset=${offset}`),

  getWalletPnl: (address: string) =>
    request<WalletPnl>(`/wallet/${address}/pnl`),

  getWatchlist: () => request<WatchlistItem[]>('/watchlist'),

  addToWatchlist: (wallet_address: string, label?: string) =>
    request<WatchlistItem>('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ wallet_address, label }),
    }),

  removeFromWatchlist: (wallet_address: string) =>
    request<{ deleted: boolean }>(`/watchlist/${wallet_address}`, {
      method: 'DELETE',
    }),
};

export function cabalToGraph(cabal: CabalData): {
  nodes: GraphNode[];
  links: GraphLink[];
} {
  const nodeMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  const ensureNode = (
    id: string,
    group: GraphNode['group'],
    suspicionScore?: number,
  ) => {
    if (!nodeMap.has(id)) {
      nodeMap.set(id, {
        id,
        label: id.slice(0, 4) + '…' + id.slice(-4),
        group,
        suspicionScore,
      });
    }
  };

  for (const cluster of cabal.clusters) {
    for (const wallet of cluster.wallets) {
      ensureNode(wallet, 'member', cluster.suspicion_score);
    }
    if (cluster.common_funder) {
      ensureNode(cluster.common_funder, 'funder', cluster.suspicion_score);
    }
    for (const conn of cluster.connections) {
      links.push({
        source: conn.from,
        target: conn.to,
        type: conn.type,
        amount_sol: conn.amount_sol,
      });
    }
  }

  for (const wallet of cabal.independent_wallets) {
    ensureNode(wallet, 'independent');
  }

  return { nodes: Array.from(nodeMap.values()), links };
}

export { ApiError };
