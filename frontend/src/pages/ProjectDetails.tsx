import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, FolderGit2, Plus } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { StatusBadge } from "@/components/StatusBadge";
import { useI18n } from "@/i18n";
import { formatDate } from "@/i18n/helpers";
import { api } from "@/services/api";
import type { JobStatusRead, Project } from "@/types";

export function ProjectDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t, locale } = useI18n();
  const [project, setProject] = useState<Project | null>(null);
  const [jobs, setJobs] = useState<JobStatusRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const projectId = Number(id);

  const load = useCallback(async () => {
    try {
      const [proj, jobList] = await Promise.all([
        api.getProject(projectId),
        api.listJobs(projectId),
      ]);
      setProject(proj);
      setJobs(jobList);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("projectDetails.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center">
        <p className="text-danger">{error ?? t("projectDetails.notFound")}</p>
        <Link to="/projects" className="btn-secondary mt-4">
          <ArrowLeft className="h-4 w-4" />
          {t("projectDetails.back")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <Link
        to="/projects"
        className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("projectDetails.back")}
      </Link>

      <div className="card relative overflow-hidden">
        <div className="absolute -right-14 -top-14 h-44 w-44 rounded-full bg-primary/15 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-gradient-soft">
              <FolderGit2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{project.name}</h1>
              {project.description && (
                <p className="mt-0.5 text-sm text-muted">{project.description}</p>
              )}
              <div className="mt-1.5 flex flex-wrap gap-2">
                <span className="rounded-md bg-accent/10 px-2 py-0.5 text-xs text-accent">
                  {project.source_language}
                </span>
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs text-primary">
                  → {project.target_stack}
                </span>
                {project.repo_url && (
                  <a
                    href={project.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-md bg-surface2 px-2 py-0.5 text-xs text-muted hover:text-slate-200"
                  >
                    {project.repo_url}
                  </a>
                )}
              </div>
            </div>
          </div>
          <Link to={`/upload?project=${project.id}`} className="btn-accent shrink-0 self-start sm:self-auto">
            <Plus className="h-4 w-4" />
            {t("projectDetails.newMigration")}
          </Link>
        </div>
      </div>

      <section className="card">
        <h2 className="mb-4 text-base font-semibold text-white">
          {t("projectDetails.jobsTitle", { count: jobs.length })}
        </h2>
        {jobs.length === 0 ? (
          <EmptyState
            title={t("projectDetails.noJobsTitle")}
            description={t("projectDetails.noJobsDesc")}
            action={
              <Link to={`/upload?project=${project.id}`} className="btn-primary">
                <Plus className="h-4 w-4" />
                {t("projectDetails.submitCode")}
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wider text-muted">
                  <th className="pb-2 pr-4 font-medium">{t("jobs.table.title")}</th>
                  <th className="pb-2 pr-4 font-medium">{t("jobs.table.status")}</th>
                  <th className="pb-2 pr-4 font-medium">{t("jobs.table.selfHeals")}</th>
                  <th className="pb-2 pr-4 font-medium">{t("jobs.table.created")}</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/jobs/${job.id}`)}
                    className="group cursor-pointer transition-colors hover:bg-surface2/70"
                  >
                    <td className="py-3 pr-4">
                      <p className="font-medium text-slate-200">{job.title}</p>
                      <p className="text-xs text-muted">
                        {t("common.job")} #{job.id}
                      </p>
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-3 pr-4 text-muted">{job.self_heal_attempts}</td>
                    <td className="py-3 pr-4 text-muted">
                      {formatDate(job.created_at, locale)}
                    </td>
                    <td className="py-3 text-right">
                      <ArrowRight className="ml-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
