'use client';

import type { TradeRecord } from '@/lib/types';

export function TradeHistory({ trades }: { trades: TradeRecord[] }) {
  if (trades.length === 0) {
    return (
      <p className="py-8 text-center font-mono text-sm text-gray-500">
        No trades found
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border-2 border-cobweb-border">
      <table className="w-full min-w-[600px] font-mono text-xs">
        <thead>
          <tr className="border-b-2 border-cobweb-border bg-cobweb-surface2 font-pixel text-[8px] uppercase text-gray-400">
            <th className="px-3 py-2 text-left">Time</th>
            <th className="px-3 py-2 text-left">Type</th>
            <th className="px-3 py-2 text-left">Source</th>
            <th className="px-3 py-2 text-left">Signature</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, i) => (
            <tr
              key={trade.signature ?? i}
              className="border-b border-cobweb-border/50 hover:bg-cobweb-surface2/40"
            >
              <td className="px-3 py-2 text-gray-400">
                {trade.timestamp
                  ? new Date(trade.timestamp * 1000).toLocaleString()
                  : '—'}
              </td>
              <td className="px-3 py-2 text-gray-200">
                {trade.type ?? trade.description?.slice(0, 30) ?? '—'}
              </td>
              <td className="px-3 py-2 text-cobweb-cyan">
                {(trade.source ?? '—').slice(0, 24)}
              </td>
              <td className="px-3 py-2">
                {trade.signature ? (
                  <a
                    href={`https://solscan.io/tx/${trade.signature}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cobweb-pink-light hover:underline"
                  >
                    {trade.signature.slice(0, 8)}…
                  </a>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
