'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMemo, useState, type ComponentType, type ReactNode } from 'react';
import {
  ConnectionProvider,
  WalletProvider,
} from '@solana/wallet-adapter-react';
import { WalletModalProvider } from '@solana/wallet-adapter-react-ui';
import { PhantomWalletAdapter } from '@solana/wallet-adapter-phantom';
import { SolflareWalletAdapter } from '@solana/wallet-adapter-solflare';
import type { WalletAdapter } from '@solana/wallet-adapter-base';
import { clusterApiUrl } from '@solana/web3.js';
import '@solana/wallet-adapter-react-ui/styles.css';

type ProviderProps = { children: ReactNode };

const SolanaConnectionProvider = ConnectionProvider as ComponentType<
  ProviderProps & { endpoint: string }
>;
const SolanaWalletProvider = WalletProvider as ComponentType<
  ProviderProps & { wallets: WalletAdapter[]; autoConnect?: boolean }
>;

function useWalletAdapters() {
  return useMemo(
    () => [new PhantomWalletAdapter(), new SolflareWalletAdapter()],
    [],
  );
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  const endpoint = useMemo(
    () =>
      process.env.NEXT_PUBLIC_SOLANA_RPC ??
      clusterApiUrl('mainnet-beta'),
    [],
  );

  const wallets = useWalletAdapters();

  return (
    <QueryClientProvider client={queryClient}>
      <SolanaConnectionProvider endpoint={endpoint}>
        <SolanaWalletProvider wallets={wallets} autoConnect>
          <WalletModalProvider>{children}</WalletModalProvider>
        </SolanaWalletProvider>
      </SolanaConnectionProvider>
    </QueryClientProvider>
  );
}
