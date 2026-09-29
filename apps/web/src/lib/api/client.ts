"use client";

import { createApiClient, type ApiClient } from "@fi-sikkati/types";

import { clientEnv } from "@/lib/env";

let browserClient: ApiClient | undefined;

/** Singleton API client for Client Components (TanStack Query hooks call through this). */
export function getBrowserApiClient(): ApiClient {
  browserClient ??= createApiClient({ baseUrl: clientEnv.NEXT_PUBLIC_API_URL });
  return browserClient;
}
