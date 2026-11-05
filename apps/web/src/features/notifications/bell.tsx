"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { useSession } from "@/features/auth/session-provider";
import {
  clearAllNotifications,
  listNotifications,
  markNotificationsRead,
  unreadNotificationCount,
} from "@/features/notifications/api";
import { NotificationRow } from "@/features/notifications/item";
import { PhoneAlerts } from "@/features/notifications/phone-alerts";
import { refreshPhoneAlerts } from "@/features/notifications/push";
import { Link } from "@/i18n/navigation";

export function NotificationBell() {
  const t = useTranslations("Notifications");
  const nav = useTranslations("Nav");
  const { status } = useSession();
  const queryClient = useQueryClient();
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const acknowledged = useRef(false);
  const [open, setOpen] = useState(false);
  const signedIn = status === "authenticated";
  const unread = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: unreadNotificationCount,
    enabled: signedIn,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  });
  const list = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    enabled: signedIn,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  });
  const clearAll = useMutation({
    mutationFn: clearAllNotifications,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const count = unread.data ?? list.data?.filter((item) => !item.readAt).length ?? 0;

  useEffect(() => {
    if (!signedIn) return;
    void refreshPhoneAlerts().catch(() => undefined);
  }, [signedIn]);

  useEffect(() => {
    if (!open) {
      acknowledged.current = false;
      return;
    }
    if (acknowledged.current || count === 0) return;
    acknowledged.current = true;
    void markNotificationsRead().then(() => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    });
  }, [count, open, queryClient]);

  if (!signedIn) return null;
  const items = (list.data ?? []).slice(0, 8);
  const hasItems = (list.data?.length ?? 0) > 0;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="hover:bg-surface-muted relative inline-flex size-9 items-center justify-center rounded-full sm:size-11"
        aria-label={nav("notifications")}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          setOpen((current) => !current);
        }}
      >
        <Bell aria-hidden="true" className="size-5" />
        {count > 0 ? (
          <span
            className="bg-red-600 ring-background absolute end-2 top-2 size-2.5 rounded-full ring-2"
            aria-hidden="true"
          />
        ) : null}
      </button>
      {open ? (
        <div
          id={panelId}
          className="border-border bg-background fixed inset-x-3 top-[3.75rem] z-50 flex max-h-[min(34rem,calc(100dvh-5.5rem))] flex-col overflow-hidden rounded-2xl border shadow-lg sm:absolute sm:inset-x-auto sm:end-0 sm:top-auto sm:mt-2 sm:w-[min(22rem,calc(100vw-2rem))]"
        >
          <div className="border-border flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2.5">
            <p className="text-sm font-bold">{t("title")}</p>
            {hasItems ? (
              <button
                type="button"
                className="text-danger text-xs font-bold underline-offset-2 hover:underline disabled:opacity-50"
                disabled={clearAll.isPending}
                onClick={() => {
                  if (window.confirm(t("confirmClearAll"))) clearAll.mutate();
                }}
              >
                {t("clearAll")}
              </button>
            ) : null}
          </div>
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain px-3 py-3">
            {list.isPending ? (
              <p className="text-muted-foreground px-1 py-6 text-center text-sm">{t("loading")}</p>
            ) : null}
            {list.isError ? (
              <p className="text-muted-foreground px-1 py-6 text-center text-sm">{t("loadError")}</p>
            ) : null}
            {list.data?.length === 0 ? (
              <p className="text-muted-foreground px-1 py-6 text-center text-sm">{t("empty")}</p>
            ) : null}
            {items.map((item) => (
              <NotificationRow
                key={item.id}
                item={item}
                onNavigate={() => {
                  window.setTimeout(() => {
                    setOpen(false);
                  }, 0);
                }}
              />
            ))}
            <PhoneAlerts />
          </div>
          <div className="border-border bg-background sticky bottom-0 shrink-0 border-t px-3 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <Link
              href="/me/notifications"
              className={ButtonLikeClass}
              onClick={() => {
                setOpen(false);
              }}
            >
              {t("openAll")}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}

const ButtonLikeClass =
  "bg-primary text-primary-foreground inline-flex min-h-11 w-full items-center justify-center rounded-full px-4 text-sm font-bold";
