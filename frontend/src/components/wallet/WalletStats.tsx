import type { WalletProfile } from '@/lib/types';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { ArchetypeBadge, Badge } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/shared/ScoreBar';
import { formatUsd, formatPercent } from '@/lib/utils';

export function WalletStats({ profile }: { profile: WalletProfile }) {
  const stats = [
    { label: 'Win Rate', value: formatPercent(profile.winrate) },
    { label: 'Total PnL', value: formatUsd(profile.total_pnl_usd), highlight: true },
    { label: 'Total Trades', value: String(profile.total_trades) },
    { label: 'Avg Hold', value: `${Math.round(profile.avg_hold_time_minutes)}m` },
    { label: 'Avg Position', value: formatUsd(profile.avg_position_size_usd) },
    { label: 'Favorite DEX', value: profile.favorite_dex?.slice(0, 20) ?? '—' },
  ];

  return (
    <div className="space-y-4">
      {profile.total_trades === 0 && (
        <div className="border-2 border-cobweb-amber/50 bg-cobweb-amber/10 p-3 font-mono text-xs text-cobweb-amber">
          No swap activity found in the last {''}500 transactions of this wallet.
          Scores below are based on transfer heuristics only.
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {stats.map((s) => (
          <div
            key={s.label}
            className="border-2 border-cobweb-border bg-cobweb-bg p-3 text-center"
          >
            <p className="font-pixel text-[7px] uppercase text-gray-500 mb-1">{s.label}</p>
            <p
              className={`font-mono text-sm font-bold ${
                s.highlight
                  ? profile.total_pnl_usd >= 0
                    ? 'text-cobweb-mint'
                    : 'text-cobweb-red'
                  : 'text-gray-100'
              }`}
            >
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Bot Score</CardTitle>
            <Badge variant={profile.bot_score > 60 ? 'danger' : 'success'}>
              {profile.bot_score > 60 ? 'BOT' : profile.bot_score < 30 ? 'HUMAN' : 'UNKNOWN'}
            </Badge>
          </CardHeader>
          <ScoreBar score={profile.bot_score} label="Bot Likelihood" invert />
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Smart Money Score</CardTitle>
          </CardHeader>
          <ScoreBar score={profile.smart_money_score} label="Smart Money" />
        </Card>
      </div>

      <div className="flex flex-wrap gap-4 font-mono text-xs text-gray-400">
        {profile.first_seen && (
          <span>First seen: {new Date(profile.first_seen).toLocaleDateString()}</span>
        )}
        {profile.last_active && (
          <span>Last active: {new Date(profile.last_active).toLocaleDateString()}</span>
        )}
      </div>
    </div>
  );
}

export function WalletHeader({ profile }: { profile: WalletProfile }) {
  return (
    <div className="pixel-card p-6">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <ArchetypeBadge archetype={profile.archetype} />
        <Badge variant="pink">SM {profile.smart_money_score}</Badge>
        <Badge variant={profile.bot_score > 60 ? 'danger' : 'default'}>
          Bot {profile.bot_score}
        </Badge>
      </div>
      <p className="font-mono text-sm text-gray-300 break-all">{profile.wallet_address}</p>
    </div>
  );
}
