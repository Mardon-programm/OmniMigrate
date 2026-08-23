import { useI18n } from "@/i18n";
import type { JobStatus } from "@/types";

const STYLES: Record<JobStatus, { classes: string; core: string; ring: string }> = {
  queued: {
    classes: "bg-slate-500/10 text-slate-300 border-slate-500/30",
    core: "bg-slate-400",
    ring: "",
  },
  parsing: {
    classes: "bg-accent/10 text-accent border-accent/30",
    core: "bg-accent shadow-[0_0_8px_rgba(6,182,212,0.8)]",
    ring: "bg-accent/50 animate-led-ping",
  },
  analyzing: {
    classes: "bg-primary/10 text-primary border-primary/30",
    core: "bg-primary shadow-[0_0_8px_rgba(16,185,129,0.8)]",
    ring: "bg-primary/50 animate-led-ping",
  },
  refactoring: {
    classes: "bg-primary/10 text-primary border-primary/30",
    core: "bg-primary shadow-[0_0_8px_rgba(16,185,129,0.8)]",
    ring: "bg-primary/50 animate-led-ping",
  },
  verifying: {
    classes: "bg-primary/10 text-primary border-primary/30",
    core: "bg-primary shadow-[0_0_8px_rgba(16,185,129,0.8)]",
    ring: "bg-primary/50 animate-led-ping",
  },
  healing: {
    classes: "bg-warning/10 text-warning border-warning/30",
    core: "bg-warning shadow-[0_0_8px_rgba(245,158,11,0.8)]",
    ring: "bg-warning/50 animate-led-ping",
  },
  completed: {
    classes: "bg-success/10 text-success border-success/40 shadow-glow-sm",
    core: "bg-success shadow-[0_0_8px_rgba(16,185,129,0.9)]",
    ring: "",
  },
  failed: {
    classes: "bg-danger/10 text-danger border-danger/30",
    core: "bg-danger shadow-[0_0_8px_rgba(239,68,68,0.8)]",
    ring: "",
  },
  cancelled: {
    classes: "bg-muted/10 text-muted border-muted/30",
    core: "bg-muted",
    ring: "",
  },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const { t } = useI18n();
  const style = STYLES[status] ?? STYLES.queued;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${style.classes}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {style.ring && <span className={`absolute inline-flex h-full w-full rounded-full ${style.ring}`} />}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${style.core}`} />
      </span>
      {t(`status.${status}`)}
    </span>
  );
}
