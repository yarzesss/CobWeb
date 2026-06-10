'use client';

import { cn, copyToClipboard, truncateAddress } from '@/lib/utils';
import { Copy, Check, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export function AddressLink({
  address,
  href,
  externalHref,
  showCopy = true,
  className,
}: {
  address: string;
  href?: string;
  externalHref?: string;
  showCopy?: boolean;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await copyToClipboard(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const content = (
    <span className={cn('font-mono text-sm text-cobweb-cyan hover:text-cobweb-pink-light', className)}>
      {truncateAddress(address, 6)}
    </span>
  );

  return (
    <span className="inline-flex items-center gap-1.5">
      {href ? (
        <Link href={href} className="hover:underline">
          {content}
        </Link>
      ) : (
        content
      )}
      {showCopy && (
        <button
          type="button"
          onClick={handleCopy}
          className="p-1 text-gray-400 hover:text-cobweb-pink-light transition-colors"
          title="Copy address"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-cobweb-mint" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      )}
      {externalHref && (
        <a
          href={externalHref}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 text-gray-400 hover:text-cobweb-pink-light"
          title="View on Solscan"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}
    </span>
  );
}
