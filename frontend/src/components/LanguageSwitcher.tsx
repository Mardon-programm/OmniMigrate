import { Languages } from "lucide-react";

import { useI18n } from "@/i18n";
import { LOCALES, LOCALE_LABELS } from "@/i18n/translations";

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className="flex items-center gap-1 rounded-xl border border-border bg-surface2/70 p-1">
      <Languages className="ml-1.5 mr-0.5 h-3.5 w-3.5 text-muted" />
      {LOCALES.map((code) => (
        <button
          key={code}
          onClick={() => setLocale(code)}
          title={LOCALE_LABELS[code]}
          className={`rounded-lg px-2 py-1 text-xs font-semibold transition-colors ${
            locale === code
              ? "bg-primary/20 text-primary"
              : "text-muted hover:bg-surface2 hover:text-slate-200"
          }`}
        >
          {compact ? code.toUpperCase() : LOCALE_LABELS[code]}
        </button>
      ))}
    </div>
  );
}
