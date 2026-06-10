'use client';

import { useMemo, useState } from 'react';
import type { EarlyBuyer } from '@/lib/types';
import { AddressLink } from '@/components/shared/AddressLink';
import { ArchetypeBadge, Badge } from '@/components/ui/Badge';
import { getSolscanWalletUrl, formatUsd } from '@/lib/utils';
import type { Archetype } from '@/lib/types';

type Filter = 'all' | 'smart' | 'bots';

export function EarlyBuyersTable({ buyers }: { buyers: EarlyBuyer[] }) {
  const [filter, setFilter] = useState<Filter>('all');

  const filtered = useMemo(() => {
    return buyers.filter((b) => {
      const botScore = b.bot_score ?? 0;
      if (filter === 'smart') return botScore < 30;
      if (filter === 'bots') return botScore > 60;
      return true;
    });
  }, [buyers, filter]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {(['all', 'smart', 'bots'] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={
              filter === f
                ? 'pixel-tab-active'
                : 'pixel-tab hover:text-gray-200'
            }
          >
            {f === 'all' ? 'All Buyers' : f === 'smart' ? 'Smart Money' : 'Bot Activity'}
            <span className="ml-1 text-cobweb-pink">
              ({f === 'all' ? buyers.length : buyers.filter((b) => {
                const s = b.bot_score ?? 0;
                return f === 'smart' ? s < 30 : s > 60;
              }).length})
            </span>
          </button>
        ))}
      </div>

      <div className="overflow-x-auto border-2 border-cobweb-border">
        <table className="w-full min-w-[640px] font-mono text-xs">
          <thead>
            <tr className="border-b-2 border-cobweb-border bg-cobweb-surface2 text-left font-pixel text-[8px] uppercase text-gray-400">
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2">Archetype</th>
              <th className="px-3 py-2">Bot Score</th>
              <th className="px-3 py-2">Entry Mcap</th>
              <th className="px-3 py-2">Amount</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-gray-500">
                  No wallets match this filter
                </td>
              </tr>
            ) : (
              filtered.map((buyer) => (
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
                    <Badge variant={(buyer.bot_score ?? 0) > 60 ? 'danger' : 'success'}>
                      {buyer.bot_score ?? '—'}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-gray-300">
                    {buyer.market_cap_usd != null
                      ? formatUsd(buyer.market_cap_usd)
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-gray-300">
                    {buyer.amount_usd != null ? formatUsd(buyer.amount_usd) : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
