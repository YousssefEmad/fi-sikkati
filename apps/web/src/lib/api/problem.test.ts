import { describe, expect, it } from "vitest";

import { asProblem } from "./problem";

describe("asProblem", () => {
  it("passes through a Problem Details document", () => {
    const problem = {
      type: "https://fisikkati.app/errors/validation",
      title: "Invalid input",
      status: 400,
      code: "VALIDATION_ERROR",
      detail: "Check the marked fields.",
      errors: null,
      request_id: "req-1",
    };
    expect(asProblem(problem, "fallback")).toEqual(problem);
  });

  it("wraps unknown errors so the UI always has a code to show", () => {
    const wrapped = asProblem({ message: "nope" }, "Could not save.");
    expect(wrapped.code).toBe("UNKNOWN");
    expect(wrapped.title).toBe("Could not save.");
    expect(wrapped.detail).toBe("Could not save.");
  });
});
