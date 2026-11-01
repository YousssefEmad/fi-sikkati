"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import { enablePhoneAlerts, refreshPhoneAlerts } from "@/features/notifications/push";

type PhoneState = "on" | "off" | "denied" | "unsupported";

export function PhoneAlerts() {
  const t = useTranslations("Notifications");
  const { status } = useSession();
  const [state, setState] = useState<PhoneState | "pending">("pending");

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    const apply = (next: PhoneState) => {
      if (!cancelled) setState(next);
    };
    if (!("Notification" in window) || !("PushManager" in window)) {
      queueMicrotask(() => {
        apply("unsupported");
      });
    } else if (Notification.permission === "denied") {
      queueMicrotask(() => {
        apply("denied");
      });
    } else if (Notification.permission !== "granted") {
      queueMicrotask(() => {
        apply("off");
      });
    } else {
      void refreshPhoneAlerts()
        .then((on) => {
          apply(on ? "on" : "off");
        })
        .catch((error: unknown) => {
          const message = error instanceof Error ? error.message : "";
          apply(message.includes("push service") ? "unsupported" : "off");
        });
    }
    return () => {
      cancelled = true;
    };
  }, [status]);

  if (status !== "authenticated" || state === "pending") return null;

  return (
    <div className="border-border bg-brand-soft mt-4 rounded-xl border px-4 py-3">
      <p className="font-semibold">{t("phoneTitle")}</p>
      <p className="text-muted-foreground mt-1 text-sm">{t("phoneBody")}</p>
      {state === "on" ? <p className="mt-2 text-sm font-semibold">{t("phoneOn")}</p> : null}
      {state === "denied" ? <p className="mt-2 text-sm">{t("phoneDenied")}</p> : null}
      {state === "unsupported" ? <p className="mt-2 text-sm">{t("phoneUnsupported")}</p> : null}
      {state === "off" ? (
        <Button
          className="mt-3"
          variant="brand"
          onClick={() => {
            void enablePhoneAlerts().then((next) => {
              if (next === "on") setState("on");
              else if (next === "unsupported") setState("unsupported");
              else setState("denied");
            });
          }}
        >
          {t("phoneEnable")}
        </Button>
      ) : null}
    </div>
  );
}
