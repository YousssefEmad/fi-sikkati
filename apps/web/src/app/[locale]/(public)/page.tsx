import { CarFront, MessageSquareHeart, Search } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Button } from "@/components/ui/button";

const STEPS = [
  { key: "publish", Icon: CarFront },
  { key: "discover", Icon: Search },
  { key: "join", Icon: MessageSquareHeart },
] as const;

export default async function LandingPage() {
  const t = await getTranslations("Landing");
  const tCommon = await getTranslations("Common");

  return (
    <>
      <section className="mx-auto w-full max-w-6xl px-4 pb-12 pt-16 sm:px-6 sm:pt-24">
        <p className="text-accent-foreground bg-accent/30 inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide">
          {t("eyebrow")}
        </p>
        <h1 className="mt-6 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight sm:text-6xl">
          {t("headline")}
        </h1>
        <p className="text-muted-foreground mt-6 max-w-2xl text-lg leading-relaxed">
          {t("subheadline")}
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Button size="lg" disabled aria-describedby="status-note">
            {t("ctaPassenger")}
          </Button>
          <Button size="lg" variant="secondary" disabled aria-describedby="status-note">
            {t("ctaDriver")}
          </Button>
        </div>
        <p id="status-note" className="text-muted-foreground mt-4 text-sm">
          {t("statusNote")}
        </p>
      </section>

      <section aria-labelledby="how-it-works" className="bg-surface-muted">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
          <h2 id="how-it-works" className="text-2xl font-bold tracking-tight sm:text-3xl">
            {t("howItWorksTitle")}
          </h2>
          <ol className="mt-8 grid gap-6 sm:grid-cols-3">
            {STEPS.map(({ key, Icon }, index) => (
              <li
                key={key}
                className="bg-surface border-border flex flex-col gap-3 rounded-lg border p-6"
              >
                <span className="bg-primary text-primary-foreground inline-flex size-10 items-center justify-center rounded-full">
                  <Icon aria-hidden="true" className="size-5" />
                  <span className="sr-only">{index + 1}</span>
                </span>
                <h3 className="text-lg font-semibold">{t(`steps.${key}.title`)}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {t(`steps.${key}.body`)}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="trust" className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
        <h2 id="trust" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {t("trustTitle")}
        </h2>
        <p className="text-muted-foreground mt-4 max-w-3xl leading-relaxed">{t("trustBody")}</p>
        <p className="text-muted-foreground mt-6 text-sm">
          <span className="border-border rounded-full border px-3 py-1">
            {tCommon("comingSoon")}
          </span>
        </p>
      </section>
    </>
  );
}
