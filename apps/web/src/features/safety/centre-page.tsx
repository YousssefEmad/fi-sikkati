"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, SelectInput, TextArea, TextInput } from "@/components/ui/field";
import { RequireAccount } from "@/features/auth/require-account";
import { apiJson } from "@/lib/api/json";

interface BlockRow {
  userId: string;
  displayName: string;
  createdAt: string;
}

interface ReportRow {
  id: string;
  targetType: string;
  reason: string;
  status: string;
  createdAt: string;
}

export function SafetyCentrePage() {
  return (
    <RequireAccount>
      <SafetyCentre />
    </RequireAccount>
  );
}

function SafetyCentre() {
  const t = useTranslations("Safety");
  const queryClient = useQueryClient();
  const blocks = useQuery({
    queryKey: ["blocks"],
    queryFn: () => apiJson<{ items: BlockRow[] }>("/api/v1/me/blocks"),
  });
  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: () => apiJson<{ items: ReportRow[] }>("/api/v1/me/reports"),
  });
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("OTHER");
  const [description, setDescription] = useState("");

  const report = useMutation({
    mutationFn: () =>
      apiJson("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({
          targetType: "USER",
          targetId,
          reason,
          description: description || null,
        }),
      }),
    onSuccess: async () => {
      setTargetId("");
      setDescription("");
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });

  const unblock = useMutation({
    mutationFn: (userId: string) => apiJson(`/api/v1/me/blocks/${userId}`, { method: "DELETE" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["blocks"] });
    },
  });

  return (
    <div className="mx-auto w-full max-w-3xl space-y-10 px-4 py-10 sm:px-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground mt-2 text-sm">{t("body")}</p>
      </div>
      <section>
        <h2 className="text-xl font-bold">{t("reportTitle")}</h2>
        <form
          className="mt-4 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (targetId) report.mutate();
          }}
        >
          <Field id="target" label={t("targetId")}>
            <TextInput id="target" value={targetId} onChange={(e) => setTargetId(e.target.value)} />
          </Field>
          <Field id="reason" label={t("reason")}>
            <SelectInput id="reason" value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="SAFETY">SAFETY</option>
              <option value="HARASSMENT">HARASSMENT</option>
              <option value="SPAM">SPAM</option>
              <option value="NO_SHOW">NO_SHOW</option>
              <option value="FRAUD">FRAUD</option>
              <option value="OTHER">OTHER</option>
            </SelectInput>
          </Field>
          <Field id="desc" label={t("description")}>
            <TextArea id="desc" value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <Button type="submit" disabled={report.isPending || !targetId}>
            {t("submitReport")}
          </Button>
        </form>
      </section>
      <section>
        <h2 className="text-xl font-bold">{t("myReports")}</h2>
        <div className="mt-4 space-y-3">
          {reports.data?.items.length === 0 ? <EmptyState title={t("noReports")} /> : null}
          {reports.data?.items.map((item) => (
            <p key={item.id} className="border-border rounded-xl border px-4 py-3 text-sm">
              {item.reason} · {item.status} · {item.targetType}
            </p>
          ))}
        </div>
      </section>
      <section>
        <h2 className="text-xl font-bold">{t("blocks")}</h2>
        <div className="mt-4 space-y-3">
          {blocks.data?.items.length === 0 ? <EmptyState title={t("noBlocks")} /> : null}
          {blocks.data?.items.map((item) => (
            <div
              key={item.userId}
              className="border-border flex items-center justify-between rounded-xl border px-4 py-3"
            >
              <p className="font-semibold">{item.displayName}</p>
              <Button variant="outline" size="sm" onClick={() => unblock.mutate(item.userId)}>
                {t("unblock")}
              </Button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
