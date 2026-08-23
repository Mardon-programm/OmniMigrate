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
    return { projects: projects.length, jobs: jobs.length, completed, failed };
  }, [projects, jobs]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const firstName = user?.full_name.split(" ")[0] ?? t("dash.engineer");

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      <OnboardingChecklist />
      <div className="group relative overflow-hidden rounded-2xl border border-border bg-surface/60 p-6 shadow-card sm:p-8">
        <span className="hud-frame always" aria-hidden />
        <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-primary/20 blur-3xl animate-aurora" />
        <div className="pointer-events-none absolute -bottom-24 right-32 h-52 w-52 rounded-full bg-accent/15 blur-3xl animate-aurora-slow" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-16 animate-scan bg-gradient-to-b from-transparent via-primary/[0.05] to-transparent" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <p className="mb-1.5 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-primary/80">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-primary/50 animate-led-ping" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success shadow-[0_0_8px_rgba(16,185,129,0.9)]" />
              </span>
              {t("dash.overline")}
            </p>
            <h1 className="text-2xl font-extrabold tracking-tight sm:text-4xl">
              <span className="text-white">{t("dash.welcomePre", { name: firstName })}</span>{" "}
              <span className="text-gradient-animated">{firstName}</span>
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
              {t("dash.subtitle")}
            </p>
          </div>
          <Link to="/upload" className="btn-accent shrink-0 self-start sm:self-auto">
            <Plus className="h-4 w-4" />
            {t("dash.newMigration")}
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label={t("dash.stats.projects")}
          value={stats.projects}
          tone="primary"
          icon={<FolderGit2 className="h-5 w-5 text-primary" />}
        />
        <StatCard
          label={t("dash.stats.totalJobs")}
          value={stats.jobs}
          tone="primary"
          icon={<Layers className="h-5 w-5 text-accent" />}
        />
        <StatCard
          label={t("dash.stats.completed")}
          value={stats.completed}
          tone="success"
          icon={<CheckCircle2 className="h-5 w-5 text-success" />}
        />
        <StatCard
          label={t("dash.stats.failed")}
          value={stats.failed}
          tone="danger"
          icon={<XCircle className="h-5 w-5 text-danger" />}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="card lg:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-base font-semibold text-white">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15">
                <Cpu className="h-4 w-4 text-primary" />
              </span>
              {t("dash.recentMigrations")}
            </h2>
            {jobs.length > 0 && (
              <Link to="/jobs" className="text-sm font-medium text-primary hover:underline">
                {t("common.viewAll")}
              </Link>
            )}
          </div>

          {jobs.length === 0 ? (
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
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-wider text-muted">
                    <th className="pb-2 pr-4 font-medium">{t("jobs.table.title")}</th>
                    <th className="pb-2 pr-4 font-medium">{t("jobs.table.status")}</th>
                    <th className="pb-2 pr-4 font-medium">{t("jobs.table.selfHeals")}</th>
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
                          {t("common.job")} #{job.id} · {formatDate(job.created_at, locale)}
                        </p>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="py-3 pr-4 text-muted">{job.self_heal_attempts}</td>
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

        <section className="card lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-base font-semibold text-white">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15">
                <FolderGit2 className="h-4 w-4 text-primary" />
              </span>
              {t("dash.projectsTitle")}
            </h2>
            <Link to="/projects" className="text-sm font-medium text-primary hover:underline">
              {t("common.manage")}
            </Link>
          </div>

          {projects.length === 0 ? (
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
          ) : (
            <div className="space-y-3">
              {projects.slice(0, 5).map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="group block rounded-xl border border-border bg-code p-4 transition-all duration-200 hover:border-primary/40 hover:shadow-glow-sm"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-slate-200">{project.name}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted">
                        {project.job_count} {t("common.jobs")}
                      </span>
                      <ArrowUpRight className="h-3.5 w-3.5 text-muted opacity-0 transition-opacity group-hover:opacity-100 group-hover:text-primary" />
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded-md bg-accent/10 px-2 py-0.5 text-xs text-accent">
                      {project.source_language}
                    </span>
                    <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs text-primary">
                      → {project.target_stack}
                    </span>
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
