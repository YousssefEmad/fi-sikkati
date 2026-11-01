import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";

export type JoinRequest = Schemas["JoinRequestResponse"];

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throw new ApiRequestError(asProblem(error, fallback));
  return data;
}

export async function createJoinRequest(
  tripId: string,
  body: Schemas["JoinRequestCreate"],
): Promise<JoinRequest> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/trips/{trip_id}/join-requests",
    {
      params: { path: { trip_id: tripId } },
      body,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    },
  );
  return unwrap(data, error, "Could not request a seat.");
}

export async function listTripRequests(tripId: string): Promise<JoinRequest[]> {
  const { data, error } = await getBrowserApiClient().GET(
    "/api/v1/trips/{trip_id}/join-requests",
    { params: { path: { trip_id: tripId } } },
  );
  return unwrap(data, error, "Could not load requests.").items;
}

export async function listMyRequests(): Promise<JoinRequest[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me/join-requests");
  return unwrap(data, error, "Could not load requests.").items;
}

export async function acceptRequest(requestId: string): Promise<JoinRequest> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/join-requests/{request_id}/accept",
    { params: { path: { request_id: requestId } } },
  );
  return unwrap(data, error, "Could not accept the request.");
}

export async function rejectRequest(requestId: string): Promise<JoinRequest> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/join-requests/{request_id}/reject",
    { params: { path: { request_id: requestId } } },
  );
  return unwrap(data, error, "Could not reject the request.");
}

export async function cancelRequest(requestId: string): Promise<JoinRequest> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/join-requests/{request_id}/cancel",
    { params: { path: { request_id: requestId } } },
  );
  return unwrap(data, error, "Could not cancel the request.");
}
