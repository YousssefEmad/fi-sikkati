"use client";

import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { apiJson } from "@/lib/api/json";

type TripItem = {
  id: string;
  driverDisplayName: string;
  status: string;
  originLabel: string;
  destinationLabel: string;
  departureAt: string;
  availableSeats: number;
  totalSeats: number;
  createdAt: string;
};

function isStaff(roles: readonly string[]): boolean {
  return roles.includes("ADMIN") || roles.includes("SUPER_ADMIN");
}

function formatDate(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "ar-EG", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function AdminTripsPage() {
  return (
    <RequireAccount>
      <TripsConsole />
    </RequireAccount>
  );
}

function TripsConsole() {
  const t = useTranslations("AdminDash");
  const locale = useLocale();
  const { account } = useSession();
  const query = useQuery({
    queryKey: ["admin", "trips"],
    queryFn: () =>
      apiJson<{ items: TripItem[]; totalCount: number }>("/api/v1/admin/trips?page_size=50"),
    enabled: Boolean(account && isStaff(account.roles)),
  });

  if (account && !isStaff(account.roles)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="text-2xl font-extrabold">{t("forbidden")}</h1>
      </div>
    );
  }

  const items = query.data?.items ?? [];

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <p className="text-muted-foreground text-sm">
        <Link href="/admin" className="underline-offset-4 hover:underline">
          {t("title")}
        </Link>
      </p>
      <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{t("navTrips")}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("count", { n: query.data?.totalCount ?? 0 })}</p>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-[color:var(--border)]">
        <table className="min-w-full text-start text-sm">
          <thead className="bg-[color:var(--surface-muted)] text-[color:var(--muted-foreground)]">
            <tr>
              <th className="px-4 py-3 font-semibold">{t("tripRoute")}</th>
              <th className="px-4 py-3 font-semibold">{t("tripDriver")}</th>
              <th className="px-4 py-3 font-semibold">{t("colStatus")}</th>
              <th className="px-4 py-3 font-semibold">{t("tripDeparture")}</th>
              <th className="px-4 py-3 font-semibold">{t("tripSeats")}</th>
            </tr>
          </thead>
          <tbody>
            {query.isPending
              ? Array.from({ length: 5 }, (_, index) => (
                  <tr key={index} className="border-t border-[color:var(--border)]">
                    <td className="px-4 py-3" colSpan={5}>
                      <Skeleton className="h-10 w-full" />
                    </td>
                  </tr>
                ))
              : null}
            {!query.isPending && items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10">
                  <EmptyState title={t("empty")} />
                </td>
              </tr>
            ) : null}
            {items.map((trip) => (
              <tr key={trip.id} className="border-t border-[color:var(--border)]">
                <td className="px-4 py-3">
                  <p className="font-bold">
                    {trip.originLabel} → {trip.destinationLabel}
                  </p>
                </td>
                <td className="px-4 py-3">{trip.driverDisplayName}</td>
                <td className="px-4 py-3 font-semibold">{trip.status}</td>
                <td className="text-muted-foreground px-4 py-3 whitespace-nowrap">
                  {formatDate(trip.departureAt, locale)}
                </td>
                <td className="px-4 py-3">
                  {trip.availableSeats}/{trip.totalSeats}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
