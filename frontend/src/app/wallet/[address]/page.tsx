'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { useState } from 'react';
import { api } from '@/lib/api';
import { useIsAuthenticated } from '@/lib/use-auth';
import { WalletHeader, WalletStats } from '@/components/wallet/WalletStats';
import { TradeHistory } from '@/components/wallet/TradeHistory';
import { PnLBreakdown } from '@/components/wallet/PnLBreakdown';
import { LoadingSpinner } from '@/components/ui/Loading';
import { Tabs } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import Link from 'next/link';
import { Star } from 'lucide-react';

export default function WalletPage() {
  const params = useParams();
  const address = params.address as string;
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('overview');
  const isAuthed = useIsAuthenticated();

  const profileQuery = useQuery({
    queryKey: ['wallet', address],
    queryFn: () => api.getWallet(address),
    enabled: !!address,
  });

  const tradesQuery = useQuery({
    queryKey: ['wallet', address, 'trades'],
    queryFn: () => api.getWalletTrades(address, 50),
    enabled: !!address && tab === 'trades',
  });

  const pnlQuery = useQuery({
    queryKey: ['wallet', address, 'pnl'],
    queryFn: () => api.getWalletPnl(address),
    enabled: !!address && tab === 'pnl',
  });

  const watchlistMutation = useMutation({
    mutationFn: () => api.addToWatchlist(address),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'trades', label: 'Trades' },
    { id: 'pnl', label: 'PnL' },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Link href="/" className="font-pixel text-[8px] uppercase text-gray-500 hover:text-cobweb-pink-light">
          ← Back
        </Link>
        {isAuthed && profileQuery.data && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => watchlistMutation.mutate()}
            disabled={watchlistMutation.isPending}
          >
            <Star className="h-3 w-3" />
            {watchlistMutation.isSuccess ? 'Added!' : 'Add to Watchlist'}
          </Button>
        )}
      </div>

      {profileQuery.isLoading && <LoadingSpinner label="Profiling wallet..." />}

      {profileQuery.error && (
        <Card className="p-8 text-center">
          <p className="font-pixel text-[10px] uppercase text-cobweb-red mb-4">Error</p>
          <p className="font-mono text-sm text-gray-400">
            {profileQuery.error instanceof Error
              ? profileQuery.error.message
              : 'Failed to load wallet'}
          </p>
        </Card>
      )}

      {profileQuery.data && (
        <div className="space-y-6">
          <WalletHeader profile={profileQuery.data} />
          <Tabs tabs={tabs} active={tab} onChange={setTab} />

          {tab === 'overview' && <WalletStats profile={profileQuery.data} />}

          {tab === 'trades' && (
            <Card>
              {tradesQuery.isLoading ? (
                <LoadingSpinner label="Loading trades..." />
              ) : (
                <TradeHistory trades={tradesQuery.data?.trades ?? []} />
              )}
            </Card>
          )}

          {tab === 'pnl' && (
            <Card>
              {pnlQuery.isLoading ? (
                <LoadingSpinner label="Calculating PnL..." />
              ) : pnlQuery.data ? (
                <PnLBreakdown pnl={pnlQuery.data} />
              ) : (
                <p className="py-8 text-center font-mono text-sm text-gray-500">
                  No PnL data available
                </p>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
