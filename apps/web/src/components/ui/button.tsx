import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Accessible button primitive (shadcn/ui style). 44px minimum hit target on mobile. */
export const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary-hover",
        secondary: "bg-surface text-foreground border border-border hover:bg-surface-muted",
        ghost: "text-foreground hover:bg-surface-muted",
      },
      size: {
        md: "min-h-11 px-5",
        lg: "min-h-12 px-6 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, type = "button", ...props }: ButtonProps) {
  return (
    <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  );
}
