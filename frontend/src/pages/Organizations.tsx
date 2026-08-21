import { useCallback, useEffect, useState } from "react";
import {
  Building2,
  CheckCircle2,
  Plus,
  Shield,
  Trash2,
  Users,
} from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { AuditLogEntry, OrgMember, Organization } from "@/types";

export function Organizations() {
  const { t } = useI18n();
  const toast = useToast();

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgSlug, setNewOrgSlug] = useState("");
  const [newMemberUserId, setNewMemberUserId] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("member");
  const [creating, setCreating] = useState(false);

  const loadOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const me = await api.me();
      const userOrgs: Organization[] = [];
      const urls = ["/organizations"];
      for (const url of urls) {
        try {
          const res = await api.getOrg(Number(url));
          userOrgs.push(res);
        } catch {
          // skip
        }
      }
      void me;
      setOrgs(userOrgs);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  const loadOrgDetails = useCallback(async (orgId: number) => {
    try {
      const [membersRes, logsRes] = await Promise.all([
        api.listOrgMembers(orgId),
        api.listAuditLogs(orgId),
      ]);
      setMembers(membersRes);
      setAuditLogs(logsRes);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      void loadOrgDetails(selectedOrg.id);
    }
  }, [selectedOrg, loadOrgDetails]);

  const onCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim() || !newOrgSlug.trim()) return;
    setCreating(true);
    try {
      const org = await api.createOrg({
        name: newOrgName.trim(),
        slug: newOrgSlug.trim(),
      });
      setOrgs((prev) => [...prev, org]);
      setSelectedOrg(org);
      setShowCreateModal(false);
      setNewOrgName("");
      setNewOrgSlug("");
      toast.success(t("organizations.created"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    } finally {
      setCreating(false);
    }
  };

  const onAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !newMemberUserId.trim()) return;
    try {
      const member = await api.addOrgMember(selectedOrg.id, {
        user_id: Number(newMemberUserId),
        role: newMemberRole,
      });
      setMembers((prev) => [...prev, member]);
      setShowAddMemberModal(false);
      setNewMemberUserId("");
      setNewMemberRole("member");
      toast.success(t("organizations.memberAdded"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  };

  const onRemoveMember = async (member: OrgMember) => {
    if (!selectedOrg) return;
    if (!window.confirm(t("organizations.removeConfirm"))) return;
    try {
      await api.removeOrgMember(selectedOrg.id, member.id);
      setMembers((prev) => prev.filter((m) => m.id !== member.id));
      toast.success(t("organizations.removed"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  };

  const onUpdateRole = async (member: OrgMember, newRole: string) => {
    if (!selectedOrg) return;
    try {
      const updated = await api.updateOrgMember(selectedOrg.id, member.id, { role: newRole });
      setMembers((prev) => prev.map((m) => (m.id === member.id ? updated : m)));
      toast.success(t("organizations.memberUpdated"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner label={t("projects.loading")} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("organizations.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("organizations.subtitle")}</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          <Plus className="h-4 w-4" />
          {t("organizations.create")}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-3">
          {orgs.length === 0 && (
            <div className="card text-center text-sm text-muted">
              <Building2 className="mx-auto mb-2 h-8 w-8 opacity-50" />
              <p>{t("organizations.noMembers")}</p>
            </div>
          )}
          {orgs.map((org) => (
            <button
              key={org.id}
              onClick={() => setSelectedOrg(org)}
              className={`card w-full text-left transition-all hover:border-primary/50 ${
                selectedOrg?.id === org.id ? "border-primary shadow-glow-sm" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-medium text-white">{org.name}</p>
                  <p className="text-xs text-muted">/{org.slug}</p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="space-y-6 lg:col-span-2">
          {selectedOrg && (
            <>
              <div className="card">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="flex items-center gap-2 text-base font-semibold text-white">
                    <Users className="h-4 w-4 text-primary" />
                    {t("organizations.members")}
                  </h2>
                  <button
                    onClick={() => setShowAddMemberModal(true)}
                    className="btn-secondary px-3 py-1.5 text-xs"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {t("organizations.addMember")}
                  </button>
                </div>
                {members.length === 0 ? (
                  <p className="text-sm text-muted">{t("organizations.noMembers")}</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs text-muted">
                          <th className="pb-2 pr-4">ID</th>
                          <th className="pb-2 pr-4">{t("organizations.role")}</th>
                          <th className="pb-2 pr-4">{t("admin.active")}</th>
                          <th className="pb-2" />
                        </tr>
                      </thead>
                      <tbody>
                        {members.map((m) => (
                          <tr key={m.id} className="border-b border-border/50">
                            <td className="py-2.5 pr-4 font-mono text-xs text-slate-300">
                              {m.user_id}
                            </td>
                            <td className="py-2.5 pr-4">
                              <select
                                value={m.role}
                                onChange={(e) => void onUpdateRole(m, e.target.value)}
                                className="input max-w-[140px] py-1 text-xs"
                                disabled={m.role === "owner"}
                              >
                                <option value="owner">Owner</option>
                                <option value="admin">Admin</option>
                                <option value="member">Member</option>
                                <option value="viewer">Viewer</option>
                              </select>
                            </td>
                            <td className="py-2.5 pr-4">
                              {m.is_active ? (
                                <CheckCircle2 className="h-4 w-4 text-success" />
                              ) : (
                                <span className="text-xs text-muted">-</span>
                              )}
                            </td>
                            <td className="py-2.5">
                              {m.role !== "owner" && (
                                <button
                                  onClick={() => void onRemoveMember(m)}
                                  className="rounded p-1 text-muted transition-colors hover:bg-surface2 hover:text-danger"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="card">
                <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-white">
                  <Shield className="h-4 w-4 text-accent" />
                  {t("organizations.auditLogsTitle")}
                </h2>
                {auditLogs.length === 0 ? (
                  <p className="text-sm text-muted">{t("organizations.noAuditLogs")}</p>
                ) : (
                  <div className="max-h-[300px] overflow-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs text-muted">
                          <th className="pb-2 pr-4">{t("organizations.action")}</th>
                          <th className="pb-2 pr-4">{t("organizations.resource")}</th>
                          <th className="pb-2 pr-4">{t("organizations.user")}</th>
                          <th className="pb-2">{t("organizations.date")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {auditLogs.map((log) => (
                          <tr key={log.id} className="border-b border-border/50">
                            <td className="py-2 pr-4">
                              <span className="rounded bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">
                                {log.action}
                              </span>
                            </td>
                            <td className="py-2 pr-4 text-xs text-slate-300">
                              {log.resource_type}
                              {log.resource_id ? `#${log.resource_id}` : ""}
                            </td>
                            <td className="py-2 pr-4 font-mono text-xs text-muted">
                              {log.user_id ?? "-"}
                            </td>
                            <td className="py-2 text-xs text-muted">
                              {new Date(log.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card mx-4 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold text-white">{t("organizations.createTitle")}</h3>
            <form onSubmit={(e) => void onCreateOrg(e)} className="space-y-3">
              <div>
                <label className="label">{t("organizations.name")}</label>
                <input
                  className="input"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder={t("organizations.namePlaceholder")}
                  required
                />
              </div>
              <div>
                <label className="label">{t("organizations.slug")}</label>
                <input
                  className="input"
                  value={newOrgSlug}
                  onChange={(e) => setNewOrgSlug(e.target.value)}
                  placeholder={t("organizations.slugPlaceholder")}
                  required
                />
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

      {showAddMemberModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card mx-4 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold text-white">{t("organizations.addMemberTitle")}</h3>
            <form onSubmit={(e) => void onAddMember(e)} className="space-y-3">
              <div>
                <label className="label">{t("organizations.userId")}</label>
                <input
                  type="number"
                  className="input"
                  value={newMemberUserId}
                  onChange={(e) => setNewMemberUserId(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">{t("organizations.role")}</label>
                <select
                  className="input"
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value)}
                >
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="btn-secondary"
                >
                  {t("common.cancel")}
                </button>
                <button type="submit" className="btn-primary">
                  {t("organizations.addMember")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
