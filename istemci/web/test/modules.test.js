import test from 'node:test';
import assert from 'node:assert/strict';
import {moduleRequest} from '../modules.js';

const client=()=>({generation:1,session:{access_token:'user-one',expires_at:Date.now()/1000+3600},requests:new Set(),emit(){},writing:false});
const pause=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const response=(value={},status=200)=>({ok:status>=200&&status<300,status,json:async()=>value});
const transport=(t,fn)=>{const old=globalThis.fetch;globalThis.fetch=fn;t.after(()=>globalThis.fetch=old);};

test('modül cevabı kişi değiştikten sonra yeni ekrana dönmez',async t=>{
 const c=client(),pending=pause();transport(t,()=>pending.promise);
 const call=moduleRequest(c,'/irp/moduller');c.generation++;
 pending.resolve(response({private:'eski kişinin verisi'}));
 await assert.rejects(call,e=>e.code==='STALE_SESSION');assert.equal(c.requests.size,0);
});

test('modül yazarken ortak kişi değiştirme kilidi çalışır ve ikinci yazma engellenir',async t=>{
 const c=client(),pending=pause();transport(t,()=>pending.promise);
 const call=moduleRequest(c,'/irp/moduller/M11B/api/plan',{method:'POST',body:{}});
 assert.equal(c.writing,true);
 await assert.rejects(moduleRequest(c,'/another',{method:'POST',body:{}}),/Devam eden işlem/);
 pending.resolve(response());await call;
 assert.equal(c.writing,false);assert.equal(c.requests.size,0);
});

test('modül ortak oturumu bir kez yeniler ve güncel kullanıcı anahtarını kullanır',async t=>{
 const c=client(),tokens=[];let refresh=0;
 c.refreshSession=async()=>{refresh++;c.session.access_token='renewed-user';};
 transport(t,async(_path,opts)=>{
  tokens.push(opts.headers.Authorization);
  return response({},tokens.length===1?401:200);
 });
 await moduleRequest(c,'/irp/moduller');
 assert.equal(refresh,1);assert.deepEqual(tokens,['Bearer user-one','Bearer renewed-user']);
});

test('kapanmış modül yeni ağ isteği başlatmaz; reddedilen yazma kilidi bırakır',async t=>{
 const c=client(),abort=new AbortController();abort.abort();
 transport(t,async(_path,opts)=>{
  assert.equal(opts.signal.aborted,true);throw new DOMException('Aborted','AbortError');
 });
 await assert.rejects(moduleRequest(c,'/irp/moduller',{method:'POST',body:{},signal:abort.signal}),/İşlem kesildi/);
 assert.equal(c.writing,false);assert.equal(c.requests.size,0);
});
