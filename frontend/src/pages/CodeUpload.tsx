import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  FileCode2,
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
  critical: "text-danger-text",
  warning: "text-warning-text",
  info: "text-info-text",
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
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">{t("upload.title")}</h1>
        <p className="page-subtitle max-w-2xl">{t("upload.subtitle")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <div className="card space-y-6 p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="form-group">
                <label className="label" htmlFor="u-project">
                  {t("upload.project")}
                </label>
                <select
                  id="u-project"
                  className="select"
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
                  <p className="form-hint">
                    {t("upload.noProjectsYet")}{" "}
                    <Link to="/projects" className="text-brand-emeraldLight hover:underline">
                      {t("upload.createOne")}
                    </Link>
                    .
                  </p>
                )}
              </div>
              <div className="form-group">
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

            <div className="form-group max-w-[220px]">
              <label className="label" htmlFor="u-priority">
                {t("upload.priority")}
              </label>
              <select
                id="u-priority"
                className="select"
                value={priority}
                onChange={(e) =>
                  setPriority(e.target.value as "urgent" | "normal" | "bulk")
                }
              >
                <option value="urgent">{t("upload.priorityUrgent")}</option>
                <option value="normal">{t("upload.priorityNormal")}</option>
                <option value="bulk">{t("upload.priorityBulk")}</option>
              </select>
              <p className="form-hint">{t("upload.priorityHint")}</p>
            </div>

            <div className="form-group">
              <label className="label" htmlFor="u-rule">
                {t("upload.contextRule")}
              </label>
              <textarea
                id="u-rule"
                className="textarea min-h-[64px]"
                value={contextRule}
                onChange={(e) => setContextRule(e.target.value)}
                placeholder={t("upload.contextRulePlaceholder")}
              />
              <p className="form-hint">{t("upload.contextRuleHint")}</p>
            </div>

            <div className="form-group">
              <label className="label" htmlFor="u-filename">
                {t("upload.filename")}
              </label>
              <input
                id="u-filename"
                className="input max-w-[220px] font-mono text-code"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
              />
            </div>

            <div className="form-group">
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0" htmlFor="u-code">
                  {t("upload.legacyCode")}
                </label>
                <button
                  type="button"
                  onClick={onAnalyze}
                  disabled={analyzing || !code.trim()}
                  className="btn-secondary btn-sm"
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
                className="textarea min-h-[420px]"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder={t("upload.codePlaceholder")}
                spellCheck={false}
              />
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border-primary pt-4">
              <Link to="/" className="btn-secondary">
                {t("common.cancel")}
              </Link>
              <button
                onClick={onSubmit}
                disabled={submitting || !code.trim() || !projectId}
                className="btn-primary"
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
          <div className="card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-heading-sm font-semibold text-text-primary">
              <FileCode2 className="h-5 w-5 text-brand-emerald" />
              {t("upload.analysisTitle")}
            </h2>

            {analyzing && (
              <div className="flex items-center justify-center py-8">
                <Spinner label={t("upload.analyzingDesc")} />
              </div>
            )}

            {parseError && !analyzing && (
              <div className="rounded-xl border border-danger-border bg-danger-bg p-4 text-body-sm text-danger-text">
                <p className="font-medium">{t("upload.parseError")}</p>
                <p className="mt-1 font-mono text-code">{parseError}</p>
              </div>
            )}

            {findings && !analyzing && !parseError && (
              <>
                {findings.length === 0 ? (
                  <div className="rounded-xl border border-success-border bg-success-bg p-4 text-body-sm text-success-text flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    {t("upload.noIssues")}
                  </div>
                ) : (
                  <>
                    {findingStats && (
                      <div className="mb-4 flex flex-wrap gap-2 text-caption">
                        <span className="badge-danger">{t("upload.critical", { count: findingStats.critical })}</span>
                        <span className="badge-warning">{t("upload.warnings", { count: findingStats.warning })}</span>
                        <span className="badge-info">{t("upload.info", { count: findingStats.info })}</span>
                      </div>
                    )}
                    <div className="max-h-[520px] space-y-2 overflow-auto pr-1">
                      {findings.map((finding, i) => (
                        <div key={i} className="card p-3">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className={`h-3.5 w-3.5 ${SEVERITY_STYLES[finding.severity]}`} />
                            <span className="badge-dot {SEVERITY_BADGES[finding.severity]}">
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
                      ))}
                    </div>
                  </>
                )}
              </>
            )}

            {!findings && !parseError && !analyzing && (
              <p className="text-body-sm text-text-tertiary text-center py-8">
                {t("upload.analysisHint")}
              </p>
            )}
          </div>

          <div className="card p-6">
            <h2 className="mb-3 flex items-center gap-2 text-heading-sm font-semibold text-text-primary">
              <GitCompareArrows className="h-5 w-5 text-brand-cyan" />
              {t("upload.pipelineTitle")}
            </h2>
            <ol className="space-y-2 text-body-sm text-text-tertiary">
              {dict.upload.pipelineSteps.map((step, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex shrink-0 h-6 w-6 items-center justify-center rounded-full bg-brand-emerald/10 text-brand-emeraldLight font-mono text-caption font-medium">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}