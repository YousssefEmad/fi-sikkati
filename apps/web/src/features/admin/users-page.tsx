"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TextInput } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import {
  deactivateAdminUser,
  listAdminUsers,
  restoreAdminUser,
  suspendAdminUser,
  type AdminUserListItem,
} from "@/features/admin/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api/error-message";

function isStaff(roles: readonly string[]): boolean {
  return roles.includes("ADMIN") || roles.includes("SUPER_ADMIN");
}

function formatDate(value: string | null | undefined, locale: string): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "ar-EG", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function AdminUsersPage() {
  return (
    <RequireAccount>
      <UsersConsole />
    </RequireAccount>
  );
}

function UsersConsole() {
  const t = useTranslations("AdminDash");
  const errorsT = useTranslations("Errors");
  const locale = useLocale();
  const { account } = useSession();
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [status, setStatus] = useState<string>("");
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<string | undefined>();
  const [pendingId, setPendingId] = useState<string | null>(null);

  const canModerate = Boolean(
    account?.roles.includes("ADMIN") || account?.roles.includes("SUPER_ADMIN"),
  );

  const query = useQuery({
    queryKey: ["admin", "users", submittedQ, status, page],
    queryFn: () => {
      const params: {
        q?: string;
        status?: string;
        page?: number;
        pageSize?: number;
      } = { page, pageSize: 50 };
      if (submittedQ) params.q = submittedQ;
      if (status) params.status = status;
      return listAdminUsers(params);
    },
    enabled: Boolean(account && isStaff(account.roles)),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] });

  const suspend = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => suspendAdminUser(id, reason),
    onSuccess: async () => {
      setActionError(undefined);
      await invalidate();
    },
    onError: (error) => setActionError(apiErrorMessage(error, errorsT)),
    onSettled: () => setPendingId(null),
  });

  const restore = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => restoreAdminUser(id, reason),
    onSuccess: async () => {
      setActionError(undefined);
      await invalidate();
    },
    onError: (error) => setActionError(apiErrorMessage(error, errorsT)),
    onSettled: () => setPendingId(null),
  });

  const deactivate = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => deactivateAdminUser(id, reason),
    onSuccess: async () => {
      setActionError(undefined);
      await invalidate();
      await queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
    },
    onError: (error) => setActionError(apiErrorMessage(error, errorsT)),
    onSettled: () => setPendingId(null),
  });

  const items = query.data?.items ?? [];
  const totalPages = query.data?.totalPages ?? 1;

  const statusOptions = useMemo(
    () =>
      [
        ["", t("filterAll")],
        ["ACTIVE", t("statusActive")],
        ["SUSPENDED", t("statusSuspended")],
        ["DEACTIVATED", t("statusDeactivated")],
      ] as const,
    [t],
  );

  if (account && !isStaff(account.roles)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="text-2xl font-extrabold">{t("forbidden")}</h1>
      </div>
    );
  }

  function askReason(promptLabel: string): string | null {
    const reason = window.prompt(promptLabel, t("reasonDefault"));
    if (!reason || reason.trim().length < 8) {
      setActionError(t("reasonTooShort"));
      return null;
    }
    return reason.trim();
  }

  function onSuspend(user: AdminUserListItem) {
    const reason = askReason(t("suspendPrompt", { name: user.displayName }));
    if (!reason) return;
    setPendingId(user.id);
    suspend.mutate({ id: user.id, reason });
  }

  function onRestore(user: AdminUserListItem) {
    const reason = askReason(t("restorePrompt", { name: user.displayName }));
    if (!reason) return;
    setPendingId(user.id);
    restore.mutate({ id: user.id, reason });
  }

  function onDeactivate(user: AdminUserListItem) {
    if (!window.confirm(t("deactivateConfirm", { name: user.displayName, email: user.email }))) {
      return;
    }
    const reason = askReason(t("deactivatePrompt", { name: user.displayName }));
    if (!reason) return;
    setPendingId(user.id);
    deactivate.mutate({ id: user.id, reason });
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-muted-foreground text-sm">
            <Link href="/admin" className="underline-offset-4 hover:underline">
              {t("title")}
            </Link>
          </p>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{t("navUsers")}</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            {t("usersBody")}
          </p>
        </div>
        <p className="text-muted-foreground text-sm font-semibold">
          {t("count", { n: query.data?.totalCount ?? 0 })}
        </p>
      </div>

      <form
        className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setSubmittedQ(q.trim());
        }}
      >
        <label className="min-w-0 flex-1 text-sm font-semibold">
          <span className="mb-1 block">{t("searchLabel")}</span>
          <TextInput
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder={t("searchPlaceholder")}
            autoComplete="off"
          />
        </label>
        <label className="text-sm font-semibold sm:w-48">
          <span className="mb-1 block">{t("statusLabel")}</span>
          <select
            className="border-border bg-background min-h-12 w-full rounded-xl border px-3 text-base"
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value);
            }}
          >
            {statusOptions.map(([value, label]) => (
              <option key={value || "all"} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit" variant="brand">
          {t("search")}
        </Button>
      </form>

      {actionError ? (
        <p className="text-destructive mt-4 text-sm font-semibold" role="alert">
          {actionError}
        </p>
      ) : null}

      <div className="mt-6 overflow-x-auto rounded-2xl border border-[color:var(--border)]">
        <table className="min-w-full text-start text-sm">
          <thead className="bg-[color:var(--surface-muted)] text-[color:var(--muted-foreground)]">
            <tr>
              <th className="px-4 py-3 font-semibold">{t("colUser")}</th>
              <th className="px-4 py-3 font-semibold">{t("colStatus")}</th>
              <th className="px-4 py-3 font-semibold">{t("colRoles")}</th>
              <th className="px-4 py-3 font-semibold">{t("colJoined")}</th>
              <th className="px-4 py-3 font-semibold">{t("colLastLogin")}</th>
              <th className="px-4 py-3 font-semibold">{t("colActions")}</th>
            </tr>
          </thead>
          <tbody>
            {query.isPending
              ? Array.from({ length: 6 }, (_, index) => (
                  <tr key={index} className="border-t border-[color:var(--border)]">
                    <td className="px-4 py-3" colSpan={6}>
                      <Skeleton className="h-10 w-full" />
                    </td>
                  </tr>
                ))
              : null}
            {!query.isPending && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10">
                  <EmptyState title={t("empty")} />
                </td>
              </tr>
            ) : null}
            {items.map((user) => {
              const busy = pendingId === user.id;
              const isProtected = user.roles.includes("SUPER_ADMIN");
              return (
                <tr key={user.id} className="border-t border-[color:var(--border)] align-top">
                  <td className="px-4 py-3">
                    <p className="font-bold">{user.displayName}</p>
                    <p className="text-muted-foreground mt-0.5 break-all">{user.email}</p>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {user.emailVerified ? t("emailVerified") : t("emailUnverified")}
                      {user.city ? ` · ${user.city}` : ""}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={user.status} />
                    <p className="text-muted-foreground mt-1 text-xs">
                      {identityLabel(t, user.identityVerificationStatus)}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <span
                          key={role}
                          className="bg-[color:var(--surface-muted)] rounded-full px-2 py-0.5 text-xs font-semibold"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="text-muted-foreground px-4 py-3 whitespace-nowrap">
                    {formatDate(user.createdAt, locale)}
                  </td>
                  <td className="text-muted-foreground px-4 py-3 whitespace-nowrap">
                    {formatDate(user.lastLoginAt, locale)}
                  </td>
                  <td className="px-4 py-3">
                    {canModerate && !isProtected ? (
                      <div className="flex flex-col gap-2">
                        {user.status === "ACTIVE" ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() => onSuspend(user)}
                          >
                            {t("actionSuspend")}
                          </Button>
                        ) : null}
                        {user.status === "SUSPENDED" ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() => onRestore(user)}
                          >
                            {t("actionRestore")}
                          </Button>
                        ) : null}
                        {user.status !== "DEACTIVATED" && user.status !== "DELETED" ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busy}
                            onClick={() => onDeactivate(user)}
                          >
                            {t("actionDeactivate")}
                          </Button>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        {isProtected ? t("protectedAccount") : "—"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 ? (
        <div className="mt-4 flex items-center justify-between gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || query.isPending}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            {t("prevPage")}
          </Button>
          <p className="text-muted-foreground text-sm">
            {t("pageOf", { page, total: totalPages })}
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || query.isPending}
            onClick={() => setPage((current) => current + 1)}
          >
            {t("nextPage")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function identityLabel(
  t: (key: "identity.PENDING" | "identity.APPROVED" | "identity.REJECTED" | "identity.UNVERIFIED") => string,
  status: string,
): string {
  switch (status) {
    case "PENDING":
      return t("identity.PENDING");
    case "APPROVED":
      return t("identity.APPROVED");
    case "REJECTED":
      return t("identity.REJECTED");
    default:
      return t("identity.UNVERIFIED");
  }
}

function StatusPill({ status }: { status: string }) {
  const t = useTranslations("AdminDash");
  const label =
    status === "ACTIVE"
      ? t("statusActive")
      : status === "SUSPENDED"
        ? t("statusSuspended")
        : status === "DEACTIVATED"
          ? t("statusDeactivated")
          : status === "DELETED"
            ? t("statusDeleted")
            : status;
  return (
    <span className="bg-[color:var(--surface-muted)] inline-flex rounded-full px-2.5 py-1 text-xs font-bold">
      {label}
    </span>
  );
}
