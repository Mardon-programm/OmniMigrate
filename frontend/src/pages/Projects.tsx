import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { FolderGit2, Pencil, Plus, Trash2 } from "lucide-react";

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

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" label={t("projects.loading")} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("projects.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("projects.subtitle")}</p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus className="h-4 w-4" />
          {t("projects.newProject")}
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="card">
          <EmptyState
            title={t("projects.emptyTitle")}
            description={t("projects.emptyDesc")}
            action={
              <button onClick={openCreate} className="btn-primary">
                <FolderGit2 className="h-4 w-4" />
                {t("projects.createProject")}
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className="card-hover group cursor-pointer"
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient-soft">
                    <FolderGit2 className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">{project.name}</h3>
                    <p className="text-xs text-muted">
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
                    className="rounded-lg p-1.5 text-muted hover:bg-surface2 hover:text-slate-200"
                    title={t("projects.edit")}
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      void onDelete(project);
                    }}
                    className="rounded-lg p-1.5 text-muted hover:bg-surface2 hover:text-danger"
                    title={t("projects.delete")}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {project.description && (
                <p className="mt-3 line-clamp-2 text-sm text-muted">{project.description}</p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-md bg-accent/10 px-2 py-0.5 text-xs text-accent">
                  {project.source_language}
                </span>
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs text-primary">
                  → {project.target_stack}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? t("projects.editTitle") : t("projects.createTitle")}
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
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
            />
          </div>
          <div>
            <label className="label" htmlFor="p-desc">
              {t("projects.description")}
            </label>
            <textarea
              id="p-desc"
              className="input min-h-[80px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("projects.descriptionPlaceholder")}
            />
          </div>
          <div>
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
            <div>
              <label className="label" htmlFor="p-src">
                {t("projects.sourceLang")}
              </label>
              <select
                id="p-src"
                className="input"
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
            <div>
              <label className="label" htmlFor="p-target">
                {t("projects.targetStack")}
              </label>
              <select
                id="p-target"
                className="input"
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
          <div className="flex justify-end gap-3 pt-2">
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
