"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BadgeCheck,
  CarFront,
  CircleDot,
  Clock,
  MapPin,
  Users,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

type BrowseTrip = {
  id: string;
  originLabel: string;
  destinationLabel: string;
  departureAt: string;
  availableSeats: number;
  totalSeats: number;
  pricePerSeatMinor: number | null;
  currency: string;
};

async function fetchBrowseTrips(): Promise<BrowseTrip[]> {
  const response = await fetch("/api/v1/trips/browse?limit=12", {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return [];
  const payload = (await response.json()) as { items?: BrowseTrip[] };
  return payload.items ?? [];
}

function formatDeparture(iso: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "ar-EG", {
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
      day: "numeric",
      month: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function HomeTripCarousel() {
  const t = useTranslations("Landing.preview");
  const locale = useLocale();
  const { status } = useSession();
  const query = useQuery({
    queryKey: ["trips", "browse"],
    queryFn: fetchBrowseTrips,
    staleTime: 30_000,
  });

  const trips = query.data ?? [];

  return (
    <div className="lg:ps-6">
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <StatusBadge tone="success">{t("label")}</StatusBadge>
        <p className="text-muted-foreground text-xs font-semibold sm:text-sm">{t("scrollHint")}</p>
      </div>

      {query.isPending ? (
        <Card className="shadow-lift mx-auto max-w-md rounded-xl p-6">
          <p className="text-muted-foreground text-base">{t("loading")}</p>
        </Card>
      ) : null}

      {!query.isPending && trips.length === 0 ? (
        <Card className="shadow-lift mx-auto max-w-md rounded-xl p-6">
          <span className="bg-brand text-brand-foreground flex size-11 items-center justify-center rounded-full">
            <CarFront aria-hidden="true" className="size-6" />
          </span>
          <p className="mt-4 text-base font-semibold leading-relaxed">{t("empty")}</p>
          <Link
            href={status === "authenticated" ? "/search" : "/auth/sign-in"}
            className={buttonVariants({ variant: "brand", block: true, className: "mt-5" })}
          >
            {t("action")}
          </Link>
        </Card>
      ) : null}

      {trips.length > 0 ? (
        <div className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 sm:-mx-0 sm:px-0">
          {trips.map((trip) => (
            <Card
              key={trip.id}
              className="shadow-lift w-[min(100%,22rem)] shrink-0 snap-center rounded-xl p-5 sm:p-6"
            >
              <div className="flex items-center gap-3">
                <span className="bg-brand text-brand-foreground flex size-11 items-center justify-center rounded-full">
                  <CarFront aria-hidden="true" className="size-6" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-base font-bold">{t("driver")}</p>
                  <p className="text-success mt-0.5 inline-flex items-center gap-1 text-sm font-bold">
                    <BadgeCheck aria-hidden="true" className="size-4" />
                    {t("driverBadge")}
                  </p>
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <div aria-hidden="true" className="flex flex-col items-center pt-1">
                  <CircleDot className="text-brand-strong size-5" />
                  <span className="border-border-strong my-1.5 w-0 flex-1 border-s-2 border-dashed" />
                  <MapPin className="text-foreground size-5" />
                </div>
                <div className="flex-1 space-y-5">
                  <div>
                    <p className="text-muted-foreground text-xs font-bold uppercase tracking-wide">
                      {t("fromLabel")}
                    </p>
                    <p className="text-base font-bold leading-snug">{trip.originLabel}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs font-bold uppercase tracking-wide">
                      {t("toLabel")}
                    </p>
                    <p className="text-base font-bold leading-snug">{trip.destinationLabel}</p>
                  </div>
                </div>
              </div>

              <div className="border-border text-foreground mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-t pt-4 text-sm font-semibold">
                <span className="inline-flex items-center gap-1.5">
                  <Clock aria-hidden="true" className="size-4" />
                  {formatDeparture(trip.departureAt, locale)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Users aria-hidden="true" className="size-4" />
                  {trip.availableSeats}/{trip.totalSeats}
                </span>
              </div>

              <Link
                href={status === "authenticated" ? `/trips/${trip.id}` : "/auth/sign-in"}
                className={buttonVariants({ variant: "brand", block: true, className: "mt-5" })}
              >
                {t("action")}
              </Link>
              {status === "anonymous" ? (
                <p className="text-muted-foreground mt-2 text-center text-xs">{t("signInHint")}</p>
              ) : null}
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}
