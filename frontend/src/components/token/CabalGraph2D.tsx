'use client';

import type { ForceGraphMethods } from 'react-force-graph-2d';
import dynamic from 'next/dynamic';
import { useCallback, useMemo, useRef, useState } from 'react';
import type { CabalData } from '@/lib/types';
import { cabalToGraph } from '@/lib/api';
import { GraphLegend, NodeDetailPanel, type SelectedNode } from './NodeDetailPanel';
import { LoadingSpinner } from '@/components/ui/Loading';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => <LoadingSpinner label="Loading network..." />,
});

const NODE_COLORS: Record<string, string> = {
  funder: '#ef4444',
  member: '#C2185B',
  independent: '#4ade80',
};

export function CabalGraph2D({ cabal }: { cabal: CabalData }) {
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [selected, setSelected] = useState<SelectedNode | null>(null);

  const graphData = useMemo(() => cabalToGraph(cabal), [cabal]);

  const drawNode = useCallback(
    (node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as { x?: number; y?: number; id?: string; group?: string; suspicionScore?: number };
      if (n.x == null || n.y == null) return;

      const size = n.group === 'funder' ? 14 : 10;
      const color = NODE_COLORS[n.group ?? 'member'] ?? NODE_COLORS.member;

      // Pixel-style square node
      ctx.fillStyle = color;
      ctx.fillRect(n.x - size / 2, n.y - size / 2, size, size);

      // Inner highlight
      ctx.fillStyle = 'rgba(255,255,255,0.25)';
      ctx.fillRect(n.x - size / 2 + 2, n.y - size / 2 + 2, size / 3, size / 3);

      // Border
      ctx.strokeStyle = '#0d0d18';
      ctx.lineWidth = 2 / globalScale;
      ctx.strokeRect(n.x - size / 2, n.y - size / 2, size, size);

      // Label at sufficient zoom
      if (globalScale > 1.2 && n.id) {
        ctx.font = `${10 / globalScale}px monospace`;
        ctx.fillStyle = '#e5e7eb';
        ctx.textAlign = 'center';
        ctx.fillText(n.id.slice(0, 4) + '…', n.x, n.y + size + 8 / globalScale);
      }
    },
    [],
  );

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
      <div className="flex h-[400px] items-center justify-center border-2 border-dashed border-cobweb-border bg-cobweb-bg">
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
          onClick={() => graphRef.current?.zoomToFit?.(400, 60)}
        >
          Fit View
        </button>
      </div>

      <div className="relative h-[440px] overflow-hidden border-2 border-cobweb-border bg-[#080812] scanlines">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          backgroundColor="#080812"
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            const n = node as { x?: number; y?: number; group?: string };
            if (n.x == null || n.y == null) return;
            const size = n.group === 'funder' ? 20 : 16;
            ctx.fillStyle = color;
            ctx.fillRect(n.x - size / 2, n.y - size / 2, size, size);
          }}
          linkColor={(link) => {
            const l = link as { type?: string };
            return l.type === 'funding' ? '#fbbf24' : '#22d3ee';
          }}
          linkWidth={(link) => {
            const l = link as { type?: string };
            return l.type === 'funding' ? 2.5 : 1.5;
          }}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          enableNodeDrag
          cooldownTicks={100}
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
        Pixel node map — drag to rearrange, click to interact.
      </p>
    </div>
  );
}
