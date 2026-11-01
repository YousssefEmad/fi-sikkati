import type { Schemas } from "@fi-sikkati/types";

import { ApiRequestError } from "@/features/auth/api";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";
import { postMultipart } from "@/lib/api/upload";

export type VerificationStatus = Schemas["VerificationStatusResponse"];
export type IdentityDocument = Schemas["IdentityDocumentResponse"];

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throw new ApiRequestError(asProblem(error, fallback));
  return data;
}

export async function getVerification(): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me/verification");
  return unwrap(data, error, "Could not load verification status.");
}

export async function uploadIdentityDocument(
  documentType: "NATIONAL_ID_FRONT" | "NATIONAL_ID_BACK" | "SELFIE",
  file: File,
): Promise<VerificationStatus> {
  const form = new FormData();
  form.set("documentType", documentType);
  form.set("file", file);
  return postMultipart<VerificationStatus>("/api/v1/me/verification/identity/documents", form);
}

export async function submitIdentity(): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/me/verification/identity/submit",
  );
  return unwrap(data, error, "Could not submit identity documents.");
}

export async function uploadLicence(file: File): Promise<Schemas["LicenceUploadResponse"]> {
  const form = new FormData();
  form.set("file", file);
  return postMultipart<Schemas["LicenceUploadResponse"]>(
    "/api/v1/me/verification/driver/documents",
    form,
  );
}

export async function submitDriver(
  body: Schemas["DriverSubmitRequest"],
): Promise<VerificationStatus> {
  const { data, error } = await getBrowserApiClient().POST(
    "/api/v1/me/verification/driver/submit",
    {
      body,
    },
  );
  return unwrap(data, error, "Could not submit the driver application.");
}
