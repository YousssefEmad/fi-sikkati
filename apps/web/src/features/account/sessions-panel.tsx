"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { listSessions, revokeSession, type SessionSummary } from "@/features/auth/api";
import { apiErrorMessage } from "@/lib/api/error-message";
import { useQuery, useQueryClient } from "@tanstack/react-query";

export function SessionsPanel() {
  const t = useTranslations("Account");
  const errorsT = useTranslations("Errors");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["sessions"], queryFn: listSessions });
  const [error, setError] = useState<string | undefined>();

  async function onRevoke(session: SessionSummary) {
    setError(undefined);
    try {
      await revokeSession(session.id);
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    } catch (caught) {
      setError(apiErrorMessage(caught, errorsT));
    }
  }

  if (query.isPending) {
    return <p className="text-muted-foreground">{t("loading")}</p>;
  }
  if (query.isError) {
    return <p className="text-danger">{t("errors.generic")}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? <p className="text-danger text-sm">{error}</p> : null}
      <ul className="flex flex-col gap-3">
        {query.data.map((session) => (
          <li
            key={session.id}
            className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-semibold">
                {session.device ?? t("unknownDevice")}
                {session.current ? (
                  <span className="text-success ms-2 text-xs font-medium">{t("thisDevice")}</span>
                ) : null}
              </p>
              <p className="text-muted-foreground text-sm">
                {t("lastUsed", {
                  time: session.lastUsedAt
                    ? new Date(session.lastUsedAt).toLocaleString()
                    : t("never"),
                })}
              </p>
            </div>
            {session.current ? null : (
              <Button variant="outline" size="sm" onClick={() => void onRevoke(session)}>
                {t("revokeSession")}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
