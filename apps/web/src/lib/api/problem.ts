import { isProblem, type Problem } from "@fi-sikkati/types";

/** Turn an API error body into a Problem Details document the UI can display. */
export function asProblem(data: unknown, fallback: string): Problem {
  if (isProblem(data)) {
    return data;
  }
  return {
    type: "about:blank",
    title: fallback,
    status: 0,
    code: "UNKNOWN",
    detail: fallback,
    errors: null,
    request_id: null,
  };
}
