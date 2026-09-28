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
    <div className="empty-state">
      <div className="empty-state__icon flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-emerald/10">
        {icon ? (
          <span className="text-brand-emerald">{icon}</span>
        ) : (
          <ChevronRight className="h-7 w-7 text-brand-emerald" />
        )}
      </div>
      <div className="text-center">
        <h3 className="empty-state__title">{title}</h3>
        {description && (
          <p className="mt-1 empty-state__description">{description}</p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}