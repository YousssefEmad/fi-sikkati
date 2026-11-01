import { apiJson } from "@/lib/api/json";

export interface NotificationItem {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  readAt: string | null;
  createdAt: string;
}

export async function listNotifications(): Promise<NotificationItem[]> {
  const body = await apiJson<{ items: NotificationItem[] }>("/api/v1/me/notifications");
  return body.items;
}

export async function unreadNotificationCount(): Promise<number> {
  const body = await apiJson<{ unread: number }>("/api/v1/me/notifications/unread-count");
  return body.unread;
}

export async function markNotificationsRead(ids?: string[]): Promise<void> {
  await apiJson("/api/v1/me/notifications/read", {
    method: "POST",
    body: JSON.stringify(ids ? { ids } : {}),
  });
}
