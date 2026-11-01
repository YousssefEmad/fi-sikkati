"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { apiJson } from "@/lib/api/json";

interface Overview {
  usersTotal: number;
  usersActive7d: number;
  drivers: number;
  tripsTotal: number;
  tripsCompleted: number;
  tripsCancelled: number;
  joinRequestsTotal: number;
  joinRequestsMatched: number;
  reportsOpen: number;
}

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
    queryFn: () => apiJson<Overview>("/api/v1/admin/analytics/overview"),
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
    ["reportsOpen", query.data?.reportsOpen],
  ] as const;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("body")}</p>
      <nav className="mt-6 flex flex-wrap gap-4 text-sm font-semibold">
        <Link href="/admin/verifications" className="underline-offset-4 hover:underline">
          {t("navVerifications")}
        </Link>
        <Link href="/admin/users" className="underline-offset-4 hover:underline">
          {t("navUsers")}
        </Link>
        <Link href="/admin/trips" className="underline-offset-4 hover:underline">
          {t("navTrips")}
        </Link>
        <Link href="/admin/reports" className="underline-offset-4 hover:underline">
          {t("navReports")}
        </Link>
      </nav>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {query.isPending
          ? Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-28" />)
          : cards.map(([key, value]) => (
              <Card key={key}>
                <p className="text-muted-foreground text-sm">{t(key)}</p>
                <p className="mt-2 text-3xl font-extrabold">{value ?? "—"}</p>
              </Card>
            ))}
      </div>
    </div>
  );
}
