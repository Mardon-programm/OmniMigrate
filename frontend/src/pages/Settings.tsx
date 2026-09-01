import { useState } from "react";
import { Key, ShieldCheck, User as UserIcon } from "lucide-react";

import { Spinner } from "@/components/Spinner";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

function MfaSection() {
  const { t } = useI18n();
  const toast = useToast();
  const { user, refreshUser } = useAuth();
  const mfaEnabled = user?.mfa_enabled ?? false;

  const [stage, setStage] = useState<"idle" | "setup">("idle");
  const [secret, setSecret] = useState("");
  const [otpauthUri, setOtpauthUri] = useState("");
  const [enableCode, setEnableCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [busy, setBusy] = useState(false);

  const startSetup = async () => {
    setBusy(true);
    try {
      const res = await api.mfaSetup();
      setSecret(res.secret);
      setOtpauthUri(res.otpauth_uri);
      setStage("setup");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  };

  const confirmEnable = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.mfaEnable(enableCode);
      await refreshUser();
      toast.success(t("settings.mfa.enabled"));
      setStage("idle");
      setEnableCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("settings.mfa.invalidCode"));
    } finally {
      setBusy(false);
    }
  };

  const confirmDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.mfaDisable(disablePassword, disableCode);
      await refreshUser();
      toast.success(t("settings.mfa.disabled"));
      setDisablePassword("");
      setDisableCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("settings.mfa.invalidCode"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card space-y-4">
      <h2 className="flex items-center gap-2 text-base font-semibold text-white">
        <ShieldCheck className={`h-4 w-4 ${mfaEnabled ? "text-success" : "text-warning"}`} />
        {t("settings.mfa.title")}
        <span
          className={`ml-auto rounded-full border px-2 py-0.5 text-[11px] font-medium ${
            mfaEnabled
              ? "border-success/40 bg-success/10 text-success"
              : "border-border bg-surface2 text-muted"
          }`}
        >
          {mfaEnabled ? t("settings.mfa.on") : t("settings.mfa.off")}
        </span>
      </h2>

      {!mfaEnabled && stage === "idle" && (
        <div className="space-y-3">
          <p className="text-sm leading-relaxed text-muted">{t("settings.mfa.desc")}</p>
          <button type="button" onClick={() => void startSetup()} disabled={busy} className="btn-primary">
            {busy ? <Spinner size="sm" /> : t("settings.mfa.enable")}
          </button>
        </div>
      )}

      {!mfaEnabled && stage === "setup" && (
        <form onSubmit={(e) => void confirmEnable(e)} className="space-y-4">
          <p className="text-sm text-muted">{t("settings.mfa.scanPrompt")}</p>
          <div className="rounded-xl border border-border bg-black/50 p-3 font-mono text-xs">
            <p className="mb-2 text-muted">{t("settings.mfa.manualKey")}</p>
            <code className="break-all text-primary">{secret}</code>
            <p className="mt-3 truncate text-accent/80">{otpauthUri}</p>
          </div>
          <div>
            <label className="label" htmlFor="mfa-enable-code">
              {t("settings.mfa.enterCode")}
            </label>
            <input
              id="mfa-enable-code"
              type="text"
              inputMode="numeric"
              required
              maxLength={6}
              autoFocus
              className="input max-w-[200px] font-mono tracking-[0.3em]"
              placeholder="000000"
              value={enableCode}
              onChange={(e) => setEnableCode(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <button type="submit" disabled={busy} className="btn-primary">
            {busy ? <Spinner size="sm" /> : t("settings.mfa.verifyAndEnable")}
          </button>
        </form>
      )}

      {mfaEnabled && (
        <form onSubmit={(e) => void confirmDisable(e)} className="space-y-4">
          <p className="text-sm text-muted">{t("settings.mfa.disableDesc")}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="mfa-disable-pw">
                {t("settings.currentPassword")}
              </label>
              <input
                id="mfa-disable-pw"
                type="password"
                required
                autoComplete="current-password"
                className="input"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="mfa-disable-code">
                {t("settings.mfa.enterCode")}
              </label>
              <input
                id="mfa-disable-code"
                type="text"
                inputMode="numeric"
                required
                maxLength={6}
                className="input font-mono tracking-[0.3em]"
                placeholder="000000"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ""))}
              />
            </div>
          </div>
          <button type="submit" disabled={busy} className="btn-danger">
            {busy ? <Spinner size="sm" /> : t("settings.mfa.disable")}
          </button>
        </form>
      )}
    </div>
  );
}

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

      <MfaSection />

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
