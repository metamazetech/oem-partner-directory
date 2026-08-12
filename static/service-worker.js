const CACHE_NAME = 'oem-portal-cache-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/dashboard',
  '/rfps',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png'
];

// Install Event
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Activate Event
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event - Network First with Cache Fallback for dynamic content, Cache First for static assets
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // We only intercept GET requests
  if (req.method !== 'GET') return;

  // For static assets (CSS, JS, images, fonts), use Cache-First strategy
  if (url.origin === self.location.origin && (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json')) {
    event.respondWith(
      caches.match(req).then(cachedResponse => {
        if (cachedResponse) return cachedResponse;
        return fetch(req).then(networkResponse => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(req, networkResponse.clone());
            return networkResponse;
          });
        });
      })
    );
  } else {
    // For navigation pages, use Network-First with Cache Fallback
    event.respondWith(
      fetch(req).catch(() => {
        return caches.match(req).then(cachedResponse => {
          if (cachedResponse) return cachedResponse;
          return new Response(
            `<!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Offline - NextNode Systems Portal</title>
              <style>
                body { background: #0b0f19; color: #f8fafc; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }
                h1 { color: #6366f1; margin-bottom: 0.5rem; }
                p { color: #94a3b8; margin: 0; }
                .card { background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); padding: 2rem; border-radius: 12px; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.3); }
              </style>
            </head>
            <body>
              <div class="card">
                <h1>📶 You are Offline</h1>
                <p>Please check your connection. You are currently viewing the offline portal fallback.</p>
              </div>
            </body>
            </html>`,
            { headers: { 'Content-Type': 'text/html' } }
          );
        });
      })
    );
  }
});
