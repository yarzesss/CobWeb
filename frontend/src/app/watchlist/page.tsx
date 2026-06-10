'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useIsAuthenticated } from '@/lib/use-auth';
import { LoadingSpinner } from '@/components/ui/Loading';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { AddressLink } from '@/components/shared/AddressLink';
import { getSolscanWalletUrl } from '@/lib/utils';
import { Trash2, Wallet } from 'lucide-react';
import { WalletConnectButton } from '@/components/layout/WalletConnectButton';

export default function WatchlistPage() {
  const queryClient = useQueryClient();
  const isAuthed = useIsAuthenticated();

  const { data, isLoading, error } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => api.getWatchlist(),
    enabled: isAuthed,
  });

  const removeMutation = useMutation({
    mutationFn: (address: string) => api.removeFromWatchlist(address),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  if (!isAuthed) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <Wallet className="mx-auto h-12 w-12 text-cobweb-pink mb-6" />
        <h1 className="font-pixel text-sm text-white mb-4">Watchlist</h1>
        <p className="font-mono text-sm text-gray-400 mb-8">
          Connect your wallet and sign in to save wallets you want to track.
        </p>
        <WalletConnectButton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="font-pixel text-sm text-cobweb-pink-light mb-2">Watchlist</h1>
      <p className="font-mono text-xs text-gray-500 mb-8">
        Your saved Smart Money wallets
      </p>

      {isLoading && <LoadingSpinner label="Loading watchlist..." />}

      {error && (
        <Card className="p-8 text-center">
          <p className="font-mono text-sm text-cobweb-red">
            {error instanceof Error ? error.message : 'Failed to load watchlist'}
          </p>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card className="p-12 text-center">
          <p className="font-pixel text-[10px] uppercase text-gray-500 mb-4">
            No wallets saved yet
          </p>
          <p className="font-mono text-sm text-gray-400 mb-6">
            Browse token analysis and add wallets from their profile page.
          </p>
          <Link href="/">
            <Button variant="ghost">Analyze a Token</Button>
          </Link>
        </Card>
      )}

      {data && data.length > 0 && (
        <div className="space-y-3">
          {data.map((item) => (
            <Card key={item.wallet_address} className="flex items-center justify-between gap-4">
              <div>
                {item.label && (
                  <p className="font-pixel text-[8px] uppercase text-cobweb-pink mb-1">
                    {item.label}
                  </p>
                )}
                <AddressLink
                  address={item.wallet_address}
                  href={`/wallet/${item.wallet_address}`}
                  externalHref={getSolscanWalletUrl(item.wallet_address)}
                />
                <p className="font-mono text-[10px] text-gray-600 mt-1">
                  Added {new Date(item.added_at).toLocaleDateString()}
                </p>
              </div>
              <Button
                size="sm"
                variant="danger"
                onClick={() => removeMutation.mutate(item.wallet_address)}
                disabled={removeMutation.isPending}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
