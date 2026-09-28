import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { FolderGit2, Pencil, Plus, Trash2, Search } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Modal } from "@/components/Modal";
import { Spinner } from "@/components/Spinner";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Project } from "@/types";

const STACKS = ["python-3.12", "django-5", "node-22", "typescript", "react-18", "async-fastapi"];
const LANGUAGES = ["python", "javascript", "typescript", "java", "go", "php", "ruby", "csharp"];

export function Projects() {
  const navigate = useNavigate();
  const toast = useToast();
  const { t } = useI18n();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");

  // form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState("python");
  const [targetStack, setTargetStack] = useState("python-3.12");

  const load = useCallback(async () => {
    try {
      setProjects(await api.listProjects());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setName("");
    setDescription("");
    setRepoUrl("");
    setSourceLanguage("python");
    setTargetStack("python-3.12");
    setModalOpen(true);
  };

  const openEdit = (project: Project) => {
    setEditing(project);
    setName(project.name);
    setDescription(project.description ?? "");
    setRepoUrl(project.repo_url ?? "");
    setSourceLanguage(project.source_language);
    setTargetStack(project.target_stack);
    setModalOpen(true);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editing) {
        await api.updateProject(editing.id, {
          name,
          description: description || null,
          repo_url: repoUrl || null,
          source_language: sourceLanguage,
          target_stack: targetStack,
        });
        toast.success(t("projects.updated"));
      } else {
        await api.createProject({
          name,
          description: description || null,
          repo_url: repoUrl || null,
          source_language: sourceLanguage,
          target_stack: targetStack,
        });
        toast.success(t("projects.created"));
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("projects.operationFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (project: Project) => {
    if (!window.confirm(t("projects.deleteConfirm", { name: project.name }))) return;
    try {
      await api.deleteProject(project.id);
      toast.success(t("projects.deleted"));
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("projects.deleteFailed"));
    }
  };

  const filteredProjects = useMemo(() => {
    return projects.filter((p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description?.toLowerCase().includes(search.toLowerCase())
    );
  }, [projects, search]);

  if (loading) {
    return (
      <div className="page">
        <div className="flex min-h-[60vh] items-center justify-center">
          <Spinner size="lg" label={t("projects.loading")} />
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="page-title">{t("projects.title")}</h1>
            <p className="page-subtitle">{t("projects.subtitle")}</p>
          </div>
          <button onClick={openCreate} className="btn-primary shrink-0">
            <Plus className="h-4 w-4" />
            {t("projects.newProject")}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="border-b border-border-primary p-4 sm:p-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <input
              type="text"
              placeholder={t("projects.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </div>

        {filteredProjects.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title={search ? t("projects.noResultsTitle") : t("projects.emptyTitle")}
              description={search ? t("projects.noResultsDesc") : t("projects.emptyDesc")}
              action={
                <button onClick={openCreate} className="btn-primary">
                  <FolderGit2 className="h-4 w-4" />
                  {t("projects.createProject")}
                </button>
              }
            />
          </div>
        ) : (
          <div className="grid gap-4 p-4 sm:p-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                className="card-interactive group"
                onClick={() => navigate(`/projects/${project.id}`)}
              >
                <div className="p-4 sm:p-6">
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
                    <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openEdit(project);
                        }}
                        className="rounded-lg p-2 text-text-tertiary hover:bg-bg-tertiary hover:text-text-primary focus-ring"
                        title={t("projects.edit")}
                        aria-label={t("projects.edit")}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          void onDelete(project);
                        }}
                        className="rounded-lg p-2 text-text-tertiary hover:bg-bg-tertiary hover:text-danger focus-ring"
                        title={t("projects.delete")}
                        aria-label={t("projects.delete")}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {project.description && (
                    <p className="mt-3 line-clamp-2 text-body-sm text-text-secondary">{project.description}</p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="badge-info">{project.source_language}</span>
                    <span className="badge-primary">→ {project.target_stack}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? t("projects.editTitle") : t("projects.createTitle")}
        size="md"
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="form-group">
            <label className="label" htmlFor="p-name">
              {t("projects.name")}
            </label>
            <input
              id="p-name"
              required
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("projects.namePlaceholder")}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label className="label" htmlFor="p-desc">
              {t("projects.description")}
            </label>
            <textarea
              id="p-desc"
              className="textarea min-h-[80px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("projects.descriptionPlaceholder")}
            />
          </div>
          <div className="form-group">
            <label className="label" htmlFor="p-repo">
              {t("projects.repoUrl")}
            </label>
            <input
              id="p-repo"
              type="url"
              className="input"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder={t("projects.repoUrlPlaceholder")}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="form-group">
              <label className="label" htmlFor="p-src">
                {t("projects.sourceLang")}
              </label>
              <select
                id="p-src"
                className="select"
                value={sourceLanguage}
                onChange={(e) => setSourceLanguage(e.target.value)}
              >
                {LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="label" htmlFor="p-target">
                {t("projects.targetStack")}
              </label>
              <select
                id="p-target"
                className="select"
                value={targetStack}
                onChange={(e) => setTargetStack(e.target.value)}
              >
                {STACKS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2 border-t border-border-primary">
            <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? t("common.saving") : editing ? t("common.save") : t("common.create")}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}