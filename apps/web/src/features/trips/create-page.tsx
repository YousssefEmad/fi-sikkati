"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, SelectInput, TextInput } from "@/components/ui/field";
import { SuggestInput } from "@/components/ui/suggest-input";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { PlaceSuggest, type PickedPlace } from "@/features/places/place-suggest";
import { createTrip, estimatePrice, previewRoute } from "@/features/trips/api";
import { GoogleRouteMap } from "@/features/trips/route-sketch";
import { listVehicles } from "@/features/vehicles/api";
import { seatOptions } from "@/features/vehicles/catalog";
import { Link, useRouter } from "@/i18n/navigation";

function CreateForm() {
  const t = useTranslations("Trips");
  const auth = useTranslations("Auth");
  const account = useTranslations("Account");
  const { account: session, refreshing } = useSession();
  const router = useRouter();
  const queryClient = useQueryClient();
  const vehicles = useQuery({ queryKey: ["vehicles", "mine"], queryFn: listVehicles });
  const fleet = (vehicles.data ?? []).filter(
    (item) => item.status === "ACTIVE" && item.verificationStatus === "APPROVED",
  );
  const [vehicleId, setVehicleId] = useState("");
  const [originQuery, setOriginQuery] = useState("");
  const [destQuery, setDestQuery] = useState("");
  const [origin, setOrigin] = useState<PickedPlace | null>(null);
  const [destination, setDestination] = useState<PickedPlace | null>(null);
  const [when, setWhen] = useState("");
  const [seats, setSeats] = useState("3");
  const [notes, setNotes] = useState("");
  const [preview, setPreview] = useState<{
    coordinates: number[][];
    distanceM: number;
    durationS: number;
  } | null>(null);
  const [price, setPrice] = useState<number | null>(null);
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  const isDriver = session?.roles.includes("DRIVER") === true;

  if (refreshing && !isDriver) {
    return <p className="text-muted-foreground px-4 py-16 text-center">{auth("loading")}</p>;
  }

  async function onPreview(): Promise<void> {
    if (!origin || !destination) return;
    setBusy(true);
    setError(undefined);
    try {
      const route = await previewRoute([
        { lat: origin.lat, lng: origin.lng, label: origin.label },
        { lat: destination.lat, lng: destination.lng, label: destination.label },
      ]);
      setPreview({
        coordinates: route.coordinates,
        distanceM: route.distanceM,
        durationS: route.durationS,
      });
      const quote = await estimatePrice(route.distanceM);
      setPrice(quote.suggestedPriceMinor);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(): Promise<void> {
    if (!origin || !destination || !vehicleId || !when) return;
    setBusy(true);
    setError(undefined);
    try {
      const trip = await createTrip({
        vehicleId,
        departureAt: new Date(when).toISOString(),
        totalSeats: Number(seats),
        stops: [
          { lat: origin.lat, lng: origin.lng, label: origin.label },
          { lat: destination.lat, lng: destination.lng, label: destination.label },
        ],
        notes: notes || null,
      });
      await queryClient.invalidateQueries({ queryKey: ["trips", "mine"] });
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  if (!isDriver) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">{t("needDriver")}</p>
        <Link href="/drive" className="text-primary mt-4 inline-block font-semibold underline">
          {account("navDrive")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("createTitle")}</h1>
      <p className="text-muted-foreground mt-2">{t("createIntro")}</p>
      <div className="mt-8 space-y-4">
        <Field id="vehicle" label={t("vehicle")}>
          <SelectInput
            id="vehicle"
            value={vehicleId}
            onChange={(event) => {
              setVehicleId(event.target.value);
            }}
          >
            <option value="">{t("chooseVehicle")}</option>
            {fleet.map((item) => (
              <option key={item.id} value={item.id}>
                {t("vehicleLabel", { make: item.make, model: item.model })}
              </option>
            ))}
          </SelectInput>
        </Field>
        <Field id="origin" label={t("origin")}>
          <PlaceSuggest
            id="origin"
            value={originQuery}
            onValueChange={setOriginQuery}
            onPick={setOrigin}
          />
        </Field>
        <Field id="destination" label={t("destination")}>
          <PlaceSuggest
            id="destination"
            value={destQuery}
            onValueChange={setDestQuery}
            onPick={setDestination}
          />
        </Field>
        <Field id="when" label={t("departure")}>
          <TextInput
            id="when"
            type="datetime-local"
            value={when}
            onChange={(event) => {
              setWhen(event.target.value);
            }}
          />
        </Field>
        <Field id="seats" label={t("seats")}>
          <SuggestInput id="seats" value={seats} options={seatOptions(6)} onValueChange={setSeats} />
        </Field>
        <Field id="notes" label={t("notes")}>
          <TextInput
            id="notes"
            value={notes}
            onChange={(event) => {
              setNotes(event.target.value);
            }}
          />
        </Field>
        <Button
          variant="outline"
          disabled={busy || !origin || !destination}
          onClick={() => {
            void onPreview();
          }}
        >
          {t("preview")}
        </Button>
        {origin && destination ? (
          <GoogleRouteMap
            points={[
              { lat: origin.lat, lng: origin.lng, label: origin.label },
              { lat: destination.lat, lng: destination.lng, label: destination.label },
            ]}
            label={t("routeSketch")}
          />
        ) : null}
        {price !== null ? (
          <p className="text-sm">
            {t("price", {
              amount: (price / 100).toFixed(0),
              km: preview ? Math.round(preview.distanceM / 1000) : 0,
            })}
          </p>
        ) : null}
        {error ? <FormError message={error} /> : null}
        <Button
          disabled={busy || !origin || !destination || !vehicleId || !when}
          onClick={() => void onCreate()}
        >
          {busy ? t("saving") : t("saveDraft")}
        </Button>
      </div>
    </div>
  );
}

export function CreateTripPage() {
  return (
    <RequireAccount>
      <CreateForm />
    </RequireAccount>
  );
}
