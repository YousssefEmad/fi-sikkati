/** In-memory CSRF token from the last session response (ADR-0004 double-submit). */

const CSRF_COOKIE_NAME = "__Host-fs_csrf";

let csrfToken: string | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split("; ")) {
    const separator = part.indexOf("=");
    if (separator === -1 || part.slice(0, separator) !== name) continue;
    return decodeURIComponent(part.slice(separator + 1));
  }
  return null;
}

export function getCsrfToken(): string | null {
  if (csrfToken) return csrfToken;
  const fromCookie = readCookie(CSRF_COOKIE_NAME);
  if (fromCookie) csrfToken = fromCookie;
  return fromCookie;
}

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}
