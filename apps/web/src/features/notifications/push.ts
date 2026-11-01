import { apiJson } from "@/lib/api/json";

function keyBytes(value: string): Uint8Array<ArrayBuffer> {
  const padded = value.padEnd(value.length + ((4 - (value.length % 4)) % 4), "=");
  const binary = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

/** Register this browser for phone alerts. No-op until the user has allowed notifications. */
export async function enablePhoneAlerts(): Promise<"on" | "denied" | "unsupported"> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    return "unsupported";
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";
  await subscribeCurrentDevice();
  return "on";
}

/** Keep an already-granted device registered. Does not prompt. */
export async function refreshPhoneAlerts(): Promise<boolean> {
  if (!("Notification" in window) || Notification.permission !== "granted") return false;
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
  await subscribeCurrentDevice();
  return true;
}

async function subscribeCurrentDevice(): Promise<void> {
  const config = await apiJson<{ vapidPublicKey: string | null }>("/api/v1/platform/config");
  if (!config.vapidPublicKey) return;
  const registration = await navigator.serviceWorker.ready;
  const existing = await registration.pushManager.getSubscription();
  const subscription =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes(config.vapidPublicKey),
    }));
  const json = subscription.toJSON();
  if (!subscription.endpoint || !json.keys?.p256dh || !json.keys.auth) return;
  await apiJson("/api/v1/me/push-subscriptions", {
    method: "PUT",
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    }),
  });
}
