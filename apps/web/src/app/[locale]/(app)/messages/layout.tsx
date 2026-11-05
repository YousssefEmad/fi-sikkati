import type { ReactNode } from "react";

/** Chat screens keep the composer above the mobile bottom nav — no site footer. */
export default function MessagesLayout({ children }: { children: ReactNode }) {
  return <div className="flex min-h-0 flex-1 flex-col">{children}</div>;
}
