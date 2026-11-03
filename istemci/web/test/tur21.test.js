import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {operationSchema,formHTML,validationIssues,refOptions} from '../forms.js';
import {assignmentSchema} from '../office.js';
import {assignmentPayload} from '../assignment.js';
import {sortProjectJobs} from '../project_model.js';
import {responseMessage} from '../client.js';
import {Workflow} from '../workflow.js';
const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));
const client={person:'K004',context:{atama_adaylari:['K041']},people:[{kimlik:'K001',ad:'CEO'},{kimlik:'K004',ad:'Yönetici'},{kimlik:'K041',ad:'Ofis Çalışanı'},{kimlik:'ESKI',ad:'Ayrılmış',aktif:false}],projects:[],units:[],cached:()=>[]};
const ctx={client,refs:{ETAP:[{kimlik:'E',ad:'Etap',proje:'P'}]},code:'GOREV.ATADIM'};
test('genel yeni iş önceki proje, kişi, tarih ve emek değerini almaz',()=>{
 const row=Workflow.prototype.newTask.call({state:{project:'ESKI'},c:client});
 for(const k of ['proje','kisi','birim','teslim_tarihi','zaman_degeri','zorluk','onaylayan'])assert.equal(row[k],undefined);
});
test('koşullu gerekli alan yıldızları, doğrulama ve Etap Dışı aynı sözleşmeden gelir',()=>{
 const base=schemas['GOREV.ATADIM'].girdi_semasi.properties.gorevler.items;
 for(const onay of [false,true]){
  const row={nereye:'PROJE',onay_gerekli:onay},s=assignmentSchema(base,row),html=formHTML(s,row,ctx);
  assert.match(html,/data-path="proje" data-required="true"/);assert.match(html,/data-path="etap" data-required="true"/);assert.match(html,/>Etap Dışı</);
  assert.equal(validationIssues(row,s).some(e=>e.path==='onaylayan'),onay);
  assert.equal(html.includes('data-path="onaylayan" data-required="true"'),onay);
 }
 const row={nereye:'PROJE_DISI',onay_gerekli:false},s=assignmentSchema(base,row);s.properties.kategori={type:'string'};
 assert(validationIssues(row,s).some(e=>e.path==='kategori'));assert(!validationIssues(row,s).some(e=>e.path==='etap'));
});
test('atama, onaylayan ve sorumluluk önerisinde ayrı seçim sınırları korunur',()=>{
 assert.deepEqual(refOptions('kisi','kisi',ctx,{}).map(x=>x.value),['K041']);
 assert.deepEqual(refOptions('onaylayan','onaylayan',ctx,{kisi:'K041'}).map(x=>x.value),['K001','K004']);
 assert.equal(refOptions('etap','etap',ctx,{}).length,0);assert.equal(refOptions('etap','etap',ctx,{proje:'P'}).length,1);
 const rctx={...ctx,code:'GOREV.REDDETTIM',refs:{KISI:client.people}};
 assert(refOptions('kimlik','sorumlular.0.kimlik',rctx,{sorumlular:[{tur:'KISI'}]}).some(x=>x.value==='K001'));
 const schema=operationSchema('GOREV.REDDETTIM',schemas,{revizyon_ver:true});assert(!schema.properties.sebep_olan);
 for(const k of ['kime','yeni_teslim_tarihi','zaman_degeri'])assert(validationIssues({revizyon_ver:true,not:'Hata'},schema).some(x=>x.path===k));
});
test('inceleme açılırken ve açıkken çift istek ikinci pencere oluşturmaz',async()=>{
 const w=Object.create(Workflow.prototype),dialog=new EventTarget();let calls=0,release;const ready=new Promise(r=>release=r);
 w.runInspect=async()=>{calls++;await ready;return dialog;};const first=w.inspect('GOREV','g');await w.inspect('GOREV','g');assert.equal(calls,1);release();await first;await w.inspect('GOREV','g');assert.equal(calls,1);dialog.dispatchEvent(new Event('close'));await w.inspect('GOREV','g');assert.equal(calls,2);
});
test('inceleme okuma hatası tekrar denemeyi engellemez',async()=>{const w=Object.create(Workflow.prototype);let n=0;w.runInspect=async()=>{if(!n++)throw Error('Bağlantı');};await assert.rejects(w.inspect('GOREV','g'));await w.inspect('GOREV','g');assert.equal(n,2);});
test('kuyruk doluyken başlayan kabul düğmesi görünür kalır; diğer kabul işlemleri açılmaz',()=>{
 const w=Object.create(Workflow.prototype);w.c={pending:1};w.accepting=new Set(['g1']);
 assert.equal(w.available('GOREV.KABUL_ETTIM',{kimlik:'g1',durum:'ATANDI'}),true);
 assert.equal(w.available('GOREV.KABUL_ETTIM',{kimlik:'g2',durum:'ATANDI'}),false);
});

test('etap bilinçli seçilir: boş hata, Etap Dışı null, motor girdisinde işaret yok',()=>{
 const base=schemas['GOREV.ATADIM'].girdi_semasi.properties.gorevler.items;
 const row={nereye:'PROJE',proje:'P'},s=assignmentSchema(base,row);
 assert(validationIssues(row,s).some(x=>x.path==='etap'));
 row.etap=null;assert(!validationIssues(row,s).some(x=>x.path==='etap'));
 assert.match(formHTML(s,row,ctx),/data-null-option selected>Etap Dışı/);
 assert.equal(assignmentPayload([row]).gorevler[0].etap,undefined);
 row.etap='E';assert.equal(assignmentPayload([row]).gorevler[0].etap,'E');
});
test('boolean zorunluluğu korunurken kutucuk etiketinde yıldız olmaz',()=>{
 const s={type:'object',required:['dosya_gerekli'],properties:{dosya_gerekli:{type:'boolean'}}};
 assert(!validationIssues({dosya_gerekli:false},s).length);
 const html=formHTML(s,{dosya_gerekli:false},ctx);assert(!html.includes(' *'));assert(html.includes('data-required="true"'));
});
test('teslim notu ilk alan, gecikme nedeni ve açıklaması sondadır',()=>{
 const keys=Object.keys(operationSchema('GOREV.TAMAMLADIM',schemas).properties);
 assert.equal(keys[0],'not');assert.deepEqual(keys.slice(-2),['gecikme_nedeni','gecikme_aciklamasi']);
});
test('proje işleri tamamlanma anına göre sıralanır; oluşturma veya API sırası belirlemez',()=>{
 const rows=[{kimlik:'G2',atama_ani:'2026-11-02T10:00:00Z',bitis_ani:'2026-11-02T11:00:00Z'},
 {kimlik:'G3',atama_ani:'2026-11-02T12:00:00Z',bitis_ani:null},
 {kimlik:'I1',atama_ani:'2026-11-02T08:00:00Z',bitis_ani:'2026-11-02T14:00:00+03:00'},
 {kimlik:'G1',atama_ani:'2026-11-02T09:00:00Z',bitis_ani:'2026-11-02T12:00:00Z'},
 {kimlik:'ESKI',bitis_ani:'geçersiz'}];
 assert.deepEqual(sortProjectJobs(rows).map(x=>x.kimlik),['G1','G2','I1','G3','ESKI']);
 assert.equal(rows[0].kimlik,'G2');
});
test('hesap beklemede kısa mesaj bekleyip tekrar denemeyi ister; bağlantı belirsizliğiyle karışmaz',()=>{
 assert.match(responseMessage({kod:'HESAP_BEKLIYOR'}),/hesaplanıyor.*henüz gönderilmedi/);
});
