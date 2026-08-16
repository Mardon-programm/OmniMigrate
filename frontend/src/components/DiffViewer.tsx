import { useMemo } from "react";
import { FileDiff } from "lucide-react";

import { useI18n } from "@/i18n";

export interface DiffLine {
  type: "header" | "meta" | "add" | "del" | "context";
  content: string;
}

export function parseDiff(diff: string): DiffLine[] {
  return diff.split("\n").map((line) => {
    if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
      return { type: "meta", content: line };
    }
    if (line.startsWith("+")) return { type: "add", content: line };
    if (line.startsWith("-")) return { type: "del", content: line };
    if (line.startsWith("diff --git") || line.startsWith("Index:")) {
      return { type: "header", content: line };
    }
    return { type: "context", content: line };
  });
}

const LINE_CLASSES: Record<DiffLine["type"], string> = {
  header: "bg-surface2 text-primary-600 font-semibold",
  meta: "bg-primary/10 text-accent font-medium",
  add: "bg-success/[0.08] text-success",
  del: "bg-danger/[0.08] text-danger",
  context: "text-slate-400",
};

const PREFIX_CLASSES: Record<DiffLine["type"], string> = {
  header: "",
  meta: "",
  add: "text-success",
  del: "text-danger",
  context: "text-muted",
};

interface DiffViewerProps {
  diff: string;
  className?: string;
}

export function DiffViewer({ diff, className = "" }: DiffViewerProps) {
  const { t } = useI18n();
  const lines = useMemo(() => parseDiff(diff), [diff]);

  const stats = useMemo(() => {
    let additions = 0;
    let deletions = 0;
    for (const line of parseDiff(diff)) {
      if (line.type === "add") additions += 1;
      if (line.type === "del") deletions += 1;
    }
    return { additions, deletions };
  }, [diff]);

  if (!diff || !lines.length) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-muted">
        <FileDiff className="h-10 w-10" />
        <p className="text-sm">{t("diff.noDiff")}</p>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden rounded-2xl border border-border ${className}`}>
      <div className="flex items-center justify-between border-b border-border bg-surface2 px-4 py-2.5">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <FileDiff className="h-4 w-4 text-primary" />
          {t("diff.title")}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-success">+{stats.additions}</span>
          <span className="text-danger">-{stats.deletions}</span>
        </div>
      </div>
      <pre className="max-h-[560px] overflow-auto bg-code py-3 font-mono text-[13px] leading-5">
        {lines.map((line, index) => (
          <div key={index} className={`flex ${LINE_CLASSES[line.type]}`}>
            <span className="w-12 shrink-0 select-none border-r border-border/50 px-2 text-right text-[11px] text-muted/50">
              {index}
            </span>
            <span className={`w-6 shrink-0 select-none px-1 text-center ${PREFIX_CLASSES[line.type]}`}>
              {line.type === "add" ? "+" : line.type === "del" ? "-" : ""}
            </span>
            <span className="whitespace-pre pr-4">{line.content}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
