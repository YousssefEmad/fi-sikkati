"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { useSession } from "@/features/auth/session-provider";
import {
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
  const items = (list.data ?? []).slice(0, 6);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="hover:bg-surface-muted relative inline-flex size-11 items-center justify-center rounded-full"
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
          className="border-border bg-background absolute end-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border p-3 shadow-lg"
        >
          <p className="px-1 text-sm font-bold">{t("title")}</p>
          <div className="mt-3 max-h-96 space-y-2 overflow-y-auto">
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
          </div>
          <PhoneAlerts />
          <Link
            href="/me/notifications"
            className="text-primary mt-3 block px-1 text-center text-sm font-semibold"
            onClick={() => {
              setOpen(false);
            }}
          >
            {t("openAll")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
