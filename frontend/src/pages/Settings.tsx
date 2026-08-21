import { useState } from "react";
import { Key, User as UserIcon } from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

export function Settings() {
  const { t } = useI18n();
  const toast = useToast();
  const { user } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const onChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (newPassword !== confirmPassword) {
      toast.error(t("settings.passwordsMismatch"));
      return;
    }
    if (newPassword.length < 8) {
      toast.error(t("auth.passwordTooShort"));
      return;
    }
    setSaving(true);
    try {
      await api.changePassword(user.id, {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success(t("settings.passwordChanged"));
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t("settings.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("settings.subtitle")}</p>
      </div>

      <div className="card space-y-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-white">
          <UserIcon className="h-4 w-4 text-primary" />
          {t("settings.profile")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">{t("admin.fullName")}</label>
            <input className="input" value={user?.full_name ?? ""} disabled />
          </div>
          <div>
            <label className="label">{t("settings.email")}</label>
            <input className="input" value={user?.email ?? ""} disabled />
          </div>
          <div>
            <label className="label">{t("settings.role")}</label>
            <input className="input" value={user?.role ?? ""} disabled />
          </div>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-white">
          <Key className="h-4 w-4 text-accent" />
          {t("settings.changePassword")}
        </h2>
        <form onSubmit={(e) => void onChangePassword(e)} className="space-y-4">
          <div>
            <label className="label" htmlFor="current-pw">
              {t("settings.currentPassword")}
            </label>
            <input
              id="current-pw"
              type="password"
              className="input"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="new-pw">
                {t("settings.newPassword")}
              </label>
              <input
                id="new-pw"
                type="password"
                className="input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div>
              <label className="label" htmlFor="confirm-pw">
                {t("settings.confirmPassword")}
              </label>
              <input
                id="confirm-pw"
                type="password"
                className="input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Spinner size="sm" /> : t("settings.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
