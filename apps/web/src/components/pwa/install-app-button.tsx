"use client";

import { Download, Share, Smartphone, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DISMISS_KEY = "fi-sikkati-pwa-banner-dismissed";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(display-mode: standalone)").matches) return true;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return nav.standalone === true;
}

function isIosDevice(): boolean {
  if (typeof window === "undefined") return false;
  const ua = window.navigator.userAgent.toLowerCase();
  const iPadOs = window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1;
  return /iphone|ipad|ipod/.test(ua) || iPadOs;
}

/** Header + banner CTA to install Fi Sikkati as a home-screen app (Android + iOS + desktop). */
export function InstallAppButton({
  className,
  tone = "header",
}: {
  className?: string;
  tone?: "header" | "banner";
}) {
  const t = useTranslations("Pwa");
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [ios, setIos] = useState(false);
  const [showIosHelp, setShowIosHelp] = useState(false);
  const [bannerHidden, setBannerHidden] = useState(true);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setInstalled(isStandaloneDisplay());
    setIos(isIosDevice());
    try {
      setBannerHidden(localStorage.getItem(DISMISS_KEY) === "1");
    } catch {
      setBannerHidden(false);
    }
    setReady(true);

    function onBeforeInstall(event: Event) {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
    }
    function onInstalled() {
      setInstalled(true);
      setDeferred(null);
      setShowIosHelp(false);
    }

    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (!ready || installed) return null;

  const canNativeInstall = deferred !== null;
  const canShowIos = ios;
  if (!canNativeInstall && !canShowIos) return null;

  async function onInstall() {
    if (deferred) {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === "accepted") {
        setDeferred(null);
        setInstalled(true);
      }
      return;
    }
    if (ios) setShowIosHelp(true);
  }

  function dismissBanner() {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* ignore */
    }
    setBannerHidden(true);
  }

  if (tone === "banner") {
    if (bannerHidden) return null;
    return (
      <>
        <div
          className={cn(
            "border-border bg-brand text-brand-foreground border-b",
            className,
          )}
        >
          <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-3 py-2.5 sm:px-6">
            <Smartphone aria-hidden="true" className="size-5 shrink-0" />
            <p className="min-w-0 flex-1 text-sm font-bold leading-snug sm:text-base">
              {t("bannerBody")}
            </p>
            <Button
              type="button"
              size="sm"
              variant="inverse"
              className="shrink-0"
              onClick={() => void onInstall()}
            >
              <Download aria-hidden="true" className="size-4" />
              {t("install")}
            </Button>
            <button
              type="button"
              className="hover:bg-brand-strong/20 rounded-full p-1.5"
              aria-label={t("dismiss")}
              onClick={dismissBanner}
            >
              <X aria-hidden="true" className="size-4" />
            </button>
          </div>
        </div>
        {showIosHelp ? <IosInstallSheet onClose={() => setShowIosHelp(false)} /> : null}
      </>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void onInstall()}
        className={cn(
          "border-border-strong bg-brand text-brand-foreground hover:bg-brand-strong inline-flex h-11 max-w-[9.5rem] items-center gap-1.5 rounded-full border px-2.5 text-sm font-bold sm:max-w-none sm:gap-2 sm:px-3",
          className,
        )}
        aria-label={t("install")}
        title={t("install")}
      >
        <Download aria-hidden="true" className="size-4 shrink-0" />
        <span className="truncate">{t("installShort")}</span>
      </button>
      {showIosHelp ? <IosInstallSheet onClose={() => setShowIosHelp(false)} /> : null}
    </>
  );
}

function IosInstallSheet({ onClose }: { onClose: () => void }) {
  const t = useTranslations("Pwa");
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pwa-ios-title"
      onClick={onClose}
    >
      <div
        className="bg-surface text-foreground w-full max-w-md rounded-2xl p-5 shadow-lift"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="pwa-ios-title" className="text-xl font-extrabold">
            {t("iosTitle")}
          </h2>
          <button
            type="button"
            className="hover:bg-surface-muted rounded-full p-1.5"
            aria-label={t("dismiss")}
            onClick={onClose}
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{t("iosBody")}</p>
        <ol className="mt-4 space-y-3 text-sm font-semibold">
          <li className="border-border flex items-start gap-3 rounded-xl border p-3">
            <span className="bg-brand text-brand-foreground flex size-8 shrink-0 items-center justify-center rounded-full font-extrabold">
              1
            </span>
            <span className="pt-1">
              {t.rich("iosStep1", {
                share: (chunks) => (
                  <span className="text-primary inline-flex items-center gap-1">
                    <Share aria-hidden="true" className="size-4" />
                    {chunks}
                  </span>
                ),
              })}
            </span>
          </li>
          <li className="border-border flex items-start gap-3 rounded-xl border p-3">
            <span className="bg-brand text-brand-foreground flex size-8 shrink-0 items-center justify-center rounded-full font-extrabold">
              2
            </span>
            <span className="pt-1">{t("iosStep2")}</span>
          </li>
          <li className="border-border flex items-start gap-3 rounded-xl border p-3">
            <span className="bg-brand text-brand-foreground flex size-8 shrink-0 items-center justify-center rounded-full font-extrabold">
              3
            </span>
            <span className="pt-1">{t("iosStep3")}</span>
          </li>
        </ol>
        <Button type="button" className="mt-5" block onClick={onClose}>
          {t("iosDone")}
        </Button>
      </div>
    </div>
  );
}
