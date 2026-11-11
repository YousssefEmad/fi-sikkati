import { ApiRequestError } from "@/features/auth/api";
import { getCsrfToken } from "@/features/auth/csrf";
import { asProblem } from "@/lib/api/problem";

/** Untyped JSON helper for endpoints not yet in the generated OpenAPI client. */
export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const method = (init.method ?? "GET").toUpperCase();
  const csrf = getCsrfToken();
  if (csrf && method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrf);
  }
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers, credentials: "include" });
  } catch {
    throw new ApiRequestError(
      asProblem(
        {
          type: "about:blank",
          title: "Service unavailable",
          status: 503,
          code: "SERVICE_UNAVAILABLE",
          detail: null,
          errors: null,
          request_id: null,
        },
        "Service unavailable",
      ),
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const raw = await response.text();
  let data: unknown = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const fallbackCode =
      response.status === 502 || response.status === 503 || response.status === 504
        ? "SERVICE_UNAVAILABLE"
        : "UNKNOWN";
    throw new ApiRequestError(
      asProblem(data, "Request failed.", {
        status: response.status,
        code: fallbackCode,
      }),
    );
  }
  return data as T;
}
