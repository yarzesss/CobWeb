'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { WalletConnectButton } from './WalletConnectButton';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/', label: 'Analyze' },
  { href: '/watchlist', label: 'Watchlist' },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b-2 border-cobweb-border bg-cobweb-bg/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="group flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center border-2 border-cobweb-pink bg-cobweb-surface shadow-pixel-sm">
            <svg viewBox="0 0 16 16" className="h-6 w-6" fill="none">
              <circle cx="8" cy="8" r="2" fill="#C2185B" />
              <line x1="8" y1="2" x2="8" y2="6" stroke="#C2185B" strokeWidth="1" />
              <line x1="8" y1="10" x2="8" y2="14" stroke="#C2185B" strokeWidth="1" />
              <line x1="2" y1="8" x2="6" y2="8" stroke="#C2185B" strokeWidth="1" />
              <line x1="10" y1="8" x2="14" y2="8" stroke="#C2185B" strokeWidth="1" />
              <line x1="4" y1="4" x2="6" y2="6" stroke="#880E4F" strokeWidth="1" />
              <line x1="10" y1="10" x2="12" y2="12" stroke="#880E4F" strokeWidth="1" />
              <line x1="12" y1="4" x2="10" y2="6" stroke="#880E4F" strokeWidth="1" />
              <line x1="6" y1="10" x2="4" y2="12" stroke="#880E4F" strokeWidth="1" />
            </svg>
          </div>
          <div>
            <span className="font-pixel text-sm text-cobweb-pink-light group-hover:text-white transition-colors">
              COBWEB
            </span>
            <p className="font-mono text-[10px] text-gray-500 hidden sm:block">
              on-chain intelligence
            </p>
          </div>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'px-3 py-2 font-pixel text-[9px] uppercase tracking-wider transition-colors',
                pathname === item.href
                  ? 'text-cobweb-pink-light'
                  : 'text-gray-400 hover:text-gray-200',
              )}
            >
              {item.label}
            </Link>
          ))}
          <WalletConnectButton />
        </nav>
      </div>
    </header>
  );
}
