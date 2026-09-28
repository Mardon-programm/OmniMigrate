import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRightLeft, Lock, Mail, ShieldCheck, Smartphone, Eye, EyeOff } from "lucide-react";

import { AuthShell } from "@/components/AuthShell";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { ApiError } from "@/services/api";
import { useI18n } from "@/i18n";

export function Login() {
  const { login } = useAuth();
  const { error: toastError } = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const from = (location.state as { from?: string })?.from ?? "/";

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password, mfaRequired ? mfaCode : undefined);
      navigate(from, { replace: true });
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 401 &&
        /mfa code required/i.test(err.message)
      ) {
        setMfaRequired(true);
        toastError(t("auth.mfaCodeRequired"));
        return;
      }
      const message =
        err instanceof ApiError
          ? err.status === 401
            ? /invalid mfa/i.test(err.message)
              ? t("auth.mfaInvalid")
              : t("auth.loginInvalid")
            : err.message
          : t("auth.loginFailed");
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
        <h1 className="text-heading-lg font-bold text-text-primary">{t("auth.welcomeTitle")}</h1>
        <p className="mt-2 text-body text-text-secondary">{t("auth.welcomeSubtitle")}</p>
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-5">
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
              autoComplete="current-password"
              className="input pl-10 pr-10"
              placeholder={t("auth.passwordPlaceholder")}
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
          <Link to="/forgot-password" className="mt-1.5 block text-right text-caption text-brand-emeraldLight hover:underline">
            {t("auth.forgotPassword")}
          </Link>
        </div>

        {mfaRequired && (
          <div className="form-group">
            <label className="label" htmlFor="mfa-code">
              {t("auth.mfaCode")}
            </label>
            <div className="relative">
              <Smartphone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-emerald" />
              <input
                id="mfa-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                autoFocus
                required
                maxLength={6}
                className="input pl-10 font-mono tracking-[0.3em] text-code"
                placeholder="000000"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ""))}
              />
            </div>
            <p className="form-hint">{t("auth.mfaHint")}</p>
          </div>
        )}

        <button type="submit" disabled={submitting} className="btn-primary w-full py-3">
          {submitting ? t("auth.signingIn") : mfaRequired ? t("auth.verifyCode") : t("auth.signIn")}
        </button>

        <p className="flex items-center justify-center gap-2 text-caption text-text-tertiary">
          <ShieldCheck className="h-3.5 w-3.5 text-success-text shrink-0" />
          {t("auth.securityNote")}
        </p>
      </form>

      <p className="mt-6 text-center text-body-sm text-text-tertiary">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="font-medium text-brand-emeraldLight hover:underline">
          {t("auth.createOne")}
        </Link>
      </p>
    </AuthShell>
  );
}