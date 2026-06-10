import { cn } from '@/lib/utils';
import { type ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          variant === 'primary' && 'pixel-btn',
          variant === 'ghost' && 'pixel-btn-ghost',
          variant === 'danger' &&
            'pixel-btn bg-cobweb-red border-red-800 hover:bg-red-500',
          size === 'sm' && 'px-3 py-1.5 text-[8px]',
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';
