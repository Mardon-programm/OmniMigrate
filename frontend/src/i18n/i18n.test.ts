import { describe, expect, it } from "vitest";

import { resolveKey, interpolate } from "@/i18n";
import { translations } from "@/i18n/translations";

describe("i18n resolution", () => {
  it("resolves keys from the selected locale dictionary", () => {
    expect(resolveKey("nav.dashboard", translations.en)).toBe("Dashboard");
    expect(resolveKey("nav.dashboard", translations.ru)).toBe("Дашборд");
    expect(resolveKey("app.tagline", translations.ru)).toBe("Автономный движок рефакторинга");
  });

  it("falls back to the path for unknown keys", () => {
    expect(resolveKey("missing.key", translations.ru)).toBe("missing.key");
  });

  it("interpolates named parameters", () => {
    expect(interpolate("Welcome, {name}", { name: "Alex" })).toBe("Welcome, Alex");
    expect(interpolate("Попытка {attempt}/{max}", { attempt: "1", max: "3" })).toBe(
      "Попытка 1/3",
    );
  });

  it("keeps untranslated placeholders when params are missing", () => {
    expect(interpolate("Hi {name}", undefined)).toBe("Hi {name}");
  });

  it("en and ru dictionaries expose the same key surface", () => {
    const collect = (obj: unknown, prefix = ""): string[] => {
      const keys: string[] = [];
      for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "string") {
          keys.push(path);
        } else if (value && typeof value === "object") {
          keys.push(...collect(value, path));
        }
      }
      return keys;
    };
    const enKeys = collect(translations.en).sort();
    const ruKeys = collect(translations.ru).sort();
    expect(ruKeys).toEqual(enKeys);
  });
});
