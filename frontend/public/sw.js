// Fitness Coach PWA Service Worker
const CACHE_NAME = 'fitness-coach-v1';
const STATIC_CACHE = 'fitness-static-v1';
const API_CACHE = 'fitness-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/workout',
  '/chat',
  '/plans',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  const currentCaches = [CACHE_NAME, STATIC_CACHE, API_CACHE];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !currentCaches.includes(name))
          .map((name) => {
            console.log('Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first for API, cache first for static
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip non-http protocols
  if (!url.protocol.startsWith('http')) return;

  // IMPORTANT: Skip chat endpoints completely (SSE streaming)
  if (url.pathname.includes('/chat')) return;

  // API requests - network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    // Always cache workout plans for offline access
    if (url.pathname.includes('/api/fitness/plans/')) {
      event.respondWith(
        caches.open(API_CACHE).then(cache =>
          fetch(request).then(response => {
            if (response.ok) {
              cache.put(request, response.clone());
            }
            return response;
          }).catch(() => cache.match(request))
        )
      );
      return;
    }

    // Other API requests - network first, cache as fallback
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(API_CACHE).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets - cache first, network fallback (stale-while-revalidate)
  event.respondWith(
    caches.match(request).then(cached => {
      const fetchPromise = fetch(request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
        }
        return response;
      });

      return cached || fetchPromise;
    })
  );
});
