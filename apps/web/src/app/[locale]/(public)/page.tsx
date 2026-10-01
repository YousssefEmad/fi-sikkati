import {
  BadgeCheck,
  CarFront,
  CircleDot,
  Clock,
  Flag,
  MapPin,
  MessageCircle,
  Route,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const DIFFERENCE = [
  { key: "notTaxi", Icon: CarFront },
  { key: "routeMatch", Icon: Route },
  { key: "neighbours", Icon: Users },
] as const;

const STEPS = [
  { key: "publish", Icon: CarFront },
  { key: "discover", Icon: Search },
  { key: "join", Icon: MessageCircle },
] as const;

const TRUST = [
  { key: "verified", Icon: BadgeCheck },
  { key: "pickup", Icon: MapPin },
  { key: "chat", Icon: MessageCircle },
  { key: "report", Icon: Flag },
] as const;

export default async function LandingPage() {
  const [t, tCommon] = await Promise.all([getTranslations("Landing"), getTranslations("Common")]);

  return (
    <>
      {/* Hero */}
      <section className="hero-glow border-border/60 border-b">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pb-24 lg:pt-20">
          <div>
            <Badge variant="brand">{t("eyebrow")}</Badge>
            <h1 className="mt-6 text-[2.5rem] font-extrabold leading-[1.1] tracking-tight sm:text-6xl">
              {t("headline")}
            </h1>
            <p className="text-muted-foreground mt-6 max-w-xl text-lg leading-relaxed">
              {t("subheadline")}
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" disabled aria-describedby="status-note">
                <Search aria-hidden="true" className="size-5" />
                {t("ctaPassenger")}
              </Button>
              <Button size="lg" variant="outline" disabled aria-describedby="status-note">
                <CarFront aria-hidden="true" className="size-5" />
                {t("ctaDriver")}
              </Button>
            </div>
            <p id="status-note" className="text-muted-foreground mt-5 max-w-md text-sm">
              {t("statusNote")}
            </p>
          </div>

          {/* Static design preview of the trip card — not connected to any data yet. */}
          <div className="lg:ps-6">
            <Card className="shadow-lift relative mx-auto max-w-md rounded-xl p-5 sm:p-6">
              <Badge
                variant="soft"
                size="sm"
                className="shadow-card bg-surface absolute -top-3 end-5"
              >
                {t("preview.label")}
              </Badge>

              <div className="flex items-center gap-3">
                <span className="bg-brand text-brand-foreground flex size-11 items-center justify-center rounded-full">
                  <CarFront aria-hidden="true" className="size-6" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-bold">{t("preview.driver")}</p>
                  <p className="text-muted-foreground inline-flex items-center gap-1 text-xs">
                    <BadgeCheck aria-hidden="true" className="text-brand-strong size-3.5" />
                    {t("preview.driverBadge")}
                  </p>
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <div aria-hidden="true" className="flex flex-col items-center pt-1">
                  <CircleDot className="text-brand-strong size-5" />
                  <span className="border-border-strong my-1.5 w-0 flex-1 border-s-2 border-dashed" />
                  <MapPin className="text-foreground size-5" />
                </div>
                <div className="flex-1 space-y-5">
                  <div>
                    <p className="text-muted-foreground text-xs font-semibold uppercase tracking-wide">
                      {t("preview.fromLabel")}
                    </p>
                    <p className="font-semibold">{t("preview.origin")}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs font-semibold uppercase tracking-wide">
                      {t("preview.toLabel")}
                    </p>
                    <p className="font-semibold">{t("preview.destination")}</p>
                  </div>
                </div>
              </div>

              <div className="border-border text-muted-foreground mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-t pt-4 text-sm">
                <span className="inline-flex items-center gap-1.5">
                  <Clock aria-hidden="true" className="size-4" />
                  {t("preview.departure")}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Users aria-hidden="true" className="size-4" />
                  {t("preview.seats")}
                </span>
              </div>

              <Button variant="brand" block disabled className="mt-5">
                {t("preview.action")}
              </Button>
            </Card>
          </div>
        </div>
      </section>

      {/* Why it is not a taxi app */}
      <section aria-labelledby="difference" className="bg-inverse text-inverse-foreground">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
          <h2
            id="difference"
            className="max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl"
          >
            {t("difference.title")}
          </h2>
          <p className="mt-4 max-w-2xl leading-relaxed text-white/70">{t("difference.body")}</p>
          <ul className="mt-12 grid gap-8 sm:grid-cols-3">
            {DIFFERENCE.map(({ key, Icon }) => (
              <li key={key} className="border-t-2 border-white/15 pt-5">
                <Icon aria-hidden="true" className="text-brand size-7" />
                <h3 className="mt-4 text-lg font-bold">{t(`difference.points.${key}.title`)}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/70">
                  {t(`difference.points.${key}.body`)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* How it works */}
      <section aria-labelledby="how-it-works">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
          <div className="max-w-2xl">
            <Badge variant="soft" size="sm">
              {t("howItWorksEyebrow")}
            </Badge>
            <h2
              id="how-it-works"
              className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl"
            >
              {t("howItWorksTitle")}
            </h2>
            <p className="text-muted-foreground mt-4 leading-relaxed">{t("howItWorksBody")}</p>
          </div>
          <ol className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map(({ key, Icon }, index) => (
              <li key={key}>
                <Card className="h-full rounded-xl">
                  <div className="flex items-center justify-between">
                    <span className="bg-foreground text-primary-foreground flex size-11 items-center justify-center rounded-full">
                      <Icon aria-hidden="true" className="size-5" />
                    </span>
                    <span
                      aria-hidden="true"
                      className="text-surface-sunken text-5xl font-extrabold leading-none"
                    >
                      {index + 1}
                    </span>
                  </div>
                  <h3 className="mt-5 text-xl font-bold">{t(`steps.${key}.title`)}</h3>
                  <p className="text-muted-foreground mt-2 leading-relaxed">
                    {t(`steps.${key}.body`)}
                  </p>
                </Card>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Trust & safety */}
      <section aria-labelledby="trust" className="bg-surface-muted border-border border-y">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
          <div className="max-w-2xl">
            <Badge variant="soft" size="sm" className="bg-surface">
              <ShieldCheck aria-hidden="true" className="size-3.5" />
              {t("trustEyebrow")}
            </Badge>
            <h2 id="trust" className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl">
              {t("trustTitle")}
            </h2>
            <p className="text-muted-foreground mt-4 leading-relaxed">{t("trustBody")}</p>
          </div>
          <ul className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {TRUST.map(({ key, Icon }) => (
              <li key={key}>
                <Card className="h-full">
                  <span className="bg-brand text-brand-foreground flex size-10 items-center justify-center rounded-full">
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <h3 className="mt-4 font-bold">{t(`trustItems.${key}.title`)}</h3>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {t(`trustItems.${key}.body`)}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Closing band — ends on the brand colour */}
      <section aria-labelledby="closing" className="bg-brand text-brand-foreground">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 text-center sm:px-6 lg:py-20">
          <Badge variant="inverse" size="sm" className="bg-brand-foreground text-brand">
            {tCommon("comingSoon")}
          </Badge>
          <h2
            id="closing"
            className="mx-auto mt-5 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl"
          >
            {t("closing.title")}
          </h2>
          <p className="mx-auto mt-4 max-w-xl leading-relaxed opacity-80">{t("closing.body")}</p>
          <div className="mt-8 flex justify-center">
            <Button size="lg" disabled aria-describedby="closing-note">
              {t("closing.cta")}
            </Button>
          </div>
          <p id="closing-note" className="mt-4 text-sm opacity-70">
            {t("closing.note")}
          </p>
        </div>
      </section>
    </>
  );
}
