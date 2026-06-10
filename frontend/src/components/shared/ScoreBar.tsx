import { cn, scoreBgColor } from '@/lib/utils';

export function ScoreBar({
  score,
  label,
  invert = false,
  className,
}: {
  score: number;
  label?: string;
  invert?: boolean;
  className?: string;
}) {
  const display = Math.min(100, Math.max(0, score));

  return (
    <div className={cn('space-y-1', className)}>
      {label && (
        <div className="flex justify-between font-mono text-xs text-gray-400">
          <span>{label}</span>
          <span className="font-bold text-gray-200">{Math.round(display)}</span>
        </div>
      )}
      <div className="h-3 border-2 border-cobweb-border bg-cobweb-bg">
        <div
          className={cn('h-full transition-all duration-500', scoreBgColor(display, invert))}
          style={{ width: `${display}%` }}
        />
      </div>
    </div>
  );
}
