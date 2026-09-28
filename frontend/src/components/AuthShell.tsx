import type { ReactNode } from "react";
import {
  ArrowRightLeft,
  ScanSearch,
  Wand2,
  FlaskConical,
  HeartPulse,
} from "lucide-react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useI18n } from "@/i18n";

const FEATURES = [
  { icon: ScanSearch, title: "auth.feature1Title", text: "auth.feature1Text" },
  { icon: Wand2, title: "auth.feature2Title", text: "auth.feature2Text" },
  { icon: FlaskConical, title: "auth.feature3Title", text: "auth.feature3Text" },
  { icon: HeartPulse, title: "auth.feature4Title", text: "auth.feature4Text" },
];

export function AuthShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen bg-bg-primary">
      <div className="relative hidden w-1/2 overflow-hidden border-r border-border-primary lg:block">
        <div className="absolute inset-0 bg-mesh-gradient" />
        <div className="absolute inset-0 bg-noise opacity-[0.03]" />

        <div className="relative flex h-full flex-col justify-between p-8 sm:p-12">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient shadow-[0_4px_20px_-8px_rgb(16_185_129_/_0.4)]">
              <ArrowRightLeft className="h-5 w-5 text-white" />
            </div>
            <span className="text-heading-lg font-bold text-text-primary">
              {t("app.name")}
            </span>
            <span className="status-indicator">
              <span className="status-indicator__dot">
                <span className="relative block h-2 w-2 rounded-full bg-brand-emerald shadow-[0_0_8px_rgb(16_185_129_/_0.9)]" />
              </span>
            </span>
          </div>

          <div>
            <p className="mb-3 font-mono text-overline text-brand-emerald/80">{t("app.tagline")}</p>
            <h2 className="max-w-md text-display-sm font-extrabold tracking-tight">
              <span className="text-text-primary">{t("auth.brandTitlePre")} </span>
              <span className="text-gradient-emerald">{t("auth.brandTitleAccent")}</span>
            </h2>
            <p className="mt-5 max-w-md text-body text-text-secondary">{t("auth.brandSubtitle")}</p>

            <ul className="mt-10 space-y-4 stagger">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="group flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-emerald/10 border border-brand-emerald/20 transition-transform duration-fast group-hover:scale-105">
                    <Icon className="h-5 w-5 text-brand-emerald" />
                  </div>
                  <div>
                    <p className="font-mono text-body-sm font-medium text-text-primary">{t(title)}</p>
                    <p className="mt-0.5 text-caption text-text-tertiary">{t(text)}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="font-mono text-caption text-text-tertiary">{t("footer.text")}</p>
        </div>
      </div>

      <div className="relative flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="absolute right-4 top-4 z-10">
          <LanguageSwitcher />
        </div>
        <div className="w-full max-w-md animate-fade-in">{children}</div>
      </div>
    </div>
  );
}