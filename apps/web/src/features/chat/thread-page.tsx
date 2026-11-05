"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckSquare, Eraser, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TextInput } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  clearConversation,
  deleteMessage,
  deleteMessages,
  getConversation,
  listMessages,
  markConversationRead,
  sendMessage,
} from "@/features/chat/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

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
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);
  const isModerator =
    account?.roles.includes("ADMIN") === true || account?.roles.includes("SUPER_ADMIN") === true;

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

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }, [messages.data, selectMode]);

  async function refreshMessages() {
    await queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
  }

  const send = useMutation({
    mutationFn: () => sendMessage(conversationId, draft.trim()),
    onSuccess: async () => {
      setDraft("");
      await refreshMessages();
    },
  });

  const removeOne = useMutation({
    mutationFn: (messageId: string) => deleteMessage(conversationId, messageId),
    onSuccess: async () => {
      await refreshMessages();
    },
  });

  const removeMany = useMutation({
    mutationFn: (ids: string[]) => deleteMessages(conversationId, ids),
    onSuccess: async () => {
      setSelected(new Set());
      setSelectMode(false);
      await refreshMessages();
    },
  });

  const clearAll = useMutation({
    mutationFn: () => clearConversation(conversationId),
    onSuccess: async () => {
      setSelected(new Set());
      setSelectMode(false);
      await refreshMessages();
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

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="bg-background fixed inset-x-0 top-14 bottom-20 z-30 flex flex-col sm:top-16 md:bottom-0">
      <div className="border-border mx-auto flex h-full w-full max-w-3xl flex-col border-x">
        <header className="border-border shrink-0 border-b px-4 py-3 sm:px-5">
          <Link href="/messages" className="text-sm font-bold underline-offset-4 hover:underline">
            {t("back")}
          </Link>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-extrabold sm:text-2xl">
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
          <p className="text-muted-foreground mt-1 line-clamp-1 text-sm">
            {isCommunity
              ? t("communityHint")
              : trip.memberNames.filter(Boolean).join(" · ") || t("tripHint")}
          </p>
          {isModerator ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {selectMode ? (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={selected.size === 0 || removeMany.isPending}
                    onClick={() => {
                      if (
                        window.confirm(t("confirmDeleteSelected", { count: selected.size }))
                      ) {
                        removeMany.mutate([...selected]);
                      }
                    }}
                  >
                    <Trash2 aria-hidden="true" className="size-4" />
                    {t("deleteSelected", { count: selected.size })}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setSelectMode(false);
                      setSelected(new Set());
                    }}
                  >
                    <X aria-hidden="true" className="size-4" />
                    {t("cancelSelect")}
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectMode(true);
                    }}
                  >
                    <CheckSquare aria-hidden="true" className="size-4" />
                    {t("selectMessages")}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={clearAll.isPending}
                    onClick={() => {
                      if (window.confirm(t("confirmClear"))) {
                        clearAll.mutate();
                      }
                    }}
                  >
                    <Eraser aria-hidden="true" className="size-4" />
                    {t("clearChat")}
                  </Button>
                </>
              )}
            </div>
          ) : null}
        </header>

        <div
          ref={listRef}
          className="bg-surface-muted/40 min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-3 sm:px-4"
        >
          <div className="flex min-h-full flex-col justify-end gap-1.5">
            {(messages.data ?? []).map((item) => {
              const mine = item.senderId === account?.id;
              const text = item.deleted
                ? t("removed")
                : messageText(item.body, item.systemEvent, item.kind, t);
              const canModerate =
                isModerator && item.kind === "TEXT" && !item.deleted;
              const checked = selected.has(item.id);

              if (item.kind === "SYSTEM") {
                return (
                  <div key={item.id} className="flex justify-center py-1">
                    <span className="bg-surface text-muted-foreground rounded-full px-3 py-1 text-center text-xs font-semibold shadow-sm">
                      {text}
                    </span>
                  </div>
                );
              }

              return (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-end gap-2",
                    mine ? "justify-end" : "justify-start",
                    selectMode && canModerate && "cursor-pointer",
                  )}
                  onClick={() => {
                    if (selectMode && canModerate) toggleSelected(item.id);
                  }}
                >
                  {selectMode && canModerate ? (
                    <input
                      type="checkbox"
                      className="mb-3 size-4 shrink-0"
                      checked={checked}
                      readOnly
                      aria-label={t("selectMessage")}
                    />
                  ) : null}
                  <div className={cn("max-w-[82%] sm:max-w-[75%]", mine && "items-end")}>
                    <p
                      className={cn(
                        "text-muted-foreground mb-0.5 px-1 text-[11px] font-bold",
                        mine ? "text-end" : "text-start",
                      )}
                    >
                      {item.senderDisplayName ??
                        (mine ? account?.displayName : t("unknownSender"))}
                    </p>
                    <div
                      className={cn(
                        "rounded-2xl px-3.5 py-2 text-[15px] leading-snug shadow-sm",
                        item.deleted
                          ? "bg-surface-muted text-muted-foreground italic"
                          : mine
                            ? "bg-primary text-primary-foreground rounded-ee-md"
                            : "bg-surface text-foreground rounded-es-md",
                        checked && "ring-brand-strong ring-2",
                      )}
                    >
                      {text}
                    </div>
                    {isModerator && !selectMode && canModerate ? (
                      <button
                        type="button"
                        className={cn(
                          "text-danger mt-1 text-xs font-bold underline-offset-2 hover:underline",
                          mine ? "ms-auto block" : "block",
                        )}
                        disabled={removeOne.isPending}
                        onClick={(event) => {
                          event.stopPropagation();
                          if (window.confirm(t("confirmDeleteOne"))) {
                            removeOne.mutate(item.id);
                          }
                        }}
                      >
                        {t("deleteOne")}
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <form
          className="border-border bg-background shrink-0 border-t px-3 py-2.5 sm:px-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (draft.trim()) send.mutate();
          }}
        >
          <div className="flex items-center gap-2">
            <label htmlFor="chat-body" className="sr-only">
              {t("composer")}
            </label>
            <TextInput
              id="chat-body"
              className="min-h-12 flex-1 rounded-full px-4"
              placeholder={t("composer")}
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
              }}
              disabled={trip.isReadOnly || send.isPending || selectMode}
              autoComplete="off"
            />
            <Button
              type="submit"
              className="min-h-12 shrink-0 rounded-full px-5"
              disabled={
                trip.isReadOnly || send.isPending || selectMode || !draft.trim()
              }
            >
              {t("send")}
            </Button>
          </div>
          {trip.isReadOnly ? (
            <p className="text-muted-foreground mt-1 text-center text-xs font-semibold">
              {t("readOnly")}
            </p>
          ) : null}
        </form>
      </div>
    </div>
  );
}
