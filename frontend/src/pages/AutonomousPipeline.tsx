import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Rocket,
  GitBranch,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

interface AutoJob {
  job_id: number;
  status: string;
  progress: number;
  message: string;
  pull_request_url: string | null;
  branch_name: string | null;
  error_message: string | null;
  diff_summary: string | null;
}

export function AutonomousPipeline() {
  const { t } = useI18n();
  const toast = useToast();
  const [repoUrl, setRepoUrl] = useState("");
  const [token, setToken] = useState("");
  const [baseBranch, setBaseBranch] = useState("main");
  const [targetFiles, setTargetFiles] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [job, setJob] = useState<AutoJob | null>(null);
  const [polling, setPolling] = useState(false);

  const poll = useCallback(
    async (jobId: number) => {
      try {
        const data = await api.getAutonomousJob(jobId);
        setJob(data as unknown as AutoJob);
        const s = (data as unknown as AutoJob).status;
        if (s !== "completed" && s !== "failed" && s !== "cancelled") {
          setTimeout(() => void poll(jobId), 3000);
        } else {
          setPolling(false);
        }
      } catch {
        setPolling(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (job && polling) {
      void poll(job.job_id);
    }
  }, [job, polling, poll]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      toast.error(t("autonomous.fillRepo"));
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.runAutonomous({
        repo_url: repoUrl.trim(),
        github_token: token || undefined,
        base_branch: baseBranch.trim() || "main",
        target_files: targetFiles
          .split(",")
          .map((f) => f.trim())
          .filter((f) => f.length > 0),
      });
      setJob({
        job_id: (res as Record<string, unknown>).job_id as number,
        status: (res as Record<string, unknown>).status as string,
        progress: 0,
        message: (res as Record<string, unknown>).message as string,
        pull_request_url: null,
        branch_name: null,
        error_message: null,
        diff_summary: null,
      });
      setPolling(true);
      toast.success(t("autonomous.jobStarted"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("autonomous.failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t("autonomous.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("autonomous.subtitle")}</p>
      </div>

      <div className="card">
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="repo-url">
              {t("autonomous.repoUrl")}
            </label>
            <input
              id="repo-url"
              required
              className="input"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder={t("autonomous.repoUrlPlaceholder")}
            />
          </div>
          <div>
            <label className="label" htmlFor="gh-token">
              {t("autonomous.token")}
            </label>
            <input
              id="gh-token"
              type="password"
              className="input"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={t("autonomous.tokenPlaceholder")}
            />
          </div>
          <div>
            <label className="label" htmlFor="base-branch">
              {t("autonomous.baseBranch")}
            </label>
            <input
              id="base-branch"
              className="input"
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              placeholder={t("autonomous.baseBranchPlaceholder")}
            />
            <p className="mt-1 text-xs text-muted">{t("autonomous.baseBranchHint")}</p>
          </div>
          <div>
            <label className="label" htmlFor="target-files">
              {t("autonomous.targetFiles")}
            </label>
            <textarea
              id="target-files"
              className="input min-h-[64px]"
              value={targetFiles}
              onChange={(e) => setTargetFiles(e.target.value)}
              placeholder={t("autonomous.targetFilesPlaceholder")}
            />
            <p className="mt-1 text-xs text-muted">{t("autonomous.targetFilesHint")}</p>
          </div>
          <button type="submit" className="btn-primary" disabled={submitting}>
            <Rocket className="h-4 w-4" />
            {submitting ? t("autonomous.submitting") : t("autonomous.submit")}
          </button>
        </form>
      </div>

      {job && (
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <span className="rounded-lg bg-primary/15 px-3 py-1 text-sm font-medium text-primary">
              {t(`status.${job.status}` as never)}
            </span>
            {polling && <Spinner size="sm" />}
          </div>

          <p className="text-sm text-muted">{job.message}</p>

          {job.status !== "completed" && job.status !== "failed" && (
            <div className="h-2 overflow-hidden rounded-full bg-surface2">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${job.progress}%` }}
              />
            </div>
          )}

          {job.status === "completed" && (
            <div className="flex items-center gap-2 text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span className="text-sm font-medium">{t("autonomous.success")}</span>
            </div>
          )}

          {job.status === "failed" && (
            <div className="flex items-center gap-2 text-danger">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm font-medium">{job.error_message ?? t("autonomous.failed")}</span>
            </div>
          )}

          {job.pull_request_url && (
            <a
              href={job.pull_request_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              {t("autonomous.prLink")}
            </a>
          )}

          {job.branch_name && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <GitBranch className="h-4 w-4" />
              {t("autonomous.branchName")}: {job.branch_name}
            </div>
          )}

          <Link
            to={`/jobs/${job.job_id}`}
            className="text-sm font-medium text-primary hover:underline"
          >
            {t("common.viewAll")} →
          </Link>
        </div>
      )}
    </div>
  );
}
