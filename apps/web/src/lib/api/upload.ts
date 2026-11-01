import { ApiRequestError } from "@/features/auth/api";
import { getCsrfToken } from "@/features/auth/csrf";
import { asProblem } from "@/lib/api/problem";

/** Multipart POST through the same-origin rewrite so cookies and CSRF stay on the web host. */
export async function postMultipart<T>(path: string, form: FormData): Promise<T> {
  const csrf = getCsrfToken();
  const headers = new Headers();
  if (csrf) {
    headers.set("X-CSRF-Token", csrf);
  }
  const response = await fetch(path, {
    method: "POST",
    headers,
    body: form,
    credentials: "include",
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiRequestError(asProblem(data, "Upload failed."));
  }
  return data as T;
}
