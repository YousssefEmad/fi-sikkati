import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";

export type SearchTripItem = Schemas["SearchTripItem"];
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

export async function searchTrips(query: {
  pickupLat: number;
  pickupLng: number;
  dropoffLat: number;
  dropoffLng: number;
  date: string;
  time?: string;
  seats: number;
}): Promise<SearchTripItem[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/search/trips", {
    params: {
      query: {
        pickupLat: query.pickupLat,
        pickupLng: query.pickupLng,
        dropoffLat: query.dropoffLat,
        dropoffLng: query.dropoffLng,
        date: query.date,
        seats: query.seats,
        ...(query.time !== undefined ? { time: query.time } : {}),
      },
    },
  });
  return unwrap(data, error, "Could not search trips.").items;
}
