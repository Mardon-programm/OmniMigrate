import { Link, NavLink, useNavigate } from "react-router-dom";
import { ArrowRightLeft, LogOut, Settings, TerminalSquare } from "lucide-react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useI18n();

  const NAV_ITEMS = [
    { to: "/", label: t("nav.dashboard"), end: true },
    { to: "/projects", label: t("nav.projects"), end: false },
    { to: "/upload", label: t("nav.upload"), end: false },
    { to: "/autonomous", label: t("nav.autonomous"), end: false },
    { to: "/organizations", label: t("nav.organizations"), end: false },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="group flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient shadow-glow-sm transition-transform group-hover:scale-105">
            <ArrowRightLeft className="h-5 w-5 text-white" />
          </div>
          <div className="leading-tight">
            <span className="block text-base font-semibold text-white">
              {t("app.name")}
            </span>
            <span className="block text-[10px] uppercase tracking-widest text-muted">
              {t("app.tagline")}
            </span>
          </div>
        </Link>

        {user && (
          <nav className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-xl border border-border/70 bg-surface/60 p-1">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                      isActive
                        ? "bg-primary/15 text-primary shadow-glow-sm"
                        : "text-muted hover:text-slate-200 hover:bg-surface2"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>

            <div className="ml-1 flex items-center gap-2.5">
              {user.role === "admin" && (
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                      isActive
                        ? "bg-primary/15 text-primary shadow-glow-sm"
                        : "text-muted hover:text-slate-200 hover:bg-surface2"
                    }`
                  }
                >
                  {t("nav.admin")}
                </NavLink>
              )}
              <LanguageSwitcher compact />
              <div className="flex items-center gap-3 border-l border-border pl-2.5">
                <div className="text-right leading-tight">
                  <span className="block max-w-[140px] truncate text-sm font-medium text-slate-200">
                    {user.full_name}
                  </span>
                  <span className="block text-[10px] uppercase tracking-wide text-accent">
                    {t(`nav.role.${user.role}`)}
                  </span>
                </div>
                <NavLink
                  to="/settings"
                  className="rounded-lg p-2 text-muted transition-colors hover:bg-surface2 hover:text-primary"
                  title={t("nav.settings")}
                >
                  <Settings className="h-4 w-4" />
                </NavLink>
                <button
                  onClick={handleLogout}
                  className="rounded-lg p-2 text-muted transition-colors hover:bg-surface2 hover:text-danger"
                  title={t("nav.logout")}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}

export function BrandFooter() {
  const { t } = useI18n();
  return (
    <div className="mt-12 flex items-center justify-center gap-2 pb-6 text-xs text-muted">
      <TerminalSquare className="h-3.5 w-3.5 text-primary/70" />
      {t("footer.text")}
    </div>
  );
}
