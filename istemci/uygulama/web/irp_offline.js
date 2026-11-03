'use strict';

// Yalnız bu uygulamanın sabit kaynakları. Oturum ve günlük IndexedDB'dedir.
const ONBELLEK = 'irp-kabuk-v4';
const KAYNAKLAR = [
  '', 'index.html', 'main.dart.js', 'flutter.js', 'flutter_bootstrap.js',
  'manifest.json', 'favicon.png', 'icons/Icon-192.png', 'icons/Icon-512.png',
  'canvaskit/canvaskit.js', 'canvaskit/canvaskit.wasm',
  'assets/AssetManifest.bin', 'assets/AssetManifest.bin.json', 'assets/FontManifest.json',
  'assets/fonts/MaterialIcons-Regular.otf',
  'assets/packages/cupertino_icons/assets/CupertinoIcons.ttf',
  'assets/assets/fontlar/roboto-regular.ttf', 'assets/assets/fontlar/roboto-bold.ttf',
  'assets/test/fikstur/telefon.json', 'assets/test/fikstur/web.json', 'assets/test/fikstur/yonetim.json', 'assets/assets/eylem_semalari.json',
  'assets/assets/gosterim.json',
  'assets/assets/cizimler/harita.json', 'assets/assets/cizimler/ornek_1.png',
  'assets/assets/cizimler/ornek_2.png', 'assets/assets/cizimler/ornek_3.png',
  'assets/shaders/ink_sparkle.frag', 'assets/shaders/stretch_effect.frag'
];
const kapsam = new URL(self.registration.scope);
// ayar.json bu listeye girmez: anahtar saklanmaz, değişiklik her açılışta okunur.

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(ONBELLEK);
    await cache.addAll(KAYNAKLAR.map(yol => new Request(new URL(yol, kapsam), {cache: 'reload'})));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  const istek = event.request;
  const url = new URL(istek.url);
  if (istek.method !== 'GET' || url.origin !== kapsam.origin || !url.pathname.startsWith(kapsam.pathname)) return;
  const yol = url.pathname.slice(kapsam.pathname.length);
  if (!KAYNAKLAR.includes(yol)) return;
  event.respondWith((async () => {
    const cache = await caches.open(ONBELLEK);
    try {
      const cevap = await fetch(istek);
      if (cevap.ok) {
        await cache.put(istek, cevap.clone()).catch(() => {});
        return cevap;
      }
      const sakli = await cache.match(istek, {ignoreSearch: true});
      return sakli || cevap;
    } catch (hata) {
      const sakli = await cache.match(istek, {ignoreSearch: true});
      if (sakli) return sakli;
      throw hata;
    }
  })());
});
