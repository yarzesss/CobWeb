'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { TokenDashboard } from '@/components/token/TokenDashboard';
import { LoadingSpinner } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';

export default function TokenPage() {
  const params = useParams();
  const ca = params.ca as string;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['token', ca],
    queryFn: () => api.getToken(ca),
    enabled: !!ca,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6">
        <Link href="/" className="font-pixel text-[8px] uppercase text-gray-500 hover:text-cobweb-pink-light">
          ← Back to search
        </Link>
      </div>

      {isLoading && <LoadingSpinner label="Analyzing token on-chain..." />}

      {error && (
        <div className="pixel-card p-8 text-center">
          <p className="font-pixel text-[10px] uppercase text-cobweb-red mb-4">
            Analysis Failed
          </p>
          <p className="font-mono text-sm text-gray-400 mb-6">
            {error instanceof Error ? error.message : 'Could not fetch token data. Is the backend running?'}
          </p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => refetch()}>Retry</Button>
            <Link href="/">
              <Button variant="ghost">Go Home</Button>
            </Link>
          </div>
        </div>
      )}

      {data && <TokenDashboard data={data} />}
    </div>
  );
}
