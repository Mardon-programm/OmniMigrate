import { useMemo, useState } from "react";
import { Copy, Check } from "lucide-react";

import { useI18n } from "@/i18n";

interface CodeBlockProps {
  code: string;
  language?: string;
  maxHeight?: string;
  title?: string;
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
        <span className="font-mono text-xs text-muted">{title ?? language}</span>
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
        className="overflow-auto bg-code p-4 font-mono text-[13px] leading-5 text-slate-300"
        style={{ maxHeight }}
      >
        {lines.map((line, i) => (
          <div key={i} className="flex">
            <span className="w-10 shrink-0 select-none pr-4 text-right text-muted/40">
              {i + 1}
            </span>
            <span className="whitespace-pre">{line || " "}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
