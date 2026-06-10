import { cn } from '@/lib/utils';

export function Tabs({
  tabs,
  active,
  onChange,
  className,
}: {
  tabs: { id: string; label: string; count?: number }[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap gap-1 border-b-2 border-cobweb-border pb-0', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={active === tab.id ? 'pixel-tab-active' : 'pixel-tab hover:text-gray-200'}
        >
          {tab.label}
          {tab.count != null && (
            <span className="ml-1 text-cobweb-pink">({tab.count})</span>
          )}
        </button>
      ))}
    </div>
  );
}
