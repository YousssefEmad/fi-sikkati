"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { SuggestInput } from "@/components/ui/suggest-input";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { getVerification, submitDriver, uploadLicence } from "@/features/verification/api";
import {
  createVehicle,
  deactivateVehicle,
  listVehicles,
  uploadVehicleDocument,
  type Vehicle,
} from "@/features/vehicles/api";
import {
  colorOptions,
  makeOptions,
  modelOptions,
  seatOptions,
  yearOptions,
} from "@/features/vehicles/catalog";
import { Link } from "@/i18n/navigation";

const VEHICLE_TYPES = ["SEDAN", "HATCHBACK", "SUV", "VAN", "MINIBUS", "OTHER"] as const;

function DriveForm() {
  const t = useTranslations("Drive");
  const vehicles = useTranslations("Vehicles");
  const locale = useLocale();
  const account = useTranslations("Account");
  const { account: session } = useSession();
  const queryClient = useQueryClient();
  const verification = useQuery({ queryKey: ["verification", "me"], queryFn: getVerification });
  const vehicleQuery = useQuery({ queryKey: ["vehicles", "mine"], queryFn: listVehicles });
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [licenceFileId, setLicenceFileId] = useState<string | null>(null);
  const [expiry, setExpiry] = useState("");
  const [make, setMake] = useState("");
  const [makeId, setMakeId] = useState<string | null>(null);
  const [model, setModel] = useState("");
  const [year, setYear] = useState("2020");
  const [color, setColor] = useState("");
  const [vehicleType, setVehicleType] = useState<(typeof VEHICLE_TYPES)[number]>("SEDAN");
  const [typeLabel, setTypeLabel] = useState("");
  const [seats, setSeats] = useState("5");
  const [plate, setPlate] = useState("");

  const identityApproved = verification.data?.identityStatus === "APPROVED";
  const fleet = vehicleQuery.data ?? [];

  async function onCreateVehicle(): Promise<void> {
    setBusy(true);
    setError(undefined);
    try {
      await createVehicle({
        make,
        model,
        year: Number(year),
        color,
        vehicleType,
        seatCapacity: Number(seats),
        plateNumber: plate,
      });
      await queryClient.invalidateQueries({ queryKey: ["vehicles", "mine"] });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : vehicles("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function onVehicleFile(
    vehicleId: string,
    documentType: "REGISTRATION_FRONT" | "REGISTRATION_BACK" | "VEHICLE_PHOTO",
    file: File | undefined,
  ): Promise<void> {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      await uploadVehicleDocument(vehicleId, documentType, file);
      await queryClient.invalidateQueries({ queryKey: ["vehicles", "mine"] });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : vehicles("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function onLicence(file: File | undefined): Promise<void> {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      const uploaded = await uploadLicence(file);
      setLicenceFileId(uploaded.fileId);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function onApply(vehicle: Vehicle): Promise<void> {
    if (!licenceFileId || !expiry) return;
    setBusy(true);
    setError(undefined);
    try {
      queryClient.setQueryData(
        ["verification", "me"],
        await submitDriver({
          vehicleId: vehicle.id,
          licenceExpiresOn: expiry,
          licenceFileId,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  const driverStatus = verification.data?.driver.status;
  const acceptedDriver =
    session?.roles.includes("DRIVER") === true || driverStatus === "APPROVED";
  const shownStatus = driverStatus ?? (acceptedDriver ? "APPROVED" : undefined);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2">{t("intro")}</p>
      <p className="mt-3 text-sm">
        {t("status", { status: shownStatus ? t(shownStatus) : t("none") })}
      </p>
      {acceptedDriver ? (
        <p className="mt-4">
          <Link
            href="/trips/new"
            className="text-primary font-semibold underline-offset-4 hover:underline"
          >
            {t("publishTrip")}
          </Link>
        </p>
      ) : null}
      {identityApproved ? null : (
        <p className="bg-brand-soft mt-4 rounded-md px-4 py-3 text-sm">
          {t("needIdentity")}
          <Link href="/me/verification" className="ms-1 font-semibold underline">
            {account("navVerification")}
          </Link>
        </p>
      )}

      <section className="mt-10">
        <h2 className="text-xl font-bold">{vehicles("title")}</h2>
        {fleet.length === 0 ? (
          <p className="text-muted-foreground mt-2 text-sm">{vehicles("empty")}</p>
        ) : null}
        <ul className="mt-4 space-y-4">
          {fleet.map((vehicle) => (
            <li key={vehicle.id} className="border-border rounded-lg border p-4">
              <p className="font-semibold">
                {vehicles("summary", {
                  make: vehicle.make,
                  model: vehicle.model,
                  plate: vehicle.plateNumber,
                })}
              </p>
              <p className="text-muted-foreground text-sm">
                {vehicles("status", { status: vehicle.verificationStatus })}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">{vehicles("plateHint")}</p>
              <div className="mt-3 space-y-2 text-sm">
                {(["REGISTRATION_FRONT", "REGISTRATION_BACK", "VEHICLE_PHOTO"] as const).map(
                  (doc) => {
                    const fieldId = `vehicle-${vehicle.id}-${doc}`;
                    const label =
                      doc === "REGISTRATION_FRONT"
                        ? vehicles("front")
                        : doc === "REGISTRATION_BACK"
                          ? vehicles("back")
                          : vehicles("photo");
                    return (
                      <label key={doc} htmlFor={fieldId} className="block font-semibold">
                        {label}
                        <input
                          id={fieldId}
                          className="mt-1 block font-normal"
                          type="file"
                          accept="image/jpeg,image/png,application/pdf"
                          aria-label={label}
                          disabled={busy || vehicle.verificationStatus === "APPROVED"}
                          onChange={(event) => {
                            void onVehicleFile(vehicle.id, doc, event.target.files?.[0]);
                          }}
                        />
                      </label>
                    );
                  },
                )}
              </div>
              {vehicle.status === "ACTIVE" ? (
                <Button
                  className="mt-3"
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  onClick={() => {
                    void deactivateVehicle(vehicle.id).then(() =>
                      queryClient.invalidateQueries({ queryKey: ["vehicles", "mine"] }),
                    );
                  }}
                >
                  {vehicles("deactivate")}
                </Button>
              ) : null}
              {(identityApproved || verification.data?.identityStatus === "PENDING") &&
              licenceFileId &&
              expiry &&
              vehicle.verificationStatus !== "APPROVED" ? (
                <Button className="ms-2 mt-3" disabled={busy} onClick={() => void onApply(vehicle)}>
                  {busy ? t("submitting") : t("submit")}
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10 space-y-4">
        <h2 className="text-xl font-bold">{vehicles("add")}</h2>
        <Field id="make" label={vehicles("make")}>
          <SuggestInput
            id="make"
            value={make}
            options={makeOptions(locale)}
            onValueChange={(value) => {
              setMake(value);
              setMakeId(null);
            }}
            onPick={(option) => {
              setMakeId(option.id);
            }}
          />
        </Field>
        <Field id="model" label={vehicles("model")}>
          <SuggestInput
            id="model"
            value={model}
            options={modelOptions(locale, makeId)}
            onValueChange={setModel}
          />
        </Field>
        <Field id="year" label={vehicles("year")}>
          <SuggestInput id="year" value={year} options={yearOptions()} onValueChange={setYear} />
        </Field>
        <Field id="color" label={vehicles("color")}>
          <SuggestInput
            id="color"
            value={color}
            options={colorOptions(locale)}
            onValueChange={setColor}
          />
        </Field>
        <Field id="vehicleType" label={vehicles("type")}>
          <SuggestInput
            id="vehicleType"
            value={typeLabel || vehicles(`types.${vehicleType}`)}
            options={VEHICLE_TYPES.map((option) => ({
              id: option,
              label: vehicles(`types.${option}`),
              pinned: true,
            }))}
            onValueChange={setTypeLabel}
            onPick={(option) => {
              setVehicleType(option.id as (typeof VEHICLE_TYPES)[number]);
              setTypeLabel(option.label);
            }}
          />
        </Field>
        <Field id="seats" label={vehicles("seats")}>
          <SuggestInput id="seats" value={seats} options={seatOptions()} onValueChange={setSeats} />
        </Field>
        <Field id="plate" label={vehicles("plate")} hint={vehicles("plateHint")}>
          <TextInput
            id="plate"
            value={plate}
            onChange={(event) => {
              setPlate(event.target.value);
            }}
          />
        </Field>
        <Button disabled={busy} onClick={() => void onCreateVehicle()}>
          {busy ? vehicles("saving") : vehicles("save")}
        </Button>
      </section>

      <section className="mt-10 space-y-4">
        <h2 className="text-xl font-bold">{t("licence")}</h2>
        <label htmlFor="licence-file" className="block text-sm font-semibold">
          {t("uploadLicence")}
          <input
            id="licence-file"
            className="mt-1 block"
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            aria-label={t("uploadLicence")}
            disabled={busy || !identityApproved}
            onChange={(event) => {
              void onLicence(event.target.files?.[0]);
            }}
          />
        </label>
        <Field id="licenceExpiry" label={t("licenceExpiry")}>
          <TextInput
            id="licenceExpiry"
            type="date"
            value={expiry}
            onChange={(event) => {
              setExpiry(event.target.value);
            }}
          />
        </Field>
      </section>

      {error ? <FormError message={error} /> : null}
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

export function DrivePage() {
  return (
    <RequireAccount>
      <DriveForm />
    </RequireAccount>
  );
}
