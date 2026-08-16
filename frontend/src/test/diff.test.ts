import { describe, expect, it } from "vitest";

import { parseDiff } from "@/components/DiffViewer";

describe("parseDiff", () => {
  const diff = [
    "--- legacy/source.py",
    "+++ modern/source.py",
    "@@ -1,3 +1,3 @@",
    "-print 'hi'",
    "+print('hi')",
    " x = 1",
    "",
  ].join("\n");

  it("classifies added lines", () => {
    const lines = parseDiff(diff);
    const adds = lines.filter((l) => l.type === "add");
    expect(adds).toHaveLength(1);
    expect(adds[0].content).toBe("+print('hi')");
  });

  it("classifies removed lines", () => {
    const lines = parseDiff(diff);
    const dels = lines.filter((l) => l.type === "del");
    expect(dels).toHaveLength(1);
    expect(dels[0].content).toBe("-print 'hi'");
  });

  it("classifies meta lines", () => {
    const lines = parseDiff(diff);
    expect(lines.filter((l) => l.type === "meta").length).toBeGreaterThanOrEqual(3);
  });

  it("treats blank context lines as context", () => {
    const lines = parseDiff(diff);
    expect(lines[lines.length - 1].type).toBe("context");
  });

  it("returns empty for empty input", () => {
    expect(parseDiff("")).toHaveLength(1);
  });
});
