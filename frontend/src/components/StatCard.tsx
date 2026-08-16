import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "primary";
  chipClassName?: string;
}

const TONES = {
  default: "text-muted",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  primary: "text-primary",
};

const CHIP_TONES = {
  default: "bg-surface2",
  success: "bg-success/15",
  warning: "bg-warning/15",
  danger: "bg-danger/15",
  primary: "bg-primary/15",
};

export function StatCard({
  label,
  value,
  icon,
  tone = "default",
  chipClassName,
}: StatCardProps) {
  return (
    <div className="card group flex items-center gap-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30">
      {icon && (
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-transform duration-200 group-hover:scale-105 ${CHIP_TONES[tone]} ${chipClassName ?? ""}`}
        >
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wider text-muted">
          {label}
        </p>
        <p className={`truncate text-xl font-semibold ${TONES[tone]}`}>{value}</p>
      </div>
    </div>
  );
}
