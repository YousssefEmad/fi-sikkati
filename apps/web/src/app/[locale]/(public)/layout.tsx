import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { SystemStatus } from "@/features/platform/components/system-status";
import { Link } from "@/i18n/navigation";

export default async function PublicLayout({ children }: { children: ReactNode }) {
  const [tMeta, tFooter] = await Promise.all([
    getTranslations("Metadata"),
    getTranslations("Footer"),
  ]);

  return (
    <>
      <header className="border-border border-b">
        <nav
          aria-label={tMeta("siteName")}
          className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6"
        >
          <Link href="/" className="text-primary text-lg font-bold tracking-tight">
            {tMeta("siteName")}
          </Link>
          <LanguageSwitcher />
        </nav>
      </header>

      <main id="main" className="flex-1">
        {children}
      </main>

      <footer className="border-border border-t">
        <div className="text-muted-foreground mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-6 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>{tFooter("rights", { year: new Date().getFullYear() })}</p>
          <SystemStatus />
        </div>
      </footer>
    </>
  );
}
