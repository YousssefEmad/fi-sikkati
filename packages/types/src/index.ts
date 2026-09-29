/**
 * Typed API client for the Fi Sikkati backend.
 *
 * `schema.d.ts` is generated from `openapi.json` (`pnpm types:generate`) and must never be edited
 * by hand. CI fails when the committed OpenAPI document differs from the running API (api.md §5).
 */
import createClient, { type ClientOptions, type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };

/** Convenience aliases for frequently used schemas. */
export type Schemas = components["schemas"];
export type PublicConfig = Schemas["PublicConfig"];
export type Problem = Schemas["Problem"];

export const REQUEST_ID_HEADER = "X-Request-Id";

export interface CreateApiClientOptions extends Omit<ClientOptions, "baseUrl"> {
  baseUrl: string;
  /** Called with the `X-Request-Id` of every response — useful for support tooling and logs. */
  onRequestId?: (requestId: string) => void;
}

/**
 * Create a typed client bound to the API origin. Cookies are sent with every request so the
 * browser client works with the cookie-based session (ADR-0004).
 */
export function createApiClient(options: CreateApiClientOptions) {
  const { onRequestId, ...clientOptions } = options;
  const client = createClient<paths>({ credentials: "include", ...clientOptions });

  if (onRequestId) {
    const requestIdMiddleware: Middleware = {
      onResponse({ response }) {
        const id = response.headers.get(REQUEST_ID_HEADER);
        if (id) onRequestId(id);
        return response;
      },
    };
    client.use(requestIdMiddleware);
  }

  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;

/** Type guard for RFC 9457 problem documents returned by the API. */
export function isProblem(value: unknown): value is Problem {
  return (
    typeof value === "object" &&
    value !== null &&
    "code" in value &&
    "status" in value &&
    typeof (value as { code: unknown }).code === "string"
  );
}
