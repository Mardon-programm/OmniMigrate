import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Rocket } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { StatusBadge } from "@/components/StatusBadge";
import { useI18n } from "@/i18n";
import { formatDate } from "@/i18n/helpers";
import { api } from "@/services/api";
import type { JobStatusRead } from "@/types";

export function Jobs() {
  const navigate = useNavigate();
  const { t, locale } = useI18n();
  const [jobs, setJobs] = useState<JobStatusRead[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setJobs(await api.listJobs());
    } finally {
      setLoading(false);
    }
  }, []);

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

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t("jobs.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("jobs.subtitle")}</p>
      </div>

      {jobs.length === 0 ? (
        <div className="card">
          <EmptyState
            title={t("jobs.emptyTitle")}
            description={t("jobs.emptyDesc")}
            action={
              <Link to="/upload" className="btn-primary">
                <Rocket className="h-4 w-4" />
                {t("jobs.submitCode")}
              </Link>
            }
          />
        </div>
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-surface2/80 text-xs uppercase tracking-wider text-muted">
                <th className="px-5 py-3 font-medium">{t("jobs.table.title")}</th>
                <th className="px-5 py-3 font-medium">{t("jobs.table.project")}</th>
                <th className="px-5 py-3 font-medium">{t("jobs.table.status")}</th>
                <th className="px-5 py-3 font-medium">{t("jobs.table.selfHeals")}</th>
                <th className="px-5 py-3 font-medium">{t("jobs.table.created")}</th>
                <th className="px-5 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="group cursor-pointer transition-colors hover:bg-surface2/70"
                >
                  <td className="px-5 py-3.5">
                    <p className="font-medium text-slate-200">{job.title}</p>
                    <p className="text-xs text-muted">
                      {t("common.job")} #{job.id}
                    </p>
                  </td>
                  <td className="px-5 py-3.5 text-muted">#{job.project_id}</td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="px-5 py-3.5 text-muted">{job.self_heal_attempts}</td>
                  <td className="px-5 py-3.5 text-muted">
                    {formatDate(job.created_at, locale)}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <ArrowRight className="ml-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
