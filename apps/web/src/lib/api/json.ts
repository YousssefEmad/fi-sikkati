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
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (response.status === 204) {
    return undefined as T;
  }
  const raw = await response.text();
  const data: unknown = raw ? JSON.parse(raw) : null;
  if (!response.ok) {
    throw new ApiRequestError(asProblem(data, "Request failed."));
  }
  return data as T;
}
