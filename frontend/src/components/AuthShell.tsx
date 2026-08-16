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
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 overflow-hidden lg:block">
        <div className="absolute inset-0 bg-brand-gradient-soft" />
        <div className="absolute inset-0 bg-grid opacity-60" />
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/30 blur-3xl animate-float" />
        <div className="absolute -right-10 bottom-24 h-80 w-80 rounded-full bg-accent/20 blur-3xl animate-float-delayed" />

        <div className="relative flex h-full flex-col justify-between p-12">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient shadow-glow">
              <ArrowRightLeft className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-white">{t("app.name")}</span>
          </div>

          <div>
            <h2 className="max-w-md text-3xl font-bold leading-tight text-white">
              {t("auth.brandTitle")}
            </h2>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300/80">
              {t("auth.brandSubtitle")}
            </p>

            <ul className="mt-8 space-y-4">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                    <Icon className="h-4 w-4 text-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{t(title)}</p>
                    <p className="text-xs text-slate-400">{t(text)}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-slate-500">{t("footer.text")}</p>
        </div>
      </div>

      <div className="relative flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="absolute right-4 top-4">
          <LanguageSwitcher />
        </div>
        <div className="w-full max-w-md animate-fade-in">{children}</div>
      </div>
    </div>
  );
}
