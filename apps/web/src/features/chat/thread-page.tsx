"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, TextInput } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
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

function messageText(
  body: string,
  systemEvent: string | null | undefined,
  kind: string,
  t: ReturnType<typeof useTranslations<"Chat">>,
): string {
  if (kind === "SYSTEM" && systemEvent) {
    try {
      return t(`events.${systemEvent}` as "events.TRIP_STARTED");
    } catch {
      /* fall through */
    }
  }
  if (kind === "SYSTEM" && body.includes(" / ")) {
    const [ar] = body.split(" / ");
    return (ar ?? body).trim();
  }
  return body;
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
  const isCommunity = trip.tripId === null;

  return (
    <div className="mx-auto flex min-h-[70dvh] w-full max-w-3xl flex-col px-4 py-8 sm:px-6">
      <Link href="/messages" className="text-base font-bold underline-offset-4 hover:underline">
        {t("back")}
      </Link>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-extrabold">
          {isCommunity
            ? t("community")
            : trip.originLabel && trip.destinationLabel
              ? `${trip.originLabel} → ${trip.destinationLabel}`
              : t("untitled")}
        </h1>
        <StatusBadge tone={isCommunity ? "success" : "warning"}>
          {isCommunity ? t("communityBadge") : t("tripBadge")}
        </StatusBadge>
      </div>
      <p className="text-muted-foreground mt-2 text-base">
        {isCommunity
          ? t("communityHint")
          : trip.memberNames.filter(Boolean).join(" · ") || t("tripHint")}
      </p>
      {trip.isReadOnly ? (
        <p className="text-muted-foreground mt-1 text-sm font-semibold">{t("readOnly")}</p>
      ) : null}
      <ol className="mt-6 flex flex-1 flex-col gap-3">
        {messages.data?.map((item) => {
          const mine = item.senderId === account?.id;
          const text = item.deleted
            ? t("removed")
            : messageText(item.body, item.systemEvent, item.kind, t);
          return (
            <li
              key={item.id}
              className={item.kind === "SYSTEM" ? "self-center" : mine ? "self-end" : "self-start"}
              style={{ maxWidth: item.kind === "SYSTEM" ? "95%" : "85%" }}
            >
              {item.kind === "SYSTEM" ? null : (
                <p className={mine ? "mb-1 text-end text-xs font-bold" : "mb-1 text-xs font-bold"}>
                  {item.senderDisplayName ?? (mine ? account?.displayName : t("unknownSender"))}
                </p>
              )}
              <div
                className={
                  item.kind === "SYSTEM"
                    ? "bg-surface-muted text-foreground rounded-full px-4 py-2 text-center text-sm font-semibold"
                    : mine
                      ? "bg-primary text-primary-foreground rounded-2xl px-4 py-2.5 text-base"
                      : "bg-surface-muted rounded-2xl px-4 py-2.5 text-base"
                }
              >
                {text}
              </div>
            </li>
          );
        })}
      </ol>
      <form
        className="mt-6 flex items-end gap-2"
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
