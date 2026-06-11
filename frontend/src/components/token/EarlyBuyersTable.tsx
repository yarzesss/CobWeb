'use client';

import { useMemo, useState } from 'react';
import type { EarlyBuyer, BuyerCategory } from '@/lib/types';
import { AddressLink } from '@/components/shared/AddressLink';
import { ArchetypeBadge, Badge } from '@/components/ui/Badge';
import { getSolscanWalletUrl, formatUsd, formatTokenAmount } from '@/lib/utils';
import type { Archetype } from '@/lib/types';

type Filter = 'all' | 'smart' | 'cluster' | 'bots';

const FILTER_LABELS: Record<Filter, string> = {
  all: 'All Buyers',
  smart: 'Smart Money',
  cluster: 'Clusters',
  bots: 'Bot Activity',
};

/**
 * Buyer category resolution.
 * Prefers the explicit `category` field from the backend; falls back to
 * scores so the table still works against an older API response.
 * Each wallet lands in EXACTLY ONE bucket — tabs can never show
 * identical lists again.
 */
function getCategory(b: EarlyBuyer): BuyerCategory {
  if (b.category) return b.category;
  const botScore = b.bot_score ?? 0;
  if (botScore >= 60) return 'bot';
  if (b.in_cluster && (b.suspicion_score ?? 0) >= 70) return 'cluster';
  if ((b.smart_money_score ?? 0) >= 55) return 'smart_money';
  return 'regular';
}

function matchesFilter(b: EarlyBuyer, filter: Filter): boolean {
  if (filter === 'all') return true;
  const cat = getCategory(b);
  if (filter === 'smart') return cat === 'smart_money';
  if (filter === 'cluster') return cat === 'cluster';
  return cat === 'bot';
}

export function EarlyBuyersTable({ buyers }: { buyers: EarlyBuyer[] }) {
  const [filter, setFilter] = useState<Filter>('all');

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: buyers.length, smart: 0, cluster: 0, bots: 0 };
    for (const b of buyers) {
      const cat = getCategory(b);
      if (cat === 'smart_money') c.smart += 1;
      else if (cat === 'cluster') c.cluster += 1;
      else if (cat === 'bot') c.bots += 1;
    }
    return c;
  }, [buyers]);

  const filtered = useMemo(
    () => buyers.filter((b) => matchesFilter(b, filter)),
    [buyers, filter],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {(['all', 'smart', 'cluster', 'bots'] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={filter === f ? 'pixel-tab-active' : 'pixel-tab hover:text-gray-200'}
          >
            {FILTER_LABELS[f]}
            <span className="ml-1 text-cobweb-pink">({counts[f]})</span>
          </button>
        ))}
      </div>

      <div className="overflow-x-auto border-2 border-cobweb-border">
        <table className="w-full min-w-[760px] font-mono text-xs">
          <thead>
            <tr className="border-b-2 border-cobweb-border bg-cobweb-surface2 text-left font-pixel text-[8px] uppercase text-gray-400">
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2">Archetype</th>
              <th className="px-3 py-2">Bot</th>
              <th className="px-3 py-2">SM Score</th>
              <th className="px-3 py-2">Entry Mcap</th>
              <th className="px-3 py-2">Bought</th>
              <th className="px-3 py-2">Size (USD)</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-gray-500">
                  No wallets match this filter
                </td>
              </tr>
            ) : (
              filtered.map((buyer) => {
                const mcap = buyer.entry_market_cap_usd ?? buyer.market_cap_usd;
                const tokens = buyer.amount_tokens ?? buyer.amount;
                return (
                  <tr
                    key={buyer.wallet}
                    className="border-b border-cobweb-border/50 hover:bg-cobweb-surface2/50 transition-colors"
                  >
                    <td className="px-3 py-2">
                      <AddressLink
                        address={buyer.wallet}
                        href={`/wallet/${buyer.wallet}`}
                        externalHref={getSolscanWalletUrl(buyer.wallet)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <ArchetypeBadge archetype={(buyer.archetype as Archetype) ?? 'unknown'} />
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={(buyer.bot_score ?? 0) >= 60 ? 'danger' : 'success'}>
                        {buyer.bot_score ?? '—'}
                      </Badge>
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={(buyer.smart_money_score ?? 0) >= 55 ? 'pink' : 'default'}>
                        {buyer.smart_money_score ?? '—'}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-gray-300">
                      {mcap != null ? formatUsd(mcap).replace('+', '') : '—'}
                    </td>
                    <td className="px-3 py-2 text-gray-300">
                      {tokens != null && tokens > 0 ? formatTokenAmount(tokens) : '—'}
                    </td>
                    <td className="px-3 py-2 text-gray-300">
                      {buyer.amount_usd != null ? formatUsd(buyer.amount_usd).replace('+', '') : '—'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
