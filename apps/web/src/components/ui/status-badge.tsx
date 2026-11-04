import { BadgeCheck, CircleAlert, Clock3, ShieldX } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const TONE = {
  success: {
    className: "bg-success/15 text-success border-success/30",
    Icon: BadgeCheck,
  },
  warning: {
    className: "bg-brand-soft text-brand-foreground border-brand-strong/40",
    Icon: Clock3,
  },
  danger: {
    className: "bg-danger/10 text-danger border-danger/25",
    Icon: ShieldX,
  },
  muted: {
    className: "bg-surface-muted text-muted-foreground border-border",
    Icon: CircleAlert,
  },
} as const;

export type StatusTone = keyof typeof TONE;

/** High-visibility status chip for verified / pending / rejected states. */
export function StatusBadge({
  tone,
  children,
  className,
}: {
  tone: StatusTone;
  children: ReactNode;
  className?: string;
}) {
  const { className: toneClass, Icon } = TONE[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold leading-none",
        toneClass,
        className,
      )}
    >
      <Icon aria-hidden="true" className="size-4 shrink-0" />
      {children}
    </span>
  );
}

export function identityTone(
  status: "NOT_SUBMITTED" | "PENDING" | "APPROVED" | "REJECTED" | string,
): StatusTone {
  if (status === "APPROVED") return "success";
  if (status === "PENDING") return "warning";
  if (status === "REJECTED") return "danger";
  return "muted";
}
