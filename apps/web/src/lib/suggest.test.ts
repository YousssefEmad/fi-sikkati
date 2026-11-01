import { describe, expect, it } from "vitest";

import { fold, matchSuggest, type SuggestOption } from "@/lib/suggest";

const places: SuggestOption[] = [
  { id: "obour", label: "مدينة العبور", keywords: "El Obour", pinned: true },
  { id: "nasr", label: "مدينة نصر", keywords: "Nasr City", pinned: true },
  { id: "heliopolis", label: "مصر الجديدة", keywords: "Heliopolis", pinned: true },
  { id: "maadi", label: "المعادي", keywords: "Maadi" },
];

describe("matchSuggest", () => {
  it("folds alef variants and ta marbuta", () => {
    expect(fold("إبّارة")).toBe("اباره");
  });

  it("shows pinned places before the user types", () => {
    expect(matchSuggest(places, "").map((place) => place.id)).toEqual([
      "obour",
      "nasr",
      "heliopolis",
    ]);
  });

  it("matches Arabic and English as the user types", () => {
    expect(matchSuggest(places, "نصر").map((place) => place.id)).toEqual(["nasr"]);
    expect(matchSuggest(places, "obour").map((place) => place.id)).toEqual(["obour"]);
  });

  it("prefers a name that starts with the query", () => {
    const ranked = matchSuggest(
      [
        { id: "new", label: "القاهرة الجديدة", keywords: "New Cairo" },
        { id: "cairo", label: "القاهرة", keywords: "Cairo" },
      ],
      "قاهره",
    );
    expect(ranked[0]?.id).toBe("cairo");
  });
});
