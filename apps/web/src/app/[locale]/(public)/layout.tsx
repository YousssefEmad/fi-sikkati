import type { ReactNode } from "react";

import { MobileChrome } from "@/components/layout/mobile-chrome";
import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";
import { InstallAppButton } from "@/components/pwa/install-app-button";
import { IntroGate } from "@/features/intro/intro-gate";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <IntroGate />
      <SiteHeader />
      <InstallAppButton tone="banner" />
      <MobileChrome>
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </MobileChrome>
    </div>
  );
}
