import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  FolderGit2,
  Layers,
  Plus,
  Rocket,
  CheckCircle2,
  XCircle,
  Cpu,
  ArrowUpRight,
} from "lucide-react";

import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { api } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { formatDate } from "@/i18n/helpers";
import type { JobStatusRead, Project } from "@/types";

export function Dashboard() {
  const { user } = useAuth();
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<JobStatusRead[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [proj, jobList] = await Promise.all([api.listProjects(), api.listJobs()]);
      setProjects(proj);
      setJobs(jobList.slice(0, 6));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    const completed = jobs.filter((j) => j.status === "completed").length;
    const failed = jobs.filter((j) => j.status === "failed").length;
    const running = jobs.filter((j) =>
      ["parsing", "analyzing", "refactoring", "verifying", "healing"].includes(j.status)
    ).length;
    return { projects: projects.length, jobs: jobs.length, completed, failed, running };
  }, [projects, jobs]);

  if (loading) {
    return (
      <div className="page">
        <div className="flex min-h-[60vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  const firstName = user?.full_name.split(" ")[0] ?? t("dash.engineer");

  return (
    <div className="page">
      <OnboardingChecklist />

      <div className="card-elevated stagger">
        <div className="relative overflow-hidden rounded-2xl bg-mesh-gradient p-6 sm:p-8">
          <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
            <div>
              <p className="flex items-center gap-2 text-overline text-brand-emeraldLight">
                <span className="status-indicator__dot">
                  <span className="relative block h-1.5 w-1.5 rounded-full bg-brand-emerald shadow-[0_0_8px_rgb(16_185_129_/_0.9)]" />
                </span>
                {t("dash.overline")}
              </p>
              <h1 className="mt-1.5 text-display-sm font-extrabold tracking-tight text-text-primary">
                {t("dash.welcomePre", { name: firstName })}
                <span className="text-gradient-emerald"> {firstName}</span>
              </h1>
              <p className="mt-3 max-w-xl text-body text-text-secondary">
                {t("dash.subtitle")}
              </p>
            </div>
            <Link to="/upload" className="btn-primary shrink-0 self-start sm:self-auto">
              <Plus className="h-4 w-4" />
              {t("dash.newMigration")}
            </Link>
          </div>
        </div>
      </div>

      <div className="grid-stats stagger">
        <StatCard
          label={t("dash.stats.projects")}
          value={stats.projects}
          tone="primary"
          icon={<FolderGit2 className="h-5 w-5" />}
          trend={{ value: 12, label: t("dash.stats.vsLastMonth") }}
        />
        <StatCard
          label={t("dash.stats.totalJobs")}
          value={stats.jobs}
          tone="default"
          icon={<Layers className="h-5 w-5" />}
          trend={{ value: 8, label: t("dash.stats.vsLastMonth") }}
        />
        <StatCard
          label={t("dash.stats.completed")}
          value={stats.completed}
          tone="success"
          icon={<CheckCircle2 className="h-5 w-5" />}
          trend={{ value: 15, label: t("dash.stats.vsLastMonth") }}
        />
        <StatCard
          label={t("dash.stats.failed")}
          value={stats.failed}
          tone="danger"
          icon={<XCircle className="h-5 w-5" />}
          trend={{ value: -5, label: t("dash.stats.vsLastMonth") }}
        />
      </div>

      <div className="grid-dashboard">
        <section className="card lg:col-span-3">
          <div className="flex items-center justify-between border-b border-border-primary px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-emerald/10">
                <Cpu className="h-5 w-5 text-brand-emerald" />
              </div>
              <h2 className="text-heading-md text-text-primary">{t("dash.recentMigrations")}</h2>
            </div>
            {jobs.length > 0 && (
              <Link to="/jobs" className="btn-ghost btn-sm">
                {t("common.viewAll")}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>

          {jobs.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title={t("dash.noMigrationsTitle")}
                description={t("dash.noMigrationsDesc")}
                action={
                  <Link to="/upload" className="btn-primary">
                    <Rocket className="h-4 w-4" />
                    {t("dash.startMigrating")}
                  </Link>
                }
              />
            </div>
          ) : (
            <div className="table-container">
              <table className="table table-clickable">
                <thead>
                  <tr>
                    <th className="w-[40%]">{t("jobs.table.title")}</th>
                    <th className="w-[20%]">{t("jobs.table.status")}</th>
                    <th className="w-[15%]">{t("jobs.table.selfHeals")}</th>
                    <th className="text-right pr-6">{t("jobs.table.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => navigate(`/jobs/${job.id}`)}
                    >
                      <td>
                        <p className="font-medium text-text-primary truncate">{job.title}</p>
                        <p className="text-caption text-text-tertiary">
                          {t("common.job")} #{job.id} · {formatDate(job.created_at, locale)}
                        </p>
                      </td>
                      <td>
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="font-mono tabular-nums text-text-tertiary">
                        {job.self_heal_attempts}
                      </td>
                      <td className="text-right pr-6">
                        <ArrowRight className="mx-auto h-4 w-4 text-text-tertiary transition-transform hover:translate-x-0.5 hover:text-brand-emerald" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card lg:col-span-2">
          <div className="flex items-center justify-between border-b border-border-primary px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-emerald/10">
                <FolderGit2 className="h-5 w-5 text-brand-emerald" />
              </div>
              <h2 className="text-heading-md text-text-primary">{t("dash.projectsTitle")}</h2>
            </div>
            <Link to="/projects" className="btn-ghost btn-sm">
              {t("common.manage")}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {projects.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title={t("dash.noProjectsTitle")}
                description={t("dash.noProjectsDesc")}
                action={
                  <Link to="/projects" className="btn-secondary">
                    <FolderGit2 className="h-4 w-4" />
                    {t("dash.createProject")}
                  </Link>
                }
              />
            </div>
          ) : (
            <div className="divide-y divide-border-primary">
              {projects.slice(0, 5).map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="card-interactive p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-gradient-soft">
                        <FolderGit2 className="h-5 w-5 text-brand-emerald" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-text-primary truncate">{project.name}</h3>
                        <p className="text-caption text-text-tertiary">
                          {project.job_count} {t("common.jobs")}
                        </p>
                      </div>
                    </div>
                    <ArrowUpRight className="shrink-0 h-4 w-4 text-text-tertiary opacity-0 transition-opacity group-hover:opacity-100 group-hover:text-brand-emerald" />
                  </div>
                  {project.description && (
                    <p className="mt-3 line-clamp-2 text-body-sm text-text-secondary">{project.description}</p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="badge-info">{project.source_language}</span>
                    <span className="badge-primary">→ {project.target_stack}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}