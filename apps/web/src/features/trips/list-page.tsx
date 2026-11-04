"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { RequireAccount } from "@/features/auth/require-account";
import { listMyTrips } from "@/features/trips/api";
import { Link } from "@/i18n/navigation";

function List() {
  const t = useTranslations("Trips");
  const query = useQuery({ queryKey: ["trips", "mine", "driver"], queryFn: () => listMyTrips("driver") });
  const riding = useQuery({
    queryKey: ["trips", "mine", "passenger"],
    queryFn: () => listMyTrips("passenger"),
  });
  const items = query.data ?? [];
  const passengerTrips = riding.data ?? [];
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("listTitle")}</h1>
      <p className="mt-4">
        <Link
          href="/trips/new"
          className="text-primary font-semibold underline-offset-4 hover:underline"
        >
          {t("createTitle")}
        </Link>
      </p>
      {items.length === 0 ? (
        <p className="text-muted-foreground mt-6 text-sm">{t("empty")}</p>
      ) : null}
      <ul className="mt-6 space-y-3">
        {items.map((trip) => (
          <li key={trip.id} className="border-border rounded-lg border p-4">
            <Link
              href={`/trips/${trip.id}`}
              className="font-semibold underline-offset-4 hover:underline"
            >
              {t("summary", { origin: trip.originLabel, destination: trip.destinationLabel })}
            </Link>
            <p className="text-foreground mt-1 text-sm font-bold">{t(`status.${trip.status}`)}</p>
            <p className="mt-1 text-sm">
              {t("seatsFilled", {
                filled: trip.totalSeats - trip.availableSeats,
                available: trip.availableSeats,
                total: trip.totalSeats,
              })}
            </p>
          </li>
        ))}
      </ul>
      <h2 className="mt-10 text-xl font-bold">{t("ridingTitle")}</h2>
      {passengerTrips.length === 0 ? (
        <p className="text-muted-foreground mt-3 text-sm">{t("ridingEmpty")}</p>
      ) : null}
      <ul className="mt-4 space-y-3">
        {passengerTrips.map((trip) => (
          <li key={trip.id} className="border-border rounded-lg border p-4">
            <Link
              href={`/trips/${trip.id}`}
              className="font-semibold underline-offset-4 hover:underline"
            >
              {t("summary", { origin: trip.originLabel, destination: trip.destinationLabel })}
            </Link>
            <p className="text-foreground mt-1 text-sm font-bold">{t(`status.${trip.status}`)}</p>
            <p className="mt-1 text-sm">
              {t("seatsFilled", {
                filled: trip.totalSeats - trip.availableSeats,
                available: trip.availableSeats,
                total: trip.totalSeats,
              })}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function TripListPage() {
  return (
    <RequireAccount>
      <List />
    </RequireAccount>
  );
}
