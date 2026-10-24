// Minimal service worker: makes the app installable and caches static assets.
const CACHE = 'chemtutor-v1.3';
const ASSETS = ['/static/tailwind.css', '/static/chart.umd.min.js', '/static/icon.svg', '/static/icon-192.png', '/static/icon-512.png'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))));
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method === 'GET' && url.pathname.startsWith('/static/'))
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
