import type { WalletPnl } from '@/lib/types';
import { Card, CardTitle } from '@/components/ui/Card';
import { formatUsd } from '@/lib/utils';

export function PnLBreakdown({ pnl }: { pnl: WalletPnl }) {
  const summary = pnl.summary;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="border-2 border-cobweb-border bg-cobweb-bg p-3">
          <p className="font-pixel text-[7px] uppercase text-gray-500">Realized</p>
          <p className={`font-mono text-lg font-bold ${summary.total_realized_usd >= 0 ? 'text-cobweb-mint' : 'text-cobweb-red'}`}>
            {formatUsd(summary.total_realized_usd)}
          </p>
        </div>
        {summary.total_unrealized_usd != null && (
          <div className="border-2 border-cobweb-border bg-cobweb-bg p-3">
            <p className="font-pixel text-[7px] uppercase text-gray-500">Unrealized</p>
            <p className="font-mono text-lg font-bold text-gray-200">
              {formatUsd(summary.total_unrealized_usd)}
            </p>
          </div>
        )}
        <div className="border-2 border-cobweb-border bg-cobweb-bg p-3">
          <p className="font-pixel text-[7px] uppercase text-gray-500">Win Rate</p>
          <p className="font-mono text-lg font-bold text-gray-200">
            {(summary.winrate * 100).toFixed(1)}%
          </p>
        </div>
        <div className="border-2 border-cobweb-border bg-cobweb-bg p-3">
          <p className="font-pixel text-[7px] uppercase text-gray-500">Trades</p>
          <p className="font-mono text-lg font-bold text-gray-200">{summary.total_trades}</p>
        </div>
      </div>

      {pnl.by_token && pnl.by_token.length > 0 && (
        <Card>
          <CardTitle className="mb-3">By Token</CardTitle>
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-xs">
              <thead>
                <tr className="border-b border-cobweb-border text-gray-500">
                  <th className="py-2 text-left">Token</th>
                  <th className="py-2 text-right">PnL</th>
                  <th className="py-2 text-right">Trades</th>
                </tr>
              </thead>
              <tbody>
                {pnl.by_token.map((t) => (
                  <tr key={t.mint} className="border-b border-cobweb-border/30">
                    <td className="py-2 text-cobweb-cyan">{t.symbol ?? t.mint.slice(0, 8) + '…'}</td>
                    <td className={`py-2 text-right ${t.realized_usd >= 0 ? 'text-cobweb-mint' : 'text-cobweb-red'}`}>
                      {formatUsd(t.realized_usd)}
                    </td>
                    <td className="py-2 text-right text-gray-400">{t.trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
