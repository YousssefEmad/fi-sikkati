import { MapPin } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { SystemStatus } from "@/features/platform/components/system-status";
import { Link } from "@/i18n/navigation";

export async function SiteFooter() {
  const tFooter = await getTranslations("Footer");

  return (
    <footer className="bg-inverse text-inverse-foreground mt-auto">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <Logo tone="inverse" />
            <p className="mt-4 text-sm leading-relaxed text-white/70">{tFooter("blurb")}</p>
            <p className="mt-4 inline-flex items-center gap-2 text-sm text-white/70">
              <MapPin aria-hidden="true" className="size-4" />
              {tFooter("location")}
            </p>
          </div>
          <div className="flex flex-col items-start gap-4">
            <LanguageSwitcher tone="inverse" />
            <nav className="flex flex-wrap gap-4 text-sm">
              <Link href="/how-it-works" className="text-white/70 underline-offset-4 hover:underline">
                {tFooter("how")}
              </Link>
              <Link href="/safety" className="text-white/70 underline-offset-4 hover:underline">
                {tFooter("safety")}
              </Link>
              <Link href="/faq" className="text-white/70 underline-offset-4 hover:underline">
                {tFooter("faq")}
              </Link>
              <Link href="/about" className="text-white/70 underline-offset-4 hover:underline">
                {tFooter("about")}
              </Link>
              <Link href="/contact" className="text-white/70 underline-offset-4 hover:underline">
                {tFooter("contact")}
              </Link>
              <Link
                href="/legal/terms"
                className="text-white/70 underline-offset-4 hover:underline"
              >
                {tFooter("terms")}
              </Link>
              <Link
                href="/legal/privacy"
                className="text-white/70 underline-offset-4 hover:underline"
              >
                {tFooter("privacy")}
              </Link>
            </nav>
            <SystemStatus />
          </div>
        </div>
        <div className="mt-10 flex flex-col gap-2 border-t border-white/10 pt-6 text-xs text-white/60 sm:flex-row sm:items-center sm:justify-between">
          <p>{tFooter("rights", { year: new Date().getFullYear() })}</p>
          <p>{tFooter("buildNote")}</p>
        </div>
      </div>
    </footer>
  );
}
