'use client';

import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { useCallback, useEffect, useState } from 'react';
import { signInWithWallet, getStoredJwt, clearStoredJwt } from '@/lib/wallet-auth';
import { Badge } from '@/components/ui/Badge';

export function WalletConnectButton() {
  const { publicKey, signMessage, connected, disconnect } = useWallet();
  const [authenticated, setAuthenticated] = useState(false);
  const [signing, setSigning] = useState(false);

  useEffect(() => {
    setAuthenticated(!!getStoredJwt());
  }, []);

  const handleSignIn = useCallback(async () => {
    if (!publicKey || !signMessage) return;
    setSigning(true);
    try {
      await signInWithWallet(publicKey.toBase58(), signMessage);
      setAuthenticated(true);
    } catch (err) {
      console.error('Sign in failed:', err);
    } finally {
      setSigning(false);
    }
  }, [publicKey, signMessage]);

  const handleDisconnect = useCallback(async () => {
    clearStoredJwt();
    setAuthenticated(false);
    await disconnect();
  }, [disconnect]);

  if (connected && publicKey && authenticated) {
    return (
      <div className="flex items-center gap-2 ml-2">
        <Badge variant="success">Connected</Badge>
        <button type="button" onClick={handleDisconnect} className="pixel-btn-ghost text-[8px] py-1.5">
          Disconnect
        </button>
      </div>
    );
  }

  if (connected && publicKey && !authenticated) {
    return (
      <button
        type="button"
        onClick={handleSignIn}
        disabled={signing}
        className="pixel-btn ml-2 text-[8px] py-1.5"
      >
        {signing ? 'Signing...' : 'Sign In'}
      </button>
    );
  }

  return (
    <div className="ml-2">
      <WalletMultiButton />
    </div>
  );
}
