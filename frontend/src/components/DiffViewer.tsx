import { useMemo, useState } from "react";
import { Columns2, FileDiff, Rows3 } from "lucide-react";

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

export type DiffMode = "unified" | "split";

export interface SplitRow {
  kind: "pair" | "divider";
  left: DiffLine | null;
  right: DiffLine | null;
}

/** Build side-by-side rows: pair deletion/addition runs, keep context aligned. */
export function toSplitRows(lines: DiffLine[]): SplitRow[] {
  const rows: SplitRow[] = [];
  let dels: DiffLine[] = [];
  let adds: DiffLine[] = [];

  const flush = () => {
    const n = Math.max(dels.length, adds.length);
    for (let i = 0; i < n; i += 1) {
      rows.push({ kind: "pair", left: dels[i] ?? null, right: adds[i] ?? null });
    }
    dels = [];
    adds = [];
  };

  for (const line of lines) {
    if (line.type === "del") {
      dels.push(line);
    } else if (line.type === "add") {
      adds.push(line);
    } else if (line.type === "context") {
      flush();
      rows.push({ kind: "pair", left: line, right: line });
    } else {
      flush();
      rows.push({ kind: "divider", left: line, right: null });
    }
  }
  flush();
  return rows;
}

const UNIFIED_LINE_CLASSES: Record<DiffLine["type"], string> = {
  header: "bg-surface2 text-primary-400 font-semibold",
  meta: "bg-accent/10 text-accent font-medium",
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

function SideNumber({ n }: { n: number }) {
  return (
    <span className="w-10 shrink-0 select-none border-r border-border/40 px-1.5 text-right text-[11px] text-muted/40">
      {n}
    </span>
  );
}

interface DiffViewerProps {
  diff: string;
  className?: string;
}

export function DiffViewer({ diff, className = "" }: DiffViewerProps) {
  const { t } = useI18n();
  const [mode, setMode] = useState<DiffMode>("split");
  const lines = useMemo(() => parseDiff(diff), [diff]);
  const splitRows = useMemo(
    () => (mode === "split" ? toSplitRows(lines) : []),
    [lines, mode],
  );

  const stats = useMemo(() => {
    let additions = 0;
    let deletions = 0;
    for (const line of lines) {
      if (line.type === "add") additions += 1;
      if (line.type === "del") deletions += 1;
    }
    return { additions, deletions };
  }, [lines]);

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
          <span className="ml-2 flex items-center gap-3 font-mono text-xs">
            <span className="text-success">+{stats.additions}</span>
            <span className="text-danger">-{stats.deletions}</span>
          </span>
        </div>
        <div className="flex items-center gap-0.5 rounded-lg border border-border bg-black/30 p-0.5">
          {(
            [
              { id: "split", icon: Columns2, key: "diff.modeSplit" },
              { id: "unified", icon: Rows3, key: "diff.modeUnified" },
            ] as const
          ).map(({ id, icon: Icon, key }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              title={t(key)}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all duration-150 ${
                mode === id
                  ? "bg-primary/15 text-primary shadow-glow-sm"
                  : "text-muted hover:text-slate-200"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t(key)}</span>
            </button>
          ))}
        </div>
      </div>

      {mode === "unified" ? (
        <pre className="max-h-[560px] overflow-auto bg-code py-3 font-mono text-[13px] leading-5">
          {lines.map((line, index) => (
            <div key={index} className={`flex ${UNIFIED_LINE_CLASSES[line.type]}`}>
              <SideNumber n={index} />
              <span
                className={`w-6 shrink-0 select-none px-1 text-center ${PREFIX_CLASSES[line.type]}`}
              >
                {line.type === "add" ? "+" : line.type === "del" ? "-" : ""}
              </span>
              <span className="whitespace-pre pr-4">{line.content}</span>
            </div>
          ))}
        </pre>
      ) : (
        <div className="max-h-[560px] overflow-auto">
          <div className="sticky top-0 z-10 grid grid-cols-2 border-b border-border text-[11px] font-semibold uppercase tracking-wider">
            <div className="flex items-center gap-1.5 bg-red-950/50 px-3 py-1.5 text-danger backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-danger" />
              {t("diff.legacy")}
            </div>
            <div className="flex items-center gap-1.5 border-l border-border bg-emerald-950/50 px-3 py-1.5 text-primary backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              {t("diff.modernized")}
            </div>
          </div>
          <pre className="grid grid-cols-2 bg-code font-mono text-[13px] leading-5">
            <code className="border-r border-border bg-red-950/20 pb-3 pt-3">
              {splitRows.map((row, index) =>
                row.kind === "divider" ? (
                  <div
                    key={index}
                    className="my-1 flex h-6 items-center overflow-hidden bg-surface2 px-3 text-[11px] font-semibold text-primary-400"
                  >
                    <span className="truncate whitespace-pre">
                      {row.left?.content ?? ""}
                    </span>
                  </div>
                ) : row.left ? (
                  <div
                    key={index}
                    className={`flex ${
                      row.left.type === "meta"
                        ? "bg-accent/10 text-accent"
                        : row.left.type === "del"
                          ? "bg-danger/15 text-danger"
                          : "text-slate-400"
                    }`}
                  >
                    <SideNumber n={index} />
                    <span className="whitespace-pre pr-4">{row.left.content}</span>
                  </div>
                ) : (
                  <div key={index} className="h-5 bg-black/30" />
                ),
              )}
            </code>
            <code className="bg-emerald-950/20 pb-3 pt-3">
              {splitRows.map((row, index) =>
                row.kind === "divider" ? (
                  <div
                    key={index}
                    className="my-1 h-6 bg-surface2"
                  />
                ) : row.right ? (
                  <div
                    key={index}
                    className={`flex ${
                      row.right.type === "meta"
                        ? "bg-accent/10 text-accent"
                        : row.right.type === "add"
                          ? "bg-success/15 text-success"
                          : "text-slate-400"
                    }`}
                  >
                    <SideNumber n={index} />
                    <span className="whitespace-pre pr-4">{row.right.content}</span>
                  </div>
                ) : (
                  <div key={index} className="h-5 bg-black/30" />
                ),
              )}
            </code>
          </pre>
        </div>
      )}
    </div>
  );
}
