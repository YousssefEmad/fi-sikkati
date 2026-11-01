"use client";

import { createApiClient, type ApiClient } from "@fi-sikkati/types";

import { getCsrfToken } from "@/features/auth/csrf";

let browserClient: ApiClient | undefined;

/**
 * Singleton API client for Client Components.
 *
 * The base URL is empty: the browser calls this origin and Next.js rewrites `/api/*` to FastAPI
 * so session cookies stay on the web host (ADR-0004).
 */
export function getBrowserApiClient(): ApiClient {
  browserClient ??= createApiClient({
    baseUrl: "",
    getCsrfToken,
  });
  return browserClient;
}
