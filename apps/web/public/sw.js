/* Fi Sikkati service worker: cache the installable shell only. No offline API claims. */
const CACHE = "fi-sikkati-shell-v2";
const SHELL = ["/icons/icon-192.png", "/icons/icon-512.png", "/brand/logo.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = typeof data.title === "string" ? data.title : "في سكتي";
  const body = typeof data.body === "string" ? data.body : "";
  const url = typeof data.url === "string" ? data.url : "/";
  const tag = typeof data.tag === "string" ? data.tag : "fi-sikkati";
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url },
      tag,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(self.clients.openWindow(url));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(request).catch(() => caches.match(request).then((cached) => cached || caches.match("/"))),
  );
});
