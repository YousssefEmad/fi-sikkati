import type { ReactNode } from "react";

export function AuthShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-md px-4 py-14 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{title}</h1>
      {description ? (
        <p className="text-muted-foreground mt-3 leading-relaxed">{description}</p>
      ) : null}
      <div className="mt-8">{children}</div>
    </div>
  );
}
