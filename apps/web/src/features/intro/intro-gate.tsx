"use client";

import { CarFront, Search, ShieldCheck, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { useSession } from "@/features/auth/session-provider";
import { useRouter } from "@/i18n/navigation";

const STORAGE_KEY = "fs.intro.done";
const CHANGE = "fs-intro";
const SLIDES = ["welcome", "passenger", "driver", "start"] as const;

const ICONS = {
  welcome: Users,
  passenger: Search,
  driver: CarFront,
  start: ShieldCheck,
} as const;

function subscribe(onStoreChange: () => void) {
  window.addEventListener(CHANGE, onStoreChange);
  return () => {
    window.removeEventListener(CHANGE, onStoreChange);
  };
}

function introSeen() {
  return localStorage.getItem(STORAGE_KEY) === "1";
}

function rememberIntro() {
  localStorage.setItem(STORAGE_KEY, "1");
  window.dispatchEvent(new Event(CHANGE));
}

/** First-open walkthrough. Shown once, then the person lands on sign-in. */
export function IntroGate() {
  const t = useTranslations("Intro");
  const router = useRouter();
  const { status } = useSession();
  const seen = useSyncExternalStore(subscribe, introSeen, () => false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (status === "authenticated" && !introSeen()) rememberIntro();
  }, [status]);

  function finish(path: "/auth/sign-in" | "/auth/register") {
    rememberIntro();
    router.push(path);
  }

  if (seen || status !== "anonymous") return null;

  const slide = SLIDES[index] ?? "welcome";
  const Icon = ICONS[slide];
  const last = index === SLIDES.length - 1;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="intro-title"
      className="bg-inverse text-inverse-foreground fixed inset-0 z-50 flex flex-col"
    >
      <div className="flex justify-end px-4 pt-4">
        <Button
          variant="ghost"
          className="text-inverse-foreground"
          onClick={() => {
            finish("/auth/sign-in");
          }}
        >
          {t("skip")}
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <span className="bg-brand text-brand-foreground flex size-20 items-center justify-center rounded-full">
          <Icon aria-hidden="true" className="size-10" />
        </span>
        <p className="mt-8 text-sm font-semibold text-white/60">
          {t("progress", { current: index + 1, total: SLIDES.length })}
        </p>
        <h1 id="intro-title" className="mt-3 max-w-md text-3xl font-extrabold tracking-tight">
          {t(`slides.${slide}.title`)}
        </h1>
        <p className="mt-4 max-w-md text-lg leading-relaxed text-white/75">
          {t(`slides.${slide}.body`)}
        </p>
      </div>

      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-6 pb-8">
        <div className="flex justify-center gap-2" aria-hidden="true">
          {SLIDES.map((key, dot) => (
            <span
              key={key}
              className={
                dot === index ? "bg-brand h-2 w-6 rounded-full" : "size-2 rounded-full bg-white/30"
              }
            />
          ))}
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="text-inverse-foreground flex-1 border-white/30"
            disabled={index === 0}
            onClick={() => {
              setIndex((current) => Math.max(0, current - 1));
            }}
          >
            {t("previous")}
          </Button>
          {last ? (
            <Button
              variant="brand"
              className="flex-1"
              onClick={() => {
                finish("/auth/sign-in");
              }}
            >
              {t("signIn")}
            </Button>
          ) : (
            <Button
              variant="brand"
              className="flex-1"
              onClick={() => {
                setIndex((current) => current + 1);
              }}
            >
              {t("next")}
            </Button>
          )}
        </div>
        {last ? (
          <Button
            variant="ghost"
            className="text-inverse-foreground"
            onClick={() => {
              finish("/auth/register");
            }}
          >
            {t("register")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
