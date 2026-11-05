"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { SuggestInput } from "@/components/ui/suggest-input";
import { apiErrorMessage } from "@/lib/api/error-message";
import { RequireAccount } from "@/features/auth/require-account";
import { PlaceSuggest, type PickedPlace } from "@/features/places/place-suggest";
import { searchTrips, type SearchTripItem } from "@/features/search/api";
import { seatOptions } from "@/features/vehicles/catalog";
import { Link } from "@/i18n/navigation";

function ResultCard({ item }: { item: SearchTripItem }) {
  const t = useTranslations("Search");
  return (
    <li className="border-border rounded-xl border p-5">
      <p className="text-lg font-bold">
        {t("summary", { origin: item.originLabel, destination: item.destinationLabel })}
      </p>
      <p className="text-muted-foreground mt-2 text-base">
        {t("driverLine", { kind: t(`match.${item.matchKind}`), name: item.driver.displayName })}
      </p>
      <p className="text-foreground mt-2 text-base font-semibold">
        {t("seatsLeft", { available: item.availableSeats, total: item.totalSeats })}
      </p>
      {item.pricePerSeatMinor !== null ? (
        <p className="text-brand-strong mt-1 text-base font-bold">
          {t("price", { amount: (item.pricePerSeatMinor / 100).toFixed(0) })}
        </p>
      ) : null}
      <Link
        href={`/trips/${item.tripId}`}
        className="bg-brand text-brand-foreground mt-4 inline-flex min-h-12 items-center justify-center rounded-full px-5 text-base font-bold"
      >
        {t("viewTrip")}
      </Link>
    </li>
  );
}

function SearchForm() {
  const t = useTranslations("Search");
  const errorsT = useTranslations("Errors");
  const [originQuery, setOriginQuery] = useState("");
  const [destQuery, setDestQuery] = useState("");
  const [origin, setOrigin] = useState<PickedPlace | null>(null);
  const [destination, setDestination] = useState<PickedPlace | null>(null);
  const [day, setDay] = useState("");
  const [clock, setClock] = useState("");
  const [seats, setSeats] = useState("1");
  const [submitted, setSubmitted] = useState(false);

  const results = useQuery({
    queryKey: [
      "search",
      origin?.lat,
      origin?.lng,
      destination?.lat,
      destination?.lng,
      day,
      clock,
      seats,
    ],
    queryFn: () =>
      searchTrips({
        pickupLat: origin?.lat ?? 0,
        pickupLng: origin?.lng ?? 0,
        dropoffLat: destination?.lat ?? 0,
        dropoffLng: destination?.lng ?? 0,
        date: day,
        seats: Number(seats),
        ...(clock ? { time: clock } : {}),
      }),
    enabled: submitted && origin !== null && destination !== null && day !== "",
  });

  function onSubmit(): void {
    if (!origin || !destination || !day) return;
    setSubmitted(true);
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2">{t("intro")}</p>
      <div className="mt-8 space-y-4">
        <Field id="pickup" label={t("pickup")}>
          <PlaceSuggest
            id="pickup"
            value={originQuery}
            onValueChange={setOriginQuery}
            onPick={setOrigin}
          />
        </Field>
        <Field id="dropoff" label={t("dropoff")}>
          <PlaceSuggest
            id="dropoff"
            value={destQuery}
            onValueChange={setDestQuery}
            onPick={setDestination}
          />
        </Field>
        <Field id="day" label={t("date")}>
          <TextInput
            id="day"
            type="date"
            value={day}
            onChange={(event) => {
              setDay(event.target.value);
            }}
          />
        </Field>
        <Field id="clock" label={t("time")}>
          <TextInput
            id="clock"
            type="time"
            value={clock}
            onChange={(event) => {
              setClock(event.target.value);
            }}
          />
        </Field>
        <Field id="seats" label={t("seats")}>
          <SuggestInput
            id="seats"
            value={seats}
            options={seatOptions(6)}
            onValueChange={setSeats}
          />
        </Field>
        {results.isError ? (
          <FormError
            message={
              apiErrorMessage(results.error, errorsT)
            }
          />
        ) : null}
        <Button
          disabled={!origin || !destination || !day || results.isFetching}
          onClick={() => {
            onSubmit();
          }}
        >
          {t("submit")}
        </Button>
      </div>
      {results.isFetching ? (
        <p className="text-muted-foreground mt-8 text-sm">{t("loading")}</p>
      ) : null}
      {results.isFetched && !results.isFetching && (results.data ?? []).length === 0 ? (
        <p className="text-muted-foreground mt-8 text-sm">{t("empty")}</p>
      ) : null}
      <ul className="mt-8 space-y-3">
        {(results.data ?? []).map((item) => (
          <ResultCard key={item.tripId} item={item} />
        ))}
      </ul>
    </div>
  );
}

export function SearchPage() {
  return (
    <RequireAccount>
      <SearchForm />
    </RequireAccount>
  );
}
