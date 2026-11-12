import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { apiJson } from "@/lib/api/json";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";

export type AdminIdentityItem = Schemas["AdminIdentityQueueItem"];
export type AdminDriverItem = Schemas["AdminDriverQueueItem"];
export type VerificationStatus = Schemas["VerificationStatusResponse"];

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throw new ApiRequestError(asProblem(error, fallback));
  return data;
}

export async function listIdentityQueue(): Promise<Schemas["AdminIdentityQueueResponse"]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/admin/verifications/identity");
  return unwrap(data, error, "Could not load the identity queue.");
}

export async function listDriverQueue(): Promise<Schemas["AdminDriverQueueResponse"]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/admin/verifications/driver");
  return unwrap(data, error, "Could not load the driver queue.");
}

export async function approveVehicleRegistration(
  userId: string,
  vehicleId: string,
): Promise<void> {
  await apiJson(`/api/v1/admin/verifications/driver/${userId}/registration`, {
    method: "POST",
    body: JSON.stringify({ vehicleId }),
  });
}

export async function rejectVehicle(vehicleId: string, reason: string): Promise<void> {
  const { error } = await getBrowserApiClient().POST(
    "/api/v1/admin/vehicles/{vehicle_id}/reject",
    { params: { path: { vehicle_id: vehicleId } }, body: { reason } },
  );
  if (error) throw new ApiRequestError(asProblem(error, "Could not reject the vehicle."));
}

export async function getAdminVehicle(vehicleId: string): Promise<Schemas["VehicleResponse"]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/admin/vehicles/{vehicle_id}", {
    params: { path: { vehicle_id: vehicleId } },
  });
  return unwrap(data, error, "Could not load the vehicle.");
}

export async function getIdentityReview(userId: string): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().GET(
    "/api/v1/admin/verifications/identity/{user_id}",
    { params: { path: { user_id: userId } } },
  );
  return unwrap(data, error, "Could not load the application.");
}

export async function approveIdentity(userId: string): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/admin/verifications/identity/{user_id}/approve",
    { params: { path: { user_id: userId } } },
  );
  return unwrap(data, error, "Could not approve.");
}

export async function rejectIdentity(userId: string, reason: string): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/admin/verifications/identity/{user_id}/reject",
    { params: { path: { user_id: userId } }, body: { reason } },
  );
  return unwrap(data, error, "Could not reject.");
}

export async function approveDriver(userId: string): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/admin/verifications/driver/{user_id}/approve",
    { params: { path: { user_id: userId } } },
  );
  return unwrap(data, error, "Could not approve.");
}

export async function rejectDriver(userId: string, reason: string): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/admin/verifications/driver/{user_id}/reject",
    { params: { path: { user_id: userId } }, body: { reason } },
  );
  return unwrap(data, error, "Could not reject.");
}

export async function documentDownloadUrl(fileId: string): Promise<string> {
  const { data, error } = await getBrowserApiClient().GET(
    "/api/v1/admin/verifications/files/{file_id}/download-url",
    { params: { path: { file_id: fileId } } },
  );
  return unwrap(data, error, "Could not open the document.").url;
}

export type AdminUserListItem = Schemas["AdminUserListItem"];

export type AdminUserListResponse = {
  items: AdminUserListItem[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
};

export type AdminOverview = {
  usersTotal: number;
  usersActive7d: number;
  drivers: number;
  tripsTotal: number;
  tripsCompleted: number;
  tripsCancelled: number;
  joinRequestsTotal: number;
  joinRequestsMatched: number;
  reportsOpen: number;
};

export async function fetchAdminOverview(): Promise<AdminOverview> {
  return apiJson<AdminOverview>("/api/v1/admin/analytics/overview");
}

export async function listAdminUsers(params: {
  q?: string;
  status?: string;
  role?: string;
  page?: number;
  pageSize?: number;
}): Promise<AdminUserListResponse> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.status) search.set("status", params.status);
  if (params.role) search.set("role", params.role);
  if (params.page) search.set("page", String(params.page));
  if (params.pageSize) search.set("page_size", String(params.pageSize));
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return apiJson<AdminUserListResponse>(`/api/v1/admin/users${suffix}`);
}

export async function suspendAdminUser(userId: string, reason: string): Promise<void> {
  await apiJson(`/api/v1/admin/users/${userId}/suspend`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function restoreAdminUser(userId: string, reason: string): Promise<void> {
  await apiJson(`/api/v1/admin/users/${userId}/restore`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function deactivateAdminUser(userId: string, reason: string): Promise<void> {
  await apiJson(`/api/v1/admin/users/${userId}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
