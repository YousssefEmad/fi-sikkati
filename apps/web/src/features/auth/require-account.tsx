"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useSession } from "@/features/auth/session-provider";
import { usePathname, useRouter } from "@/i18n/navigation";

/**
 * Sends anonymous visitors to sign-in.
 * When ``needIdentity`` is set, users who have not submitted ID docs go to setup first
 * so they are not blocked mid-flow (search / publish / join).
 */
export function RequireAccount({
  children,
  needIdentity = false,
}: {
  children: React.ReactNode;
  needIdentity?: boolean;
}) {
  const { status, account } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("Auth");

  useEffect(() => {
    if (status === "anonymous") {
      router.replace("/auth/sign-in");
      return;
    }
    if (
      needIdentity &&
      status === "authenticated" &&
      account &&
      (account.identityVerificationStatus === "NOT_SUBMITTED" ||
        account.identityVerificationStatus === "REJECTED") &&
      pathname !== "/me/setup" &&
      pathname !== "/me/verification"
    ) {
      router.replace("/me/setup");
    }
  }, [status, account, needIdentity, pathname, router]);

  if (status === "loading") {
    return <p className="text-muted-foreground px-4 py-16 text-center text-base">{t("loading")}</p>;
  }
  if (status !== "authenticated") {
    return null;
  }
  if (
    needIdentity &&
    account &&
    (account.identityVerificationStatus === "NOT_SUBMITTED" ||
      account.identityVerificationStatus === "REJECTED")
  ) {
    return null;
  }
  return children;
}
