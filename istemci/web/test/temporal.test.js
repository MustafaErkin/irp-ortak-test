import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseTemporal,displayTemporal,validTemporal,leavePayload,overtimeTargets} from '../temporal.js';
import {operationSchema,validationIssues,formHTML} from '../forms.js';
import {ensureDocumentType} from '../prerequisites.js';
const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));

test('kısmi yıl korunur; artık yıl ve gerçek takvim günü denetlenir',()=>{
 for(const text of ['02.11.2','02.11.20','02.11.202','31.02.2026','29.02.2026']){
  assert.equal(parseTemporal(text,'date'),text);assert.equal(validTemporal(parseTemporal(text,'date'),'date'),false);
 }
 assert.equal(parseTemporal('29.02.2028','date'),'2028-02-29');
 assert.equal(parseTemporal('02.11.2026','date'),'2026-11-02');
 assert.equal(displayTemporal('2026-11-02','date'),'02.11.2026');
});
test('saat 24 saat biçimindedir; AM/PM, 24:00 ve bozuk dakika kabul edilmez',()=>{
 for(const value of ['09:30','00:00','23:59'])assert.ok(validTemporal(value,'time'));
 for(const value of ['9:30 PM','24:00','09:60','9:3'])assert.equal(validTemporal(value,'time'),false);
 const iso=parseTemporal('02.11.2026 21:30','datetime-local');assert.equal(iso,'2026-11-02T21:30:00+03:00');assert.ok(validTemporal(iso,'datetime-local'));
});
test('tarih/saat hataları iç içe iş satırındaki alan yoluna bağlanır',()=>{
 const s=operationSchema('GOREV.ATADIM',schemas);
 const issues=validationIssues({gorevler:[{teslim_tarihi:'31.02.2026',teslim_saati:'24:30'}]},s);
 assert.ok(issues.some(i=>i.path==='gorevler.0.teslim_tarihi'));assert.ok(issues.some(i=>i.path==='gorevler.0.teslim_saati'));
});
test('izin yalnız oturum kişisine gider; tam gün son günü de içerir',()=>{
 const value={kisi:'K001',tur:'YILLIK',baslangic:'2026-12-31',bitis:'2026-12-31',gerekce:'Yıl sonu'};
 const out=leavePayload(value,'K041');assert.equal(out.kisi,'K041');assert.equal(out.baslangic,'2026-12-31T00:00:00+03:00');assert.equal(out.bitis,'2027-01-01T00:00:00+03:00');
 const hourly=leavePayload({...value,tur:'SAATLIK',baslangic_saati:'09:30',bitis_saati:'10:30'},'K041');
 assert.equal(hourly.bitis,'2026-12-31T10:30:00+03:00');assert.equal(hourly.baslangic_saati,undefined);
});
test('izin üç tür gösterir; çalışan seçimi yok, saatlikte iki saat zorunludur',()=>{
 const values={tur:'SAATLIK'},schema=operationSchema('IZIN.TALEP_ETTIM',schemas,values);
 const html=formHTML(schema,values,{code:'IZIN.TALEP_ETTIM',client:{people:[],cached:()=>[]},refs:{}});
 for(const text of ['Yıllık İzin','Saatlik İzin','Mazeret İzni'])assert.ok(html.includes(text));
 assert.doesNotMatch(html,/data-path="kisi"/);assert.doesNotMatch(html,/type="time"|type="datetime-local"/);
 assert.ok(validationIssues(values,schema).some(i=>i.path==='baslangic_saati'));
 assert.ok(validationIssues(values,schema).some(i=>i.path==='bitis_saati'));
});
test('ek mesai hedefleri seçili çalışana aittir; iptal ve onay görevleri girmez',()=>{
 const refs={GOREV:[{kimlik:'G1',kisi:'K041',ad:'Çizim',durum:'ACIK'},{kimlik:'G2',kisi:'K001'},{kimlik:'G3',kisi:'K041',tur:'ONAY'},{kimlik:'G4',kisi:'K041',durum:'IPTAL'}],IS:[{kimlik:'I1',kisi:'K017',islem:'Kesim'}]};
 assert.deepEqual(overtimeTargets(refs,'K041'),[{tur:'GOREV',kimlik:'G1',ad:'Çizim'}]);assert.equal(overtimeTargets(refs,'K017')[0].tur,'IS');
});
test('belge hazırlığı mevcut firma türünü değiştirmez ve yetkisiz yazmaz',async()=>{
 let writes=0;const c={admin:false,context:{nesne_turleri:[{kod:'OZEL'}]},write:async()=>writes++};
 await ensureDocumentType(c);assert.equal(writes,0);c.context.nesne_turleri=[];
 await assert.rejects(ensureDocumentType(c),/hazırlanmamış/);assert.equal(writes,0);
});
test('belge hazırlığı taze bağlamda bulunan türü ikinci kez göndermez',async()=>{
 let writes=0;const c={admin:true,context:{nesne_turleri:[]},read:async()=>({deger:{nesne_turleri:[{kod:'BELGE'}]}}),write:async()=>writes++};
 await ensureDocumentType(c);assert.equal(writes,0);
});
test('belge hazırlığı normal olaydan sonra yeni bağlamı bekler',async()=>{
 const definition={kod:'BELGE'},c={admin:true,context:{nesne_turleri:[]},read:async()=>({deger:{nesne_turleri:[]}})};let calls=0;
 c.write=async(code,g)=>{calls++;assert.equal(code,'NESNE_TURU.TANIMLADIM');assert.deepEqual(g,definition);c.context.nesne_turleri=[definition];};
 await ensureDocumentType(c,async()=>({belge:definition}));await ensureDocumentType(c);assert.equal(calls,1);
});
test('form uyarlaması çekirdeğin paylaşılan şemasını değiştirmez',()=>{
 const before=structuredClone(schemas);
 for(const code of Object.keys(schemas))operationSchema(code,schemas);
 assert.deepEqual(schemas,before);
});
