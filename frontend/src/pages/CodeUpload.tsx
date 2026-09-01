import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  FileCode2,
  Info,
  Rocket,
  ScanSearch,
  GitCompareArrows,
} from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Finding, Project } from "@/types";

const SEVERITY_STYLES: Record<Finding["severity"], string> = {
  critical: "text-danger",
  warning: "text-warning",
  info: "text-accent",
};

export function CodeUpload() {
  const navigate = useNavigate();
  const toast = useToast();
  const { t, dict } = useI18n();
  const [searchParams] = useSearchParams();

  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | "">(
    Number(searchParams.get("project")) || "",
  );
  const [title, setTitle] = useState("");
  const [contextRule, setContextRule] = useState("");
  const [code, setCode] = useState("");
  const [filename, setFilename] = useState("source.py");
  const [priority, setPriority] = useState<"urgent" | "normal" | "bulk">("normal");

  const [analyzing, setAnalyzing] = useState(false);
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
    } catch {
      toast.error(t("upload.toast.failedLoadProjects"));
    }
  }, [toast, t]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const onAnalyze = async () => {
    if (!code.trim()) {
      toast.warning(t("upload.toast.needCode"));
      return;
    }
    setAnalyzing(true);
    setFindings(null);
    setParseError(null);
    try {
      const result = await api.analyze(code, filename);
      if (!result.success) {
        setParseError(result.parse_error);
      } else {
        setFindings(result.findings);
        toast.info(t("upload.toast.foundIssues", { count: result.findings.length }));
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("upload.toast.analysisFailed"));
    } finally {
      setAnalyzing(false);
    }
  };

  const onSubmit = async () => {
    if (!projectId) {
      toast.warning(t("upload.toast.selectProject"));
      return;
    }
    if (!title.trim()) {
      toast.warning(t("upload.toast.needTitle"));
      return;
    }
    if (!code.trim()) {
      toast.warning(t("upload.toast.needCode2"));
      return;
    }
    setSubmitting(true);
    try {
      const job = await api.submitJob({
        project_id: Number(projectId),
        title: title.trim(),
        context_rule: contextRule.trim() || undefined,
        input_code: code,
        priority,
      });
      toast.success(t("upload.toast.submitted"));
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("upload.toast.submitFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const findingStats = useMemo(() => {
    if (!findings) return null;
    return {
      critical: findings.filter((f) => f.severity === "critical").length,
      warning: findings.filter((f) => f.severity === "warning").length,
      info: findings.filter((f) => f.severity === "info").length,
    };
  }, [findings]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t("upload.title")}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">{t("upload.subtitle")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <div className="card space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="u-project">
                  {t("upload.project")}
                </label>
                <select
                  id="u-project"
                  className="input"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}
                >
                  <option value="">{t("upload.selectProject")}</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                {projects.length === 0 && (
                  <p className="mt-1.5 text-xs text-warning">
                    {t("upload.noProjectsYet")}{" "}
                    <Link to="/projects" className="text-primary hover:underline">
                      {t("upload.createOne")}
                    </Link>
                    .
                  </p>
                )}
              </div>
              <div>
                <label className="label" htmlFor="u-title">
                  {t("upload.jobTitle")}
                </label>
                <input
                  id="u-title"
                  className="input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t("upload.jobTitlePlaceholder")}
                />
              </div>
            </div>

            <div className="max-w-[220px]">
              <label className="label" htmlFor="u-priority">
                {t("upload.priority")}
              </label>
              <select
                id="u-priority"
                className="input"
                value={priority}
                onChange={(e) =>
                  setPriority(e.target.value as "urgent" | "normal" | "bulk")
                }
              >
                <option value="urgent">{t("upload.priorityUrgent")}</option>
                <option value="normal">{t("upload.priorityNormal")}</option>
                <option value="bulk">{t("upload.priorityBulk")}</option>
              </select>
              <p className="mt-1 text-xs text-muted">{t("upload.priorityHint")}</p>
            </div>

            <div>
              <label className="label" htmlFor="u-rule">
                {t("upload.contextRule")}
              </label>
              <textarea
                id="u-rule"
                className="input min-h-[64px] font-mono text-xs"
                value={contextRule}
                onChange={(e) => setContextRule(e.target.value)}
                placeholder={t("upload.contextRulePlaceholder")}
              />
              <p className="mt-1 text-xs text-muted">{t("upload.contextRuleHint")}</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <label className="label mb-0" htmlFor="u-filename">
                {t("upload.filename")}
              </label>
              <input
                id="u-filename"
                className="input max-w-[220px] font-mono text-xs"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="label mb-0" htmlFor="u-code">
                  {t("upload.legacyCode")}
                </label>
                <button
                  type="button"
                  onClick={onAnalyze}
                  disabled={analyzing || !code.trim()}
                  className="btn-secondary px-3 py-1.5 text-xs"
                >
                  {analyzing ? (
                    <Spinner size="sm" label={t("upload.analyzing")} />
                  ) : (
                    <>
                      <ScanSearch className="h-3.5 w-3.5" />
                      {t("upload.runAnalysis")}
                    </>
                  )}
                </button>
              </div>
              <textarea
                id="u-code"
                className="input min-h-[420px] font-mono text-xs leading-5"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder={t("upload.codePlaceholder")}
              />
            </div>

            <div className="flex items-center justify-end gap-3">
              <Link to="/" className="btn-secondary">
                {t("common.cancel")}
              </Link>
              <button
                onClick={onSubmit}
                disabled={submitting || !code.trim() || !projectId}
                className="btn-accent"
              >
                {submitting ? (
                  <Spinner size="sm" label={t("upload.submitting")} />
                ) : (
                  <>
                    <Rocket className="h-4 w-4" />
                    {t("upload.submit")}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="card">
            <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
              <FileCode2 className="h-4 w-4 text-primary" />
              {t("upload.analysisTitle")}
            </h2>

            {analyzing && <Spinner label={t("upload.analyzingDesc")} />}

            {parseError && !analyzing && (
              <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
                <p className="font-medium">{t("upload.parseError")}</p>
                <p className="mt-1 font-mono text-xs">{parseError}</p>
              </div>
            )}

            {findings && !analyzing && !parseError && (
              <>
                {findings.length === 0 ? (
                  <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 p-3 text-sm text-success">
                    <CheckCircle2 className="h-4 w-4" />
                    {t("upload.noIssues")}
                  </div>
                ) : (
                  <>
                    {findingStats && (
                      <div className="mb-3 flex gap-2 text-xs">
                        <span className="rounded-md bg-danger/15 px-2 py-1 text-danger">
                          {t("upload.critical", { count: findingStats.critical })}
                        </span>
                        <span className="rounded-md bg-warning/15 px-2 py-1 text-warning">
                          {t("upload.warnings", { count: findingStats.warning })}
                        </span>
                        <span className="rounded-md bg-accent/15 px-2 py-1 text-accent">
                          {t("upload.info", { count: findingStats.info })}
                        </span>
                      </div>
                    )}
                    <div className="max-h-[520px] space-y-2 overflow-auto pr-1">
                      {findings.map((finding, i) => (
                        <div key={i} className="rounded-lg border border-border bg-code p-3">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className={`h-3.5 w-3.5 ${SEVERITY_STYLES[finding.severity]}`} />
                            <span className={`text-xs font-medium ${SEVERITY_STYLES[finding.severity]}`}>
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
                          <p className="mt-1.5 text-xs text-slate-300">{finding.message}</p>
                          {finding.suggestion && (
                            <p className="mt-1 flex items-start gap-1 text-[11px] text-muted">
                              <Info className="mt-0.5 h-3 w-3 shrink-0" />
                              {finding.suggestion}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}

            {!findings && !parseError && !analyzing && (
              <p className="text-sm text-muted">
                {t("upload.analysisHint")}
              </p>
            )}
          </div>

          <div className="card">
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
              <GitCompareArrows className="h-4 w-4 text-accent" />
              {t("upload.pipelineTitle")}
            </h2>
            <ol className="space-y-1.5 text-xs text-muted">
              {dict.upload.pipelineSteps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
