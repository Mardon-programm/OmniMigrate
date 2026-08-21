import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Edit2, Plus, Shield, XCircle } from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { UserRead } from "@/types";

export function Admin() {
  const { t } = useI18n();
  const toast = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState<UserRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRead | null>(null);

  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newRole, setNewRole] = useState("client");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (user && user.role !== "admin") {
      navigate("/");
    }
  }, [user, navigate]);

  const loadUsers = useCallback(async () => {
    try {
      const list = await api.listUsers();
      setUsers(list);
    } catch {
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const onCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const created = await api.createUser({
        email: newEmail.trim(),
        password: newPassword,
        full_name: newFullName.trim(),
        role: newRole,
      });
      setUsers((prev) => [...prev, created]);
      setShowCreateModal(false);
      setNewEmail("");
      setNewPassword("");
      setNewFullName("");
      setNewRole("client");
      toast.success(t("admin.created"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    } finally {
      setCreating(false);
    }
  };

  const onUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      const updated = await api.updateUser(editingUser.id, {
        role: newRole,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setEditingUser(null);
      toast.success(t("admin.updated"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  };

  const onToggleActive = async (u: UserRead) => {
    try {
      const updated = await api.updateUser(u.id, { is_active: !u.is_active });
      setUsers((prev) => prev.map((usr) => (usr.id === updated.id ? updated : usr)));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  };

  if (user?.role !== "admin") {
    return null;
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("admin.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("admin.subtitle")}</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          <Plus className="h-4 w-4" />
          {t("admin.createUser")}
        </button>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="pb-3 pr-4">{t("organizations.user")}</th>
                <th className="pb-3 pr-4">{t("admin.email")}</th>
                <th className="pb-3 pr-4">{t("admin.role")}</th>
                <th className="pb-3 pr-4">{t("admin.active")}</th>
                <th className="pb-3" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-border/50">
                  <td className="py-3 pr-4 font-medium text-white">{u.full_name}</td>
                  <td className="py-3 pr-4 text-slate-300">{u.email}</td>
                  <td className="py-3 pr-4">
                    <span className="rounded bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <button onClick={() => void onToggleActive(u)}>
                      {u.is_active ? (
                        <CheckCircle2 className="h-4 w-4 text-success" />
                      ) : (
                        <XCircle className="h-4 w-4 text-muted" />
                      )}
                    </button>
                  </td>
                  <td className="py-3">
                    <button
                      onClick={() => {
                        setEditingUser(u);
                        setNewRole(u.role);
                      }}
                      className="rounded p-1 text-muted transition-colors hover:bg-surface2 hover:text-primary"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-muted">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card mx-4 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold text-white">{t("admin.createUserTitle")}</h3>
            <form onSubmit={(e) => void onCreateUser(e)} className="space-y-3">
              <div>
                <label className="label">{t("admin.fullName")}</label>
                <input
                  className="input"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">{t("admin.email")}</label>
                <input
                  type="email"
                  className="input"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">{t("admin.password")}</label>
                <input
                  type="password"
                  className="input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>
              <div>
                <label className="label">{t("admin.role")}</label>
                <select
                  className="input"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                >
                  <option value="client">Client</option>
                  <option value="engineer">Engineer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  {t("common.cancel")}
                </button>
                <button type="submit" disabled={creating} className="btn-primary">
                  {creating ? <Spinner size="sm" /> : t("common.create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card mx-4 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold text-white">{t("admin.editUser")}</h3>
            <form onSubmit={(e) => void onUpdateUser(e)} className="space-y-3">
              <p className="text-sm text-muted">{editingUser.email}</p>
              <div>
                <label className="label">{t("admin.role")}</label>
                <select
                  className="input"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                >
                  <option value="client">Client</option>
                  <option value="engineer">Engineer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="btn-secondary"
                >
                  {t("common.cancel")}
                </button>
                <button type="submit" className="btn-primary">
                  <Shield className="h-4 w-4" />
                  {t("common.save")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
