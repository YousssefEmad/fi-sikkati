import { describe, expect, it, vi } from "vitest";

import { getCsrfToken, setCsrfToken } from "./csrf";

describe("csrf token store", () => {
  it("remembers the last session token and can be cleared", () => {
    setCsrfToken("token-a");
    expect(getCsrfToken()).toBe("token-a");
    setCsrfToken(null);
    expect(getCsrfToken()).toBeNull();
  });

  it("reads the session cookie after a reload clears memory", () => {
    vi.spyOn(document, "cookie", "get").mockReturnValue("__Host-fs_csrf=from-cookie");
    try {
      setCsrfToken(null);
      expect(getCsrfToken()).toBe("from-cookie");
      setCsrfToken("memory");
      expect(getCsrfToken()).toBe("memory");
    } finally {
      vi.restoreAllMocks();
    }
  });
});
