import { useI18n } from "@/i18n";
import type { JobStatus } from "@/types";

const STYLES: Record<JobStatus, { badge: string; dot: string; pulse: boolean }> = {
  queued: {
    badge: "badge-neutral",
    dot: "bg-text-tertiary",
    pulse: false,
  },
  parsing: {
    badge: "badge-info",
    dot: "bg-info",
    pulse: true,
  },
  analyzing: {
    badge: "badge-primary",
    dot: "bg-brand-emerald",
    pulse: true,
  },
  refactoring: {
    badge: "badge-primary",
    dot: "bg-brand-emerald",
    pulse: true,
  },
  verifying: {
    badge: "badge-primary",
    dot: "bg-brand-emerald",
    pulse: true,
  },
  healing: {
    badge: "badge-warning",
    dot: "bg-warning",
    pulse: true,
  },
  completed: {
    badge: "badge-success",
    dot: "bg-success",
    pulse: false,
  },
  failed: {
    badge: "badge-danger",
    dot: "bg-danger",
    pulse: false,
  },
  cancelled: {
    badge: "badge-neutral",
    dot: "bg-text-tertiary",
    pulse: false,
  },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const { t } = useI18n();
  const style = STYLES[status] ?? STYLES.queued;
  return (
    <span className={`inline-flex items-center gap-1.5 ${style.badge}`}>
      <span className="relative flex h-1.5 w-1.5">
        {style.pulse && (
          <span className="absolute inset-0 rounded-full bg-current/50 animate-ping" />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${style.dot}`} />
      </span>
      {t(`status.${status}`)}
    </span>
  );
}