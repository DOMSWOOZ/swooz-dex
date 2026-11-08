const CACHE_NAME = 'swooz-dex-v65';
const ASSETS = [
  './',
  'index.html',
  'strategy_explainer_visual.html',
  'manifest.json',
  'logo.png',
  'icon-192.png',
  'icon-512.png',
  'icon.svg',
  'nft-media/if_1506.gif',
  'nft-media/if_1286.gif',
  'nft-media/if_140.gif',
  'nft-media/if_42.gif',
  'nft-media/beast_2313_full.png',
  'nft-media/beast_2313_pfp.png',
  'nft-media/clonex_9143.png',
  'nft-media/minisupers_6915.png',
  'nft-media/the_walk_1.gif',
  'nft-media/supers_84.png',
  'nft-media/supers_144.png',
  'nft-media/enso_146.png',
  'nft-media/enso_190.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (
    event.request.mode === 'navigate' ||
    event.request.url.endsWith('.html') ||
    event.request.url.endsWith('/') ||
    event.request.url.includes('snapshot.json') ||
    event.request.url.includes('/api/') ||
    event.request.url.includes('nft-media/')
  ) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' })
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
