import Image from "next/image";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

import logoMark from "../../../public/brand/logo-square.png";

interface LogoProps {
  /** `inverse` is used on the dark footer/CTA bands. */
  tone?: "default" | "inverse";
  className?: string;
}

/**
 * Brand lockup: the logo mark plus the wordmark as live text (so it scales, translates and stays
 * selectable). The mark itself is decorative — the link is labelled by the wordmark.
 */
export function Logo({ tone = "default", className }: LogoProps) {
  const t = useTranslations("Common");

  return (
    <Link
      href="/"
      className={cn(
        "group inline-flex items-center gap-2.5 rounded-full text-lg font-extrabold tracking-tight",
        tone === "inverse" ? "text-inverse-foreground" : "text-foreground",
        className,
      )}
    >
      <Image
        src={logoMark}
        alt=""
        aria-hidden="true"
        width={40}
        height={40}
        priority
        sizes="40px"
        className="size-10 rounded-full transition-transform group-hover:scale-105"
      />
      <span>{t("brand")}</span>
    </Link>
  );
}
