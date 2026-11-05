"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { StatusBadge } from "@/components/ui/status-badge";
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

function systemOrBody(
  body: string | undefined | null,
  systemEvent: string | null | undefined,
  t: ReturnType<typeof useTranslations<"Chat">>,
): string {
  if (systemEvent) {
    try {
      return t(`events.${systemEvent}` as "events.TRIP_STARTED");
    } catch {
      /* fall through */
    }
  }
  if (!body) return t("noMessages");
  // Legacy bilingual system bodies stored as "ar / en"
  if (body.includes(" / ")) {
    const [ar] = body.split(" / ");
    return (ar ?? body).trim();
  }
  return body;
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
      <p className="text-muted-foreground mt-2 text-base leading-relaxed">{t("body")}</p>
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
          .map((item) => {
            const isCommunity = item.tripId === null;
            return (
              <Link
                key={item.id}
                href={`/messages/${item.id}`}
                className="border-border hover:bg-surface-muted flex items-start justify-between gap-4 rounded-xl border p-4"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-bold">
                      {isCommunity
                        ? t("community")
                        : item.originLabel && item.destinationLabel
                          ? `${item.originLabel} → ${item.destinationLabel}`
                          : t("untitled")}
                    </p>
                    <StatusBadge tone={isCommunity ? "success" : "warning"}>
                      {isCommunity ? t("communityBadge") : t("tripBadge")}
                    </StatusBadge>
                    {item.muted ? <StatusBadge tone="muted">{t("mutedBadge")}</StatusBadge> : null}
                  </div>
                  <p className="text-muted-foreground mt-1 text-sm">
                    {isCommunity
                      ? t("communityHint")
                      : item.memberNames.filter(Boolean).join(" · ") || t("tripHint")}
                  </p>
                  <p className="text-muted-foreground mt-1 line-clamp-2 text-sm">
                    {item.lastMessage?.deleted
                      ? t("removed")
                      : systemOrBody(
                          item.lastMessage?.body,
                          item.lastMessage?.systemEvent,
                          t,
                        )}
                  </p>
                </div>
                {item.unreadCount > 0 ? (
                  <span className="bg-brand text-brand-foreground rounded-full px-2.5 py-1 text-sm font-bold">
                    {item.unreadCount}
                  </span>
                ) : null}
              </Link>
            );
          })}
      </div>
    </div>
  );
}
