import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertOctagon,
  ArrowLeft,
  Check,
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
  const [copiedMetric, setCopiedMetric] = useState<string | null>(null);
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

  const copyMetric = (label: string, value: string) => {
    navigator.clipboard.writeText(value);
    setCopiedMetric(label);
    setTimeout(() => setCopiedMetric(null), 2000);
  };

  if (loading) {
    return (
      <div className="page">
        <div className="flex min-h-[60vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="page">
        <div className="mx-auto max-w-7xl px-4 py-16 text-center">
          <AlertOctagon className="mx-auto mb-3 h-10 w-10 text-danger" />
          <p className="text-danger">{error ?? t("jobDetails.notFound")}</p>
          <button onClick={() => navigate("/")} className="btn-secondary mt-4">
            <ArrowLeft className="h-4 w-4" />
            {t("jobDetails.backToDashboard")}
          </button>
        </div>
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

  const metrics = job.metrics ? [
    { label: t("jobDetails.metrics.duration"), value: `${(job.metrics.duration_seconds ?? 0).toFixed(2)}s`, key: "duration" },
    { label: t("jobDetails.metrics.findings"), value: String(job.metrics.findings_count ?? 0), key: "findings" },
    { label: t("jobDetails.metrics.selfHeals"), value: String(job.metrics.self_heal_attempts ?? 0), key: "selfHeals" },
    { label: t("jobDetails.metrics.added"), value: String(job.metrics.additions ?? 0), key: "added", tone: "success" as const },
    { label: t("jobDetails.metrics.removed"), value: String(job.metrics.deletions ?? 0), key: "removed", tone: "danger" as const },
    { label: t("jobDetails.metrics.net"), value: String(job.metrics.net_lines ?? 0), key: "net" },
  ] : [];

  return (
    <div className="page">
      <button
        onClick={() => (window.history.length > 1 ? window.history.back() : navigate("/"))}
        className="inline-flex items-center gap-1.5 text-body-sm text-text-tertiary transition-colors hover:text-text-primary mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("jobDetails.back")}
      </button>

      <div className="card space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-heading-lg font-bold text-text-primary">{job.title}</h1>
              <StatusBadge status={job.status} />
            </div>
            <p className="mt-1 text-body-sm text-text-tertiary">
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
          <div className="space-y-2">
            <div className="flex items-center justify-between text-caption">
              <span className="flex items-center gap-1.5 text-text-tertiary">
                <Timer className="h-3.5 w-3.5" />
                {localizeStageMessage(progressMessage ?? "", t) || t("jobDetails.working")}
              </span>
              <span className="font-mono tabular-nums text-text-primary">{progress}%</span>
            </div>
            <div className="progress">
              <div
                className="progress__fill"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {job.error_message && (
          <div className="rounded-xl border border-danger-border bg-danger-bg p-4 text-body-sm text-danger-text">
            <p className="font-medium">{t("jobDetails.error")}</p>
            <p className="mt-1 font-mono text-code">{job.error_message}</p>
          </div>
        )}

        {metrics.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {metrics.map((metric) => (
              <div
                key={metric.key}
                className="card p-4 cursor-pointer hover:bg-bg-cardHover transition-colors"
                onClick={() => copyMetric(metric.label, metric.value)}
                title={copiedMetric === metric.key ? t("jobDetails.copied") : t("jobDetails.copyToClipboard")}
              >
                <p className="text-overline text-text-tertiary">{metric.label}</p>
                <div className="mt-1 flex items-center gap-1.5">
                  <p className={`font-mono text-heading-sm font-bold ${metric.tone ? `text-${metric.tone}-text` : "text-text-primary"}`}>
                    {metric.value}
                  </p>
                  {copiedMetric === metric.key && (
                    <Check className="h-4 w-4 text-success-text animate-scale-in" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="tabs mt-6" role="tablist">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            role="tab"
            aria-selected={tab === key}
            className={`tab ${tab === key ? "tab-active" : ""}`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="mt-6 animate-fade-in">
        {tab === "diff" && <DiffViewer diff={job.diff ?? ""} />}
        {tab === "output" &&
          (job.output_code ? (
            <CodeBlock code={job.output_code} title={t("jobDetails.tabs.output")} />
          ) : (
            <div className="card flex items-center justify-center py-12 text-body-sm text-text-tertiary">
              {t("jobDetails.outputNotAvailable")}
            </div>
          ))}
        {tab === "input" && <CodeBlock code={job.input_code} title={t("jobDetails.tabs.input")} />}
        {tab === "context" && (
          <div className="card">
            <h3 className="mb-3 text-heading-sm font-semibold text-text-primary">{t("jobDetails.migrationRule")}</h3>
            <pre className="code-block whitespace-pre-wrap text-code">
              {job.context_rule}
            </pre>
          </div>
        )}
        {tab === "findings" && (
          <div className="space-y-3">
            {job.findings.length === 0 ? (
              <div className="card flex items-center justify-center py-12 text-body-sm text-text-tertiary">
                {t("jobDetails.noFindings")}
              </div>
            ) : (
              job.findings.map((finding, i) => (
                <div key={i} className="card p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`badge-dot ${finding.severity === "critical" ? "badge-danger" : finding.severity === "warning" ? "badge-warning" : "badge-info"}`}>
                      {finding.severity.toUpperCase()}
                    </span>
                    <span className="badge-neutral">{finding.category}</span>
                    {finding.line != null && (
                      <span className="ml-auto font-mono text-code text-text-tertiary">
                        {t("common.line")} {finding.line}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-body-sm text-text-secondary">{finding.message}</p>
                  {finding.suggestion && (
                    <p className="mt-1.5 flex items-start gap-1.5 text-caption text-text-tertiary">
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-brand-emerald/10 text-brand-emeraldLight">
                        <span className="text-[10px]">i</span>
                      </span>
                      {finding.suggestion}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}