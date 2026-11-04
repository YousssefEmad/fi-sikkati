import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full text-xs font-semibold leading-none",
  {
    variants: {
      variant: {
        brand: "bg-brand text-brand-foreground",
        soft: "bg-surface-muted text-foreground border-border border",
        outline: "border-border-strong text-muted-foreground border",
        inverse: "bg-white/10 text-inverse-foreground",
        success: "bg-success/15 text-success border-success/30 border font-bold",
        warning: "bg-brand-soft text-brand-foreground border-brand-strong/40 border font-bold",
        danger: "bg-danger/10 text-danger border-danger/25 border font-bold",
      },
      size: {
        sm: "px-2.5 py-1 text-sm",
        md: "px-3.5 py-1.5 text-sm",
      },
    },
    defaultVariants: { variant: "brand", size: "md" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, size }), className)} {...props} />;
}
