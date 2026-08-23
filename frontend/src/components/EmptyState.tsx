import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-14 text-center">
      <div className="w-full max-w-sm overflow-hidden rounded-xl border border-border bg-code font-mono text-xs">
        <div className="flex items-center gap-1.5 border-b border-border/70 bg-surface2/60 px-3 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
        </div>
        <div className="flex items-center gap-2 px-4 py-6 text-left text-slate-300">
          {icon ?? <ChevronRight className="h-4 w-4 text-primary" />}
          <span>{title}</span>
          <span className="inline-block h-3.5 w-[7px] animate-blink bg-primary" />
        </div>
      </div>
      {description && (
        <p className="max-w-sm text-sm leading-relaxed text-muted">{description}</p>
      )}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
