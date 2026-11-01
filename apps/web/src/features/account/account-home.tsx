"use client";

import { useTranslations } from "next-intl";

import { PhoneForm } from "@/features/account/phone-form";
import { PhotoForm } from "@/features/account/photo-form";
import { ProfileForm } from "@/features/account/profile-form";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

export function AccountHome() {
  const t = useTranslations("Account");
  const { account } = useSession();
  if (!account) return null;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2">{account.email}</p>
      {account.emailVerified ? null : (
        <p className="bg-brand-soft mt-4 rounded-md px-4 py-3 text-sm">{t("verifyBanner")}</p>
      )}
      <PhoneForm account={account} />
      <p className="text-muted-foreground mt-3 text-sm">
        {t("verificationStatusLine", {
          status: t(`verificationStatus.${account.identityVerificationStatus}`),
        })}
      </p>
      <nav className="mt-6 flex flex-wrap gap-4 text-sm font-semibold">
        <Link href="/me" className="text-primary underline-offset-4 hover:underline">
          {t("navProfile")}
        </Link>
        <Link href="/me/sessions" className="text-primary underline-offset-4 hover:underline">
          {t("navSessions")}
        </Link>
        <Link href="/me/security" className="text-primary underline-offset-4 hover:underline">
          {t("navSecurity")}
        </Link>
        <Link href="/me/verification" className="text-primary underline-offset-4 hover:underline">
          {t("navVerification")}
        </Link>
        <Link href="/drive" className="text-primary underline-offset-4 hover:underline">
          {t("navDrive")}
        </Link>
        <Link href="/me/trips" className="text-primary underline-offset-4 hover:underline">
          {t("navTrips")}
        </Link>
        <Link href="/me/requests" className="text-primary underline-offset-4 hover:underline">
          {t("navRequests")}
        </Link>
        <Link href="/search" className="text-primary underline-offset-4 hover:underline">
          {t("navSearch")}
        </Link>
        <Link href="/messages" className="text-primary underline-offset-4 hover:underline">
          {t("navMessages")}
        </Link>
        <Link href="/me/notifications" className="text-primary underline-offset-4 hover:underline">
          {t("navNotifications")}
        </Link>
        <Link href="/me/safety" className="text-primary underline-offset-4 hover:underline">
          {t("navSafety")}
        </Link>
        <Link href="/assistant" className="text-primary underline-offset-4 hover:underline">
          {t("navAssistant")}
        </Link>
        {account.roles.some((role) => role === "ADMIN" || role === "SUPER_ADMIN") ? (
          <Link href="/admin" className="text-primary underline-offset-4 hover:underline">
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
