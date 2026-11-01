import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";

export type Trip = Schemas["TripResponse"];
export type MapPoint = Schemas["MapPoint"];

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throw new ApiRequestError(asProblem(error, fallback));
  return data;
}

export async function autocompletePlaces(q: string): Promise<MapPoint[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/maps/autocomplete", {
    params: { query: { q } },
  });
  return unwrap(data, error, "Could not search places.").items;
}

export async function previewRoute(
  stops: Schemas["RouteStopInput"][],
): Promise<Schemas["RoutePreviewResponse"]> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/maps/route-preview", {
    body: { stops },
  });
  return unwrap(data, error, "Could not preview the route.");
}

export async function estimatePrice(distanceM: number): Promise<Schemas["PriceEstimateResponse"]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/pricing/estimate", {
    params: { query: { distanceM } },
  });
  return unwrap(data, error, "Could not estimate the contribution.");
}

export async function createTrip(body: Schemas["TripCreateRequest"]): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/trips", {
    body,
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
  return unwrap(data, error, "Could not create the trip.");
}

export async function getTrip(tripId: string): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/trips/{trip_id}", {
    params: { path: { trip_id: tripId } },
  });
  return unwrap(data, error, "Could not load the trip.");
}

export async function listMyTrips(role: "driver" | "passenger" = "driver"): Promise<Trip[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me/trips", {
    params: { query: { role } },
  });
  return unwrap(data, error, "Could not load trips.").items;
}

export async function updateTrip(
  tripId: string,
  version: number,
  body: Schemas["TripUpdateRequest"],
): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().PATCH("/api/v1/trips/{trip_id}", {
    params: { path: { trip_id: tripId } },
    body,
    headers: { "If-Match": String(version) },
  });
  return unwrap(data, error, "Could not update the trip.");
}

export async function publishTrip(tripId: string): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/trips/{trip_id}/publish", {
    params: { path: { trip_id: tripId } },
  });
  return unwrap(data, error, "Could not publish the trip.");
}

export async function startTrip(tripId: string): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/trips/{trip_id}/start", {
    params: { path: { trip_id: tripId } },
  });
  return unwrap(data, error, "Could not start the trip.");
}

export async function completeTrip(tripId: string): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/trips/{trip_id}/complete", {
    params: { path: { trip_id: tripId } },
  });
  return unwrap(data, error, "Could not complete the trip.");
}

export async function cancelTrip(tripId: string): Promise<Trip> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/trips/{trip_id}/cancel", {
    params: { path: { trip_id: tripId } },
  });
  return unwrap(data, error, "Could not cancel the trip.");
}
