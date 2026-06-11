import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncateAddress(address: string, chars = 4): string {
  if (address.length <= chars * 2 + 3) return address;
  return `${address.slice(0, chars)}...${address.slice(-chars)}`;
}

export function formatUsd(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : value > 0 ? '+' : '';
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(2)}`;
}

export function formatPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export function formatTokenAmount(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

export function formatScore(score: number): string {
  return `${Math.round(score)}`;
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function getSolscanWalletUrl(address: string): string {
  return `https://solscan.io/account/${address}`;
}

export function getSolscanTokenUrl(ca: string): string {
  return `https://solscan.io/token/${ca}`;
}

export function scoreColor(score: number, invert = false): string {
  const s = invert ? 100 - score : score;
  if (s >= 70) return 'text-cobweb-red';
  if (s >= 40) return 'text-cobweb-amber';
  return 'text-cobweb-mint';
}

export function scoreBgColor(score: number, invert = false): string {
  const s = invert ? 100 - score : score;
  if (s >= 70) return 'bg-cobweb-red/20 border-cobweb-red/50';
  if (s >= 40) return 'bg-cobweb-amber/20 border-cobweb-amber/50';
  return 'bg-cobweb-mint/20 border-cobweb-mint/50';
}
