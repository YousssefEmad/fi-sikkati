"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, TextArea } from "@/components/ui/field";
import { RequireAccount } from "@/features/auth/require-account";
import { Link } from "@/i18n/navigation";
import { apiJson } from "@/lib/api/json";

interface AssistantReply {
  answer: string;
  searchParams: { originQuery: string | null; destinationQuery: string | null } | null;
}

export function AssistantPage() {
  return (
    <RequireAccount>
      <Assistant />
    </RequireAccount>
  );
}

function Assistant() {
  const t = useTranslations("Assistant");
  const [message, setMessage] = useState("");
  const ask = useMutation({
    mutationFn: () =>
      apiJson<AssistantReply>("/api/v1/ai/assistant", {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
  });

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("body")}</p>
      <form
        className="mt-6 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (message.trim()) ask.mutate();
        }}
      >
        <Field id="ask" label={t("prompt")}>
          <TextArea id="ask" value={message} onChange={(event) => setMessage(event.target.value)} />
        </Field>
        <Button type="submit" disabled={ask.isPending || !message.trim()}>
          {t("send")}
        </Button>
      </form>
      {ask.data ? (
        <div className="bg-surface-muted mt-8 rounded-xl p-5">
          <p>{ask.data.answer}</p>
          {ask.data.searchParams?.originQuery ? (
            <Link href="/search" className="mt-4 inline-block text-sm font-semibold underline">
              {t("openSearch")}
            </Link>
          ) : null}
        </div>
      ) : null}
      {ask.isError ? <p className="text-danger mt-4 text-sm">{t("unavailable")}</p> : null}
    </div>
  );
}
