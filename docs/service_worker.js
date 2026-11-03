// Yalnız uygulama dosyaları. Oturum, ayar, hesap ve RPC yanıtları bu depoya girmez.
const CACHE='irp-is-95f7551e73a0b271';
const STATIC=["actions.js", "app.js", "assets/core.js", "assets/eylem_semalari.json", "assets/gosterim.json", "assignment.js", "cekirdek_onkosullari.json", "client.js", "daily_summary.js", "erisim.html", "erisim.js", "erisim_sayfasi.js", "erp.css", "erp.js", "flutter_service_worker.js", "forms.js", "icons.js", "index.html", "management.js", "modul_ui.js", "modules.js", "navigation.js", "notifications.js", "office.js", "olaylar.css", "olaylar.html", "olaylar.js", "pages.js", "plan_review.js", "prerequisites.js", "presentation.js", "project_model.js", "projects.js", "read_schedule.js", "styles.css", "temporal.js", "ui.js", "workflow.js", "workshop.js", "workshop_model.js"];
const urls=new Set(STATIC.map(path=>new URL(path,self.registration.scope).href));
urls.add(self.registration.scope);
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);await cache.addAll(STATIC);await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 for(const name of await caches.keys())if((name.startsWith('irp-is-')&&name!==CACHE)||name.startsWith('flutter-'))await caches.delete(name);
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET')return;
 const url=new URL(event.request.url);url.search='';url.hash='';
 if(!urls.has(url.href))return;
 event.respondWith((async()=>{
  const key=url.href.endsWith('/')?new URL('index.html',url).href:url.href;
  try{const response=await fetch(event.request);if(response.ok){const cache=await caches.open(CACHE);await cache.put(key,response.clone());}return response;}
  catch{const cached=await caches.match(key);if(cached)return cached;throw new Error('Uygulama dosyası çevrimdışı hazır değil.');}
 })());
});
