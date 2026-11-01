import type { ReactNode } from "react";

import { BottomNav } from "@/components/layout/bottom-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main id="main" className="flex-1 pb-20 md:pb-0">
        {children}
      </main>
      <BottomNav />
      <SiteFooter />
    </div>
  );
}
