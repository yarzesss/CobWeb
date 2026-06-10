'use client';

import type { ForceGraphMethods } from 'react-force-graph-3d';
import dynamic from 'next/dynamic';
import { useCallback, useMemo, useRef, useState } from 'react';
import type { CabalData } from '@/lib/types';
import { cabalToGraph } from '@/lib/api';
import { GraphLegend, NodeDetailPanel, type SelectedNode } from './NodeDetailPanel';
import { LoadingSpinner } from '@/components/ui/Loading';

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => <LoadingSpinner label="Loading 3D web..." />,
});

const NODE_COLORS: Record<string, string> = {
  funder: '#ef4444',
  member: '#C2185B',
  independent: '#4ade80',
};

const LINK_COLORS: Record<string, string> = {
  funding: '#fbbf24',
  direct_transfer: '#22d3ee',
};

export function CabalGraph3D({ cabal }: { cabal: CabalData }) {
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [selected, setSelected] = useState<SelectedNode | null>(null);

  const graphData = useMemo(() => cabalToGraph(cabal), [cabal]);

  const handleNodeClick = useCallback(
    (node: { id?: string | number; group?: string; suspicionScore?: number }) => {
      if (!node.id) return;
      setSelected({
        id: String(node.id),
        group: (node.group as SelectedNode['group']) ?? 'member',
        suspicionScore: node.suspicionScore,
      });
    },
    [],
  );

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex h-[480px] items-center justify-center border-2 border-dashed border-cobweb-border bg-cobweb-bg">
        <p className="font-pixel text-[10px] uppercase text-gray-500">
          No wallet nodes to display
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="mb-3 flex items-center justify-between gap-4">
        <GraphLegend />
        <button
          type="button"
          className="pixel-btn-ghost text-[8px] py-1"
          onClick={() => graphRef.current?.zoomToFit?.(400, 80)}
        >
          Reset View
        </button>
      </div>

      <div className="relative h-[520px] overflow-hidden border-2 border-cobweb-border bg-[#080812] scanlines">
        <ForceGraph3D
          ref={graphRef}
          graphData={graphData}
          backgroundColor="#080812"
          nodeLabel={(node) => {
            const n = node as { id?: string; group?: string };
            return `${n.id?.slice(0, 8)}… (${n.group})`;
          }}
          nodeColor={(node) => {
            const n = node as { group?: string };
            return NODE_COLORS[n.group ?? 'member'] ?? NODE_COLORS.member;
          }}
          nodeVal={(node) => {
            const n = node as { group?: string };
            return n.group === 'funder' ? 8 : 4;
          }}
          nodeOpacity={0.95}
          linkColor={(link) => {
            const l = link as { type?: string };
            return LINK_COLORS[l.type ?? ''] ?? '#666';
          }}
          linkWidth={(link) => {
            const l = link as { type?: string };
            return l.type === 'funding' ? 2 : 1;
          }}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={() => '#C2185B'}
          onNodeClick={handleNodeClick}
          enableNodeDrag
        />

        {selected && (
          <NodeDetailPanel
            node={selected}
            links={graphData.links}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      <p className="mt-2 font-mono text-[10px] text-gray-500">
        Click any sphere to copy wallet, view profile, or inspect connections.
      </p>
    </div>
  );
}
