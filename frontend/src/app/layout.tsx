import type { Metadata } from 'next';
import { Press_Start_2P, JetBrains_Mono, Inter } from 'next/font/google';
import { Header } from '@/components/layout/Header';
import { Providers } from '@/providers';
import './globals.css';

const pixel = Press_Start_2P({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-pixel',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

const sans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

export const metadata: Metadata = {
  title: 'Cobweb — Solana On-Chain Intelligence',
  description:
    'Detect coordinated wallet clusters, Smart Money, and dev risk on Solana tokens.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${pixel.variable} ${mono.variable} ${sans.variable}`}>
      <body>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <footer className="border-t-2 border-cobweb-border py-6 text-center">
              <p className="font-pixel text-[8px] uppercase text-gray-600">
                Cobweb — wallets are nodes, connections are threads
              </p>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
