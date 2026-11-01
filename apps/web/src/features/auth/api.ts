import type { Problem, Schemas } from "@fi-sikkati/types";

import { setCsrfToken } from "@/features/auth/csrf";
import { getBrowserApiClient } from "@/lib/api/client";
import { asProblem } from "@/lib/api/problem";

export type Account = Schemas["AccountResponse"];
export type SessionResponse = Schemas["SessionResponse"];
export type SessionSummary = Schemas["SessionSummary"];
export type PublicConfig = Schemas["PublicConfig"];

export class ApiRequestError extends Error {
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.detail ?? problem.title);
    this.name = "ApiRequestError";
    this.problem = problem;
  }
}

function throwIfProblem(error: unknown, fallback: string): never {
  throw new ApiRequestError(asProblem(error, fallback));
}

function unwrap<T>(data: T | undefined, error: unknown, fallback: string): T {
  if (error || data === undefined) throwIfProblem(error, fallback);
  return data;
}

function rememberSession(body: SessionResponse | undefined): void {
  if (body?.csrfToken) {
    setCsrfToken(body.csrfToken);
  }
}

export async function fetchPublicConfig(): Promise<PublicConfig> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/platform/config");
  return unwrap(data, error, "Could not load configuration.");
}

export async function registerAccount(
  body: Schemas["RegisterRequest"],
): Promise<Schemas["AcceptedResponse"]> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/auth/register", { body });
  return unwrap(data, error, "Could not create the account.");
}

export async function signIn(email: string, password: string): Promise<SessionResponse> {
  const { data, error } = await getBrowserApiClient().POST("/api/v1/auth/login", {
    body: { email, password },
  });
  const session = unwrap(data, error, "Could not sign in.");
  rememberSession(session);
  return session;
}

export async function refreshSession(): Promise<SessionResponse | null> {
  const { data, response } = await getBrowserApiClient().POST("/api/v1/auth/refresh", {
    body: {},
  });
  if (response.status === 401) {
    setCsrfToken(null);
    return null;
  }
  if (!data) return null;
  rememberSession(data);
  return data;
}

export async function signOut(): Promise<void> {
  await getBrowserApiClient().POST("/api/v1/auth/logout");
  setCsrfToken(null);
}

export async function verifyEmail(token: string): Promise<void> {
  const { error, response } = await getBrowserApiClient().POST("/api/v1/auth/email/verify", {
    body: { token },
  });
  if (!response.ok) throwIfProblem(error, "Could not confirm the email address.");
}

export async function resendVerification(email: string): Promise<void> {
  const { error, data } = await getBrowserApiClient().POST("/api/v1/auth/email/resend", {
    body: { email },
  });
  unwrap(data, error, "Could not resend the confirmation email.");
}

export async function forgotPassword(email: string): Promise<void> {
  const { error, data } = await getBrowserApiClient().POST("/api/v1/auth/password/forgot", {
    body: { email },
  });
  unwrap(data, error, "Could not start a password reset.");
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  const { error, response } = await getBrowserApiClient().POST("/api/v1/auth/password/reset", {
    body: { token, newPassword },
  });
  if (!response.ok) throwIfProblem(error, "Could not set the new password.");
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const { error, response } = await getBrowserApiClient().POST("/api/v1/auth/password/change", {
    body: { currentPassword, newPassword },
  });
  if (!response.ok) throwIfProblem(error, "Could not change the password.");
}

export async function getMe(): Promise<Account> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me");
  return unwrap(data, error, "Could not load the account.");
}

export async function updateMe(body: Schemas["ProfileUpdateRequest"]): Promise<Account> {
  const { data, error } = await getBrowserApiClient().PATCH("/api/v1/me", { body });
  return unwrap(data, error, "Could not update the profile.");
}

export async function deleteMe(): Promise<Schemas["DeleteAccountResponse"]> {
  const { data, error } = await getBrowserApiClient().DELETE("/api/v1/me");
  const body = unwrap(data, error, "Could not close the account.");
  setCsrfToken(null);
  return body;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const { data, error } = await getBrowserApiClient().GET("/api/v1/me/sessions");
  return unwrap(data, error, "Could not load sessions.").items;
}

export async function revokeSession(sessionId: string): Promise<void> {
  const { error, response } = await getBrowserApiClient().DELETE(
    "/api/v1/me/sessions/{session_id}",
    {
      params: { path: { session_id: sessionId } },
    },
  );
  if (!response.ok) throwIfProblem(error, "Could not sign that device out.");
}
