import { cn } from '@/lib/utils';
import { type HTMLAttributes } from 'react';

export function Card({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('pixel-card p-4', className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn('mb-3 flex items-center justify-between gap-2', className)}>
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <h3 className={cn('font-pixel text-[10px] uppercase tracking-wider text-cobweb-pink-light', className)}>
      {children}
    </h3>
  );
}
