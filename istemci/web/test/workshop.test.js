import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {dropPosition,placedQueue,queueIssue,workActionAllowed,workDefinition,workRecipients,teamMembers} from '../workshop_model.js';
import {validationIssues,formHTML,operationSchema} from '../forms.js';
import {IrpClient,responseMessage} from '../client.js';
import {Workflow} from '../workflow.js';
globalThis.navigator??={onLine:true};
const j=(id,extra={})=>({kimlik:id,islem:id,durum:'SIRADA',kisi:'K017',...extra});
const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));
test('ortaya, başa, sona bırakma ve aynı listede yukarı/aşağı hareket tam sırayı korur',()=>{
 const rows=[j('a'),j('b'),j('c')];
 for(const [id,before,expected] of [['c','b',['a','c','b']],['a','c',['b','a','c']],['a',null,['b','c','a']],['d','b',['a','d','b','c']]])assert.deepEqual(placedQueue(rows,j(id),dropPosition(rows,id,before)).map(r=>r.kimlik),expected);
 assert.deepEqual(rows.map(r=>r.kimlik),['a','b','c']);
});
test('bekleten onay atlanamaz; bekletmeyen onay iş akışını kilitlemez; bekleyen iş devredilmez',()=>{
 const hold=j('a',{durum:'ONAY_BEKLIYOR',onay_beklet:true});
 assert.match(queueIssue([hold,j('b')],j('c'),1),/onay bekliyor/);
 assert.match(queueIssue([hold,j('b')],hold,2),/onay bekliyor/);
 assert.equal(queueIssue([hold,j('b')],j('c'),3),'');
 assert.equal(queueIssue([{...hold,onay_beklet:false}],j('c'),1),'');
 assert.match(queueIssue([],hold,1,{transfer:true}),/devredilemez/);
});
test('bitmiş atölye işi gerekçeyle iptal edilebilir; bitmiş iş düzenlenemez veya devredilemez',()=>{
 const done=j('a',{durum:'BITTI'});assert(workActionAllowed('IS.IPTAL_ETTIM',done));
 for(const code of ['IS.DEGISTIRDIM','IS.DEVRETTIM','IS.SIRALADIM','IS.ONAYLADIM'])assert(!workActionAllowed(code,done));
});
test('duruştan devam izni ve teslim onayı farklı durumlara aittir',()=>{
 const r=j('a',{durum:'ONAY_BEKLIYOR'}),p={kisi:'K017',is_:r,hal:{durum:'ONAY_BEKLIYOR'}};
 assert(!workActionAllowed('IS.DEVAM_ONAYLADIM',r,[p]));assert(workActionAllowed('IS.ONAYLADIM',r));
 p.hal={durum:'ARIZADA',devam_izni:false};assert(workActionAllowed('IS.DEVAM_ONAYLADIM',r,[p]));
 p.hal.devam_izni=true;assert(!workActionAllowed('IS.DEVAM_ONAYLADIM',r,[p]));
});
test('pasif/beyaz yaka atanmaz; lider Ekibimde kendini görmez; yetkili farklı ekip görünürlüğü korunur',()=>{
 const c={person:'lider',admin:false,context:{gorulebilen_kisiler:['lider','a','b','eski','ofis']},people:[{kimlik:'lider',yaka:'MAVI'},{kimlik:'a',yaka:'MAVI'},{kimlik:'b',yaka:'MAVI'},{kimlik:'eski',yaka:'MAVI',aktif:false},{kimlik:'ofis',yaka:'BEYAZ'}]};
 assert.deepEqual(workRecipients(c).map(r=>r.kimlik),['lider','a','b']);assert.deepEqual(teamMembers(c,c.people.map(p=>({kisi:p.kimlik}))).map(p=>p.kisi),['a','b']);
});
test('iş tanımı boş etap ve proje dışı kategori hatasını doğru alana bağlar; anlık işte tahmin yok',()=>{
 const base=schemas['IS.TANIMLADIM'].girdi_semasi.properties.isler.items;
 const row={islem:'İş',birim:'IMALAT',tur:'SURELI',nereye:'PROJE',proje:'P',onay_gerekli:false,onay_beklet:false};
 assert(validationIssues(row,workDefinition(base,row)).some(e=>e.path==='etap'));
 assert(!workDefinition(base,row).properties.kisi);assert(!workDefinition(base,row).properties.sira);
 row.etap=null;assert(!validationIssues(row,workDefinition(base,row)).some(e=>e.path==='etap'));
 const outside={...row,nereye:'PROJE_DISI',tur:'ANLIK'},s=workDefinition(base,outside);
 assert(!s.properties.etap);assert(!s.properties.tahmini_sure_dk);assert(validationIssues(outside,s).some(e=>e.path==='kategori'));
 const edit=workDefinition(base,row,{editing:true});for(const k of ['proje','etap','parca_kodu'])assert(!edit.properties[k]);
});
test('önizlemeden sonra liste veya iş değişirse gönderim öncesinde durur',async()=>{
 const c=new IrpClient({}, {}, {});c.read=async()=>({deger:{surum:'yeni'}});c.core=async()=>({value:['K017']});
 await assert.rejects(c.resolveTargets([{tur:'IS',kimlik:'a'}],'IS.SIRALADIM',{kisi:'K017'},{'IS:a':'eski'}),e=>e.code==='STALE_PREVIEW');
});

test('genel proje/iş eylemlerinde de bitmiş atölye iptali ofis kuralına takılmaz',()=>{
 const w=Object.create(Workflow.prototype);w.value=()=>[];w.state={unit:'IMALAT'};
 assert(w.available('IS.IPTAL_ETTIM',j('a',{durum:'BITTI'})));
 assert(!w.available('IS.DEGISTIRDIM',j('a',{durum:'BITTI'})));
 assert(!w.available('GOREV.IPTAL_ETTIM',{durum:'BITTI'}));
});

test('düzenleme yalnız motorun değiştirebildiği alanları sunar; açıklama başlıktan ayrıdır',()=>{
 const s=operationSchema('IS.DEGISTIRDIM',schemas,{degisenler:{}}).properties.degisenler;
 assert(s.properties.is_tanimi);assert(s.properties.islem);
 for(const k of ['tur','birim','kisi_sayisi','planlanan_baslangic','planlanan_bitis','nereye','proje','etap'])assert(!s.properties[k],k);
});
test('plansız işte sayı alanı yok; sıra ortak seçici ve önizlemeden alınır',()=>{
 const s=workDefinition(schemas['IS.PLANSIZ_TANIMLADIM'].girdi_semasi,{nereye:'PROJE',tur:'SURELI'},{unplanned:true});
 assert(!s.properties.sira);assert(!s.required.includes('sira'));assert(!s.properties.kisi);
});
test('ret mesajı somut sunucu nedenini korur; eski genel durum cümlesi gösterilmez',()=>{
 const message='İş teslim edilmiş ve onay bekliyor. Teslim sonucu verilmeden onay koşulları değiştirilemez.';
 assert.equal(responseMessage({kod:'DURUM',mesaj:message}),message);
 assert.equal(responseMessage({kod:'DURUM',alan_hatalari:[{path:'degisenler.onay_gerekli',message}]}),message);
 for(const data of [{kod:'DURUM'},{kod:'DURUM',mesaj:'Nesnenin durumu bu işleme uygun değil.'}])assert.doesNotMatch(responseMessage(data),/Nesnenin durumu bu işleme uygun değil/);
});
