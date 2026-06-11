import { cn } from '@/lib/utils';
import type { Archetype, DevRiskLevel } from '@/lib/types';

const ARCHETYPE_STYLES: Record<Archetype, string> = {
  sniper: 'bg-cobweb-amber/20 text-cobweb-amber border-cobweb-amber/50',
  insider: 'bg-cobweb-red/20 text-cobweb-red border-cobweb-red/50',
  swing: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  swing_trader: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  accumulator: 'bg-cobweb-mint/20 text-cobweb-mint border-cobweb-mint/50',
  flipper: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  bot: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
  unknown: 'bg-gray-600/20 text-gray-300 border-gray-600/50',
};

export function Badge({
  children,
  className,
  variant = 'default',
}: {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'pink' | 'danger' | 'success';
}) {
  const variants = {
    default: 'bg-cobweb-surface2 text-gray-200 border-cobweb-border',
    pink: 'bg-cobweb-pink/20 text-cobweb-pink-light border-cobweb-pink/50',
    danger: 'bg-cobweb-red/20 text-cobweb-red border-cobweb-red/50',
    success: 'bg-cobweb-mint/20 text-cobweb-mint border-cobweb-mint/50',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center border-2 px-2 py-0.5 font-pixel text-[8px] uppercase tracking-wider',
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ArchetypeBadge({ archetype }: { archetype: Archetype }) {
  return (
    <span
      className={cn(
        'inline-flex items-center border-2 px-2 py-0.5 font-pixel text-[8px] uppercase',
        ARCHETYPE_STYLES[archetype] ?? ARCHETYPE_STYLES.unknown,
      )}
    >
      {archetype.replace('_', ' ')}
    </span>
  );
}

export function DevRiskBadge({ level }: { level: DevRiskLevel }) {
  const styles: Record<DevRiskLevel, 'danger' | 'default' | 'success'> = {
    HIGH: 'danger',
    MEDIUM: 'default',
    LOW: 'success',
  };
  return <Badge variant={styles[level]}>{level} RISK</Badge>;
}
