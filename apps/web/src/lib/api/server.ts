import "server-only";

import { createApiClient, type ApiClient } from "@fi-sikkati/types";

import { serverEnv } from "@/lib/env";

/**
 * API client for Server Components and route handlers. Uses the internal API origin so calls
 * stay inside the private network when both apps run in containers.
 */
export function getServerApiClient(): ApiClient {
  if (!serverEnv) {
    throw new Error("getServerApiClient() must only be called on the server");
  }
  return createApiClient({ baseUrl: serverEnv.API_INTERNAL_URL, cache: "no-store" });
}
