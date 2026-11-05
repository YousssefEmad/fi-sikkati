"use client";

import { ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/** Persistent reminder so unverified users are not surprised at seat request time. */
export function IdentityNudgeBanner() {
  const t = useTranslations("Account");
  const { status, account } = useSession();
  const pathname = usePathname();

  if (status !== "authenticated" || !account) return null;

  const identity = account.identityVerificationStatus;
  if (identity === "APPROVED") return null;

  const onVerificationFlow =
    pathname.includes("/me/verification") ||
    pathname.includes("/me/setup") ||
    pathname.includes("/auth/");
  if (onVerificationFlow) return null;

  const needsAction = identity === "NOT_SUBMITTED" || identity === "REJECTED";
  const tone =
    identity === "PENDING"
      ? "bg-brand-soft text-foreground border-border"
      : "bg-danger/10 text-danger border-danger/20";

  return (
    <div className={`border-b px-4 py-3 sm:px-6 ${tone}`} role="status">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-start gap-2.5">
          <ShieldAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-extrabold sm:text-base">{t(`identityNudge.title.${identity}`)}</p>
            <p className="mt-0.5 text-sm font-semibold opacity-90">
              {t(`identityNudge.body.${identity}`)}
            </p>
          </div>
        </div>
        {needsAction ? (
          <Link
            href="/me/verification"
            className={cn(buttonVariants({ size: "sm" }), "shrink-0")}
          >
            {t("identityNudge.cta")}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
