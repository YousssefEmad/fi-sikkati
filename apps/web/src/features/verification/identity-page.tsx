"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import {
  getVerification,
  submitIdentity,
  uploadIdentityDocument,
} from "@/features/verification/api";
import { Link } from "@/i18n/navigation";

const TYPES = [
  ["NATIONAL_ID_FRONT", "front"],
  ["NATIONAL_ID_BACK", "back"],
  ["SELFIE", "selfie"],
] as const;

function IdentityForm() {
  const t = useTranslations("Verification");
  const account = useTranslations("Account");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["verification", "me"], queryFn: getVerification });
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState<string | null>(null);
  const status = query.data;
  const locked = status?.identityStatus === "PENDING" || status?.identityStatus === "APPROVED";

  async function onFile(
    documentType: (typeof TYPES)[number][0],
    file: File | undefined,
  ): Promise<void> {
    if (!file) return;
    setBusy(documentType);
    setError(undefined);
    try {
      queryClient.setQueryData(
        ["verification", "me"],
        await uploadIdentityDocument(documentType, file),
      );
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(null);
    }
  }

  async function onSubmit(): Promise<void> {
    setBusy("submit");
    setError(undefined);
    try {
      queryClient.setQueryData(["verification", "me"], await submitIdentity());
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.submit"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2">{t("intro")}</p>
      {status ? (
        <p className="mt-3 text-sm">
          {t("status", { status: account(`verificationStatus.${status.identityStatus}`) })}
        </p>
      ) : null}
      {status ? (
        <p className="text-muted-foreground mt-1 text-sm">
          {t("sla", { hours: status.reviewSlaHours })}
        </p>
      ) : null}
      {status?.identityRejectionReason ? (
        <p className="bg-brand-soft mt-4 rounded-md px-4 py-3 text-sm">
          {t("rejection", { reason: status.identityRejectionReason })}
        </p>
      ) : null}
      {locked ? <p className="text-muted-foreground mt-4 text-sm">{t("locked")}</p> : null}
      <ul className="mt-8 space-y-4">
        {TYPES.map(([documentType, key]) => {
          const uploaded = status?.identityDocuments.find(
            (doc) => doc.documentType === documentType,
          );
          return (
            <li key={documentType} className="border-border rounded-lg border p-4">
              <p className="font-semibold">{t(key)}</p>
              {uploaded ? (
                <p className="text-muted-foreground mt-1 text-sm">
                  {t("uploaded", { name: uploaded.originalName })}
                </p>
              ) : null}
              {locked ? null : (
                <label
                  htmlFor={`identity-${documentType}`}
                  className="mt-3 block text-sm font-semibold"
                >
                  {t("choose")}
                  <input
                    id={`identity-${documentType}`}
                    className="mt-1 block"
                    type="file"
                    accept="image/jpeg,image/png,application/pdf"
                    aria-label={t(key)}
                    disabled={busy !== null}
                    onChange={(event) => {
                      void onFile(documentType, event.target.files?.[0]);
                    }}
                  />
                </label>
              )}
              {busy === documentType ? <p className="mt-2 text-sm">{t("uploading")}</p> : null}
            </li>
          );
        })}
      </ul>
      {error ? <FormError message={error} /> : null}
      {locked ? null : (
        <Button className="mt-6" disabled={busy !== null} onClick={() => void onSubmit()}>
          {busy === "submit" ? t("submitting") : t("submit")}
        </Button>
      )}
      <p className="mt-8">
        <Link
          href="/me"
          className="text-primary text-sm font-semibold underline-offset-4 hover:underline"
        >
          {account("backToAccount")}
        </Link>
      </p>
    </div>
  );
}

export function IdentityPage() {
  return (
    <RequireAccount>
      <IdentityForm />
    </RequireAccount>
  );
}
