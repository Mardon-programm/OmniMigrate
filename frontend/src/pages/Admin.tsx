import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Lock, Unlock, Eye, EyeOff, Shield, AlertCircle, CheckCircle2 } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useI18n } from "@/i18n";
import { ApiError } from "@/services/api";

export function Admin() {
  const { login, user, logout } = useAuth();
  const { error: toastError } = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);

  // Check if already admin logged in
  const from = (location.state as { from?: string })?.from ?? "/";

  const handleAdminLogin = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
      // Check if user has admin role
      const currentUser = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      }).then((r) => r.json());
      
      if (currentUser.role === "admin") {
        setIsAdminLoggedIn(true);
        setShowAdminPanel(true);
        toastError("Admin access granted");
      } else {
        await logout();
        toastError("Admin access required");
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.status === 401
            ? "Invalid admin credentials"
            : err.message
          : "Admin login failed";
      toastError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAdminLogout = async () => {
    await logout();
    setIsAdminLoggedIn(false);
    setShowAdminPanel(false);
    setEmail("");
    setPassword("");
  };

  // If already admin, show panel immediately
  if (isAdminLoggedIn || (user?.role === "admin" && !showAdminPanel)) {
    setShowAdminPanel(true);
  }

  if (!showAdminPanel) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-danger/10">
              <Shield className="h-7 w-7 text-danger" />
            </div>
            <h1 className="text-heading-lg font-bold text-text-primary">Admin Access</h1>
            <p className="mt-2 text-body text-text-secondary">
              Enter admin credentials to access the admin panel
            </p>
          </div>

          <form onSubmit={handleAdminLogin} className="card p-6 space-y-5">
            <div className="form-group">
              <label className="label" htmlFor="admin-email">
                {t("admin.email")}
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                <input
                  id="admin-email"
                  type="email"
                  required
                  autoComplete="email"
                  className="input pl-10"
                  placeholder={t("admin.emailPlaceholder")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="label" htmlFor="admin-password">
                {t("admin.password")}
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                <input
                  id="admin-password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  className="input pl-10 pr-10"
                  placeholder={t("admin.passwordPlaceholder")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
                  aria-label={showPassword ? t("admin.hidePassword") : t("admin.showPassword")}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={submitting} className="btn-danger w-full py-3">
              {submitting ? t("admin.signingIn") : t("admin.signIn")}
            </button>

            <p className="flex items-center justify-center gap-2 text-caption text-text-tertiary">
              <AlertCircle className="h-3.5 w-3.5 text-warning" />
              {t("admin.accessNote")}
            </p>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => navigate(from, { replace: true })}
              className="btn-ghost btn-sm"
            >
              <Unlock className="h-4 w-4" />
              {t("admin.backToApp")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Admin Panel
  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="sticky top-0 z-50 border-b border-border-primary bg-bg-secondary/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-danger/10">
                <Shield className="h-5 w-5 text-danger" />
              </div>
              <span className="text-heading-md font-bold text-text-primary">Admin Panel</span>
              <span className="badge-danger">RESTRICTED</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-caption text-text-tertiary">
                {t("admin.loggedInAs")} {user?.email}
              </span>
              <button onClick={handleAdminLogout} className="btn-ghost btn-sm">
                <Unlock className="h-4 w-4" />
                {t("admin.logout")}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Stats Cards */}
          <div className="grid gap-4 sm:grid-cols-3 lg:col-span-3">
            <AdminStatCard
              label={t("admin.stats.totalUsers")}
              value="1,234"
              icon={<Shield className="h-5 w-5" />}
              trend={{ value: 12, label: t("admin.stats.vsLastMonth") }}
            />
            <AdminStatCard
              label={t("admin.stats.activeSubscriptions")}
              value="567"
              icon={<Shield className="h-5 w-5" />}
              trend={{ value: 8, label: t("admin.stats.vsLastMonth") }}
            />
            <AdminStatCard
              label={t("admin.stats.migrationsToday")}
              value="89"
              icon={<Shield className="h-5 w-5" />}
              trend={{ value: -3, label: t("admin.stats.vsLastMonth") }}
            />
          </div>

          {/* Quick Actions */}
          <div className="lg:col-span-2 space-y-6">
            <section className="card p-6">
              <h2 className="text-heading-md font-semibold text-text-primary mb-4">
                {t("admin.quickActions")}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <AdminActionButton
                  label={t("admin.actions.viewAllUsers")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/users")}
                />
                <AdminActionButton
                  label={t("admin.actions.viewAllJobs")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/jobs")}
                />
                <AdminActionButton
                  label={t("admin.actions.viewBilling")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/billing")}
                />
                <AdminActionButton
                  label={t("admin.actions.systemHealth")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/health")}
                />
                <AdminActionButton
                  label={t("admin.actions.viewLogs")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/logs")}
                />
                <AdminActionButton
                  label={t("admin.actions.settings")}
                  icon={<Shield className="h-5 w-5" />}
                  onClick={() => navigate("/admin/settings")}
                />
              </div>
            </section>

            {/* Recent Activity */}
            <section className="card p-6">
              <h2 className="text-heading-md font-semibold text-text-primary mb-4">
                {t("admin.recentActivity")}
              </h2>
              <div className="space-y-3">
                {[
                  { action: "New user registered", user: "john@example.com", time: "2 min ago", type: "user" },
                  { action: "Migration completed", user: "Project Alpha", time: "15 min ago", type: "job" },
                  { action: "Subscription upgraded", user: "Acme Corp", time: "1 hour ago", type: "billing" },
                  { action: "Failed migration", user: "Project Beta", time: "3 hours ago", type: "error" },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary/50">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                        item.type === "error" ? "bg-danger/10 text-danger" :
                        item.type === "billing" ? "bg-warning/10 text-warning" :
                        "bg-brand-emerald/10 text-brand-emerald"
                      }`}>
                        <CheckCircle2 className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">{item.action}</p>
                        <p className="text-caption text-text-tertiary">{item.user}</p>
                      </div>
                    </div>
                    <span className="text-caption text-text-tertiary">{item.time}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* System Info */}
          <div className="space-y-6">
            <section className="card p-6">
              <h2 className="text-heading-md font-semibold text-text-primary mb-4">
                {t("admin.systemInfo")}
              </h2>
              <dl className="space-y-3">
                <AdminInfoRow label={t("admin.system.version")} value="1.0.0" />
                <AdminInfoRow label={t("admin.system.environment")} value="production" />
                <AdminInfoRow label={t("admin.system.uptime")} value="99.9%" />
                <AdminInfoRow label={t("admin.system.database")} value="PostgreSQL 15" />
                <AdminInfoRow label={t("admin.system.redis")} value="Redis 7 (Upstash)" />
                <AdminInfoRow label={t("admin.system.workers")} value="2 active" />
              </dl>
            </section>

            <section className="card p-6">
              <h2 className="text-heading-md font-semibold text-text-primary mb-4">
                {t("admin.dangerZone")}
              </h2>
              <div className="space-y-3">
                <AdminDangerButton
                  label={t("admin.danger.clearCache")}
                  onClick={() => toastError("Cache cleared")}
                />
                <AdminDangerButton
                  label={t("admin.danger.restartWorkers")}
                  onClick={() => toastError("Workers restarted")}
                />
                <AdminDangerButton
                  label={t("admin.danger.maintenanceMode")}
                  onClick={() => toastError("Maintenance mode toggled")}
                />
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function AdminStatCard({
  label,
  value,
  icon,
  trend,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-caption text-text-tertiary">{label}</p>
          <p className="mt-1 font-mono text-heading-lg font-bold text-text-primary">{value}</p>
          {trend && (
            <p className="mt-2 flex items-center gap-1.5 text-caption">
              <span className={`font-medium ${trend.value >= 0 ? "text-success-text" : "text-danger-text"}`}>
                {trend.value >= 0 ? "+" : ""}{trend.value}%
              </span>
              <span className="text-text-tertiary">{trend.label}</span>
            </p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-emerald/10 text-brand-emerald">
          {icon}
        </div>
      </div>
    </div>
  );
}

function AdminActionButton({
  label,
  icon,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="card-interactive p-4 text-left"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-emerald/10 text-brand-emerald mb-3">
        {icon}
      </div>
      <p className="font-medium text-text-primary">{label}</p>
    </button>
  );
}

function AdminInfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border-primary/50 last:border-0">
      <dt className="text-caption text-text-tertiary">{label}</dt>
      <dd className="font-mono text-body-sm text-text-primary">{value}</dd>
    </div>
  );
}

function AdminDangerButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="btn-danger w-full justify-start"
    >
      {label}
    </button>
  );
}