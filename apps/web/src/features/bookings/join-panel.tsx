"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { SuggestInput } from "@/components/ui/suggest-input";
import { ApiRequestError } from "@/features/auth/api";
import {
  acceptRequest,
  cancelRequest,
  createJoinRequest,
  listMyRequests,
  listTripRequests,
  rejectRequest,
} from "@/features/bookings/api";
import { PlaceSuggest, type PickedPlace } from "@/features/places/place-suggest";
import { seatOptions } from "@/features/vehicles/catalog";
import { Link } from "@/i18n/navigation";

export function JoinPanel({
  tripId,
  focusRequestId,
  isDriver,
  tripStatus,
  identityStatus,
  emailVerified,
  phoneVerified,
}: {
  tripId: string;
  focusRequestId?: string | null;
  isDriver: boolean;
  tripStatus: string;
  identityStatus: string;
  emailVerified: boolean;
  phoneVerified: boolean;
}) {
  if (isDriver) {
    return <DriverRequests tripId={tripId} focusRequestId={focusRequestId ?? null} />;
  }
  return (
    <PassengerRequest
      tripId={tripId}
      tripStatus={tripStatus}
      identityStatus={identityStatus}
      emailVerified={emailVerified}
      phoneVerified={phoneVerified}
    />
  );
}

function DriverRequests({
  tripId,
  focusRequestId,
}: {
  tripId: string;
  focusRequestId?: string | null;
}) {
  const t = useTranslations("Bookings");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["join-requests", "trip", tripId],
    queryFn: () => listTripRequests(tripId),
    refetchInterval: 10_000,
  });
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState<string | undefined>();
  const items = query.data ?? [];

  useEffect(() => {
    if (!focusRequestId) return;
    document.getElementById(`join-request-${focusRequestId}`)?.scrollIntoView({ block: "center" });
  }, [focusRequestId, query.data]);

  async function act(requestId: string, kind: "accept" | "reject"): Promise<void> {
    setBusy(requestId);
    setError(undefined);
    try {
      if (kind === "accept") await acceptRequest(requestId);
      else await rejectRequest(requestId);
      await queryClient.invalidateQueries({ queryKey: ["join-requests", "trip", tripId] });
      await queryClient.invalidateQueries({ queryKey: ["trips", tripId] });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <section className="mt-8">
      <h2 className="text-xl font-bold">{t("incomingTitle")}</h2>
      {items.length === 0 ? <p className="text-muted-foreground mt-3 text-sm">{t("empty")}</p> : null}
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            id={`join-request-${item.id}`}
            className={
              item.id === focusRequestId
                ? "border-brand bg-brand-soft rounded-lg border p-4"
                : "border-border rounded-lg border p-4"
            }
          >
            <p className="font-semibold">{item.passengerDisplayName}</p>
            <p className="text-muted-foreground mt-1 text-sm">
              {t("requestLine", {
                seats: item.seatsRequested,
                status: t(`status.${item.status}`),
                pickup: item.pickupLabel,
                dropoff: item.dropoffLabel,
              })}
            </p>
            {item.note ? <p className="mt-2 text-sm">{item.note}</p> : null}
            <p className="mt-2 text-sm">
              {t("metaLine", {
                verification: item.passengerIdentityVerified ? t("verified") : t("unverified"),
                cancellations: t("cancellations", {
                  count: item.passengerCancellationsLast90Days,
                }),
              })}
            </p>
            {item.status === "PENDING" ? (
              <div className="mt-3 flex gap-2">
                <Button disabled={busy === item.id} onClick={() => void act(item.id, "accept")}>
                  {t("accept")}
                </Button>
                <Button
                  variant="outline"
                  disabled={busy === item.id}
                  onClick={() => void act(item.id, "reject")}
                >
                  {t("reject")}
                </Button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      {error ? <FormError message={error} /> : null}
    </section>
  );
}

function PassengerRequest({
  tripId,
  tripStatus,
  identityStatus,
  emailVerified,
  phoneVerified,
}: {
  tripId: string;
  tripStatus: string;
  identityStatus: string;
  emailVerified: boolean;
  phoneVerified: boolean;
}) {
  const t = useTranslations("Bookings");
  const queryClient = useQueryClient();
  const mine = useQuery({ queryKey: ["join-requests", "mine"], queryFn: listMyRequests });
  const existing = (mine.data ?? []).find((item) => item.tripId === tripId);
  const [seats, setSeats] = useState("1");
  const [note, setNote] = useState("");
  const [pickupQuery, setPickupQuery] = useState("");
  const [dropoffQuery, setDropoffQuery] = useState("");
  const [pickup, setPickup] = useState<PickedPlace | null>(null);
  const [dropoff, setDropoff] = useState<PickedPlace | null>(null);
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  if (!emailVerified) {
    return <p className="bg-brand-soft mt-8 rounded-md px-4 py-3 text-sm">{t("needEmail")}</p>;
  }
  if (!phoneVerified) {
    return (
      <p className="bg-brand-soft mt-8 rounded-md px-4 py-3 text-sm">
        {t("needPhone")}{" "}
        <Link href="/me" className="font-semibold underline-offset-4 hover:underline">
          {t("phoneLink")}
        </Link>
      </p>
    );
  }
  if (identityStatus !== "APPROVED") {
    return (
      <p className="bg-brand-soft mt-8 rounded-md px-4 py-3 text-sm">
        {t("needIdentity")}{" "}
        <Link href="/me/verification" className="font-semibold underline-offset-4 hover:underline">
          {t("verifyLink")}
        </Link>
      </p>
    );
  }
  if (existing && (existing.status === "PENDING" || existing.status === "ACCEPTED")) {
    return (
      <section className="mt-8">
        <p className="text-sm">{t(`status.${existing.status}`)}</p>
        <Button
          className="mt-3"
          variant="outline"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            setError(undefined);
            void cancelRequest(existing.id)
              .then(async () => {
                await queryClient.invalidateQueries({ queryKey: ["join-requests", "mine"] });
                await queryClient.invalidateQueries({ queryKey: ["trips", tripId] });
              })
              .catch((err: unknown) => {
                setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
              })
              .finally(() => {
                setBusy(false);
              });
          }}
        >
          {t("cancel")}
        </Button>
        {error ? <FormError message={error} /> : null}
      </section>
    );
  }
  if (tripStatus !== "PUBLISHED") return null;

  async function submit(): Promise<void> {
    if (!pickup || !dropoff) return;
    setBusy(true);
    setError(undefined);
    try {
      await createJoinRequest(tripId, {
        seatsRequested: Number(seats),
        pickup: { lat: pickup.lat, lng: pickup.lng, label: pickup.label },
        dropoff: { lat: dropoff.lat, lng: dropoff.lng, label: dropoff.label },
        note: note.trim() || null,
      });
      await queryClient.invalidateQueries({ queryKey: ["join-requests", "mine"] });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8">
      <h2 className="text-xl font-bold">{t("requestTitle")}</h2>
      <div className="mt-4 space-y-4">
        <Field id="pickup" label={t("pickup")}>
          <PlaceSuggest
            id="pickup"
            value={pickupQuery}
            onValueChange={setPickupQuery}
            onPick={setPickup}
          />
        </Field>
        <Field id="dropoff" label={t("dropoff")}>
          <PlaceSuggest
            id="dropoff"
            value={dropoffQuery}
            onValueChange={setDropoffQuery}
            onPick={setDropoff}
          />
        </Field>
        <Field id="seats" label={t("seats")}>
          <SuggestInput id="seats" value={seats} options={seatOptions(6)} onValueChange={setSeats} />
        </Field>
        <Field id="note" label={t("note")}>
          <TextInput
            id="note"
            value={note}
            onChange={(event) => {
              setNote(event.target.value);
            }}
          />
        </Field>
        <Button disabled={busy || !pickup || !dropoff} onClick={() => void submit()}>
          {busy ? t("sending") : t("submit")}
        </Button>
        {error ? <FormError message={error} /> : null}
      </div>
    </section>
  );
}
