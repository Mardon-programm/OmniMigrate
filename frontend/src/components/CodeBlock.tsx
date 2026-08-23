import { useMemo, useState } from "react";
import { Copy, Check, Terminal } from "lucide-react";

import { useI18n } from "@/i18n";

interface CodeBlockProps {
  code: string;
  language?: string;
  maxHeight?: string;
  title?: string;
}

/** Color-code pipeline stage tags inside terminal output. */
const TAG_STYLES: Array<[RegExp, string]> = [
  [/^\s*\[?AST[^\]]*\]?/i, "text-accent"],
  [/self.?heal/i, "text-healing"],
];

function lineTone(line: string): string {
  if (/fail|error|traceback|assert/i.test(line)) return "text-danger";
  if (/passed|ok\b|success/i.test(line)) return "text-success";
  if (/pytest|sandbox/i.test(line)) return "text-warning";
  for (const [pattern, tone] of TAG_STYLES) {
    if (pattern.test(line)) return tone;
  }
  return "text-slate-300";
}

export function CodeBlock({
  code,
  language = "python",
  maxHeight = "560px",
  title,
}: CodeBlockProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable; ignore
    }
  };

  const lines = useMemo(() => code.split("\n"), [code]);

  return (
    <div className="overflow-hidden rounded-2xl border border-border">
      <div className="flex items-center justify-between border-b border-border bg-surface2 px-4 py-2.5">
        <span className="flex items-center gap-2 font-mono text-xs text-muted">
          <Terminal className="h-3.5 w-3.5 text-primary/70" />
          {title ?? language}
        </span>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-muted transition-colors hover:bg-border hover:text-slate-200"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? t("code.copied") : t("code.copy")}
        </button>
      </div>
      <pre
        className="overflow-auto bg-code p-4 font-mono text-xs leading-5"
        style={{ maxHeight }}
      >
        {lines.map((line, i) => (
          <div key={i} className={`flex ${lineTone(line)}`}>
            <span className="w-10 shrink-0 select-none pr-4 text-right text-muted/30">
              {i + 1}
            </span>
            <span className="whitespace-pre">
              {line || " "}
              {i === lines.length - 1 && (
                <span className="ml-0.5 inline-block h-4 w-[7px] translate-y-[3px] animate-blink bg-primary" />
              )}
            </span>
          </div>
        ))}
      </pre>
    </div>
  );
}
