"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import { ApiRequestError, verifyEmail } from "@/features/auth/api";
import { Link } from "@/i18n/navigation";

export function VerifyEmailPanel({ token }: { token: string }) {
  const t = useTranslations("Auth");
  const [state, setState] = useState<"working" | "ok" | "error">(token ? "working" : "error");
  const [detail, setDetail] = useState<string | undefined>();

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    void verifyEmail(token)
      .then(() => {
        if (!cancelled) setState("ok");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState("error");
        setDetail(error instanceof ApiRequestError ? error.message : t("errors.generic"));
      });
    return () => {
      cancelled = true;
    };
  }, [token, t]);

  if (!token) {
    return <p className="text-danger">{t("missingToken")}</p>;
  }
  if (state === "working") {
    return <p className="text-muted-foreground">{t("verifying")}</p>;
  }
  if (state === "ok") {
    return (
      <div className="flex flex-col gap-4">
        <p>{t("verifyOk")}</p>
        <Link href="/auth/sign-in" className={buttonVariants()}>
          {t("signInSubmit")}
        </Link>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-danger">{detail}</p>
      <Link
        href="/auth/sign-in"
        className="text-primary font-semibold underline-offset-4 hover:underline"
      >
        {t("backToSignIn")}
      </Link>
    </div>
  );
}
