import test from 'node:test';
import assert from 'node:assert/strict';
import {IrpClient} from '../client.js';
globalThis.navigator??={};
Object.defineProperty(navigator,'onLine',{value:true,configurable:true});
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=()=>new Promise(r=>setImmediate(r));
function make(){const c=new IrpClient({}, {}, {});c.person='K001';c.emit=()=>{};return c;}

test('çok sayıda okuma en fazla iki istekle çalışır; hata kapasiteyi kilitlemez',async()=>{
 const c=make(),calls=[];
 c.rpc=async(name,{hedef})=>{const d=deferred();calls.push({hedef,...d});return d.promise;};
 const pending=[0,1,2,3,4].map(n=>c.read('PROJE_DURUM',String(n),{},true));
 const all=Promise.allSettled(pending);await tick();assert.equal(calls.length,2);
 calls[0].reject(new Error('zaman aşımı'));await tick();assert.equal(calls.length,3);
 calls[1].resolve({deger:1});calls[2].resolve({deger:2});await tick();assert.equal(calls.length,5);
 calls[3].resolve({deger:3});calls[4].resolve({deger:4});
 const results=await all;assert.equal(results.filter(r=>r.status==='fulfilled').length,4);
 assert.equal(c.cached('PROJE_DURUM','4'),4);
});

test('profil değişince eski kişinin kuyrukta kalan okuması ağa çıkmaz',async()=>{
 const c=make(),calls=[];c.rpc=async(name,{hedef})=>{const d=deferred();calls.push({hedef,...d});return d.promise;};
 const all=Promise.allSettled([0,1,2].map(n=>c.read('PROJE_DURUM',String(n),{},true)));
 await tick();c.generation++;c.person='K004';calls[0].resolve({deger:0});calls[1].resolve({deger:1});
 await all;assert.equal(calls.length,2);assert.equal(c.cache.size,0);
});

test('yenileme yağmuru tek sonraki turda birleşir; kabulden sonra taze okuma yapılır',async()=>{
 const c=make(),passes=[];c.base=async()=>{const d=deferred();passes.push(d);return d.promise;};c.pageReads=async()=>[];
 const first=c.refresh();await tick();assert.equal(passes.length,1);
 // İlk okuma başladıktan sonra bir iş kabul edilmiş olsun: takip eden çağrılar
 // mutlaka yeni bir tur bekler, ilk eski okumayla tamamlanmış sayılmaz.
 let done=false;const next=Promise.all(Array.from({length:12},()=>c.refresh())).then(()=>done=true);
 assert.equal(passes.length,1);assert.equal(done,false);
 passes[0].resolve();await first;await tick();assert.equal(passes.length,2);assert.equal(done,false);
 passes[1].resolve();await next;assert.equal(done,true);assert.equal(passes.length,2);
});

test('başarısız yenileme sonraki yenilemenin çalışmasını engellemez',async()=>{
 const c=make(),d=deferred();let n=0;c.base=async()=>{if(++n===1)return d.promise;};c.pageReads=async()=>[];
 const first=assert.rejects(c.refresh(),/kesinti/);const next=c.refresh();d.reject(new Error('kesinti'));
 await first;await next;assert.equal(n,2);
});

test('okuma kuyruğunda bekleyen eski profilin yenilemesi yeni kişiyle çalışmaz',async()=>{
 const c=make(),d=deferred();let n=0;c.base=async()=>{n++;await d.promise;};c.pageReads=async()=>[];
 const first=c.refresh(),old=c.refresh();c.generation++;c.person='K004';d.resolve();await Promise.all([first,old]);assert.equal(n,1);
});

test('sunucu okuma zaman aşımı anlaşılır hata olur; yazma mesajı bu dala girmez',async t=>{
 const c=make();c.config={supabase_url:'https://example.invalid',supabase_anon:'test'};c.session={expires_at:Date.now()/1000+3600,access_token:'test'};
 const before=globalThis.fetch;t.after(()=>globalThis.fetch=before);
 globalThis.fetch=async()=>({status:500,ok:false,text:async()=>JSON.stringify({code:'57014',message:'canceling statement due to statement timeout'})});
 await assert.rejects(c.request('/rest/v1/rpc/oku',{body:{veri:'PROJE_DURUM'}}),e=>e.code==='READ_TIMEOUT'&&e.message.includes('Bilgiler zamanında'));
 await assert.rejects(c.request('/rest/v1/rpc/olay_ekle',{body:{}}),e=>e.code==='500');
});
