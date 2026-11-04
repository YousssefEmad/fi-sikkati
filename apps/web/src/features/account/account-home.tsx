"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { StatusBadge, identityTone } from "@/components/ui/status-badge";
import { PhoneForm } from "@/features/account/phone-form";
import { PhotoForm } from "@/features/account/photo-form";
import { ProfileForm } from "@/features/account/profile-form";
import { readSetupRole, shouldRemindDrive } from "@/features/account/setup-intent";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

export function AccountHome() {
  const t = useTranslations("Account");
  const setup = useTranslations("Setup");
  const { account } = useSession();
  const [remindDrive, setRemindDrive] = useState(false);

  useEffect(() => {
    setRemindDrive(shouldRemindDrive() && readSetupRole() !== "driver");
  }, []);

  if (!account) return null;

  const needsSetup =
    account.identityVerificationStatus === "NOT_SUBMITTED" ||
    account.identityVerificationStatus === "REJECTED";
  const isDriver = account.roles.includes("DRIVER");

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2 text-base">{account.email}</p>
      {account.emailVerified ? null : (
        <p className="bg-brand-soft mt-4 rounded-xl px-4 py-3 text-base font-semibold">
          {t("verifyBanner")}
        </p>
      )}
      {needsSetup ? (
        <p className="bg-danger/10 text-danger mt-4 rounded-xl px-4 py-3 text-base font-bold">
          {t("verificationStatus.NOT_SUBMITTED")}{" "}
          <Link href="/me/setup" className="underline underline-offset-4">
            {t("navVerification")}
          </Link>
        </p>
      ) : null}
      {!isDriver && remindDrive ? (
        <p className="bg-brand-soft mt-4 rounded-xl px-4 py-3 text-base font-semibold">
          {setup("driveReminder")}{" "}
          <Link href="/drive" className="font-bold underline underline-offset-4">
            {t("navDrive")}
          </Link>
        </p>
      ) : null}
      <PhoneForm account={account} />
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <p className="text-base font-bold">{t("verificationLabel")}</p>
        <StatusBadge tone={identityTone(account.identityVerificationStatus)}>
          {t(`verificationBadge.${account.identityVerificationStatus}`)}
        </StatusBadge>
      </div>
      <p className="text-muted-foreground mt-2 text-sm">
        {t(`verificationStatus.${account.identityVerificationStatus}`)}
      </p>
      <nav className="border-border mt-6 grid grid-cols-2 gap-2 rounded-2xl border p-3 text-sm font-semibold sm:grid-cols-3 md:flex md:flex-wrap md:gap-4 md:border-0 md:p-0">
        <Link href="/me" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navProfile")}
        </Link>
        <Link href="/me/sessions" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navSessions")}
        </Link>
        <Link href="/me/security" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navSecurity")}
        </Link>
        <Link href="/me/verification" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navVerification")}
        </Link>
        <Link href="/drive" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navDrive")}
        </Link>
        <Link href="/me/trips" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navTrips")}
        </Link>
        <Link href="/me/requests" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navRequests")}
        </Link>
        <Link href="/search" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navSearch")}
        </Link>
        <Link href="/messages" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navMessages")}
        </Link>
        <Link href="/me/notifications" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navNotifications")}
        </Link>
        <Link href="/me/safety" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navSafety")}
        </Link>
        <Link href="/assistant" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
          {t("navAssistant")}
        </Link>
        {account.roles.some((role) => role === "ADMIN" || role === "SUPER_ADMIN") ? (
          <Link href="/admin" className="text-primary min-h-11 rounded-xl px-3 py-2 hover:bg-surface-muted md:px-0 md:py-0 md:underline-offset-4 md:hover:bg-transparent md:hover:underline">
            {t("navAdmin")}
          </Link>
        ) : null}
      </nav>
      <div className="mt-10 space-y-10">
        <PhotoForm photoUrl={account.photoUrl} />
        <ProfileForm account={account} />
      </div>
    </div>
  );
}

export function AccountHomePage() {
  return (
    <RequireAccount>
      <AccountHome />
    </RequireAccount>
  );
}
