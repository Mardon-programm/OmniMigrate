import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRightLeft, CheckCircle2, Mail } from "lucide-react";

import { AuthShell } from "@/components/AuthShell";
import { useToast } from "@/context/ToastContext";
import { api, ApiError } from "@/services/api";
import { useI18n } from "@/i18n";

export function ForgotPassword() {
  const { error: toastError } = useToast();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t("auth.forgotFailed");
      toastError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient shadow-glow lg:hidden">
          <ArrowRightLeft className="h-7 w-7 text-white" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">{t("auth.forgotTitle")}</h1>
          <p className="mt-1 text-sm text-muted">{t("auth.forgotSubtitle")}</p>
        </div>
      </div>

      {sent ? (
        <div className="card space-y-4 !bg-surface/70 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-success" />
          <p className="text-sm text-muted">{t("auth.forgotSent")}</p>
          <Link
            to="/login"
            className="btn-primary inline-block w-full py-2.5 text-center"
          >
            {t("auth.backToLogin")}
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="card space-y-4 !bg-surface/70">
          <div>
            <label className="label" htmlFor="email">
              {t("auth.email")}
            </label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="input pl-9"
                placeholder={t("auth.emailPlaceholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <button type="submit" disabled={submitting} className="btn-primary w-full py-2.5">
            {submitting ? t("auth.sending") : t("auth.sendResetLink")}
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
