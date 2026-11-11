import { isProblem, type Problem } from "@fi-sikkati/types";

/** Turn an API error body into a Problem Details document the UI can display. */
export function asProblem(
  data: unknown,
  fallback: string,
  overrides?: { status?: number; code?: string },
): Problem {
  if (isProblem(data)) {
    return {
      ...data,
      status: overrides?.status ?? data.status,
      code: data.code || overrides?.code || "UNKNOWN",
    };
  }
  return {
    type: "about:blank",
    title: fallback,
    status: overrides?.status ?? 0,
    code: overrides?.code ?? "UNKNOWN",
    detail: fallback,
    errors: null,
    request_id: null,
  };
}
