"use client";

import { CarFront, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { StatusBadge, identityTone } from "@/components/ui/status-badge";
import { ProfileForm } from "@/features/account/profile-form";
import {
  isDriveSkipped,
  markSetupDone,
  readSetupRole,
  skipDriveTemporarily,
  writeSetupRole,
  type SetupRole,
} from "@/features/account/setup-intent";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { getVerification } from "@/features/verification/api";
import { IdentityPageInner } from "@/features/verification/identity-page";
import { listVehicles } from "@/features/vehicles/api";
import { Link, useRouter } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";

function SetupBody() {
  const t = useTranslations("Setup");
  const accountT = useTranslations("Account");
  const { account, refreshAccount } = useSession();
  const router = useRouter();
  const [role, setRole] = useState<SetupRole | null>(null);
  const [driveSkipped, setDriveSkipped] = useState(false);
  const [ready, setReady] = useState(false);

  const verification = useQuery({
    queryKey: ["verification", "me"],
    queryFn: getVerification,
    enabled: role === "driver",
  });
  const vehicles = useQuery({
    queryKey: ["vehicles", "mine"],
    queryFn: listVehicles,
    enabled: role === "driver",
  });

  useEffect(() => {
    setRole(readSetupRole());
    setDriveSkipped(isDriveSkipped());
    setReady(true);
  }, []);

  if (!account || !ready) return null;

  const identityDone =
    account.identityVerificationStatus === "PENDING" ||
    account.identityVerificationStatus === "APPROVED";
  const profileDone =
    account.displayName.trim().length >= 2 && account.fullName.trim().length >= 2;
  const isAcceptedDriver = account.roles.includes("DRIVER");
  const driverAppPending = verification.data?.driver.status === "PENDING";
  const hasVehicle = (vehicles.data ?? []).length > 0;
  const driverReady = isAcceptedDriver || (hasVehicle && (driverAppPending || identityDone));

  function chooseRole(next: SetupRole) {
    writeSetupRole(next);
    setRole(next);
    if (next === "passenger") {
      skipDriveTemporarily();
      setDriveSkipped(true);
    } else {
      setDriveSkipped(false);
    }
  }

  function onSkipPassenger() {
    skipDriveTemporarily();
    setDriveSkipped(true);
    markSetupDone();
    router.replace("/search");
  }

  async function continueOn() {
    await refreshAccount();
    markSetupDone();
    if (role === "driver") {
      router.replace(driverReady || isAcceptedDriver ? "/trips/new" : "/drive");
      return;
    }
    router.replace("/search");
  }

  if (role === null) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("roleTitle")}</h1>
        <p className="text-muted-foreground mt-3 text-base leading-relaxed">{t("roleBody")}</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => chooseRole("driver")}
            className="border-border hover:border-brand-strong hover:bg-brand-soft flex flex-col items-start gap-3 rounded-2xl border-2 p-6 text-start transition-colors"
          >
            <span className="bg-brand text-brand-foreground flex size-12 items-center justify-center rounded-full">
              <CarFront aria-hidden="true" className="size-6" />
            </span>
            <span className="text-xl font-extrabold">{t("roleDriver")}</span>
            <span className="text-muted-foreground text-sm leading-relaxed">{t("roleDriverHint")}</span>
          </button>
          <button
            type="button"
            onClick={() => chooseRole("passenger")}
            className="border-border hover:border-brand-strong hover:bg-brand-soft flex flex-col items-start gap-3 rounded-2xl border-2 p-6 text-start transition-colors"
          >
            <span className="bg-primary text-primary-foreground flex size-12 items-center justify-center rounded-full">
              <UserRound aria-hidden="true" className="size-6" />
            </span>
            <span className="text-xl font-extrabold">{t("rolePassenger")}</span>
            <span className="text-muted-foreground text-sm leading-relaxed">
              {t("rolePassengerHint")}
            </span>
          </button>
        </div>
      </div>
    );
  }

  const canContinue =
    role === "passenger"
      ? true
      : identityDone && profileDone && (driverReady || isAcceptedDriver);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("title")}</h1>
        <StatusBadge tone={role === "driver" ? "warning" : "success"}>
          {role === "driver" ? t("roleDriver") : t("rolePassenger")}
        </StatusBadge>
      </div>
      <p className="text-muted-foreground mt-3 text-base leading-relaxed">
        {role === "driver" ? t("driverPathBody") : t("passengerPathBody")}
      </p>
      <button
        type="button"
        className="text-primary mt-2 text-sm font-bold underline-offset-4 hover:underline"
        onClick={() => {
          setRole(null);
        }}
      >
        {t("changeRole")}
      </button>

      <ol className="mt-8 space-y-6">
        <li className="border-border rounded-2xl border p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold">{t("stepProfile")}</h2>
            <StatusBadge
              tone={profileDone ? "success" : role === "driver" ? "warning" : "muted"}
            >
              {profileDone ? t("done") : role === "driver" ? t("needed") : t("optional")}
            </StatusBadge>
          </div>
          {role === "passenger" ? (
            <p className="text-muted-foreground mt-2 text-sm">{t("passengerProfileHint")}</p>
          ) : null}
          <div className="mt-4">
            <ProfileForm account={account} />
          </div>
        </li>

        <li className="border-border rounded-2xl border p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold">{t("stepIdentity")}</h2>
            <StatusBadge tone={identityTone(account.identityVerificationStatus)}>
              {accountT(`verificationBadge.${account.identityVerificationStatus}`)}
            </StatusBadge>
          </div>
          <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
            {role === "driver" ? t("driverIdentityHint") : t("passengerIdentityHint")}
          </p>
          <div className="mt-4">
            <IdentityPageInner embedded />
          </div>
        </li>

        {role === "driver" ? (
          <li className="border-border rounded-2xl border p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-bold">{t("stepDrive")}</h2>
              <StatusBadge tone={driverReady || isAcceptedDriver ? "success" : "warning"}>
                {driverReady || isAcceptedDriver ? t("done") : t("needed")}
              </StatusBadge>
            </div>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{t("driverDriveHint")}</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <Link href="/drive" className={buttonVariants({ size: "lg", variant: "brand" })}>
                {t("openDrive")}
              </Link>
            </div>
            {!hasVehicle ? (
              <p className="bg-brand-soft mt-4 rounded-xl px-4 py-3 text-sm font-semibold">
                {t("needVehicleFirst")}
              </p>
            ) : null}
          </li>
        ) : (
          <li className="border-border rounded-2xl border p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-bold">{t("stepDriveLater")}</h2>
              <StatusBadge tone="muted">{t("optional")}</StatusBadge>
            </div>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{t("driveHint")}</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  chooseRole("driver");
                }}
              >
                {t("switchToDriver")}
              </Button>
              <Button type="button" variant="ghost" onClick={onSkipPassenger}>
                {t("skipDrive")}
              </Button>
            </div>
            {driveSkipped ? (
              <p className="bg-brand-soft mt-4 rounded-xl px-4 py-3 text-sm font-semibold">
                {t("driveReminder")}
              </p>
            ) : null}
          </li>
        )}
      </ol>

      <div className="mt-10 flex flex-col gap-3 sm:flex-row">
        <Button
          type="button"
          size="lg"
          block={!canContinue && role === "driver"}
          disabled={role === "driver" && !canContinue}
          onClick={() => void continueOn()}
        >
          {role === "driver"
            ? canContinue
              ? t("continueDriver")
              : t("finishDriverFirst")
            : t("continue")}
        </Button>
        {role === "passenger" ? (
          <Link href="/messages" className={buttonVariants({ size: "lg", variant: "outline" })}>
            {t("communityFirst")}
          </Link>
        ) : null}
      </div>
    </div>
  );
}

export function SetupPage() {
  return (
    <RequireAccount>
      <SetupBody />
    </RequireAccount>
  );
}
