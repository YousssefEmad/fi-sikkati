"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAccount } from "@/features/auth/require-account";
import { listNotifications, markNotificationsRead } from "@/features/notifications/api";
import { NotificationRow } from "@/features/notifications/item";
import { PhoneAlerts } from "@/features/notifications/phone-alerts";

export function NotificationCentrePage() {
  return (
    <RequireAccount>
      <Centre />
    </RequireAccount>
  );
}

function Centre() {
  const t = useTranslations("Notifications");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
  const markAll = useMutation({
    mutationFn: () => markNotificationsRead(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            markAll.mutate();
          }}
          disabled={markAll.isPending}
        >
          {t("markAll")}
        </Button>
      </div>
      <p className="text-muted-foreground mt-2 text-sm">{t("intro")}</p>
      <PhoneAlerts />
      <div className="mt-8 space-y-3">
        {query.isPending ? <Skeleton className="h-24" /> : null}
        {query.data?.length === 0 ? <EmptyState title={t("empty")} /> : null}
        {query.data?.map((item) => (
          <NotificationRow key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}
