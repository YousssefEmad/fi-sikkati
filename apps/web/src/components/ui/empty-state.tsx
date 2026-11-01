import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  body,
  action,
  className,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("border-border bg-surface-muted rounded-xl border px-6 py-12 text-center", className)}>
      <p className="text-lg font-bold">{title}</p>
      {body ? <p className="text-muted-foreground mx-auto mt-2 max-w-md text-sm">{body}</p> : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
