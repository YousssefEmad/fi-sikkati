"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useRouter } from "@/i18n/navigation";
import { useSession } from "@/features/auth/session-provider";

/** Sends anonymous visitors to sign-in. Authenticated pages wrap their content with this. */
export function RequireAccount({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const router = useRouter();
  const t = useTranslations("Auth");

  useEffect(() => {
    if (status === "anonymous") {
      router.replace("/auth/sign-in");
    }
  }, [status, router]);

  if (status === "loading") {
    return <p className="text-muted-foreground px-4 py-16 text-center">{t("loading")}</p>;
  }
  if (status !== "authenticated") {
    return null;
  }
  return children;
}
