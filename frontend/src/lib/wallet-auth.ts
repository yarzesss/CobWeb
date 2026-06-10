'use client';

import bs58 from 'bs58';
import { api } from './api';

const JWT_KEY = 'cobweb_jwt';

export function getStoredJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(JWT_KEY);
}

export function setStoredJwt(token: string): void {
  localStorage.setItem(JWT_KEY, token);
}

export function clearStoredJwt(): void {
  localStorage.removeItem(JWT_KEY);
}

export async function signInWithWallet(
  publicKey: string,
  signMessage: (message: Uint8Array) => Promise<Uint8Array>,
): Promise<string> {
  const { nonce } = await api.getNonce(publicKey);
  const message = new TextEncoder().encode(`Sign in to Cobweb: ${nonce}`);
  const signatureBytes = await signMessage(message);
  const signature = bs58.encode(signatureBytes);

  const { access_token } = await api.verifyAuth({
    wallet: publicKey,
    signature,
    nonce,
  });

  setStoredJwt(access_token);
  return access_token;
}
