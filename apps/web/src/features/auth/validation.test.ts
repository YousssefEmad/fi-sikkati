import { describe, expect, it } from "vitest";

import { adultCutoffDate, isOptionalE164 } from "./validation";

describe("adultCutoffDate", () => {
  it("is minAge years before the given day", () => {
    expect(adultCutoffDate(18, new Date(2026, 9, 2))).toBe("2008-10-02");
  });
});

describe("isOptionalE164", () => {
  it("accepts empty and international numbers", () => {
    expect(isOptionalE164(undefined)).toBe(true);
    expect(isOptionalE164("+201012345678")).toBe(true);
  });

  it("rejects local and too-short numbers", () => {
    expect(isOptionalE164("01012345678")).toBe(false);
    expect(isOptionalE164("+2010")).toBe(false);
  });
});
