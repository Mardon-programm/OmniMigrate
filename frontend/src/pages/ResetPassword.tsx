import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRightLeft, CheckCircle2, Lock } from "lucide-react";

import { AuthShell } from "@/components/AuthShell";
import { useToast } from "@/context/ToastContext";
import { api, ApiError } from "@/services/api";
import { useI18n } from "@/i18n";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { error: toastError } = useToast();
  const { t } = useI18n();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toastError(t("auth.passwordTooShort"));
      return;
    }
    if (password !== confirm) {
      toastError(t("settings.passwordsMismatch"));
      return;
    }
    setSubmitting(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t("auth.resetFailed");
      toastError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <AuthShell>
        <div className="card space-y-4 !bg-surface/70 text-center">
          <p className="text-sm text-muted">{t("auth.resetNoToken")}</p>
          <Link to="/forgot-password" className="btn-primary inline-block w-full py-2.5 text-center">
            {t("auth.requestNewLink")}
          </Link>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient shadow-glow lg:hidden">
          <ArrowRightLeft className="h-7 w-7 text-white" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">{t("auth.resetTitle")}</h1>
          <p className="mt-1 text-sm text-muted">{t("auth.resetSubtitle")}</p>
        </div>
      </div>

      {done ? (
        <div className="card space-y-4 !bg-surface/70 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-success" />
          <p className="text-sm text-muted">{t("auth.resetSuccess")}</p>
          <Link to="/login" className="btn-primary inline-block w-full py-2.5 text-center">
            {t("auth.backToLogin")}
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="card space-y-4 !bg-surface/70">
          <div>
            <label className="label" htmlFor="password">
              {t("auth.newPassword")}
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                className="input pl-9"
                placeholder={t("auth.passwordHint")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="label" htmlFor="confirm">
              {t("settings.confirmPassword")}
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                id="confirm"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                className="input pl-9"
                placeholder={t("auth.passwordHint")}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </div>
          </div>

          <button type="submit" disabled={submitting} className="btn-primary w-full py-2.5">
            {submitting ? t("auth.resetting") : t("auth.resetPassword")}
          </button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-muted">
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t("auth.backToLogin")}
        </Link>
      </p>
    </AuthShell>
  );
}
