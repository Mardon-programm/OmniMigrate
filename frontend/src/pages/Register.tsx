import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRightLeft, Lock, Mail, User } from "lucide-react";

import { AuthShell } from "@/components/AuthShell";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { ApiError } from "@/services/api";
import { useI18n } from "@/i18n";

export function Register() {
  const { register } = useAuth();
  const { error: toastError } = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toastError(t("auth.passwordTooShort"));
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      navigate("/", { replace: true });
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409
          ? err.message
          : t("auth.registrationFailed");
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
          <h1 className="text-2xl font-bold text-white">{t("auth.registerTitle")}</h1>
          <p className="mt-1 text-sm text-muted">{t("auth.registerSubtitle")}</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="card space-y-4 !bg-surface/70">
        <div>
          <label className="label" htmlFor="fullName">
            {t("auth.fullName")}
          </label>
          <div className="relative">
            <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              id="fullName"
              type="text"
              required
              autoComplete="name"
              className="input pl-9"
              placeholder={t("auth.fullNamePlaceholder")}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
        </div>

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

        <div>
          <label className="label" htmlFor="password">
            {t("auth.password")}
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

        <button type="submit" disabled={submitting} className="btn-primary w-full py-2.5">
          {submitting ? t("auth.creatingAccount") : t("auth.createAccount")}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t("auth.signInLink")}
        </Link>
      </p>
    </AuthShell>
  );
}
