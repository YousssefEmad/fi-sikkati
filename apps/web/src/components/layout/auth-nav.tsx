"use client";

import { LogOut, MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export function AuthNav() {
  const t = useTranslations("Common");
  const { status, account, signOut } = useSession();

  if (status === "loading") {
    return <span className="text-muted-foreground text-sm">{t("loading")}</span>;
  }

  if (status === "authenticated" && account) {
    return (
      <div className="flex min-w-0 items-center justify-end gap-1 sm:gap-2">
        <Link
          href="/messages"
          className={cn(buttonVariants({ variant: "brand", size: "sm" }), "hidden md:inline-flex")}
        >
          <MessageCircle aria-hidden="true" className="size-4" />
          {t("communityChat")}
        </Link>
        <Link
          href="/search"
          className="hidden text-sm font-semibold underline-offset-4 hover:underline md:inline"
        >
          {t("findRide")}
        </Link>
        <Link
          href="/me/trips"
          className="hidden text-sm font-semibold underline-offset-4 hover:underline md:inline"
        >
          {t("myTrips")}
        </Link>
        <Link
          href="/me"
          className="max-w-[6.5rem] truncate text-sm font-semibold underline-offset-4 hover:underline sm:max-w-28"
        >
          {account.displayName}
        </Link>
        <button
          type="button"
          data-testid="sign-out"
          aria-label={t("signOut")}
          title={t("signOut")}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0 px-2 sm:px-3")}
          onClick={() => {
            void signOut();
          }}
        >
          <LogOut aria-hidden="true" className="size-4 sm:hidden" />
          <span className="hidden sm:inline">{t("signOut")}</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-end gap-1.5 sm:gap-2">
      <Link
        href="/messages"
        aria-label={t("communityChat")}
        className={cn(buttonVariants({ variant: "brand", size: "sm" }), "px-3")}
      >
        <MessageCircle aria-hidden="true" className="size-4" />
        <span className="hidden md:inline">{t("communityChat")}</span>
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
