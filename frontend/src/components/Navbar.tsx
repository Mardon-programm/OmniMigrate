import { Link, NavLink, useNavigate } from "react-router-dom";
import { LogOut, Settings, TerminalSquare, ChevronDown } from "lucide-react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { useState, useRef, useEffect } from "react";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const NAV_ITEMS = [
    { to: "/", label: t("nav.dashboard"), end: true },
    { to: "/projects", label: t("nav.projects"), end: false },
    { to: "/upload", label: t("nav.upload"), end: false },
    { to: "/autonomous", label: t("nav.autonomous"), end: false },
    { to: "/organizations", label: t("nav.organizations"), end: false },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }

    if (userMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userMenuOpen]);

  return (
    <header className="sticky top-0 z-sticky border-b border-border-primary bg-bg-secondary/80 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <Link to="/" className="group flex items-center gap-3" aria-label={t("app.name")}>
            <img
              src="/logo.png"
              alt={t("app.name")}
              className="h-9 w-9 rounded-xl transition-all duration-fast group-hover:scale-105"
            />
            <div className="hidden sm:block leading-tight">
              <span className="block text-heading-sm font-semibold text-text-primary">
                {t("app.name")}
              </span>
              <span className="block text-overline text-text-tertiary">
                {t("app.tagline")}
              </span>
            </div>
            <span
              title={t("nav.systemNominal")}
              className="status-indicator hidden md:flex"
            >
              <span className="status-indicator__dot">
                <span className="relative block h-2 w-2 rounded-full bg-brand-emerald shadow-[0_0_8px_rgb(16_185_129_/_0.9)]" />
              </span>
            </span>
          </Link>

          {user && (
            <nav className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-1 rounded-xl border border-border-primary bg-bg-tertiary/50 p-1">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `nav-pill ${isActive ? "nav-pill-active" : "nav-pill-inactive"}`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>

              <div className="flex items-center gap-2">
                {user.role === "admin" && (
                  <NavLink
                    to="/admin"
                    className={({ isActive }) =>
                      `nav-pill ${isActive ? "nav-pill-active" : "nav-pill-inactive"}`
                    }
                  >
                    {t("nav.admin")}
                  </NavLink>
                )}

                <LanguageSwitcher compact />

                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="flex items-center gap-2 rounded-xl px-3 py-1.5 text-body-sm font-medium text-text-secondary transition-colors hover:text-text-primary hover:bg-bg-tertiary focus-ring"
                    aria-expanded={userMenuOpen}
                    aria-haspopup="true"
                  >
                    <div className="hidden sm:block text-right leading-tight">
                      <span className="block max-w-[140px] truncate text-text-primary">
                        {user.full_name}
                      </span>
                      <span className="block text-overline text-brand-emeraldLight">
                        {t(`nav.role.${user.role}`)}
                      </span>
                    </div>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-gradient-soft">
                      <TerminalSquare className="h-4 w-4 text-brand-emeraldLight" />
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 text-text-tertiary transition-transform ${userMenuOpen ? "rotate-180" : ""}`}
                      aria-hidden="true"
                    />
                  </button>

                  {userMenuOpen && (
                    <div className="dropdown">
                      <div className="px-3 py-2 border-b border-border-primary">
                        <p className="text-body-sm font-medium text-text-primary">{user.full_name}</p>
                        <p className="text-caption text-text-tertiary">{user.email}</p>
                      </div>
                      <NavLink
                        to="/settings"
                        className="dropdown-item"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <Settings className="h-4 w-4" />
                        {t("nav.settings")}
                      </NavLink>
                      <div className="dropdown-divider" />
                      <button
                        onClick={handleLogout}
                        className="dropdown-item text-danger w-full text-left"
                      >
                        <LogOut className="h-4 w-4" />
                        {t("nav.logout")}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}

export function BrandFooter() {
  const { t } = useI18n();
  return (
    <div className="mt-12 flex items-center justify-center gap-2 pb-6 text-caption text-text-tertiary">
      <TerminalSquare className="h-3.5 w-3.5 text-brand-emerald/70" />
      {t("footer.text")}
    </div>
  );
}