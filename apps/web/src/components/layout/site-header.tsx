import { Logo } from "@/components/brand/logo";
import { AuthNav } from "@/components/layout/auth-nav";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { NotificationBell } from "@/features/notifications/bell";

/** Public and signed-in site header: brand, language, account. */
export function SiteHeader() {
  return (
    <header className="border-border/80 bg-background/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-2 sm:gap-3">
          <NotificationBell />
          <LanguageSwitcher />
          <AuthNav />
        </div>
      </div>
    </header>
  );
}
