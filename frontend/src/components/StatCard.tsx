import type { ReactNode } from "react";

import { useCountUp } from "@/hooks/useCountUp";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "primary";
  chipClassName?: string;
}

const TONES = {
  default: "text-white",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  primary: "text-primary",
};

const CHIP_TONES = {
  default: {
    ring: "from-slate-500/40 to-slate-600/20",
    text: "text-muted",
    bg: "bg-success/15",
  },
  success: {
    ring: "from-success/60 to-accent/30",
    text: "text-success",
    bg: "bg-success/15",
  },
  warning: {
    ring: "from-warning/60 to-danger/30",
    text: "text-warning",
    bg: "bg-warning/15",
  },
  danger: { ring: "from-danger/60 to-warning/30", text: "text-danger", bg: "bg-danger/15" },
  primary: {
    ring: "from-primary/70 to-accent/40",
    text: "text-primary",
    bg: "bg-primary/15",
  },
};

export function StatCard({
  label,
  value,
  icon,
  tone = "default",
  chipClassName,
}: StatCardProps) {
  const numeric =
    typeof value === "number" ? value : typeof value === "string" && /^\d+$/.test(value) ? Number(value) : null;
  const animated = useCountUp(numeric ?? 0);
  const shown = numeric !== null ? Math.round(animated) : value;
  const chips = CHIP_TONES[tone];

  return (
    <div className="card card-hover group hud-always flex items-center gap-4 hover:-translate-y-0.5">
      <span className="hud-frame" aria-hidden />
      {icon && (
        <div
          className={`shrink-0 rounded-xl bg-gradient-to-br p-[1.5px] shadow-glow-sm transition-transform duration-150 ease-spring group-hover:scale-105 ${chips.ring} ${chipClassName ?? ""}`}
        >
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-[10px] bg-surface ${chips.text}`}
          >
            {icon}
          </div>
        </div>
      )}
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label}
        </p>
        <p
          className={`truncate font-mono text-2xl font-bold tabular-nums leading-tight ${TONES[tone]}`}
        >
          {shown}
        </p>
      </div>
    </div>
  );
}
