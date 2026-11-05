"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { StatusBadge, identityTone } from "@/components/ui/status-badge";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import {
  getVerification,
  submitIdentity,
  uploadIdentityDocument,
} from "@/features/verification/api";
import { Link } from "@/i18n/navigation";

const TYPES = [
  ["NATIONAL_ID_FRONT", "front", false],
  ["NATIONAL_ID_BACK", "back", true],
  ["SELFIE", "selfie", true],
] as const;

/** Identity upload UI; ``embedded`` hides the page chrome for the setup wizard. */
export function IdentityPageInner({ embedded = false }: { embedded?: boolean }) {
  const t = useTranslations("Verification");
  const accountT = useTranslations("Account");
  const { refreshAccount } = useSession();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["verification", "me"], queryFn: getVerification });
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState<string | null>(null);
  const status = query.data;
  const locked = status?.identityStatus === "PENDING" || status?.identityStatus === "APPROVED";
  const hasFront = Boolean(
    status?.identityDocuments.find((doc) => doc.documentType === "NATIONAL_ID_FRONT"),
  );

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
      await refreshAccount();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.submit"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={embedded ? undefined : "mx-auto w-full max-w-3xl px-4 py-12 sm:px-6"}>
      {embedded ? null : (
        <>
          <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground mt-2 text-base">{t("intro")}</p>
        </>
      )}
      {status ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <StatusBadge tone={identityTone(status.identityStatus)}>
            {accountT(`verificationBadge.${status.identityStatus}`)}
          </StatusBadge>
          <p className="text-muted-foreground text-sm">
            {accountT(`verificationStatus.${status.identityStatus}`)}
          </p>
        </div>
      ) : null}
      {status ? (
        <p className="text-muted-foreground mt-2 text-sm">
          {t("sla", { hours: status.reviewSlaHours })}
        </p>
      ) : null}
      {status?.identityRejectionReason ? (
        <p className="bg-danger/10 text-danger mt-4 rounded-xl px-4 py-3 text-sm font-semibold">
          {t("rejection", { reason: status.identityRejectionReason })}
        </p>
      ) : null}
      {locked ? <p className="text-muted-foreground mt-4 text-sm font-semibold">{t("locked")}</p> : null}
      <ul className="mt-6 space-y-4">
        {TYPES.map(([documentType, key, optional]) => {
          const uploaded = status?.identityDocuments.find(
            (doc) => doc.documentType === documentType,
          );
          return (
            <li key={documentType} className="border-border rounded-xl border p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-base font-bold">{t(key)}</p>
                {optional ? (
                  <StatusBadge tone="muted">{t("optional")}</StatusBadge>
                ) : (
                  <StatusBadge tone="warning">{t("required")}</StatusBadge>
                )}
              </div>
              {key === "selfie" ? (
                <p className="text-muted-foreground mt-2 text-sm">{t("selfieHint")}</p>
              ) : null}
              {key === "back" ? (
                <p className="text-muted-foreground mt-2 text-sm">{t("backHint")}</p>
              ) : null}
              {uploaded ? (
                <StatusBadge tone="success" className="mt-2">
                  {t("uploaded", { name: uploaded.originalName })}
                </StatusBadge>
              ) : (
                <StatusBadge tone="muted" className="mt-2">
                  {optional ? t("optionalMissing") : t("missing")}
                </StatusBadge>
              )}
              {locked ? null : (
                <label
                  htmlFor={`identity-${documentType}`}
                  className="mt-3 block text-sm font-bold"
                >
                  {t("choose")}
                  <input
                    id={`identity-${documentType}`}
                    className="mt-1 block w-full text-sm font-normal"
                    type="file"
                    accept={
                      documentType === "SELFIE"
                        ? "image/jpeg,image/png"
                        : "image/jpeg,image/png,application/pdf"
                    }
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
        <Button
          className="mt-6"
          size="lg"
          disabled={busy !== null || !hasFront}
          onClick={() => void onSubmit()}
        >
          {busy === "submit" ? t("submitting") : t("submit")}
        </Button>
      )}
      {locked ? null : (
        <p className="text-muted-foreground mt-3 text-sm">{t("submitHint")}</p>
      )}
      {embedded ? null : (
        <p className="mt-8">
          <Link
            href="/me"
            className="text-primary text-base font-bold underline-offset-4 hover:underline"
          >
            {accountT("backToAccount")}
          </Link>
        </p>
      )}
    </div>
  );
}

export function IdentityPage() {
  return (
    <RequireAccount>
      <IdentityPageInner />
    </RequireAccount>
  );
}
