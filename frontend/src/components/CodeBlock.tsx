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
  [/^\s*\[?AST[^\]]*\]?/i, "text-brand-cyan"],
  [/self.?heal/i, "text-healing"],
];

function lineTone(line: string): string {
  if (/fail|error|traceback|assert/i.test(line)) return "text-danger-text";
  if (/passed|ok\b|success/i.test(line)) return "text-success-text";
  if (/pytest|sandbox/i.test(line)) return "text-warning-text";
  for (const [pattern, tone] of TAG_STYLES) {
    if (pattern.test(line)) return tone;
  }
  return "text-text-secondary";
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
    <div className="card overflow-hidden">
      <div className="code-block__header">
        <span className="code-block__title flex items-center gap-2 font-mono">
          <Terminal className="h-3.5 w-3.5 text-brand-emerald/70" />
          {title ?? language}
        </span>
        <button
          onClick={copy}
          className="code-block__copy"
          aria-label={copied ? t("code.copied") : t("code.copy")}
        >
          {copied ? <Check className="h-4 w-4 text-success-text" /> : <Copy className="h-4 w-4" />}
        </button>
      </div>
      <pre
        className="code-block overflow-auto p-4"
        style={{ maxHeight }}
      >
        {lines.map((line, i) => (
          <div key={i} className={`flex ${lineTone(line)}`}>
            <span className="w-10 shrink-0 select-none pr-4 text-right text-text-tertiary/30">
              {i + 1}
            </span>
            <span className="whitespace-pre">
              {line || " "}
              {i === lines.length - 1 && (
                <span className="ml-0.5 inline-block h-4 w-[7px] translate-y-[3px] animate-blink bg-brand-emerald" />
              )}
            </span>
          </div>
        ))}
      </pre>
    </div>
  );
}