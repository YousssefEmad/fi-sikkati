import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";

/** Public site header: brand and language switch. Account entry points arrive with Phase 2. */
export function SiteHeader() {
  return (
    <header className="border-border/80 bg-background/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <LanguageSwitcher />
      </div>
    </header>
  );
}
