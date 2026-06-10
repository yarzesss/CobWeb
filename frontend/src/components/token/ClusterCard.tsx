import type { CabalCluster } from '@/lib/types';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/shared/ScoreBar';
import { AddressLink } from '@/components/shared/AddressLink';
import { getSolscanWalletUrl } from '@/lib/utils';

export function ClusterCard({ cluster, index }: { cluster: CabalCluster; index: number }) {
  return (
    <Card className="border-cobweb-pink/30">
      <CardHeader>
        <CardTitle>Cluster #{index + 1}</CardTitle>
        <Badge variant="danger">Suspicion {cluster.suspicion_score}</Badge>
      </CardHeader>

      <ScoreBar score={cluster.suspicion_score} label="Suspicion Score" className="mb-4" />

      {cluster.common_funder && (
        <div className="mb-4 border-2 border-cobweb-amber/30 bg-cobweb-amber/5 p-3">
          <p className="font-pixel text-[8px] uppercase text-cobweb-amber mb-2">
            Common Funder
          </p>
          <AddressLink
            address={cluster.common_funder}
            href={`/wallet/${cluster.common_funder}`}
            externalHref={getSolscanWalletUrl(cluster.common_funder)}
          />
        </div>
      )}

      <div className="mb-3">
        <p className="font-pixel text-[8px] uppercase text-gray-500 mb-2">
          Wallets ({cluster.wallets.length})
        </p>
        <div className="flex flex-wrap gap-2">
          {cluster.wallets.map((w) => (
            <AddressLink
              key={w}
              address={w}
              href={`/wallet/${w}`}
              externalHref={getSolscanWalletUrl(w)}
            />
          ))}
        </div>
      </div>

      {cluster.connections.length > 0 && (
        <div>
          <p className="font-pixel text-[8px] uppercase text-gray-500 mb-2">
            Connections
          </p>
          <ul className="space-y-1 max-h-32 overflow-y-auto font-mono text-[10px] text-gray-400">
            {cluster.connections.map((c, i) => (
              <li key={i} className="border-l-2 border-cobweb-pink pl-2">
                {c.type.replace('_', ' ')}: {c.from.slice(0, 4)}… → {c.to.slice(0, 4)}…
                {c.amount_sol != null && ` (${c.amount_sol.toFixed(2)} SOL)`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
