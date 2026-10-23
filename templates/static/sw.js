\const CACHE_NAME = 'family-hub-v3-' + Date.now();

self.addEventListener('install', (e) => {
    // 새 버전 설치 시 대기 없이 즉시 가동
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
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
    // 네트워크 우선 정책: 최신 웹/서버 파일이 있으면 무조건 그것부터 로드
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
