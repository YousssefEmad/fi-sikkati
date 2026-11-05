"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import {
  enablePhoneAlerts,
  isIosDevice,
  isStandaloneApp,
  refreshPhoneAlerts,
} from "@/features/notifications/push";

type PhoneState = "on" | "off" | "denied" | "unsupported" | "need_install";

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
    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
      queueMicrotask(() => {
        apply("unsupported");
      });
      return () => {
        cancelled = true;
      };
    }
    if (isIosDevice() && !isStandaloneApp()) {
      queueMicrotask(() => {
        apply("need_install");
      });
      return () => {
        cancelled = true;
      };
    }
    if (!("PushManager" in window)) {
      queueMicrotask(() => {
        apply(isIosDevice() ? "need_install" : "unsupported");
      });
      return () => {
        cancelled = true;
      };
    }
    if (Notification.permission === "denied") {
      queueMicrotask(() => {
        apply("denied");
      });
      return () => {
        cancelled = true;
      };
    }
    if (Notification.permission !== "granted") {
      queueMicrotask(() => {
        apply("off");
      });
      return () => {
        cancelled = true;
      };
    }
    void refreshPhoneAlerts()
      .then((on) => {
        apply(on ? "on" : "off");
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "";
        apply(message.includes("push service") ? "unsupported" : "off");
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  if (status !== "authenticated" || state === "pending") return null;

  return (
    <div className="border-border bg-brand-soft mt-3 rounded-xl border px-3 py-3">
      <p className="text-sm font-semibold">{t("phoneTitle")}</p>
      <p className="text-muted-foreground mt-1 text-xs leading-relaxed sm:text-sm">{t("phoneBody")}</p>
      {state === "on" ? <p className="mt-2 text-sm font-semibold">{t("phoneOn")}</p> : null}
      {state === "denied" ? <p className="mt-2 text-sm">{t("phoneDenied")}</p> : null}
      {state === "unsupported" ? <p className="mt-2 text-sm">{t("phoneUnsupported")}</p> : null}
      {state === "need_install" ? <p className="mt-2 text-sm font-semibold">{t("phoneNeedInstall")}</p> : null}
      {state === "off" ? (
        <Button
          className="mt-3"
          size="sm"
          variant="brand"
          onClick={() => {
            void enablePhoneAlerts().then((next) => {
              if (next === "on") setState("on");
              else if (next === "unsupported") setState("unsupported");
              else if (next === "need_install") setState("need_install");
              else setState("denied");
            });
          }}
        >
          {t("phoneEnable")}
        </Button>
      ) : null}
      {state === "on" || state === "off" ? (
        <p className="text-muted-foreground mt-2 text-xs">{t("communityMuteHint")}</p>
      ) : null}
    </div>
  );
}
