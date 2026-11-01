"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import {
  approveDriver,
  approveIdentity,
  approveVehicleRegistration,
  documentDownloadUrl,
  getAdminVehicle,
  getIdentityReview,
  listDriverQueue,
  listIdentityQueue,
  rejectDriver,
  rejectIdentity,
  rejectVehicle,
} from "@/features/admin/api";
import { Link } from "@/i18n/navigation";

function AdminQueue() {
  const t = useTranslations("Admin");
  const accountT = useTranslations("Account");
  const { account } = useSession();
  const queryClient = useQueryClient();
  const identity = useQuery({ queryKey: ["admin", "identity"], queryFn: listIdentityQueue });
  const drivers = useQuery({ queryKey: ["admin", "driver"], queryFn: listDriverQueue });
  const params = useSearchParams();
  const focusUser = params.get("user");
  const focusVehicle = params.get("vehicle");
  const requestedKind = params.get("kind");
  const focusKind =
    requestedKind === "driver" || requestedKind === "vehicle" ? requestedKind : "identity";
  const focusKey = focusUser ? `${focusKind}:${focusUser}` : "";
  const [selected, setSelected] = useState<string | null>(focusUser);
  const [kind, setKind] = useState<"identity" | "driver" | "vehicle">(focusKind);
  const [appliedFocus, setAppliedFocus] = useState(focusKey);
  if (focusKey !== appliedFocus) {
    setAppliedFocus(focusKey);
    if (focusUser) {
      setSelected(focusUser);
      setKind(focusKind);
    }
  }
  const staff =
    account?.roles.includes("ADMIN") === true || account?.roles.includes("SUPER_ADMIN") === true;
  const detail = useQuery({
    queryKey: ["admin", "detail", selected],
    queryFn: () => getIdentityReview(selected ?? ""),
    enabled: selected !== null,
  });
  const vehicleId = focusVehicle ?? detail.data?.driver.vehicleId ?? null;
  const vehicle = useQuery({
    queryKey: ["admin", "vehicle", vehicleId],
    queryFn: () => getAdminVehicle(vehicleId ?? ""),
    enabled: vehicleId !== null,
  });
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  if (account && !staff) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">{t("staffOnly")}</p>
      </div>
    );
  }

  async function openFile(fileId: string): Promise<void> {
    const url = await documentDownloadUrl(fileId);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function decide(approved: boolean): Promise<void> {
    if (!selected) return;
    setBusy(true);
    setError(undefined);
    try {
      if (kind === "vehicle") {
        if (!vehicleId) return;
        if (approved) await approveVehicleRegistration(selected, vehicleId);
        else await rejectVehicle(vehicleId, reason);
      } else if (kind === "identity") {
        if (approved) await approveIdentity(selected);
        else await rejectIdentity(selected, reason);
      } else if (approved) {
        await approveDriver(selected);
      } else {
        await rejectDriver(selected, reason);
      }
      setSelected(null);
      await queryClient.invalidateQueries({ queryKey: ["admin"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      {selected && detail.data ? (
        <section className="mt-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelected(null);
            }}
          >
            {t("back")}
          </Button>
          <p className="text-muted-foreground mt-4 text-sm">{t("reviewHint")}</p>
          <ul className="mt-4 space-y-3">
            {detail.data.identityDocuments.map((doc) => (
              <li
                key={doc.id}
                className="border-border flex items-center justify-between rounded-lg border p-3"
              >
                <span>
                  {t("documentLabel", { type: doc.documentType, name: doc.originalName })}
                </span>
                <Button variant="outline" size="sm" onClick={() => void openFile(doc.fileId)}>
                  {t("openFile")}
                </Button>
              </li>
            ))}
            {detail.data.driver.licenceFileId ? (
              <li className="border-border flex items-center justify-between rounded-lg border p-3">
                <span>{detail.data.driver.licenceOriginalName}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void openFile(detail.data.driver.licenceFileId ?? "")}
                >
                  {t("openFile")}
                </Button>
              </li>
            ) : null}
            {vehicle.data ? (
              <li className="border-border rounded-lg border p-3">
                <p className="font-semibold">
                  {t("vehicleSummary", {
                    make: vehicle.data.make,
                    model: vehicle.data.model,
                    year: vehicle.data.year,
                    color: vehicle.data.color,
                    plate: vehicle.data.plateNumber,
                  })}
                </p>
                <ul className="mt-3 space-y-2">
                  {vehicle.data.documents.map((doc) => (
                    <li key={doc.id} className="flex items-center justify-between gap-3">
                      <span>
                        {t("documentLabel", { type: doc.documentType, name: doc.originalName })}
                      </span>
                      <Button variant="outline" size="sm" onClick={() => void openFile(doc.fileId)}>
                        {t("openFile")}
                      </Button>
                    </li>
                  ))}
                </ul>
              </li>
            ) : null}
          </ul>
          <div className="mt-6">
            <Field id="reason" label={t("reason")}>
              <TextInput
                id="reason"
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value);
                }}
              />
            </Field>
          </div>
          {error ? <FormError message={error} /> : null}
          <div className="mt-4 flex gap-3">
            <Button disabled={busy} onClick={() => void decide(true)}>
              {t("approve")}
            </Button>
            <Button
              variant="outline"
              disabled={busy || reason.trim().length < 3}
              onClick={() => void decide(false)}
            >
              {t("reject")}
            </Button>
          </div>
        </section>
      ) : (
        <>
          <section className="mt-8">
            <h2 className="text-xl font-bold">{t("identity")}</h2>
            <ul className="mt-3 space-y-2">
              {(identity.data?.items ?? []).map((item) => (
                <li key={item.userId}>
                  <button
                    type="button"
                    className="text-primary font-semibold underline-offset-4 hover:underline"
                    onClick={() => {
                      setKind("identity");
                      setSelected(item.userId);
                    }}
                  >
                    {t("applicant", { name: item.displayName, email: item.email })}
                  </button>
                </li>
              ))}
            </ul>
            {identity.data?.totalCount === 0 ? (
              <p className="text-muted-foreground mt-2 text-sm">{t("empty")}</p>
            ) : null}
          </section>
          <section className="mt-8">
            <h2 className="text-xl font-bold">{t("driver")}</h2>
            <ul className="mt-3 space-y-2">
              {(drivers.data?.items ?? []).map((item) => (
                <li key={item.verificationId}>
                  <button
                    type="button"
                    className="text-primary font-semibold underline-offset-4 hover:underline"
                    onClick={() => {
                      setKind("driver");
                      setSelected(item.userId);
                    }}
                  >
                    {t("applicant", { name: item.displayName, email: item.email })}
                  </button>
                </li>
              ))}
            </ul>
            {drivers.data?.totalCount === 0 ? (
              <p className="text-muted-foreground mt-2 text-sm">{t("empty")}</p>
            ) : null}
          </section>
        </>
      )}
      <p className="mt-8">
        <Link
          href="/me"
          className="text-primary text-sm font-semibold underline-offset-4 hover:underline"
        >
          {accountT("backToAccount")}
        </Link>
      </p>
    </div>
  );
}

export function AdminQueuePage() {
  return (
    <RequireAccount>
      <AdminQueue />
    </RequireAccount>
  );
}
