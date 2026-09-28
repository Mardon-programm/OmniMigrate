import type { ReactNode } from "react";

import { useCountUp } from "@/hooks/useCountUp";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "primary" | "info";
  trend?: { value: number; label: string };
}

const TONES = {
  default: { text: "text-text-primary", iconBg: "bg-brand-emerald/10", iconText: "text-brand-emerald", border: "border-brand-emerald/30" },
  success: { text: "text-success-text", iconBg: "bg-success-bg", iconText: "text-success-text", border: "border-success-border" },
  warning: { text: "text-warning-text", iconBg: "bg-warning-bg", iconText: "text-warning-text", border: "border-warning-border" },
  danger: { text: "text-danger-text", iconBg: "bg-danger-bg", iconText: "text-danger-text", border: "border-danger-border" },
  primary: { text: "text-brand-emeraldLight", iconBg: "bg-brand-emerald/10", iconText: "text-brand-emeraldLight", border: "border-brand-emerald/30" },
  info: { text: "text-info-text", iconBg: "bg-info-bg", iconText: "text-info-text", border: "border-info-border" },
};

export function StatCard({
  label,
  value,
  icon,
  tone = "default",
  trend,
}: StatCardProps) {
  const numeric =
    typeof value === "number"
      ? value
      : typeof value === "string" && /^\d+$/.test(value)
        ? Number(value)
        : null;
  const animated = useCountUp(numeric ?? 0);
  const shown = numeric !== null ? Math.round(animated) : value;
  const colors = TONES[tone];

  return (
    <div className="card card-hover group">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-overline text-text-tertiary">{label}</p>
          <p className="mt-1 font-mono text-display-sm font-bold tabular-nums leading-tight {colors.text}">
            {shown}
          </p>
          {trend && (
            <p className="mt-2 flex items-center gap-1.5 text-caption">
              <span
                className={`font-medium ${trend.value >= 0 ? "text-success-text" : "text-danger-text"}`}
              >
                {trend.value >= 0 ? "+" : ""}{trend.value}%
              </span>
              <span className="text-text-tertiary">{trend.label}</span>
            </p>
          )}
        </div>
        {icon && (
          <div
            className={`shrink-0 flex h-12 w-12 items-center justify-center rounded-xl transition-transform duration-fast group-hover:scale-105 ${colors.iconBg} ${colors.border} border`}
          >
            <div className={`${colors.iconText}`}>{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
}