import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Accessible button primitive (shadcn/ui style). 44px minimum hit target on mobile (NFR-02). */
export const buttonVariants = cva(
  "inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-full text-base font-bold transition-[background-color,color,box-shadow,transform] active:translate-y-px disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary-hover shadow-card",
        brand: "bg-brand text-brand-foreground hover:bg-brand-strong shadow-card",
        outline:
          "border-border-strong text-foreground hover:bg-surface-muted border bg-transparent",
        ghost: "text-foreground hover:bg-surface-muted bg-transparent",
        inverse: "bg-surface text-foreground hover:bg-surface-muted",
      },
      size: {
        sm: "min-h-11 px-4 text-sm",
        md: "min-h-12 px-6 text-base",
        lg: "min-h-14 px-8 text-lg",
      },
      block: {
        true: "w-full",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export function Button({
  className,
  variant,
  size,
  block,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size, block }), className)}
      {...props}
    />
  );
}
