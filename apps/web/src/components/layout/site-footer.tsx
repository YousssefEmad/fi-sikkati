import { MapPin } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { SystemStatus } from "@/features/platform/components/system-status";

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
