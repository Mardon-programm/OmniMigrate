import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertOctagon,
  ArrowLeft,
  Code2,
  Download,
  FileDiff,
  FolderGit2,
  FlaskConical,
  Layers,
  Timer,
  XCircle,
} from "lucide-react";

import { CodeBlock } from "@/components/CodeBlock";
import { DiffViewer } from "@/components/DiffViewer";
import { Spinner } from "@/components/Spinner";
import { StatusBadge } from "@/components/StatusBadge";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { formatDate, localizeStageMessage } from "@/i18n/helpers";
import { api } from "@/services/api";
import type { Job } from "@/types";

type Tab = "diff" | "output" | "findings" | "input" | "context";

const FINISHED = new Set(["completed", "failed", "cancelled"]);

export function JobDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const { t, locale } = useI18n();
  const jobId = Number(id);

  const [job, setJob] = useState<Job | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("diff");
  const [cancelling, setCancelling] = useState(false);
  const timerRef = useRef<number | null>(null);

  const poll = useCallback(async () => {
    try {
      const status = await api.getJobStatus(jobId);
      setProgress(status.progress);
      setProgressMessage(status.message);
      return status.status;
    } catch {
      return null;
    }
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const data = await api.getJob(jobId);
        if (cancelled) return;
        setJob(data);
        setProgress(null);
        setProgressMessage(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("jobDetails.loadFailed"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [jobId, t]);

  // Poll live status while the job is running.
  useEffect(() => {
    if (!job || FINISHED.has(job.status)) return;

    const tick = async () => {
      const status = await poll();
      if (status === "completed" || status === "failed" || status === "cancelled") {
        const fresh = await api.getJob(jobId);
        setJob(fresh);
        return;
      }
      timerRef.current = window.setTimeout(tick, 2500);
    };
    void tick();

    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [job, jobId, poll]);

  const onCancel = async () => {
    setCancelling(true);
    try {
      await api.cancelJob(jobId);
      toast.info(t("jobDetails.cancelRequested"));
      const fresh = await api.getJob(jobId);
      setJob(fresh);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("jobDetails.cancelFailed"));
    } finally {
      setCancelling(false);
    }
  };

  const downloadOutput = () => {
    if (!job?.output_code) return;
    const blob = new Blob([job.output_code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omnimigrate-job-${job.id}-output.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center">
        <AlertOctagon className="mx-auto mb-3 h-10 w-10 text-danger" />
        <p className="text-danger">{error ?? t("jobDetails.notFound")}</p>
        <button onClick={() => navigate("/")} className="btn-secondary mt-4">
          <ArrowLeft className="h-4 w-4" />
          {t("jobDetails.backToDashboard")}
        </button>
      </div>
    );
  }

  const running = !FINISHED.has(job.status);

  const tabs: { key: Tab; label: string; icon: typeof Code2 }[] = [
    { key: "diff", label: t("jobDetails.tabs.diff"), icon: FileDiff },
    { key: "output", label: t("jobDetails.tabs.output"), icon: Code2 },
    { key: "findings", label: t("jobDetails.tabs.findings", { count: job.findings.length }), icon: FlaskConical },
    { key: "input", label: t("jobDetails.tabs.input"), icon: Layers },
    { key: "context", label: t("jobDetails.tabs.context"), icon: FolderGit2 },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <LinkBack />

      <div className="card space-y-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-bold text-white">{job.title}</h1>
              <StatusBadge status={job.status} />
            </div>
            <p className="mt-1 text-sm text-muted">
              {t("common.job")} #{job.id} · {t("jobs.table.project")} #{job.project_id} ·{" "}
              {formatDate(job.created_at, locale)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
            {running && (
              <button
                onClick={onCancel}
                disabled={cancelling}
                className="btn-danger"
              >
                <XCircle className="h-4 w-4" />
                {cancelling ? t("jobDetails.cancelling") : t("jobDetails.cancelJob")}
              </button>
            )}
            {job.output_code && (
              <button onClick={downloadOutput} className="btn-secondary">
                <Download className="h-4 w-4" />
                {t("jobDetails.downloadOutput")}
              </button>
            )}
          </div>
        </div>

        {running && progress != null && (
          <div>
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted">
                <Timer className="h-3.5 w-3.5" />
                {localizeStageMessage(progressMessage ?? "", t) || t("jobDetails.working")}
              </span>
              <span className="text-slate-300">{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-code">
              <div
                className="h-full rounded-full bg-brand-gradient transition-all duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {job.error_message && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
            <p className="font-medium">{t("jobDetails.error")}</p>
            <p className="mt-1 font-mono text-xs">{job.error_message}</p>
          </div>
        )}

        {job.metrics && Object.keys(job.metrics).length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Metric label={t("jobDetails.metrics.duration")} value={`${(job.metrics.duration_seconds ?? 0).toFixed(2)}s`} />
            <Metric label={t("jobDetails.metrics.findings")} value={String(job.metrics.findings_count ?? 0)} />
            <Metric label={t("jobDetails.metrics.selfHeals")} value={String(job.metrics.self_heal_attempts ?? 0)} />
            <Metric label={t("jobDetails.metrics.added")} value={String(job.metrics.additions ?? 0)} tone="text-success" />
            <Metric label={t("jobDetails.metrics.removed")} value={String(job.metrics.deletions ?? 0)} tone="text-danger" />
            <Metric label={t("jobDetails.metrics.net")} value={String(job.metrics.net_lines ?? 0)} />
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all ${
              tab === key
                ? "bg-primary/15 text-primary shadow-glow-sm"
                : "text-muted hover:bg-surface2 hover:text-slate-200"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "diff" && <DiffViewer diff={job.diff ?? ""} />}
      {tab === "output" &&
        (job.output_code ? (
          <CodeBlock code={job.output_code} title={t("jobDetails.tabs.output")} />
        ) : (
          <EmptyPlaceholder text={t("jobDetails.outputNotAvailable")} />
        ))}
      {tab === "input" && <CodeBlock code={job.input_code} title={t("jobDetails.tabs.input")} />}
      {tab === "context" && (
        <div className="card">
          <h3 className="mb-2 text-sm font-semibold text-white">{t("jobDetails.migrationRule")}</h3>
          <pre className="whitespace-pre-wrap rounded-lg bg-code p-4 font-mono text-xs leading-5 text-slate-300">
            {job.context_rule}
          </pre>
        </div>
      )}
      {tab === "findings" && (
        <div className="space-y-2">
          {job.findings.length === 0 ? (
            <EmptyPlaceholder text={t("jobDetails.noFindings")} />
          ) : (
            job.findings.map((finding, i) => (
              <div key={i} className="card !p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-xs font-medium ${
                      finding.severity === "critical"
                        ? "text-danger"
                        : finding.severity === "warning"
                          ? "text-warning"
                          : "text-accent"
                    }`}
                  >
                    {finding.severity.toUpperCase()}
                  </span>
                  <span className="rounded bg-surface2 px-1.5 py-0.5 font-mono text-[10px] text-muted">
                    {finding.category}
                  </span>
                  {finding.line != null && (
                    <span className="ml-auto font-mono text-[10px] text-muted">
                      {t("common.line")} {finding.line}
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-sm text-slate-300">{finding.message}</p>
                {finding.suggestion && (
                  <p className="mt-1 text-xs text-muted">→ {finding.suggestion}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function LinkBack() {
  const { t } = useI18n();
  return (
    <button
      onClick={() => (window.history.length > 1 ? window.history.back() : undefined)}
      className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-slate-200"
    >
      <ArrowLeft className="h-4 w-4" />
      {t("jobDetails.back")}
    </button>
  );
}

function Metric({ label, value, tone = "text-slate-200" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl bg-code p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function EmptyPlaceholder({ text }: { text: string }) {
  return (
    <div className="card flex items-center justify-center py-12 text-sm text-muted">
      {text}
    </div>
  );
}
