"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { markNotificationsRead, type NotificationItem } from "@/features/notifications/api";
import { notificationCopyKey, notificationHref } from "@/features/notifications/links";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export function NotificationRow({
  item,
  onNavigate,
}: {
  item: NotificationItem;
  onNavigate?: () => void;
}) {
  const t = useTranslations("Notifications");
  const queryClient = useQueryClient();
  const key = notificationCopyKey(item);
  const title = t.has(`items.${key}.title`) ? t(`items.${key}.title`) : t("fallbackTitle");
  const body = t.has(`items.${key}.body`) ? t(`items.${key}.body`) : t("fallbackBody");
  const action = t.has(`items.${key}.action`) ? t(`items.${key}.action`) : t("open");

  return (
    <Link
      href={notificationHref(item)}
      onClick={() => {
        onNavigate?.();
        if (!item.readAt) {
          void markNotificationsRead([item.id]).then(() => {
            void queryClient.invalidateQueries({ queryKey: ["notifications"] });
          });
        }
      }}
      className={cn(
        "block rounded-xl border p-4",
        item.readAt ? "border-border" : "border-brand bg-brand-soft",
      )}
    >
      <p className="font-semibold">{title}</p>
      <p className="text-muted-foreground mt-1 text-sm">{body}</p>
      <p className="mt-3 flex items-center justify-between gap-3 text-xs">
        <span className="text-muted-foreground">{new Date(item.createdAt).toLocaleString()}</span>
        <span className="text-primary font-semibold">{action}</span>
      </p>
    </Link>
  );
}
