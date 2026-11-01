"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { listConversations } from "@/features/chat/api";
import { RequireAccount } from "@/features/auth/require-account";
import { Link } from "@/i18n/navigation";

export function InboxPage() {
  return (
    <RequireAccount>
      <Inbox />
    </RequireAccount>
  );
}

function Inbox() {
  const t = useTranslations("Chat");
  const query = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 8000,
  });

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("body")}</p>
      <div className="mt-8 space-y-3">
        {query.isPending ? (
          <>
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </>
        ) : null}
        {query.data?.length === 0 ? (
          <EmptyState title={t("emptyTitle")} body={t("emptyBody")} />
        ) : null}
        {query.data
          ?.slice()
          .sort((left, right) => Number(right.tripId === null) - Number(left.tripId === null))
          .map((item) => (
          <Link
            key={item.id}
            href={`/messages/${item.id}`}
            className="border-border hover:bg-surface-muted flex items-start justify-between gap-4 rounded-xl border p-4"
          >
            <div>
              <p className="font-semibold">
                {item.tripId === null
                  ? t("community")
                  : item.originLabel && item.destinationLabel
                    ? `${item.originLabel} → ${item.destinationLabel}`
                    : t("untitled")}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                {item.tripId === null
                  ? t("communityHint")
                  : item.memberNames.filter(Boolean).join(" · ") || t("members")}
              </p>
              <p className="text-muted-foreground mt-1 line-clamp-2 text-sm">
                {item.lastMessage?.deleted ? t("removed") : (item.lastMessage?.body ?? t("noMessages"))}
              </p>
            </div>
            {item.unreadCount > 0 ? (
              <span className="bg-brand text-brand-foreground rounded-full px-2 py-0.5 text-xs font-bold">
                {item.unreadCount}
              </span>
            ) : null}
          </Link>
        ))}
      </div>
    </div>
  );
}
