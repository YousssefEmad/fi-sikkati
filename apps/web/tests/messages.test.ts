import { describe, expect, it } from "vitest";

import ar from "../messages/ar.json";
import en from "../messages/en.json";

function flattenKeys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    flattenKeys(child, prefix ? `${prefix}.${key}` : key),
  );
}

/** Arabic is first-class (NFR-01): every key must exist in both locales with the same ICU args. */
describe("translation messages", () => {
  it("have identical key sets in ar and en", () => {
    expect(flattenKeys(ar).sort()).toEqual(flattenKeys(en).sort());
  });

  it("use the same ICU placeholders in both locales", () => {
    const placeholders = (text: string) => [...text.matchAll(/\{(\w+)/g)].map((m) => m[1]).sort();
    const lookup = (messages: unknown, path: string): string =>
      path
        .split(".")
        .reduce<unknown>((node, key) => (node as Record<string, unknown>)[key], messages) as string;

    for (const key of flattenKeys(en)) {
      expect(placeholders(lookup(ar, key)), key).toEqual(placeholders(lookup(en, key)));
    }
  });
});
