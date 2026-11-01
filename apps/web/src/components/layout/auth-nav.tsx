"use client";

import { MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

export function AuthNav() {
  const t = useTranslations("Common");
  const { status, account, signOut } = useSession();

  if (status === "loading") {
    return <span className="text-muted-foreground text-sm">{t("loading")}</span>;
  }

  if (status === "authenticated" && account) {
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Link href="/messages" className={buttonVariants({ variant: "brand", size: "sm" })}>
          <MessageCircle aria-hidden="true" className="size-4" />
          {t("communityChat")}
        </Link>
        <Link href="/search" className="text-sm font-semibold underline-offset-4 hover:underline">
          {t("findRide")}
        </Link>
        <Link href="/me/trips" className="text-sm font-semibold underline-offset-4 hover:underline">
          {t("myTrips")}
        </Link>
        <Link href="/me" className="text-sm font-semibold underline-offset-4 hover:underline">
          {account.displayName}
        </Link>
        <button
          type="button"
          data-testid="sign-out"
          className={buttonVariants({ variant: "outline", size: "sm" })}
          onClick={() => void signOut()}
        >
          {t("signOut")}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Link href="/messages" className={buttonVariants({ variant: "brand", size: "sm" })}>
        <MessageCircle aria-hidden="true" className="size-4" />
        {t("communityChat")}
      </Link>
      <Link
        href="/auth/sign-in"
        data-testid="sign-in"
        className={buttonVariants({ variant: "ghost", size: "sm" })}
      >
        {t("signIn")}
      </Link>
      <Link href="/auth/register" data-testid="register" className={buttonVariants({ size: "sm" })}>
        {t("register")}
      </Link>
    </div>
  );
}
