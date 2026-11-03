"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError } from "@/features/auth/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import {
  cancelTrip,
  completeTrip,
  getTrip,
  publishTrip,
  startTrip,
  updateTrip,
} from "@/features/trips/api";
import { JoinPanel } from "@/features/bookings/join-panel";
import { listMyRequests, listTripRequests } from "@/features/bookings/api";
import { listConversations } from "@/features/chat/api";
import { TripCalls } from "@/features/trips/call-contacts";
import { GoogleRouteMap, type MapPoint } from "@/features/trips/route-sketch";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export function TripDetail({ tripId }: { tripId: string }) {
  const t = useTranslations("Trips");
  const accountT = useTranslations("Account");
  const { account } = useSession();
  const focusRequestId = useSearchParams().get("request");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["trips", tripId],
    queryFn: () => getTrip(tripId),
    refetchInterval: 10_000,
  });
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [notesOverride, setNotesOverride] = useState<string | undefined>();
  const trip = query.data;
  const mine = trip !== undefined && account?.id === trip.driverId;
  const requests = useQuery({
    queryKey: mine ? ["join-requests", "trip", tripId] : ["join-requests", "mine"],
    queryFn: () => (mine ? listTripRequests(tripId) : listMyRequests()),
    enabled: trip !== undefined,
  });
  const chats = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    enabled: trip !== undefined && trip.status !== "DRAFT",
  });
  const tripChat = chats.data?.find((item) => item.tripId === tripId);
  const notes = notesOverride ?? trip?.notes ?? "";
  const editable =
    mine && (trip.status === "DRAFT" || trip.status === "PUBLISHED" || trip.status === "FULL");

  async function act(kind: "publish" | "start" | "complete" | "cancel" | "notes"): Promise<void> {
    if (!trip) return;
    setBusy(true);
    setError(undefined);
    try {
      const next =
        kind === "publish"
          ? await publishTrip(tripId)
          : kind === "start"
            ? await startTrip(tripId)
            : kind === "complete"
              ? await completeTrip(tripId)
              : kind === "cancel"
                ? await cancelTrip(tripId)
                : await updateTrip(tripId, trip.version, { notes });
      queryClient.setQueryData(["trips", tripId], next);
      if (kind === "notes") setNotesOverride(undefined);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      {trip ? (
        <>
          <h1 className="text-3xl font-extrabold tracking-tight">
            {t("summary", { origin: trip.originLabel, destination: trip.destinationLabel })}
          </h1>
          <p className="text-muted-foreground mt-2 text-sm">{t(`status.${trip.status}`)}</p>
          <p className="mt-4 text-sm">
            {t("seatsFilled", {
              filled: trip.totalSeats - trip.availableSeats,
              available: trip.availableSeats,
              total: trip.totalSeats,
            })}
          </p>
          {trip.pricePerSeatMinor !== null ? (
            <p className="mt-2 text-sm">
              {t("price", {
                amount: (trip.pricePerSeatMinor / 100).toFixed(0),
                km: trip.distanceM ? Math.round(trip.distanceM / 1000) : 0,
              })}
            </p>
          ) : null}
          {trip.exactStops ? null : (
            <p className="bg-brand-soft mt-4 rounded-md px-4 py-3 text-sm">
              {t("approximateLocation")}
            </p>
          )}
          <GoogleRouteMap
            points={mapPoints(trip, mine, requests.data ?? [])}
            label={t("routeSketch")}
          />
          {tripChat ? (
            <Link
              href={`/messages/${tripChat.id}`}
              className={cn(buttonVariants({ variant: "brand", size: "lg" }), "mt-4")}
            >
              <MessageCircle aria-hidden="true" className="size-5" />
              {t("tripChat")}
            </Link>
          ) : null}
          {trip.status !== "DRAFT" ? <TripCalls tripId={tripId} /> : null}
          {editable ? (
            <div className="mt-6">
              <Field id="notes" label={t("notes")}>
                <TextInput
                  id="notes"
                  value={notes}
                  onChange={(event) => {
                    setNotesOverride(event.target.value);
                  }}
                />
              </Field>
              <Button
                className="mt-3"
                variant="outline"
                disabled={busy}
                onClick={() => void act("notes")}
              >
                {t("saveNotes")}
              </Button>
            </div>
          ) : null}
          {account ? (
            <JoinPanel
              tripId={tripId}
              focusRequestId={focusRequestId}
              isDriver={mine}
              tripStatus={trip.status}
              identityStatus={account.identityVerificationStatus}
              emailVerified={account.emailVerified}
              phoneVerified={account.phoneVerified}
            />
          ) : null}
          {mine && trip.status === "DRAFT" ? (
            <Button className="mt-6" disabled={busy} onClick={() => void act("publish")}>
              {t("publish")}
            </Button>
          ) : null}
          {mine && (trip.status === "PUBLISHED" || trip.status === "FULL") ? (
            <Button className="mt-6" disabled={busy} onClick={() => void act("start")}>
              {t("start")}
            </Button>
          ) : null}
          {mine && trip.status === "IN_PROGRESS" ? (
            <Button className="mt-6" disabled={busy} onClick={() => void act("complete")}>
              {t("complete")}
            </Button>
          ) : null}
          {mine &&
          trip.status !== "COMPLETED" &&
          trip.status !== "CANCELLED" &&
          trip.status !== "EXPIRED" ? (
            <Button
              className="ms-2 mt-6"
              variant="outline"
              disabled={busy}
              onClick={() => void act("cancel")}
            >
              {t("cancel")}
            </Button>
          ) : null}
        </>
      ) : (
        <p className="text-muted-foreground">{t("loading")}</p>
      )}
      {error ? <FormError message={error} /> : null}
      <p className="mt-8">
        <Link
          href="/me/trips"
          className="text-primary text-sm font-semibold underline-offset-4 hover:underline"
        >
          {t("listTitle")}
        </Link>
        <span className="mx-2" />
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

export function TripDetailPage({ tripId }: { tripId: string }) {
  return (
    <RequireAccount>
      <TripDetail key={tripId} tripId={tripId} />
    </RequireAccount>
  );
}

function mapPoints(
  trip: {
    id: string;
    originLat: number;
    originLng: number;
    originLabel: string;
    destinationLat: number;
    destinationLng: number;
    destinationLabel: string;
  },
  mine: boolean,
  requests: {
    tripId: string;
    status: string;
    pickupLat: number;
    pickupLng: number;
    pickupLabel: string;
    dropoffLat: number;
    dropoffLng: number;
    dropoffLabel: string;
  }[],
): MapPoint[] {
  const origin = { lat: trip.originLat, lng: trip.originLng, label: trip.originLabel };
  const destination = {
    lat: trip.destinationLat,
    lng: trip.destinationLng,
    label: trip.destinationLabel,
  };
  const relevant = requests.filter(
    (item) =>
      (mine || item.tripId === trip.id) &&
      (item.status === "ACCEPTED" || item.status === "PENDING"),
  );
  const stops = relevant.flatMap((item) => [
    { lat: item.pickupLat, lng: item.pickupLng, label: item.pickupLabel },
    { lat: item.dropoffLat, lng: item.dropoffLng, label: item.dropoffLabel },
  ]);
  return dedupePoints([origin, ...stops, destination]);
}

function dedupePoints(points: MapPoint[]): MapPoint[] {
  const kept: MapPoint[] = [];
  for (const point of points) {
    if (!kept.some((other) => sameSpot(point, other))) kept.push(point);
  }
  return kept;
}

function sameSpot(left: MapPoint, right: MapPoint): boolean {
  return Math.abs(left.lat - right.lat) < 0.0002 && Math.abs(left.lng - right.lng) < 0.0002;
}
