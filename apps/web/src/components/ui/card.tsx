import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Neutral content container used across marketing and (later) product surfaces. */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("bg-surface border-border shadow-card rounded-lg border p-6", className)}
      {...props}
    />
  );
}
