import test from 'node:test';
import assert from 'node:assert/strict';
import {IrpClient,UserError,operationMessage,operationComplete,operationTone} from '../client.js';

globalThis.navigator??={};
Object.defineProperty(navigator,'onLine',{value:true,configurable:true});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
function client(){const c=new IrpClient({},{},{});c.emit=()=>{};c.uploadFiles=async()=>{};c.refresh=async()=>{};return c;}

test('kabul ve global güncel bilgisi kendi yayın makbuzunun yerini tutmaz',async()=>{
 const c=client(),publication=deferred(),trace=[];let n=0,finished=false;
 c.request=async(path,{body})=>{assert.equal(path,'/rest/v1/rpc/islem_sonucu');assert.equal(body.olay_kimligi,'A');return ++n===1?{durum:'BEKLIYOR'}:publication.promise;};
 c.refresh=async()=>trace.push('ekran');
 const pending=c.afterAccepted({sonuc:'BASARILI',hesap:'GUNCEL'},{olay_kimligi:'A'}).then(r=>{finished=true;return r;});
 await new Promise(r=>setTimeout(r,550));assert.equal(finished,false);assert.deepEqual(trace,[]);
 publication.resolve({durum:'TAMAMLANDI',yayin_ani:'2026-11-02T03:00:00Z'});
 const r=await pending;assert.equal(operationComplete(r),true);assert.deepEqual(trace,['ekran']);assert.equal(operationMessage(r),'İşlem tamamlandı.');
});
test('bekleme süresi biterse kabul edilmiş olay yeniden gönderilmez ve başarı yazılmaz',async()=>{
 const c=client();let calls=0;
 c.request=async path=>{assert.equal(path,'/rest/v1/rpc/islem_sonucu');calls++;return {durum:'BEKLIYOR'};};
 const r=await c.waitForPublication('A',{timeout:30,interval:5});assert.equal(r.durum,'BEKLIYOR');assert(calls>=1);
 assert.equal(operationComplete({islem_durumu:r.durum}),false);assert.match(operationMessage({islem_durumu:r.durum}),/Yeniden göndermenize gerek yok/);
});
test('yayın sorgusunun bağlantısı kesilirse alındı ile tamamlandı karışmaz',async()=>{
 const c=client();c.request=async()=>{throw new UserError('kesildi','NETWORK');};
 const r=await c.afterAccepted({sonuc:'BASARILI'},{olay_kimligi:'A'});assert.equal(r.sonuc,'BASARILI');assert.equal(r.islem_durumu,'DOGRULANAMADI');assert.equal(operationComplete(r),false);
});
test('başkasının veya bulunamayan olayın cevabı tamamlanmış sayılmaz',async()=>{
 const c=client();c.request=async()=>({durum:'BULUNAMADI'});
 assert.equal((await c.waitForPublication('A')).durum,'DOGRULANAMADI');
});
test('inceleme, geçersiz ve gelecek tarih ayrı sonuçlardır; olumlu tamamlandı mesajı yok',async()=>{
 for(const durum of ['INCELEME_GEREKIYOR','GECERSIZ','ZAMANI_BEKLIYOR']){
  const c=client();c.request=async()=>({durum});const r=await c.afterAccepted({sonuc:'BASARILI'},{olay_kimligi:'A'});
  assert.equal(r.islem_durumu,durum);assert.equal(operationComplete(r),false);assert.doesNotMatch(operationMessage(r),/tamamlandı/);
 }
});
test('kişi değişiminden sonra eski işlemin sonucu yeni kişiye gösterilmez',async()=>{
 const c=client(),wait=deferred();c.request=async()=>wait.promise;
 const r=c.waitForPublication('A');c.generation++;wait.resolve({durum:'TAMAMLANDI'});
 await assert.rejects(r,e=>e.code==='STALE_SESSION');
});
test('eşzamanlı sonuç sorguları kendi olaylarını izler',async()=>{
 const c=client(),a=deferred(),b=deferred();c.request=async(_,{body})=>body.olay_kimligi==='A'?a.promise:b.promise;
 const first=c.waitForPublication('A'),second=c.waitForPublication('B');b.resolve({durum:'TAMAMLANDI'});assert.equal((await second).durum,'TAMAMLANDI');
 a.resolve({durum:'INCELEME_GEREKIYOR'});assert.equal((await first).durum,'INCELEME_GEREKIYOR');
});
test('dosya ve ekran eksikleri yayımlanmış sonuçtan sonra da doğru anlatılır',()=>{
 assert.match(operationMessage({islem_durumu:'TAMAMLANDI',dosya_bekliyor:true}),/Dosya aktarımı/);
 assert.match(operationMessage({islem_durumu:'TAMAMLANDI',ekran_bekliyor:true}),/Görünümün yenilenmesi/);
 assert.match(operationMessage({yerel:true}),/bilgisayarda saklandı/);
 assert.equal(operationComplete({islem_durumu:'TAMAMLANDI',ekran_bekliyor:true}),false);
 assert.equal(operationTone({islem_durumu:'BEKLIYOR'}),'info');
 assert.equal(operationTone({islem_durumu:'INCELEME_GEREKIYOR'}),true);
 assert.equal(operationTone({islem_durumu:'TAMAMLANDI'}),false);
});
