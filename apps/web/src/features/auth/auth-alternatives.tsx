"use client";

import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/**
 * Extra sign-in/up paths. Google needs NEXT_PUBLIC_GOOGLE_CLIENT_ID + API wiring;
 * phone OTP login is staged behind a dedicated page until SMS is production-ready.
 */
export function AuthAlternatives({ mode }: { mode: "signIn" | "register" }) {
  const t = useTranslations("Auth");
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "";

  return (
    <div className="mt-6 space-y-3">
      <div className="relative flex items-center gap-3">
        <span className="border-border h-px flex-1 border-t" />
        <span className="text-muted-foreground text-xs font-bold tracking-wide uppercase">
          {t("orContinue")}
        </span>
        <span className="border-border h-px flex-1 border-t" />
      </div>

      <button
        type="button"
        className={cn(buttonVariants({ variant: "outline", block: true }), "gap-2")}
        disabled={!googleClientId}
        title={googleClientId ? t("google") : t("googleSoon")}
        onClick={() => {
          if (!googleClientId) {
            window.alert(t("googleSoon"));
            return;
          }
          window.alert(t("googleSoon"));
        }}
      >
        <GoogleMark />
        {t("google")}
      </button>

      <Link
        href="/auth/phone"
        className={cn(buttonVariants({ variant: "outline", block: true }), "gap-2")}
      >
        {mode === "register" ? t("phoneRegister") : t("phoneSignIn")}
      </Link>
      <p className="text-muted-foreground text-center text-xs leading-relaxed">{t("altHint")}</p>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5">
      <path
        fill="#EA4335"
        d="M12 10.2v3.6h5.1c-.2 1.2-.9 2.3-1.9 3l3.1 2.4c1.8-1.7 2.9-4.1 2.9-7 0-.7-.1-1.3-.2-1.9H12z"
      />
      <path
        fill="#34A853"
        d="M6.6 14.3 5.8 14.9l-2.5 2C4.8 19.7 8.1 22 12 22c2.7 0 5-.9 6.7-2.4l-3.1-2.4c-.9.6-2 1-3.6 1-2.8 0-5.1-1.9-5.9-4.4z"
      />
      <path
        fill="#4A90E2"
        d="M3.3 7.1C2.5 8.6 2 10.2 2 12s.5 3.4 1.3 4.9l3.3-2.6C6.2 13.5 6 12.8 6 12c0-.8.2-1.5.5-2.2L3.3 7.1z"
      />
      <path
        fill="#FBBC05"
        d="M12 6c1.5 0 2.8.5 3.8 1.5l2.8-2.8C16.9 3 14.7 2 12 2 8.1 2 4.8 4.3 3.3 7.1l3.2 2.5C7 7.9 9.2 6 12 6z"
      />
    </svg>
  );
}
