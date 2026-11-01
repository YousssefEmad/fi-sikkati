import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";
import { postMultipart } from "@/lib/api/upload";

export type Vehicle = Schemas["VehicleResponse"];

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throw new ApiRequestError(asProblem(error, fallback));
  return data;
}

export async function listVehicles(): Promise<Vehicle[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me/vehicles");
  return unwrap(data, error, "Could not load vehicles.").items;
}

export async function createVehicle(body: Schemas["VehicleCreateRequest"]): Promise<Vehicle> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/me/vehicles", { body });
  return unwrap(data, error, "Could not save the vehicle.");
}

export async function deactivateVehicle(vehicleId: string): Promise<Vehicle> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/me/vehicles/{vehicle_id}/deactivate",
    { params: { path: { vehicle_id: vehicleId } } },
  );
  return unwrap(data, error, "Could not deactivate the vehicle.");
}

export async function uploadVehicleDocument(
  vehicleId: string,
  documentType: "REGISTRATION_FRONT" | "REGISTRATION_BACK" | "VEHICLE_PHOTO",
  file: File,
): Promise<Vehicle> {
  const form = new FormData();
  form.set("documentType", documentType);
  form.set("file", file);
  return postMultipart<Vehicle>(`/api/v1/me/vehicles/${vehicleId}/documents`, form);
}
