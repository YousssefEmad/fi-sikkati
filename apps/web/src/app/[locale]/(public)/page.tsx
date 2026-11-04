import {
  BadgeCheck,
  CarFront,
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
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { HomeTripCarousel } from "@/features/landing/home-trip-carousel";
import { Link } from "@/i18n/navigation";

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
  const t = await getTranslations("Landing");

  return (
    <>
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
            <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link href="/messages" className={buttonVariants({ size: "lg", variant: "brand" })}>
                <MessageCircle aria-hidden="true" className="size-5" />
                {t("ctaCommunity")}
              </Link>
              <Link href="/search" className={buttonVariants({ size: "lg" })}>
                <Search aria-hidden="true" className="size-5" />
                {t("ctaPassenger")}
              </Link>
              <Link
                href="/trips/new"
                className={buttonVariants({ size: "lg", variant: "outline" })}
              >
                <CarFront aria-hidden="true" className="size-5" />
                {t("ctaDriver")}
              </Link>
            </div>
            <p id="status-note" className="text-muted-foreground mt-5 max-w-md text-base">
              {t("statusNote")}
            </p>
          </div>

          <HomeTripCarousel />
        </div>
      </section>

      <section aria-labelledby="difference" className="bg-inverse text-inverse-foreground">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
          <h2
            id="difference"
            className="max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl"
          >
            {t("difference.title")}
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-white/70">
            {t("difference.body")}
          </p>
          <ul className="mt-12 grid gap-8 sm:grid-cols-3">
            {DIFFERENCE.map(({ key, Icon }) => (
              <li key={key} className="border-t-2 border-white/15 pt-5">
                <Icon aria-hidden="true" className="text-brand size-7" />
                <h3 className="mt-4 text-lg font-bold">{t(`difference.points.${key}.title`)}</h3>
                <p className="mt-2 text-base leading-relaxed text-white/70">
                  {t(`difference.points.${key}.body`)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

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
            <p className="text-muted-foreground mt-4 text-base leading-relaxed">
              {t("howItWorksBody")}
            </p>
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
                  <p className="text-muted-foreground mt-2 text-base leading-relaxed">
                    {t(`steps.${key}.body`)}
                  </p>
                </Card>
              </li>
            ))}
          </ol>
        </div>
      </section>

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
            <p className="text-muted-foreground mt-4 text-base leading-relaxed">{t("trustBody")}</p>
          </div>
          <ul className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {TRUST.map(({ key, Icon }) => (
              <li key={key}>
                <Card className="h-full">
                  <span className="bg-brand text-brand-foreground flex size-10 items-center justify-center rounded-full">
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <h3 className="mt-4 text-base font-bold">{t(`trustItems.${key}.title`)}</h3>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {t(`trustItems.${key}.body`)}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="closing" className="bg-brand text-brand-foreground">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 text-center sm:px-6 lg:py-20">
          <h2
            id="closing"
            className="mx-auto mt-5 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl"
          >
            {t("closing.title")}
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed opacity-80">
            {t("closing.body")}
          </p>
          <div className="mt-8 flex justify-center">
            <Link
              href="/auth/register"
              className={buttonVariants({ size: "lg", variant: "inverse" })}
            >
              {t("closing.cta")}
            </Link>
          </div>
          <p id="closing-note" className="mt-4 text-sm opacity-70">
            {t("closing.note")}
          </p>
        </div>
      </section>
    </>
  );
}
