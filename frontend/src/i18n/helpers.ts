import type { Locale } from "./translations";

type TranslateFn = (path: string, params?: Record<string, unknown>) => string;

const STAGE_MATCHERS: { key: string; parse?: RegExp }[] = [
  { key: "stage.parsing", parse: /^Parsing source code via AST/ },
  { key: "stage.analyzing", parse: /^Analyzing modernization opportunities/ },
  {
    key: "stage.refactoring",
    parse: /^Running refactoring pipeline \(([^)]+)\)/,
  },
  { key: "stage.verifying", parse: /^Verifying output in sandbox/ },
  { key: "stage.completed", parse: /^Migration completed successfully/ },
  {
    key: "stage.healing",
    parse: /^Self-healing attempt (\d+)\/(\d+)$/,
  },
];

export function localizeStageMessage(message: string, t: TranslateFn): string {
  if (!message) return "";
  for (const { key, parse } of STAGE_MATCHERS) {
    const match = parse?.exec(message);
    if (match) {
      if (key === "stage.refactoring" && match[1]) {
        const provider =
          match[1] === "local-rule-engine" ? "stage.localEngine" : "stage.llmEngine";
        return t(key, { provider: t(provider) });
      }
      if (key === "stage.healing" && match[1] && match[2]) {
        return t(key, { attempt: match[1], max: match[2] });
      }
      return t(key);
    }
  }
  return message;
}

export function formatDate(iso: string, locale: Locale): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const tag = locale === "ru" ? "ru-RU" : "en-US";
  return date.toLocaleString(tag, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
