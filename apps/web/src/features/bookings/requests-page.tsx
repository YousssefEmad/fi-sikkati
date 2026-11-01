"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { RequireAccount } from "@/features/auth/require-account";
import { listMyRequests } from "@/features/bookings/api";
import { Link } from "@/i18n/navigation";

function List() {
  const t = useTranslations("Bookings");
  const query = useQuery({ queryKey: ["join-requests", "mine"], queryFn: listMyRequests });
  const items = query.data ?? [];
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("mineTitle")}</h1>
      {items.length === 0 ? <p className="text-muted-foreground mt-6 text-sm">{t("empty")}</p> : null}
      <ul className="mt-6 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="border-border rounded-lg border p-4">
            <Link
              href={`/trips/${item.tripId}`}
              className="font-semibold underline-offset-4 hover:underline"
            >
              {t("requestLine", {
                seats: item.seatsRequested,
                status: t(`status.${item.status}`),
                pickup: item.pickupLabel,
                dropoff: item.dropoffLabel,
              })}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RequestsPage() {
  return (
    <RequireAccount>
      <List />
    </RequireAccount>
  );
}
