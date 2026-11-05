"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
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
  const profileName = account.displayName || account.fullName || t("title");

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <header className="border-border from-brand-soft/40 to-surface flex flex-col items-center gap-4 rounded-3xl border bg-gradient-to-b px-5 py-8 text-center sm:flex-row sm:items-end sm:gap-6 sm:text-start">
        <Avatar
          name={profileName}
          src={account.photoUrl}
          className="border-surface size-28 shrink-0 border-4 shadow-lift sm:size-32"
        />
        <div className="min-w-0 flex-1">
          <p className="text-muted-foreground text-sm font-bold tracking-wide uppercase">
            {t("profileHeader")}
          </p>
          <h1 className="mt-1 truncate text-3xl font-extrabold tracking-tight sm:text-4xl">
            {profileName}
          </h1>
          {account.fullName && account.fullName !== account.displayName ? (
            <p className="text-muted-foreground mt-1 text-base font-semibold">{account.fullName}</p>
          ) : null}
          <p className="text-muted-foreground mt-2 truncate text-sm sm:text-base">{account.email}</p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <StatusBadge tone={identityTone(account.identityVerificationStatus)}>
              {t(`verificationBadge.${account.identityVerificationStatus}`)}
            </StatusBadge>
            {account.phoneVerified ? (
              <StatusBadge tone="success">{t("phoneVerifiedBadge")}</StatusBadge>
            ) : null}
          </div>
        </div>
      </header>
      {account.emailVerified ? null : (
        <p className="bg-brand-soft mt-4 rounded-xl px-4 py-3 text-base font-semibold">
          {t("verifyBanner")}
        </p>
      )}
      {needsSetup ? (
        <div className="bg-danger/10 text-danger border-danger/20 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3">
          <div>
            <p className="text-base font-extrabold">{t("identityNudge.title.NOT_SUBMITTED")}</p>
            <p className="mt-1 text-sm font-semibold opacity-90">
              {account.identityVerificationStatus === "REJECTED"
                ? t("identityNudge.body.REJECTED")
                : t("identityNudge.body.NOT_SUBMITTED")}
            </p>
          </div>
          <Link
            href="/me/verification"
            className="bg-danger inline-flex min-h-11 shrink-0 items-center justify-center rounded-full px-4 text-sm font-bold text-white"
          >
            {t("identityNudge.cta")}
          </Link>
        </div>
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
