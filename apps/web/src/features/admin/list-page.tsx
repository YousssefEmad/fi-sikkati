"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/empty-state";
import { RequireAccount } from "@/features/auth/require-account";
import { apiJson } from "@/lib/api/json";

export function AdminListPage({
  titleKey,
  path,
}: {
  titleKey: "navUsers" | "navTrips" | "navReports";
  path: string;
}) {
  return (
    <RequireAccount>
      <List titleKey={titleKey} path={path} />
    </RequireAccount>
  );
}

function List({
  titleKey,
  path,
}: {
  titleKey: "navUsers" | "navTrips" | "navReports";
  path: string;
}) {
  const t = useTranslations("AdminDash");
  const query = useQuery({
    queryKey: ["admin", path],
    queryFn: () => apiJson<{ items: Record<string, unknown>[]; totalCount: number }>(path),
  });
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t(titleKey)}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("count", { n: query.data?.totalCount ?? 0 })}</p>
      <div className="mt-6 space-y-3">
        {query.data?.items.length === 0 ? <EmptyState title={t("empty")} /> : null}
        {query.data?.items.map((item, index) => (
          <pre
            key={String(item.id ?? index)}
            className="border-border overflow-x-auto rounded-xl border p-4 text-xs"
          >
            {JSON.stringify(item, null, 2)}
          </pre>
        ))}
      </div>
    </div>
  );
}
