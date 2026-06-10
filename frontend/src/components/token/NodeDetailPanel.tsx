'use client';

import { useState } from 'react';
import type { GraphLink, GraphNode } from '@/lib/types';
import { copyToClipboard, truncateAddress } from '@/lib/utils';
import { AddressLink } from '@/components/shared/AddressLink';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Copy, Check, X, ExternalLink } from 'lucide-react';
import Link from 'next/link';

export interface SelectedNode {
  id: string;
  group: GraphNode['group'];
  suspicionScore?: number;
}

export function NodeDetailPanel({
  node,
  links,
  onClose,
}: {
  node: SelectedNode;
  links: GraphLink[];
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const connected = links.filter(
    (l) => l.source === node.id || l.target === node.id,
  );

  const handleCopy = async () => {
    await copyToClipboard(node.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const groupLabel = {
    funder: 'Common Funder',
    member: 'Cluster Member',
    independent: 'Independent',
  }[node.group];

  return (
    <div className="pixel-card absolute right-4 top-4 z-20 w-80 max-w-[calc(100%-2rem)]">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="font-pixel text-[9px] uppercase text-cobweb-pink-light mb-1">
            Wallet Node
          </p>
          <p className="font-mono text-xs text-gray-300 break-all">{node.id}</p>
        </div>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-white p-1">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <Badge variant={node.group === 'funder' ? 'danger' : node.group === 'independent' ? 'success' : 'pink'}>
          {groupLabel}
        </Badge>
        {node.suspicionScore != null && (
          <Badge variant="danger">Suspicion {node.suspicionScore}</Badge>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <Button size="sm" onClick={handleCopy}>
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          Copy
        </Button>
        <Link href={`/wallet/${node.id}`}>
          <Button size="sm" variant="ghost">View Profile</Button>
        </Link>
        <a
          href={`https://solscan.io/account/${node.id}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button size="sm" variant="ghost">
            <ExternalLink className="h-3 w-3" /> Solscan
          </Button>
        </a>
      </div>

      {connected.length > 0 && (
        <div>
          <p className="font-pixel text-[8px] uppercase text-gray-500 mb-2">
            Connections ({connected.length})
          </p>
          <ul className="space-y-2 max-h-40 overflow-y-auto">
            {connected.map((link, i) => {
              const other = link.source === node.id ? link.target : link.source;
              const direction = link.source === node.id ? '→' : '←';
              return (
                <li
                  key={`${link.source}-${link.target}-${i}`}
                  className="border-2 border-cobweb-border bg-cobweb-bg px-2 py-1.5 font-mono text-[10px]"
                >
                  <span className="text-gray-500">{direction}</span>{' '}
                  <Link href={`/wallet/${other}`} className="text-cobweb-cyan hover:underline">
                    {truncateAddress(other, 4)}
                  </Link>
                  <span className="ml-2 text-cobweb-amber">{link.type.replace('_', ' ')}</span>
                  {link.amount_sol != null && (
                    <span className="ml-1 text-gray-400">{link.amount_sol.toFixed(2)} SOL</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

export function GraphLegend() {
  return (
    <div className="flex flex-wrap gap-3 font-pixel text-[8px] uppercase text-gray-400">
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 bg-cobweb-red border border-cobweb-red" /> Funder
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 bg-cobweb-pink border border-cobweb-pink" /> Cluster
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 bg-cobweb-mint border border-cobweb-mint" /> Independent
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-4 bg-cobweb-amber" /> Funding
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-4 bg-cobweb-cyan border-dashed" /> Transfer
      </span>
    </div>
  );
}
