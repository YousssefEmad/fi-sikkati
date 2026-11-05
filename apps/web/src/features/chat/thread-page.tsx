"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eraser, ImagePlus, Mic, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TextInput } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  adminDeleteConversation,
  clearConversation,
  deleteMessage,
  getConversation,
  listMessages,
  markConversationRead,
  sendMessage,
} from "@/features/chat/api";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link, useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

const WALLPAPER_KEY = "fi-sikkati-chat-wallpaper";

const PRESET_WALLPAPERS = [
  {
    id: "soft",
    style: "linear-gradient(160deg, #f3f6ea 0%, #e8f0d4 45%, #dce8c4 100%)",
  },
  {
    id: "dusk",
    style: "linear-gradient(160deg, #1a1c16 0%, #2c3224 50%, #3d4630 100%)",
  },
  {
    id: "mint",
    style: "linear-gradient(160deg, #e9fff0 0%, #d4f5e0 40%, #c4ecd4 100%)",
  },
] as const;

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
  const router = useRouter();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [wallpaper, setWallpaper] = useState<string>(PRESET_WALLPAPERS[0].style);
  const [showWallpaper, setShowWallpaper] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const longPressTimer = useRef<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
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
    try {
      const saved = localStorage.getItem(WALLPAPER_KEY);
      if (saved) setWallpaper(saved);
    } catch {
      /* ignore */
    }
  }, []);

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
  }, [messages.data]);

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
      setMenuFor(null);
      await refreshMessages();
    },
  });

  const clearAll = useMutation({
    mutationFn: () => clearConversation(conversationId),
    onSuccess: async () => {
      await refreshMessages();
    },
  });

  const purgeTripChat = useMutation({
    mutationFn: () => adminDeleteConversation(conversationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      router.replace("/messages");
    },
  });

  function saveWallpaper(value: string) {
    setWallpaper(value);
    try {
      localStorage.setItem(WALLPAPER_KEY, value);
    } catch {
      /* ignore */
    }
    setShowWallpaper(false);
  }

  function startLongPress(messageId: string, canAct: boolean) {
    if (!canAct) return;
    longPressTimer.current = window.setTimeout(() => {
      setMenuFor(messageId);
    }, 480);
  }

  function cancelLongPress() {
    if (longPressTimer.current !== null) {
      window.clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }

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
  const darkPaper = wallpaper.includes("#1a1c16") || wallpaper.includes("2c3224");

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
          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                setShowWallpaper(true);
              }}
            >
              <ImagePlus aria-hidden="true" className="size-4" />
              {t("wallpaper")}
            </Button>
            {isModerator ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={clearAll.isPending}
                onClick={() => {
                  if (window.confirm(t("confirmClear"))) clearAll.mutate();
                }}
              >
                <Eraser aria-hidden="true" className="size-4" />
                {t("clearChat")}
              </Button>
            ) : null}
            {isModerator && !isCommunity ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={purgeTripChat.isPending}
                onClick={() => {
                  if (window.confirm(t("confirmDeleteTripChat"))) purgeTripChat.mutate();
                }}
              >
                <Trash2 aria-hidden="true" className="size-4" />
                {t("deleteTripChat")}
              </Button>
            ) : null}
          </div>
        </header>

        <div
          ref={listRef}
          className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain"
          style={{ background: wallpaper }}
          onClick={() => {
            setMenuFor(null);
          }}
        >
          <div
            className={cn(
              "pointer-events-none absolute inset-0",
              darkPaper ? "bg-black/25" : "bg-white/35",
            )}
          />
          <div className="relative flex min-h-full flex-col justify-end gap-1.5 px-3 py-3 sm:px-4">
            {(messages.data ?? []).map((item) => {
              const mine = item.senderId === account?.id;
              const text = item.deleted
                ? t("removed")
                : messageText(item.body, item.systemEvent, item.kind, t);
              const canAct =
                item.kind === "TEXT" &&
                !item.deleted &&
                (mine || isModerator);

              if (item.kind === "SYSTEM") {
                return (
                  <div key={item.id} className="flex justify-center py-1">
                    <span className="bg-surface/90 text-muted-foreground rounded-full px-3 py-1 text-center text-xs font-semibold shadow-sm">
                      {text}
                    </span>
                  </div>
                );
              }

              return (
                <div
                  key={item.id}
                  className={cn("flex items-end gap-2", mine ? "justify-end" : "justify-start")}
                  onPointerDown={() => {
                    startLongPress(item.id, canAct);
                  }}
                  onPointerUp={cancelLongPress}
                  onPointerLeave={cancelLongPress}
                  onPointerCancel={cancelLongPress}
                  onContextMenu={(event) => {
                    if (!canAct) return;
                    event.preventDefault();
                    setMenuFor(item.id);
                  }}
                >
                  <div className="max-w-[82%] sm:max-w-[75%]">
                    <p
                      className={cn(
                        "mb-0.5 px-1 text-[11px] font-bold",
                        darkPaper ? "text-white/80" : "text-muted-foreground",
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
                          ? "bg-surface-muted/90 text-muted-foreground italic"
                          : mine
                            ? "bg-primary text-primary-foreground rounded-ee-md"
                            : "bg-surface/95 text-foreground rounded-es-md",
                      )}
                    >
                      {text}
                    </div>
                    {menuFor === item.id && canAct ? (
                      <div
                        className={cn(
                          "bg-surface border-border mt-1 inline-flex overflow-hidden rounded-xl border shadow-lift",
                          mine ? "float-end" : "float-start",
                        )}
                        onClick={(event) => event.stopPropagation()}
                      >
                        <button
                          type="button"
                          className="text-danger hover:bg-danger/10 px-4 py-2 text-sm font-bold"
                          disabled={removeOne.isPending}
                          onClick={() => {
                            removeOne.mutate(item.id);
                          }}
                        >
                          {t("deleteOne")}
                        </button>
                        <button
                          type="button"
                          className="text-muted-foreground hover:bg-surface-muted px-3 py-2 text-sm font-bold"
                          onClick={() => {
                            setMenuFor(null);
                          }}
                        >
                          {t("cancelSelect")}
                        </button>
                      </div>
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
            <button
              type="button"
              className="border-border text-muted-foreground hover:bg-surface-muted inline-flex size-12 shrink-0 items-center justify-center rounded-full border"
              title={t("voiceSoon")}
              aria-label={t("voiceSoon")}
              onClick={() => {
                window.alert(t("voiceSoon"));
              }}
            >
              <Mic aria-hidden="true" className="size-5" />
            </button>
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
              disabled={trip.isReadOnly || send.isPending}
              autoComplete="off"
            />
            <Button
              type="submit"
              className="min-h-12 shrink-0 rounded-full px-5"
              disabled={trip.isReadOnly || send.isPending || !draft.trim()}
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

      {showWallpaper ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          onClick={() => {
            setShowWallpaper(false);
          }}
        >
          <div
            className="bg-surface w-full max-w-md rounded-2xl p-5 shadow-lift"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-extrabold">{t("wallpaperTitle")}</h2>
              <button
                type="button"
                className="hover:bg-surface-muted rounded-full p-1.5"
                aria-label={t("cancelSelect")}
                onClick={() => {
                  setShowWallpaper(false);
                }}
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>
            <p className="text-muted-foreground mt-2 text-sm">{t("wallpaperHint")}</p>
            <div className="mt-4 grid grid-cols-3 gap-3">
              {PRESET_WALLPAPERS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="border-border h-20 rounded-xl border-2"
                  style={{ background: item.style }}
                  aria-label={item.id}
                  onClick={() => {
                    saveWallpaper(item.style);
                  }}
                />
              ))}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => {
                  if (typeof reader.result === "string") {
                    saveWallpaper(`center / cover no-repeat url("${reader.result}")`);
                  }
                };
                reader.readAsDataURL(file);
              }}
            />
            <Button
              type="button"
              className="mt-4"
              block
              variant="outline"
              onClick={() => {
                fileRef.current?.click();
              }}
            >
              <ImagePlus aria-hidden="true" className="size-4" />
              {t("wallpaperCustom")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
