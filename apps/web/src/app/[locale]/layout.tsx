import type { Metadata, Viewport } from "next";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { LOCALE_DIRECTION, routing } from "@/i18n/routing";
import { clientEnv } from "@/lib/env";
import { cairo, jakarta } from "@/lib/fonts";
import { QueryProvider } from "@/lib/query/provider";
import { PwaRegister } from "@/components/pwa/register";
import { SessionProvider } from "@/features/auth/session-provider";
import { cn } from "@/lib/utils";

import "@/app/globals.css";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export const viewport: Viewport = {
  // Browser chrome follows the ink surface used by the header on scroll, not the bright brand lime.
  themeColor: "#1A1C16",
  colorScheme: "light",
  viewportFit: "cover",
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Metadata" });
  const siteUrl = clientEnv.NEXT_PUBLIC_SITE_URL;

  return {
    metadataBase: new URL(siteUrl),
    title: { default: t("title"), template: `%s · ${t("siteName")}` },
    description: t("description"),
    applicationName: t("siteName"),
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(routing.locales.map((code) => [code, `/${code}`])),
    },
    openGraph: {
      type: "website",
      siteName: t("siteName"),
      title: t("title"),
      description: t("description"),
      locale: locale === "ar" ? "ar_EG" : "en_US",
      url: `/${locale}`,
      images: [{ url: "/brand/og.png", width: 1200, height: 630, alt: t("siteName") }],
    },
    twitter: {
      card: "summary_large_image",
      title: t("title"),
      description: t("description"),
      images: ["/brand/og.png"],
    },
    robots: { index: true, follow: true },
    appleWebApp: {
      capable: true,
      title: t("siteName"),
      statusBarStyle: "default",
    },
    icons: {
      apple: "/icons/icon-192.png",
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  const direction = LOCALE_DIRECTION[locale];
  const t = await getTranslations({ locale, namespace: "Common" });

  return (
    <html
      lang={locale}
      dir={direction}
      className={cn(cairo.variable, jakarta.variable)}
      suppressHydrationWarning
    >
      <body
        className={cn("flex min-h-dvh flex-col", locale === "ar" ? "font-arabic" : "font-latin")}
      >
        <a
          href="#main"
          className="bg-primary text-primary-foreground sr-only rounded-full px-5 py-3 font-semibold focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-50"
        >
          {t("skipToContent")}
        </a>
        <NextIntlClientProvider>
          <QueryProvider>
            <SessionProvider>
              <PwaRegister />
              {children}
            </SessionProvider>
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
