import { cn } from '@/lib/utils';

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse bg-cobweb-surface2 border-2 border-cobweb-border',
        className,
      )}
    />
  );
}

export function LoadingSpinner({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="relative h-12 w-12">
        <div className="absolute inset-0 border-4 border-cobweb-border" />
        <div className="absolute inset-0 animate-spin border-4 border-transparent border-t-cobweb-pink" />
      </div>
      <p className="font-pixel text-[9px] uppercase tracking-wider text-gray-400 animate-pulse">
        {label}
      </p>
    </div>
  );
}
