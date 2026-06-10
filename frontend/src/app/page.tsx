'use client';

import { useRouter } from 'next/navigation';
import { useState, FormEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Search, Zap, Network, Shield } from 'lucide-react';

const DEMO_CAS = [
  'So11111111111111111111111111111111111111112',
  'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
];

export default function HomePage() {
  const router = useRouter();
  const [ca, setCa] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = ca.trim();
    if (trimmed.length >= 32) {
      router.push(`/token/${trimmed}`);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      {/* Hero */}
      <section className="text-center mb-16">
        <div className="mb-6 inline-block border-2 border-cobweb-pink bg-cobweb-surface px-4 py-2 shadow-pixel">
          <span className="font-pixel text-[10px] uppercase text-cobweb-pink-light">
            Solana Analytics
          </span>
        </div>

        <h1 className="font-pixel text-2xl sm:text-3xl leading-relaxed text-white mb-4">
          Who bought early —
          <br />
          <span className="text-cobweb-pink-light">insiders or Smart Money?</span>
        </h1>

        <p className="font-mono text-sm text-gray-400 max-w-xl mx-auto mb-10">
          Paste a token contract address. Cobweb finds early buyers, detects coordinated
          wallet clusters, and scores dev risk — all from on-chain data.
        </p>

        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl">
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              value={ca}
              onChange={(e) => setCa(e.target.value)}
              placeholder="Paste token contract address (CA)..."
              className="flex-1 text-base"
              spellCheck={false}
            />
            <Button type="submit" className="shrink-0 py-3">
              <Search className="h-4 w-4" />
              Analyze
            </Button>
          </div>
        </form>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <span className="font-mono text-[10px] text-gray-600">Try:</span>
          {DEMO_CAS.map((demo) => (
            <button
              key={demo}
              type="button"
              onClick={() => setCa(demo)}
              className="font-mono text-[10px] text-cobweb-cyan hover:text-cobweb-pink-light hover:underline"
            >
              {demo.slice(0, 6)}…{demo.slice(-4)}
            </button>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="grid gap-6 sm:grid-cols-3 mb-16">
        {[
          {
            icon: Network,
            title: 'Cabal Detector',
            desc: '3D web graph of wallet connections — funders, transfers, co-trading patterns.',
          },
          {
            icon: Zap,
            title: 'Smart Money',
            desc: 'Archetype classification filters bots and surfaces real alpha wallets.',
          },
          {
            icon: Shield,
            title: 'Dev Risk Score',
            desc: 'Analyze deployer history — rugs, quick sells, serial token launches.',
          },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="pixel-card p-5 hover:border-cobweb-pink/50 transition-colors">
            <Icon className="h-6 w-6 text-cobweb-pink mb-3" />
            <h3 className="font-pixel text-[9px] uppercase text-cobweb-pink-light mb-2">
              {title}
            </h3>
            <p className="font-mono text-xs text-gray-400 leading-relaxed">{desc}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className="pixel-card p-8">
        <h2 className="font-pixel text-xs uppercase text-center text-gray-300 mb-8">
          How It Works
        </h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {[
            { step: '01', text: 'Enter token CA' },
            { step: '02', text: 'Find early buyers (<$10k mcap)' },
            { step: '03', text: 'Cluster or Smart Money?' },
          ].map(({ step, text }) => (
            <div key={step} className="text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center border-2 border-cobweb-pink bg-cobweb-bg font-pixel text-sm text-cobweb-pink-light">
                {step}
              </div>
              <p className="font-mono text-sm text-gray-300">{text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
