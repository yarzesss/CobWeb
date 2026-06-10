import type { DevRisk } from '@/lib/types';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { DevRiskBadge } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/shared/ScoreBar';
import { AddressLink } from '@/components/shared/AddressLink';
import { getSolscanWalletUrl } from '@/lib/utils';

export function DevRiskCard({ devRisk }: { devRisk: DevRisk }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Dev Risk Analysis</CardTitle>
        <DevRiskBadge level={devRisk.level} />
      </CardHeader>

      <ScoreBar score={devRisk.score} label="Risk Score" className="mb-4" />

      <dl className="grid grid-cols-2 gap-3 font-mono text-xs">
        <div className="border-2 border-cobweb-border bg-cobweb-bg p-2">
          <dt className="text-gray-500 mb-1">Previous Tokens</dt>
          <dd className="text-lg font-bold text-gray-100">
            {devRisk.dev_prev_tokens ?? 0}
          </dd>
        </div>
        <div className="border-2 border-cobweb-border bg-cobweb-bg p-2">
          <dt className="text-gray-500 mb-1">Quick Sell Signal</dt>
          <dd className={devRisk.quick_sell_signal ? 'text-cobweb-red font-bold' : 'text-cobweb-mint'}>
            {devRisk.quick_sell_signal ? 'DETECTED' : 'None'}
          </dd>
        </div>
      </dl>

      {devRisk.dev_wallet && (
        <div className="mt-4 border-t-2 border-cobweb-border pt-3">
          <p className="font-pixel text-[8px] uppercase text-gray-500 mb-2">Deployer Wallet</p>
          <AddressLink
            address={devRisk.dev_wallet}
            href={`/wallet/${devRisk.dev_wallet}`}
            externalHref={getSolscanWalletUrl(devRisk.dev_wallet)}
          />
        </div>
      )}
    </Card>
  );
}
