import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRightLeft, Lock, Mail, User, Eye, EyeOff } from "lucide-react";

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
  const [showPassword, setShowPassword] = useState(false);

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
      <div className="mb-8 text-center">
        <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient shadow-[0_4px_20px_-8px_rgb(16_185_129_/_0.4)]">
          <ArrowRightLeft className="h-7 w-7 text-white" />
        </div>
        <h1 className="text-heading-lg font-bold text-text-primary">{t("auth.registerTitle")}</h1>
        <p className="mt-2 text-body text-text-secondary">{t("auth.registerSubtitle")}</p>
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-5">
        <div className="form-group">
          <label className="label" htmlFor="fullName">
            {t("auth.fullName")}
          </label>
          <div className="relative">
            <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <input
              id="fullName"
              type="text"
              required
              autoComplete="name"
              className="input pl-10"
              placeholder={t("auth.fullNamePlaceholder")}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
        </div>

        <div className="form-group">
          <label className="label" htmlFor="email">
            {t("auth.email")}
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="input pl-10"
              placeholder={t("auth.emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </div>

        <div className="form-group">
          <label className="label" htmlFor="password">
            {t("auth.password")}
          </label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              required
              minLength={8}
              autoComplete="new-password"
              className="input pl-10 pr-10"
              placeholder={t("auth.passwordHint")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
              aria-label={showPassword ? t("auth.hidePassword") : t("auth.showPassword")}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
          {submitting ? t("auth.creatingAccount") : t("auth.createAccount")}
        </button>
      </form>

      <p className="mt-6 text-center text-body-sm text-text-tertiary">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-brand-emeraldLight hover:underline">
          {t("auth.signInLink")}
        </Link>
      </p>
    </AuthShell>
  );
}