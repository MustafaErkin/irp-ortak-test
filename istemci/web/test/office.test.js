import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assignmentSchema,taskGroups,prerequisiteOptions,assignmentReview,fileList,taskDetail} from '../office.js';
import {operationSchema,refOptions,validationIssues,cleanValue} from '../forms.js';
import {assignmentPayload,remainingDrafts} from '../assignment.js';
const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));
test('bitmiş/iptal önkoşul yeni seçimde yok; seçilmiş geçmiş bağ ve devamın kaynağı korunur',()=>{
 const rows=[{kimlik:'a',durum:'BITTI'},{kimlik:'b',durum:'IPTAL'},{kimlik:'c',durum:'ACIK'},{kimlik:'self',durum:'ACIK'}];
 assert.deepEqual(prerequisiteOptions(rows,[],'self').map(r=>r.kimlik),['c']);
 assert.deepEqual(prerequisiteOptions(rows,['a','b'],'self').map(r=>r.kimlik),['a','b','c']);
 const options=refOptions('on_kosul','degisenler.on_kosul',{client:{},code:'GOREV.DEGISTIRDIM',refs:{GOREV:rows},record:{kimlik:'self'}},{degisenler:{on_kosul:['a']}});
 assert.deepEqual(options.map(x=>x.value),['a','c']);
});
test('proje dışı/onaysız görev görünmeyen eski proje, parça ve onaylayanı göndermez',()=>{
 const base=schemas['GOREV.ATADIM'].girdi_semasi.properties.gorevler.items;
 const row={ad:'Kontrol',nereye:'PROJE_DISI',proje:'P1',etap:'E1',parca_kodu:'ESKI',kategori:'PD1',onay_gerekli:false,onaylayan:'K1',olcum:'ZAMAN'};
 const s=assignmentSchema(base,row);for(const k of ['proje','etap','parca_kodu','onaylayan'])assert.equal(s.properties[k],undefined);
 const sent=assignmentPayload([row]).gorevler[0];for(const k of ['proje','etap','parca_kodu','onaylayan'])assert.equal(sent[k],undefined);
});
test('aynı görevi düzeltme ek görev alanı istemez; ayrı revizyon alıcı/tarih/emek ister',()=>{
 const no=operationSchema('GOREV.REDDETTIM',schemas,{revizyon_ver:false});assert.equal(no.properties.kime,undefined);assert.ok(validationIssues({revizyon_ver:false},no).some(i=>i.path==='not'));
 const yes=operationSchema('GOREV.REDDETTIM',schemas,{revizyon_ver:true});const errors=validationIssues({revizyon_ver:true,not:'Eksik ölçü'},yes);for(const k of ['kime','yeni_teslim_tarihi','zaman_degeri'])assert.ok(errors.some(i=>i.path===k),k);
 assert.equal(cleanValue({not:'Teslim açıklaması'},operationSchema('GOREV.TAMAMLADIM',schemas)).not,'Teslim açıklaması');
});
test('bugün filtresi gece sınırını İstanbul saatinde sayar; eski açık işler taşınır',()=>{
 const rows=[{kimlik:'a',kisi:'K1',durum:'ACIK'},{kimlik:'b',kisi:'K1',durum:'BITTI',bitis_ani:'2026-11-01T21:01:00Z'},{kimlik:'c',kisi:'K1',durum:'BITTI',bitis_ani:'2026-11-01T20:59:00Z'},{kisi:'K2',durum:'ATANDI'},{kisi:'K1',tur:'ONAY',durum:'ACIK'}];
 const g=taskGroups(rows,'K1','2026-11-02');assert.equal(g.doneToday,1);assert.deepEqual(g.done.map(r=>r.kimlik),['b']);assert.equal(g.open.length,1);
 assert.equal(taskGroups(rows,'K1','2026-11-03').done.length,0);assert.equal(taskGroups(rows,'K1','2026-11-03','').done.length,2);assert.equal(taskGroups(rows,'K1','2026-11-03','2026-11-01').done.length,1);
});
test('atama özeti her işi tek satırda, tek önkoşul adıyla ve teslim koşuluyla verir',()=>{
 const rows=[{ad:'Kesim',kisi:'K1',zaman_degeri:2},{ad:'Kontrol',kisi:'K1',zaman_degeri:1,onay_gerekli:true,onaylayan:'K2',dosya_gerekli:true,on_kosul:[{satir:1},{satir:1}]}];
 const html=assignmentReview(rows,x=>({K1:'Ofis',K2:'Yönetici'})[x]);assert.equal((html.match(/<tr data-kind/g)||[]).length,2);assert.equal((html.match(/Önce: Kesim/g)||[]).length,1);assert.ok(html.includes('Dosya gerekli'));assert.ok(html.includes('Onay: Yönetici'));
});
test('dosyalar ve kullanıcı notları HTML çalıştırmaz; desteklenmeyen dosyada indirme vardır',()=>{
 const html=fileList([{kimlik:'a',ad:'resim.png'},{kimlik:'b',ad:'çizim.dwg'},{kimlik:'c',ad:'<script>.pdf'}]);assert.equal((html.match(/data-action="file"/g)||[]).length,2);assert.equal((html.match(/data-action="download-file"/g)||[]).length,3);assert.ok(!html.includes('<script>'));
});

test('taslak önkoşul döngüsü ve ölçüm değişikliği doğru işin alanına bağlanır',async()=>{
 const {draftLinkIssues}=await import('../office.js');
 assert.deepEqual(draftLinkIssues([{on_kosul:[]},{on_kosul:[{satir:1}]}]),[]);
 assert.ok(draftLinkIssues([{on_kosul:[{satir:2}]},{on_kosul:[{satir:1}]}]).some(x=>x.index===0&&x.path==='on_kosul'&&x.message.includes('döngü')));
 assert.ok(draftLinkIssues([{olcum:'ZAMAN',on_kosul:[{satir:2}]},{olcum:'SAAT'}]).some(x=>x.index===0&&x.message.includes('Farklı')));
});
