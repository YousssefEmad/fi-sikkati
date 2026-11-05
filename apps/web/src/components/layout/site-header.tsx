import { Logo } from "@/components/brand/logo";
import { AuthNav } from "@/components/layout/auth-nav";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { InstallAppButton } from "@/components/pwa/install-app-button";
import { NotificationBell } from "@/features/notifications/bell";

/** Public and signed-in site header: brand, language, account. */
export function SiteHeader() {
  return (
    <header className="border-border/80 bg-background/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-1.5 px-3 sm:h-16 sm:gap-4 sm:px-6">
        <Logo className="min-w-0 flex-1 sm:flex-none" />
        <div className="flex shrink-0 items-center gap-1 sm:gap-3">
          {/* Desktop only — on mobile the banner under the header keeps the logo clear. */}
          <div className="hidden sm:block">
            <InstallAppButton />
          </div>
          <NotificationBell />
          <LanguageSwitcher />
          <AuthNav />
        </div>
      </div>
    </header>
  );
}
