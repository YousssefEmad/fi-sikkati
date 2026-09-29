import "server-only";

import type { PublicConfig } from "@fi-sikkati/types";

import { getServerApiClient } from "@/lib/api/server";

/**
 * Fetch public runtime configuration on the server. Returns `null` when the API is unreachable
 * so public pages still render (the API is not required to show marketing content).
 */
export async function fetchPublicConfig(): Promise<PublicConfig | null> {
  try {
    const { data } = await getServerApiClient().GET("/api/v1/platform/config");
    return data ?? null;
  } catch {
    return null;
  }
}
