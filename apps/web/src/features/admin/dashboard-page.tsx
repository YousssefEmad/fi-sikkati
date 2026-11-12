"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchAdminOverview } from "@/features/admin/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

function isStaff(roles: readonly string[]): boolean {
  return roles.includes("ADMIN") || roles.includes("SUPER_ADMIN");
}

export function AdminDashboardPage() {
  return (
    <RequireAccount>
      <Dashboard />
    </RequireAccount>
  );
}

function Dashboard() {
  const t = useTranslations("AdminDash");
  const { account } = useSession();
  const query = useQuery({
    queryKey: ["admin", "overview"],
    queryFn: fetchAdminOverview,
    enabled: Boolean(account && isStaff(account.roles)),
  });

  if (account && !isStaff(account.roles)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="text-2xl font-extrabold">{t("forbidden")}</h1>
      </div>
    );
  }

  const cards = [
    ["usersTotal", query.data?.usersTotal],
    ["usersActive7d", query.data?.usersActive7d],
    ["drivers", query.data?.drivers],
    ["tripsTotal", query.data?.tripsTotal],
    ["tripsCompleted", query.data?.tripsCompleted],
    ["tripsCancelled", query.data?.tripsCancelled],
    ["joinRequestsTotal", query.data?.joinRequestsTotal],
    ["joinRequestsMatched", query.data?.joinRequestsMatched],
    ["reportsOpen", query.data?.reportsOpen],
  ] as const;

  const nav = [
    ["navUsers", "/admin/users"],
    ["navVerifications", "/admin/verifications"],
    ["navTrips", "/admin/trips"],
    ["navReports", "/admin/reports"],
  ] as const;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2 max-w-3xl text-sm">{t("body")}</p>

      <nav className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {nav.map(([key, href]) => (
          <Link
            key={href}
            href={href}
            className="border-border bg-surface hover:bg-surface-muted rounded-2xl border px-4 py-4 text-sm font-bold transition-colors"
          >
            {t(key)}
            <span className="text-muted-foreground mt-1 block text-xs font-medium">
              {t(`${key}Hint` as "navUsersHint")}
            </span>
          </Link>
        ))}
      </nav>

      <div className="mt-10">
        <h2 className="text-xl font-extrabold tracking-tight">{t("statsTitle")}</h2>
        <p className="text-muted-foreground mt-1 text-sm">{t("statsBody")}</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {query.isPending
            ? Array.from({ length: 9 }, (_, i) => <Skeleton key={i} className="h-28" />)
            : cards.map(([key, value]) => (
                <Card key={key}>
                  <p className="text-muted-foreground text-sm">{t(key)}</p>
                  <p className="mt-2 text-3xl font-extrabold tabular-nums">{value ?? "—"}</p>
                </Card>
              ))}
        </div>
      </div>
    </div>
  );
}
