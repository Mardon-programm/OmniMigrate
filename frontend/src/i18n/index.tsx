import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { LOCALE_LABELS, translations, type Locale, type Translation } from "./translations";

const STORAGE_KEY = "omnimigrate_locale";

export function detectLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored && stored in translations) return stored;
    const nav = navigator.language?.toLowerCase() ?? "";
    return nav.startsWith("ru") ? "ru" : "en";
  } catch {
    return "en";
  }
}

export function resolveKey(path: string, dict: Translation): string {
  const parts = path.split(".");
  let node: unknown = dict;
  for (const part of parts) {
    if (node && typeof node === "object" && part in (node as Record<string, unknown>)) {
      node = (node as Record<string, unknown>)[part];
    } else {
      return path;
    }
  }
  return typeof node === "string" ? node : path;
}

export function interpolate(template: string, params?: Record<string, unknown>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    key in params ? String(params[key]) : `{${key}}`,
  );
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (path: string, params?: Record<string, unknown>) => string;
  dict: Translation;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable; keep in-memory locale
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    const html = document.documentElement;
    html.classList.toggle("lang-ru", locale === "ru");
    html.classList.toggle("lang-en", locale === "en");
  }, [locale]);

  const t = useCallback(
    (path: string, params?: Record<string, unknown>) => {
      const template = resolveKey(path, translations[locale]);
      if (template === path) return path;
      return interpolate(template, params);
    },
    [locale],
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t,
      dict: translations[locale],
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    // Fallback for production when provider hasn't mounted yet
    return {
      locale: "en" as Locale,
      setLocale: () => {},
      t: (path: string, params?: Record<string, unknown>) => path,
      dict: translations.en,
    };
  }
  return ctx;
}

export { LOCALE_LABELS, translations };
