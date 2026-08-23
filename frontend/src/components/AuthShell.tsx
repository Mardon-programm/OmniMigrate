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
      <div className="relative hidden w-1/2 overflow-hidden border-r border-border bg-black lg:block">
        {/* Aurora mesh */}
        <div className="absolute -left-40 -top-40 h-[480px] w-[480px] rounded-full bg-primary/25 blur-3xl animate-aurora" />
        <div className="absolute -bottom-48 right-0 h-[560px] w-[560px] rounded-full bg-accent/15 blur-3xl animate-aurora-slow" />
        <div className="absolute inset-0 bg-dots opacity-[0.35]" />
        {/* Scanline sweep */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-24 animate-scan bg-gradient-to-b from-transparent via-primary/[0.07] to-transparent" />

        <div className="relative flex h-full flex-col justify-between p-12">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient shadow-glow">
              <ArrowRightLeft className="h-5 w-5 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
              <span className="pointer-events-none absolute -inset-1.5 rounded-2xl bg-primary/30 blur-lg" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white">
              {t("app.name")}
            </span>
            <span className="led ml-1">
              <span className="led-ring bg-success/60" />
              <span className="led-core bg-success shadow-[0_0_8px_rgba(16,185,129,0.9)]" />
            </span>
          </div>

          <div>
            <p className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary/80">
              {t("app.tagline")}
            </p>
            <h2 className="max-w-md text-4xl font-extrabold leading-tight tracking-tight">
              <span className="text-white">{t("auth.brandTitlePre")} </span>
              <span className="text-gradient-animated">{t("auth.brandTitleAccent")}</span>
            </h2>
            <p className="mt-5 max-w-md text-sm leading-relaxed text-slate-400">
              {t("auth.brandSubtitle")}
            </p>

            <ul className="mt-10 space-y-4 stagger">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="group flex items-start gap-4">
                  <div className="rounded-xl bg-gradient-to-br from-primary/50 to-accent/25 p-[1px] transition-transform duration-150 ease-spring group-hover:scale-110">
                    <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-black">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                  <div>
                    <p className="font-mono text-sm font-medium text-slate-100">
                      {t(title)}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                      {t(text)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="font-mono text-xs text-slate-600">{t("footer.text")}</p>
        </div>
      </div>

      <div className="relative flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(640px_420px_at_50%_38%,rgba(16,185,129,0.07),transparent_70%)]" />
        <div className="absolute right-4 top-4 z-10">
          <LanguageSwitcher />
        </div>
        <div className="w-full max-w-md animate-fade-in">{children}</div>
      </div>
    </div>
  );
}
