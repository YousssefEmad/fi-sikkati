import { apiJson } from "@/lib/api/json";

export interface ChatMessage {
  id: string;
  conversationId: string;
  senderId: string | null;
  senderDisplayName: string | null;
  kind: string;
  body: string;
  systemEvent: string | null;
  createdAt: string;
  deleted: boolean;
}

export interface Conversation {
  id: string;
  tripId: string | null;
  originLabel: string | null;
  destinationLabel: string | null;
  departureAt: string | null;
  isReadOnly: boolean;
  unreadCount: number;
  lastMessage: ChatMessage | null;
  memberIds: string[];
  memberNames: string[];
}

export async function listConversations(): Promise<Conversation[]> {
  const body = await apiJson<{ items: Conversation[] }>("/api/v1/me/conversations");
  return body.items;
}

export async function getConversation(id: string): Promise<Conversation> {
  return apiJson<Conversation>(`/api/v1/conversations/${id}`);
}

export async function listMessages(id: string): Promise<ChatMessage[]> {
  const body = await apiJson<{ items: ChatMessage[] }>(`/api/v1/conversations/${id}/messages`);
  // API returns newest-first; WhatsApp-style UI needs oldest → newest.
  return [...body.items].reverse();
}

export async function sendMessage(id: string, body: string): Promise<ChatMessage> {
  return apiJson<ChatMessage>(`/api/v1/conversations/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ body, clientMessageId: crypto.randomUUID() }),
  });
}

export async function markConversationRead(id: string, messageId?: string): Promise<void> {
  await apiJson(`/api/v1/conversations/${id}/read`, {
    method: "POST",
    body: JSON.stringify({ messageId: messageId ?? null }),
  });
}

export async function deleteMessage(conversationId: string, messageId: string): Promise<ChatMessage> {
  return apiJson<ChatMessage>(`/api/v1/conversations/${conversationId}/messages/${messageId}`, {
    method: "DELETE",
  });
}

export async function deleteMessages(
  conversationId: string,
  messageIds: string[],
): Promise<{ deletedCount: number }> {
  return apiJson(`/api/v1/conversations/${conversationId}/messages/delete`, {
    method: "POST",
    body: JSON.stringify({ messageIds }),
  });
}

export async function clearConversation(
  conversationId: string,
): Promise<{ deletedCount: number }> {
  return apiJson(`/api/v1/conversations/${conversationId}/clear`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
