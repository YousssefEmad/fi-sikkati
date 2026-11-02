"use client";

import type { ReactNode } from "react";

import { BottomNav } from "@/components/layout/bottom-nav";
import { useSession } from "@/features/auth/session-provider";
import { cn } from "@/lib/utils";

/** Keeps bottom nav and safe padding only while someone is signed in. */
export function MobileChrome({ children }: { children: ReactNode }) {
  const { status } = useSession();
  const signedIn = status === "authenticated";

  return (
    <>
      <div className={cn("flex flex-1 flex-col", signedIn && "pb-20 md:pb-0")}>{children}</div>
      <BottomNav />
    </>
  );
}
