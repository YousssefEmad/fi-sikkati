"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, TextInput } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getConversation,
  listMessages,
  markConversationRead,
  sendMessage,
} from "@/features/chat/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

export function ThreadPage({ conversationId }: { conversationId: string }) {
  return (
    <RequireAccount>
      <Thread conversationId={conversationId} />
    </RequireAccount>
  );
}

function Thread({ conversationId }: { conversationId: string }) {
  const t = useTranslations("Chat");
  const { account } = useSession();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const conversation = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId),
  });
  const messages = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => listMessages(conversationId),
    refetchInterval: 5000,
  });

  useEffect(() => {
    const last = messages.data?.at(-1);
    if (last) {
      void markConversationRead(conversationId, last.id);
    }
  }, [conversationId, messages.data]);

  const send = useMutation({
    mutationFn: () => sendMessage(conversationId, draft.trim()),
    onSuccess: async () => {
      setDraft("");
      await queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  if (conversation.isPending) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="mt-6 h-64" />
      </div>
    );
  }
  if (conversation.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <EmptyState title={t("missing")} />
      </div>
    );
  }

  const trip = conversation.data;
  return (
    <div className="mx-auto flex min-h-[70dvh] w-full max-w-3xl flex-col px-4 py-8 sm:px-6">
      <Link href="/messages" className="text-sm font-semibold underline-offset-4 hover:underline">
        {t("back")}
      </Link>
      <h1 className="mt-4 text-2xl font-extrabold">
        {trip.tripId === null
          ? t("community")
          : trip.originLabel && trip.destinationLabel
            ? `${trip.originLabel} → ${trip.destinationLabel}`
            : t("untitled")}
      </h1>
      <p className="text-muted-foreground mt-1 text-sm">
        {trip.tripId === null
          ? t("communityHint")
          : trip.memberNames.filter(Boolean).join(" · ") || t("members")}
      </p>
      {trip.isReadOnly ? <p className="text-muted-foreground mt-1 text-sm">{t("readOnly")}</p> : null}
      <ol className="mt-6 flex flex-1 flex-col gap-3">
        {messages.data?.map((item) => {
          const mine = item.senderId === account?.id;
          return (
            <li
              key={item.id}
              className={mine ? "self-end" : "self-start"}
              style={{ maxWidth: "85%" }}
            >
              <p
                className={
                  item.kind === "SYSTEM"
                    ? "text-muted-foreground mb-1 text-center text-xs font-bold"
                    : mine
                      ? "mb-1 text-end text-xs font-bold"
                      : "mb-1 text-xs font-bold"
                }
              >
                {item.kind === "SYSTEM"
                  ? t("system")
                  : (item.senderDisplayName ??
                    (mine ? account.displayName : t("unknownSender")))}
              </p>
              <div
                className={
                  item.kind === "SYSTEM"
                    ? "text-muted-foreground text-center text-xs"
                    : mine
                      ? "bg-primary text-primary-foreground rounded-2xl px-4 py-2 text-sm"
                      : "bg-surface-muted rounded-2xl px-4 py-2 text-sm"
                }
              >
                {item.deleted ? t("removed") : item.body}
              </div>
            </li>
          );
        })}
      </ol>
      <form
        className="mt-6 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (draft.trim()) send.mutate();
        }}
      >
        <Field id="chat-body" label={t("composer")}>
          <TextInput
            id="chat-body"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
            }}
            disabled={trip.isReadOnly || send.isPending}
            autoComplete="off"
          />
        </Field>
        <Button type="submit" disabled={trip.isReadOnly || send.isPending || !draft.trim()}>
          {t("send")}
        </Button>
      </form>
    </div>
  );
}
