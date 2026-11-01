export interface SuggestOption {
  id: string;
  label: string;
  keywords?: string;
  hint?: string;
  /** Shown when the field is focused and still empty. */
  pinned?: boolean;
}

/** Fold Arabic and Latin text so "نصر" matches "مدينة نصر" and "Nasr". */
export function fold(value: string): string {
  return value
    .toLowerCase()
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[\u064B-\u0652]/g, "")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function score(haystack: string, needle: string): number | null {
  if (!haystack.includes(needle)) return null;
  const bare = haystack.replace(/^ال/, "");
  if (haystack.startsWith(needle) || bare.startsWith(needle)) return 0;
  const words = haystack.split(" ").map((word) => word.replace(/^ال/, ""));
  if (words.some((word) => word.startsWith(needle))) return 1;
  return 2;
}

/** Rank catalog rows for a typeahead menu. An empty query returns the pinned rows. */
export function matchSuggest<T extends SuggestOption>(options: readonly T[], query: string, limit = 40): T[] {
  const needle = fold(query);
  if (!needle) {
    const pinned = options.filter((option) => option.pinned);
    return (pinned.length > 0 ? pinned : [...options]).slice(0, limit);
  }
  return options
    .map((option, index) => ({
      option,
      index,
      rank: score(fold(`${option.label} ${option.keywords ?? ""}`), needle),
    }))
    .filter((row): row is { option: T; index: number; rank: number } => row.rank !== null)
    .sort(
      (a, b) => a.rank - b.rank || a.option.label.length - b.option.label.length || a.index - b.index,
    )
    .slice(0, limit)
    .map((row) => row.option);
}
