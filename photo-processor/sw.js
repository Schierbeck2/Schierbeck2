// Service worker for Photo Processor PWA
const CACHE_NAME = 'photo-processor-v2';

// Core files the app needs offline. Icons are cached best-effort separately
// because cache.addAll() rejects the whole install if any single request
// fails — a missing icon must not block the share target from working.
const CORE_ASSETS = ['/', '/index.html', '/manifest.json'];
const OPTIONAL_ASSETS = ['/images/icon-192.png', '/images/icon-512.png'];

// Install event - cache resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then(cache =>
        Promise.all([
          cache.addAll(CORE_ASSETS),
          ...OPTIONAL_ASSETS.map(url => cache.add(url).catch(() => {}))
        ])
      )
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches and take control immediately
self.addEventListener('activate', event => {
  event.waitUntil(
    caches
      .keys()
      .then(cacheNames =>
        Promise.all(
          cacheNames
            .filter(cacheName => cacheName !== CACHE_NAME)
            .map(cacheName => caches.delete(cacheName))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Share target: the OS POSTs the shared content here; bounce it to the
  // app page as query parameters.
  if (event.request.method === 'POST' && url.pathname === '/share-target') {
    event.respondWith(handleShare(event.request));
    return;
  }

  // Only handle same-origin GETs; the n8n webhook and any other
  // cross-origin requests go straight to the network.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Network-first for page navigations so deploys show up without a
  // CACHE_NAME bump; fall back to cache when offline.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return response;
        })
        .catch(() =>
          caches
            .match(event.request)
            .then(cached => cached || caches.match('/index.html'))
        )
    );
    return;
  }

  // Cache-first for static assets.
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});

async function handleShare(request) {
  const formData = await request.formData();
  // Field names come from share_target.params in manifest.json.
  const link = formData.get('link') || '';
  const text = formData.get('text') || '';

  let redirectUrl = '/index.html';
  if (link.includes('photos.google.com')) {
    redirectUrl += `?link=${encodeURIComponent(link)}`;
  } else if (text.includes('photos.google.com')) {
    redirectUrl += `?text=${encodeURIComponent(text)}`;
  }

  return Response.redirect(redirectUrl, 303);
}
