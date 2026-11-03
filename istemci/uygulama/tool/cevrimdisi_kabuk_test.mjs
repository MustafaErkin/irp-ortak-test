// Tarayıcı denetimi değildir. Worker işleyicileri Node VM ve bellek deposunda sınanır.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const dinleyiciler = {}, sakli = new Map();
let baglanti = true;
const ag = async request => {
  if (!baglanti) throw new Error('Bağlantı yok');
  const yol = new URL(request.url).pathname.slice('/gosteri/'.length) || 'index.html';
  return new Response(await fs.readFile(new URL(`../build/web/${yol}`, import.meta.url)));
};
const cache = {
  async addAll(istekler) { for (const r of istekler) await this.put(r, await ag(r)); },
  async put(r, cevap) { sakli.set(new URL(r.url).pathname, cevap.clone()); },
  async match(r) { return sakli.get(new URL(r.url).pathname)?.clone(); }
};
const ortam = vm.createContext({URL, Request, Response, fetch: ag,
  caches: {open: async () => cache},
  self: {registration: {scope: 'https://irp.test/gosteri/'},
    addEventListener: (ad, islev) => { dinleyiciler[ad] = islev; },
    skipWaiting: async () => {}, clients: {claim: async () => {}}}
});
vm.runInContext(await fs.readFile(new URL('../web/irp_offline.js', import.meta.url), 'utf8'), ortam);
let kurulum;
dinleyiciler.install({waitUntil: p => { kurulum = p; }});
await kurulum;
assert.ok(sakli.size >= 24, 'Uygulama, font, çizim ve CanvasKit kaynakları saklanmalı');
baglanti = false;
async function cevap(yol, method = 'GET') {
  let p;
  dinleyiciler.fetch({request: new Request(new URL(yol, 'https://irp.test/gosteri/'), {method}), respondWith: x => { p = x; }});
  return p;
}
assert.ok((await (await cevap('index.html')).text()).includes('Sibernetik IRP'));
assert.ok((await (await cevap('main.dart.js')).arrayBuffer()).byteLength > 1000);
assert.ok((await (await cevap('?kip=gosterim')).text()).includes('Sibernetik IRP'));
assert.ok((await (await cevap('assets/assets/gosterim.json')).json()).gosterim);
assert.equal(await cevap('ayar.json'), undefined);
assert.equal(await cevap('auth/v1/token', 'POST'), undefined);
assert.equal(await cevap('https://baska.test/'), undefined);
console.log('7/7: kabuk/JS, gösterim adresi/verisi, ayar dosyası, POST ve başka alan adı ayrımı.');
