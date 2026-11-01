import type { NotificationItem } from "@/features/notifications/api";

function text(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** Where a notification should take the reader so they can act on it. */
export function notificationHref(item: NotificationItem): string {
  const tripId = text(item.payload, "tripId");
  const requestId = text(item.payload, "requestId");
  const conversationId = text(item.payload, "conversationId");
  const userId = text(item.payload, "userId");
  const kind = text(item.payload, "kind")?.toLowerCase() ?? "";

  switch (item.type) {
    case "REVIEW_REQUESTED":
      if (kind === "report") return "/admin/reports";
      if (userId && (kind === "identity" || kind === "driver" || kind === "vehicle")) {
        const vehicleId = text(item.payload, "vehicleId");
        const vehicle = vehicleId ? `&vehicle=${vehicleId}` : "";
        return `/admin/verifications?user=${userId}&kind=${kind}${vehicle}`;
      }
      return "/admin/verifications";
    case "JOIN_REQUEST_RECEIVED":
      if (!tripId) return "/me/trips";
      return requestId ? `/trips/${tripId}?request=${requestId}` : `/trips/${tripId}`;
    case "JOIN_REQUEST_ACCEPTED":
    case "JOIN_REQUEST_CANCELLED":
    case "TRIP_UPDATED":
    case "TRIP_COMPLETED":
    case "TRIP_REMINDER":
    case "TRIP_STARTING_SOON":
    case "RATING_RECEIVED":
      return tripId ? `/trips/${tripId}` : "/me/trips";
    case "JOIN_REQUEST_REJECTED":
    case "TRIP_CANCELLED":
      return "/search";
    case "NEW_MESSAGE":
    case "TRIP_STARTED":
      return conversationId ? `/messages/${conversationId}` : "/messages";
    case "VERIFICATION_STATUS_CHANGED":
      return "/me/verification";
    case "REPORT_UPDATED":
    case "ACCOUNT_MODERATED":
      return "/me/safety";
    default:
      return "/me/notifications";
  }
}

/** Message key under Notifications.items. Review requests vary by what is waiting. */
export function notificationCopyKey(item: NotificationItem): string {
  if (item.type !== "REVIEW_REQUESTED") return item.type;
  const kind = text(item.payload, "kind")?.toUpperCase();
  if (kind === "DRIVER" || kind === "VEHICLE") return "REVIEW_DRIVER";
  if (kind === "REPORT") return "REVIEW_REPORT";
  return "REVIEW_IDENTITY";
}
