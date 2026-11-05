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

export function isIosDevice(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const iOS = /iPad|iPhone|iPod/.test(ua);
  const iPadOs = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
  return iOS || iPadOs;
}

export function isStandaloneApp(): boolean {
  if (typeof window === "undefined") return false;
  const media = window.matchMedia("(display-mode: standalone)").matches;
  const legacy = "standalone" in navigator && Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
  return media || legacy;
}

async function ensureServiceWorker(): Promise<ServiceWorkerRegistration> {
  const existing = await navigator.serviceWorker.getRegistration();
  const registration = existing ?? (await navigator.serviceWorker.register("/sw.js"));
  try {
    await registration.update();
  } catch {
    /* ignore update failures */
  }
  return navigator.serviceWorker.ready;
}

/** Register this browser for phone alerts. No-op until the user has allowed notifications. */
export async function enablePhoneAlerts(): Promise<"on" | "denied" | "unsupported" | "need_install"> {
  if (!("serviceWorker" in navigator) || !("Notification" in window)) {
    return "unsupported";
  }
  // iOS only exposes PushManager inside an installed Home Screen app (16.4+).
  if (!("PushManager" in window)) {
    return isIosDevice() && !isStandaloneApp() ? "need_install" : "unsupported";
  }
  if (isIosDevice() && !isStandaloneApp()) {
    return "need_install";
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
  const registration = await ensureServiceWorker();
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
