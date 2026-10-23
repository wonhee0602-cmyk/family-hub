self.addEventListener('install', (e) => {
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
    // 네트워크 우선 통신 (캐시 지연 방지)
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
