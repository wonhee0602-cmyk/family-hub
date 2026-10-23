const CACHE_NAME = 'family-hub-cache-v2';

self.addEventListener('install', (e) => {
    // 새 버전이 배포되면 즉시 이전 버전을 교체
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    // 이전 버전 캐시 즉시 청소 후 제어권 획득
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((k) => {
                    if (k !== CACHE_NAME) {
                        return caches.delete(k);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    // 서버 최신 데이터 우선 로드
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
