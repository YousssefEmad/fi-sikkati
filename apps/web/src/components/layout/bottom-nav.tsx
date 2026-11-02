"use client";

import { CarFront, MessageCircle, Search, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";

import { useSession } from "@/features/auth/session-provider";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/search", key: "findRide", Icon: Search },
  { href: "/me/trips", key: "myTrips", Icon: CarFront },
  { href: "/messages", key: "messages", Icon: MessageCircle },
  { href: "/me", key: "account", Icon: UserRound },
] as const;

export function BottomNav() {
  const t = useTranslations("Nav");
  const pathname = usePathname();
  const { status } = useSession();
  if (status !== "authenticated") return null;

  return (
    <nav
      aria-label={t("app")}
      className="border-border bg-background/95 supports-backdrop-filter:backdrop-blur-md fixed inset-x-0 bottom-0 z-40 border-t pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="mx-auto grid max-w-lg grid-cols-4">
        {ITEMS.map(({ href, key, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link
                href={href}
                className={cn(
                  "flex min-h-14 flex-col items-center justify-center gap-1 text-[11px] font-semibold",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                <Icon aria-hidden="true" className="size-5" />
                {t(key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
