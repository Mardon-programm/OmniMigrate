import { useI18n } from "@/i18n";
import type { JobStatus } from "@/types";

const STYLES: Record<JobStatus, { classes: string; dot: string }> = {
  queued: {
    classes: "bg-slate-500/10 text-slate-300 border-slate-500/30",
    dot: "bg-slate-400",
  },
  parsing: {
    classes: "bg-accent/10 text-accent border-accent/30",
    dot: "bg-accent animate-pulse",
  },
  analyzing: {
    classes: "bg-primary/10 text-primary border-primary/30",
    dot: "bg-primary animate-pulse",
  },
  refactoring: {
    classes: "bg-primary/10 text-primary border-primary/30",
    dot: "bg-primary animate-pulse",
  },
  verifying: {
    classes: "bg-primary/10 text-primary border-primary/30",
    dot: "bg-primary animate-pulse",
  },
  healing: {
    classes: "bg-warning/10 text-warning border-warning/30",
    dot: "bg-warning animate-pulse",
  },
  completed: {
    classes: "bg-success/10 text-success border-success/30",
    dot: "bg-success",
  },
  failed: {
    classes: "bg-danger/10 text-danger border-danger/30",
    dot: "bg-danger",
  },
  cancelled: {
    classes: "bg-muted/10 text-muted border-muted/30",
    dot: "bg-muted",
  },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const { t } = useI18n();
  const style = STYLES[status] ?? STYLES.queued;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${style.classes}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {t(`status.${status}`)}
    </span>
  );
}
