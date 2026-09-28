import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Rocket, Filter, Search, ChevronDown } from "lucide-react";

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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [filterOpen, setFilterOpen] = useState(false);

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

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const matchesSearch =
        job.title.toLowerCase().includes(search.toLowerCase()) ||
        String(job.id).includes(search);
      const matchesStatus = statusFilter === "all" || job.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [jobs, search, statusFilter]);

  const statusOptions = [
    { value: "all", label: t("jobs.filter.all") },
    { value: "pending", label: t("jobs.filter.pending") },
    { value: "running", label: t("jobs.filter.running") },
    { value: "completed", label: t("jobs.filter.completed") },
    { value: "failed", label: t("jobs.filter.failed") },
    { value: "cancelled", label: t("jobs.filter.cancelled") },
  ];

  if (loading) {
    return (
      <div className="page">
        <div className="flex min-h-[60vh] items-center justify-center">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="page-title">{t("jobs.title")}</h1>
            <p className="page-subtitle">{t("jobs.subtitle")}</p>
          </div>
          <Link to="/upload" className="btn-primary shrink-0">
            <Rocket className="h-4 w-4" />
            {t("jobs.submitCode")}
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="border-b border-border-primary px-6 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                placeholder={t("jobs.searchPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <button
                  onClick={() => setFilterOpen(!filterOpen)}
                  className="btn-secondary gap-2"
                >
                  <Filter className="h-4 w-4" />
                  <span>{statusFilter === "all" ? t("jobs.filter.status") : statusOptions.find((o) => o.value === statusFilter)?.label}</span>
                  <ChevronDown className={`h-4 w-4 transition-transform ${filterOpen ? "rotate-180" : ""}`} />
                </button>

                {filterOpen && (
                  <div className="dropdown w-48">
                    {statusOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => {
                          setStatusFilter(option.value);
                          setFilterOpen(false);
                        }}
                        className={`dropdown-item w-full text-left ${statusFilter === option.value ? "text-brand-emeraldLight font-medium" : ""}`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {filteredJobs.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title={search || statusFilter !== "all" ? t("jobs.noResultsTitle") : t("jobs.emptyTitle")}
              description={search || statusFilter !== "all" ? t("jobs.noResultsDesc") : t("jobs.emptyDesc")}
              action={
                <Link to="/upload" className="btn-primary">
                  <Rocket className="h-4 w-4" />
                  {t("jobs.submitCode")}
                </Link>
              }
            />
          </div>
        ) : (
          <div className="table-container">
            <table className="table table-clickable">
              <thead>
                <tr>
                  <th className="w-[35%]">{t("jobs.table.title")}</th>
                  <th className="w-[15%]">{t("jobs.table.project")}</th>
                  <th className="w-[15%]">{t("jobs.table.status")}</th>
                  <th className="w-[10%]">{t("jobs.table.selfHeals")}</th>
                  <th className="w-[15%]">{t("jobs.table.created")}</th>
                  <th className="text-right pr-6">{t("jobs.table.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/jobs/${job.id}`)}
                  >
                    <td>
                      <p className="font-medium text-text-primary truncate">{job.title}</p>
                      <p className="text-caption text-text-tertiary font-mono">
                        {t("common.job")} #{job.id}
                      </p>
                    </td>
                    <td className="text-text-tertiary font-mono">#{job.project_id}</td>
                    <td><StatusBadge status={job.status} /></td>
                    <td className="font-mono tabular-nums text-text-tertiary">{job.self_heal_attempts}</td>
                    <td className="text-text-tertiary">{formatDate(job.created_at, locale)}</td>
                    <td className="text-right pr-6">
                      <ArrowRight className="mx-auto h-4 w-4 text-text-tertiary transition-transform hover:translate-x-0.5 hover:text-brand-emerald" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}