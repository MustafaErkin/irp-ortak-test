import test from 'node:test';
import assert from 'node:assert/strict';
import {assignmentPayload,deliveryWeek,remainingDrafts} from '../assignment.js';
import {Workflow} from '../workflow.js';
import {validate} from '../forms.js';
import fs from 'node:fs';
test('teslim haftası pazartesi ile pazar arasındadır',()=>{
 assert.deepEqual(deliveryWeek('2026-11-01'),{bas:'2026-10-26',bit:'2026-11-01'});
 assert.deepEqual(deliveryWeek('2026-11-02'),{bas:'2026-11-02',bit:'2026-11-08'});
});
test('karışık atamada ön işler ve uyarılar grup içindeki satıra taşınır',()=>{
 const rows=[{olcum:'ZAMAN',ad:'Çizim',on_kosul:[]},{olcum:'SAAT',ad:'Kesim',zaman_degeri:2,birim:'IMALAT',on_kosul:[]},{olcum:'ZAMAN',ad:'Kontrol',on_kosul:[{satir:1}]}];
 const g=assignmentPayload(rows,[{satir:3,kural:'R24'}]);
 assert.deepEqual(g.gorevler[1].on_kosul,[{satir:1}]);assert.equal(g.gorevler[1].uyarilar[0].satir,2);assert.equal(g.uyarilar[0].satir,2);
 const w=assignmentPayload(rows,[],'SAAT');assert.equal(w.isler[0].tahmini_sure_dk,120);assert.equal(w.isler[0].islem,'Kesim');assert.equal(w.isler[0].olcum,undefined);
 assert.equal(rows[1].ad,'Kesim');
});
test('yeni ön işin farklı eylem grubunda veya kendisi olması reddedilir',()=>{
 assert.throws(()=>assignmentPayload([{olcum:'ZAMAN',on_kosul:[{satir:2}]},{olcum:'SAAT',on_kosul:[]}]),/Farklı/);
 assert.throws(()=>assignmentPayload([{on_kosul:[{satir:1}]}]),/kendisinin/);
});
test('onaylı havuz işi görünürde boş bırakılan onay bekletme seçeneğiyle geçerlidir',()=>{
 const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));
 const row=Workflow.prototype.newTask.call({state:{project:'P1',unit:'IMALAT'},c:{person:'K004',today:'2026-11-01',projects:[],people:[{kimlik:'K041',roller:['BEYAZ_YAKA']}]}});
 Object.assign(row,{olcum:'SAAT',ad:'Gövde Montajı',proje:'P1',etap:'E1',birim:'IMALAT',zaman_degeri:1,teslim_tarihi:'2026-11-02'});
 const payload=assignmentPayload([row],[],'SAAT');
 assert.equal(payload.isler[0].onay_gerekli,true);
 assert.equal(payload.isler[0].onay_beklet,false);
 assert.equal(payload.isler[0].tahmini_sure_dk,60);
 assert.deepEqual(validate(payload,schemas['IS.TANIMLADIM'].girdi_semasi),[]);
});
test('kısmi başarılı atamadan kalan taslaklar birbirinin doğru ön koşulu olarak kalır',()=>{
 const rows=[{ad:'Çizim',olcum:'ZAMAN'},{ad:'Kesim',olcum:'SAAT',zaman_degeri:1},{ad:'Kontrol',olcum:'ZAMAN'}, {ad:'Montaj',olcum:'SAAT',zaman_degeri:2,on_kosul:[{satir:2},'ESKI-IS']}];
 const remaining=remainingDrafts(rows,'ZAMAN');
 assert.deepEqual(remaining.map(r=>r.ad),['Kesim','Montaj']);
 assert.deepEqual(remaining[1].on_kosul,[{satir:1},'ESKI-IS']);
 assert.deepEqual(assignmentPayload(remaining,[],'SAAT').isler[1].on_isler,[{satir:1},'ESKI-IS']);
 assert.equal(rows[3].on_kosul[0].satir,2);
});
