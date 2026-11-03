import test from 'node:test';
import assert from 'node:assert/strict';
import {IrpClient} from '../client.js';

globalThis.navigator??={};
Object.defineProperty(navigator,'onLine',{value:true,configurable:true});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
function client(journal={}){
 const device={state:{gunluk:journal}};
 const c=new IrpClient({get:async()=>device},{},{});
 c.person='K041';c.session={};c.emit=()=>{};c.refresh=async()=>{};c.uploadFiles=async()=>{};
 c.waitForPublication=async()=>({durum:'TAMAMLANDI'});
 c.mark=async(id,result,status)=>{journal[id].sonuc=result;journal[id].durum=status;};
 return c;
}
test('geciken eski okuma kabulden sonraki güncel durumu geri alamaz',async()=>{
 const c=client(),old=deferred(),current=deferred();let n=0;
 c.rpc=async()=>++n===1?old.promise:current.promise;
 const first=c.read('GOREV','G1',{},true),second=c.read('GOREV','G1',{},true);
 current.resolve({deger:{durum:'ACIK'}});await second;
 old.resolve({deger:{durum:'ATANDI'}});await first;
 assert.equal(c.cached('GOREV','G1').durum,'ACIK');
});
test('eşzamanlı gönderim çağrıları aynı kabul olayını bir kez gönderir',async()=>{
 const journal={A:{durum:'BEKLIYOR',olay:{olay_kimligi:'A',oldugu_an:'2026-10-30T10:00:00+03:00'}}};
 const c=client(journal),response=deferred();let sent=0;
 c.rpc=async()=>{sent++;return response.promise;};
 const first=c.flush(),second=c.flush();
 await new Promise(r=>setImmediate(r));assert.equal(sent,1);
 response.resolve({sonuc:'BASARILI'});await Promise.all([first,second]);
 assert.equal(journal.A.durum,'GONDERILDI');assert.equal(sent,1);
});
test('kabul sonucu boş bir önceki gönderim taramasıyla karışmaz',async()=>{
 const journal={},c=client(journal),oldScan=deferred(),originalGet=c.store.get;let calls=0,sent=0;
 c.store.get=async()=>++calls===1?oldScan.promise:originalGet();
 const first=c.flush();
 c.write=async()=>{journal.A={durum:'BEKLIYOR',olay:{olay_kimligi:'A',oldugu_an:'2026-10-30T10:00:00+03:00'}};return {yerel:true,olay:journal.A.olay};};
 c.rpc=async()=>{sent++;return {sonuc:'BASARILI'};};
 const result=c.confirmed('GOREV.KABUL_ETTIM');
 oldScan.resolve({state:{gunluk:{}}});await first;
 assert.equal((await result).sonuc,'BASARILI');assert.equal(sent,1);
});
test('sunucunun reddettiği kabul başarılı görünmez',async()=>{
 const journal={},c=client(journal);
 c.write=async()=>{journal.A={durum:'BEKLIYOR',olay:{olay_kimligi:'A',oldugu_an:'2026-10-30T10:00:00+03:00'}};return {yerel:true,olay:journal.A.olay};};
 c.rpc=async()=>({sonuc:'REDDEDILDI',kod:'YETKI'});
 await assert.rejects(c.confirmed('GOREV.KABUL_ETTIM'),/yetkiniz/);
 assert.equal(journal.A.durum,'HATA');
});

test('kabulden sonra okuma hatası yeni olay göndermez; aynı sonuç korunur',async t=>{
 const event={olay_kimligi:'A',oldugu_an:'2026-11-01T10:00:00+03:00'};
 const journal={A:{durum:'GONDERILEMEDI',olay:event}},c=client(journal);let sent=0,fail=true;
 c.rpc=async()=>{sent++;return {sonuc:'BASARILI'};};c.refresh=async()=>{if(fail)throw new Error('okuma kesildi');};
 t.after(()=>clearTimeout(c.retryTimer));
 const result=await c.retryManagement('A');
 assert.equal(result.sonuc,'BASARILI');assert.equal(result.ekran_bekliyor,true);assert.equal(journal.A.durum,'GONDERILDI');
 fail=false;await c.flush();assert.equal(sent,1);
});
test('kabulden sonra dosya hatası yalnız dosyayı yeniden dener',async t=>{
 const journal={A:{durum:'GONDERILEMEDI',olay:{olay_kimligi:'A',oldugu_an:'2026-11-01T10:00:00+03:00'}}};
 const c=client(journal);let sent=0,uploads=0;
 c.rpc=async()=>{sent++;return {sonuc:'BASARILI'};};c.uploadFiles=async id=>{assert.equal(id,'A');if(++uploads===1)throw new Error('depo kesildi');};
 t.after(()=>clearTimeout(c.retryTimer));
 const result=await c.retryManagement('A');assert.equal(result.dosya_bekliyor,true);assert.equal(result.sonuc,'BASARILI');
 await c.flush();assert.equal(sent,1);assert.equal(uploads,2);
});
test('onaylı tanıklığın okuması kesilince kabul sonucu hata olmaz',async t=>{
 const event={olay_kimligi:'A',oldugu_an:'2026-11-01T10:00:00+03:00'};
 const journal={A:{durum:'GONDERILDI',olay:event,sonuc:{sonuc:'BASARILI'}}},c=client(journal);
 c.write=async()=>({yerel:true,olay:event});c.refresh=async()=>{throw new Error('okuma kesildi');};
 t.after(()=>clearTimeout(c.retryTimer));
 const result=await c.confirmed('GOREV.TAMAMLADIM');assert.equal(result.sonuc,'BASARILI');assert.equal(result.ekran_bekliyor,true);
});
test('cevabı iki kez kaybolan yönetim işlemi yeni kimlikle oluşturulmaz',async()=>{
 const journal={},c=client(journal),sent=[];let prepared=0;
 c.resolveTargets=async x=>x;c.read=async()=>({deger:{son_hal:{},liste:[],isler:{}}});
 c.durable=async fn=>(await fn()).value;
 c.core=async()=>{prepared++;const event={olay_kimligi:'A',eylem_kodu:'PROJE.ACTIM',girdiler:{ad:'Deneme'},oldugu_an:'2026-11-01T10:00:00+03:00'};journal.A={durum:'BEKLIYOR',olay:event};return {value:event,state:{gunluk:journal}};};
 c.rpc=async(name,args)=>{sent.push(structuredClone(args.olay));if(sent.length<=2){const e=new Error('cevap kayboldu');e.code='NETWORK';throw e;}return {sonuc:'BASARILI'};};
 await assert.rejects(c.write('PROJE.ACTIM',{ad:'Deneme'}),/kabul edilmiş olabilir/);
 assert.equal(journal.A.durum,'GONDERILEMEDI');
 await assert.rejects(c.write('PROJE.ACTIM',{ad:'Deneme'}),/Önceki işlemin sonucu/);assert.equal(prepared,1);
 const result=await c.retryManagement('A');assert.equal(result.sonuc,'BASARILI');assert.equal(sent.length,3);
 assert.deepEqual(sent[0],sent[1]);assert.deepEqual(sent[1],sent[2]);assert.equal(prepared,1);
});

test('hesap bekleyen proje işlemi aynı olayla tekrar denenir; tek proje isteği hazırlanır',async()=>{
 const journal={},c=client(journal),sent=[];let prepared=0;
 c.resolveTargets=async x=>x;c.read=async()=>({deger:{son_hal:{},liste:[],isler:{}}});
 c.durable=async fn=>(await fn()).value;
 c.core=async()=>{prepared++;const event={olay_kimligi:'P',eylem_kodu:'PROJE.ACTIM',girdiler:{kod:'P1',ad:'Deneme'}};journal.P={durum:'BEKLIYOR',olay:event};return {value:event,state:{gunluk:journal}};};
 c.rpc=async(name,args)=>{sent.push(structuredClone(args.olay));return sent.length===1?{sonuc:'REDDEDILDI',kod:'HESAP_BEKLIYOR'}:{sonuc:'BASARILI'};};
 assert.equal((await c.write('PROJE.ACTIM',{kod:'P1',ad:'Deneme'})).sonuc,'BASARILI');
 assert.equal(prepared,1);assert.equal(sent.length,2);assert.deepEqual(sent[0],sent[1]);assert.equal(journal.P.durum,'GONDERILDI');
});

test('kesin sunucu reddinin alanı ve açıklaması kaybolmaz',async()=>{
 const journal={P:{durum:'GONDERILEMEDI',olay:{olay_kimligi:'P'}}},c=client(journal);
 const issues=[{path:'kod',message:'Bu proje kodu daha önce kullanılmış.'}];
 c.rpc=async()=>({sonuc:'REDDEDILDI',kod:'DURUM',mesaj:issues[0].message,alan_hatalari:issues});
 await assert.rejects(c.retryManagement('P'),e=>e.code==='DURUM'&&e.message===issues[0].message&&e.issues===issues);
 assert.equal(journal.P.durum,'RED');
});

test('kişi okuması başarılı olsa da proje listesi hatası yenileme başarısı sayılmaz',async()=>{
 const c=client();c.persistCache=async()=>{};c.read=async name=>{if(name==='PROJELER')throw new Error('liste kesildi');return {deger:[]};};
 await assert.rejects(IrpClient.prototype.base.call(c),/liste kesildi/);
});
test('sayfa okuma hatası kabul edilmiş işlemi reddetmez; ekran bekliyor sonucudur',async t=>{
 const c=client();c.base=async()=>{};c.pageReads=async()=>[{veri:'ETAPLAR',error:'kesildi'}];c.refresh=IrpClient.prototype.refresh;
 t.after(()=>clearTimeout(c.retryTimer));
 const result=await c.afterAccepted({sonuc:'BASARILI'},{olay_kimligi:'A'});
 assert.equal(result.sonuc,'BASARILI');assert.equal(result.ekran_bekliyor,true);
});
test('ağ tekrar kullanılabilirken eski bağlantı hatası aynı olayın sonucunu sorgulamayı engellemez',async()=>{
 const journal={A:{durum:'GONDERILEMEDI',olay:{olay_kimligi:'A'}}},c=client(journal);c.online=false;
 c.rpc=async()=>({sonuc:'BASARILI'});
 assert.equal((await c.retryManagement('A')).sonuc,'BASARILI');assert.equal(journal.A.durum,'GONDERILDI');
});
