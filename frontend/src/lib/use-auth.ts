'use client';

import { useEffect, useState } from 'react';
import { getStoredJwt } from '@/lib/wallet-auth';

export function useIsAuthenticated(): boolean {
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(!!getStoredJwt());
  }, []);

  return authed;
}
