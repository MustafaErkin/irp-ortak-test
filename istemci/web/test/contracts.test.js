import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {OPERATIONS,OPERATIONAL} from '../actions.js';
import {operationSchema,formHTML,validate,validationIssues,cleanValue} from '../forms.js';
import {validateConfig,cacheKey} from '../client.js';
import {esc,table} from '../ui.js';

const schemas=JSON.parse(fs.readFileSync(new URL('../../../referans/eylem_semalari.json',import.meta.url)));
const client={people:[{kimlik:'K001',ad:'Yetkili'},{kimlik:'K017',ad:'Atölye Çalışanı 1'}],units:[{kimlik:'IMALAT',ad:'İmalat'}],projects:[{kimlik:'2509084',ad:'Örnek Proje'}],context:{nesne_turleri:[]},cached:()=>[]};
test('çekirdeğin 91 eylemi kullanıcı ekranına veya gerekçeli işletim yoluna eşlenir',()=>{
 assert.equal(Object.keys(schemas).length,91);
 assert.deepEqual(Object.keys(schemas).sort(),[...Object.keys(OPERATIONS),...Object.keys(OPERATIONAL)].sort());
 assert.equal(Object.keys(OPERATIONS).length,89);
 for(const op of Object.values(OPERATIONS)){assert.ok(op.title&&!op.title.includes('.'));assert.ok(op.page);}
});
test('bütün iş formları ham veri alanı olmadan oluşturulur',()=>{
 for(const code of Object.keys(OPERATIONS)){
  const s=operationSchema(code,schemas,{}),html=formHTML(s,{}, {client,code,refs:{}});
  assert.equal(html.includes('undefined'),false,code);
  assert.equal(html.includes('JSON'),false,code);
  for(const key of s.required??[]) assert.ok(code==='IZIN.TALEP_ETTIM'&&key==='kisi'||key==='hedef'&&OPERATIONS[code].target||html.includes(`data-path="${key}"`)||html.includes(`<legend>${({'degisenler':'Değiştirilecek bilgiler',gorevler:'Görevler',isler:'İşler'})[key]}`)||s.properties[key]?.type==='array'||s.properties[key]?.type==='object',code+' / '+key);
 }
});
test('görev atama zorunlu teslim ve onay alanlarını denetler',()=>{
 const s=operationSchema('GOREV.ATADIM',schemas);
 const valid={gorevler:[{ad:'Teknik resim',nereye:'PROJE',proje:'P1',etap:'E1',teslim_tarihi:'2026-11-02',zaman_degeri:2,zorluk:2,kisi:'K017',onay_gerekli:true,onaylayan:'K001',dosya_gerekli:false}]};
 assert.deepEqual(validate(valid,s),[]);
 assert.ok(validate({gorevler:[{...valid.gorevler[0],onaylayan:null}]},s).some(x=>x.includes('Onaylayan')));
 assert.ok(validate({gorevler:[]},s).length);
 assert.ok(validate({gorevler:[{...valid.gorevler[0],zaman_degeri:0}]},s).length);
});
test('düzenleme şeması gerçek iş alanlarını içerir, iç sürüm alanı almaz',()=>{
 for(const code of ['KISI.DEGISTIRDIM','GOREV.DEGISTIRDIM','IS.DEGISTIRDIM','PROJE.DEGISTIRDIM','ETAP.DEGISTIRDIM','NESNE.GUNCELLEDIM']){
  const s=operationSchema(code,schemas);assert.ok(Object.keys(s.properties.degisenler.properties).length>1,code);assert.equal(s.properties.degisenler.properties.surum,undefined);
 }
});
test('hassas anahtarlar ve servis anahtarı tarayıcı ayarı olamaz',()=>{
 assert.throws(()=>validateConfig({supabase_url:'https://example.supabase.co',supabase_anon:'sb_secret_demo'}));
 assert.throws(()=>validateConfig({supabase_url:'http://example.com',supabase_anon:'sb_publishable_test'}));
 assert.throws(()=>validateConfig({supabase_url:'https://example.com',supabase_anon:'x.'+btoa(JSON.stringify({role:'service_role'}))+'.x'}));
 assert.ok(validateConfig({supabase_url:'https://example.supabase.co',supabase_anon:'sb_publishable_test'}));
});
test('kullanıcı metni HTML olarak çalışmaz, seçili satır olmadan tablo boyanmaz',()=>{
 assert.equal(esc('<img src=x onerror=alert(1)>'),'&lt;img src=x onerror=alert(1)&gt;');
 assert.equal(table([{label:'Ad',key:'ad'}],[{ad:'Bir'}]).includes('class="selected"'),false);
});
test('okuma önbelleğinde dönemler birbirine karışmaz',()=>{
 assert.notEqual(cacheKey('GUN','K017',{gun:'2026-10-30'}),cacheKey('GUN','K017',{gun:'2026-10-31'}));
 assert.notEqual(cacheKey('MAAS','K001',{}),cacheKey('MAAS','K017',{}));
});
test('ön koşulda kendi taslağı yoktur, ön koşul ve birim seçimleri kutudur',()=>{
 const schema=schemas['GOREV.ATADIM'].girdi_semasi.properties.gorevler.items;
 const rows=[{ad:'Kesim',olcum:'ZAMAN'},{ad:'Kontrol',olcum:'ZAMAN'}];
 const html=formHTML(schema,rows[1],{client,code:'GOREV.ATADIM',refs:{},taskRows:rows,taskRowIndex:1});
 assert.match(html,/type="checkbox" data-multi-path="on_kosul" value="@row:0"/);
 assert.doesNotMatch(html,/value="@row:1"/);
 assert.match(html,/\* Kesim/);
 assert.doesNotMatch(html,/Satır 1/);
 assert.match(html,/henüz atanmamış iş/);
 const note=formHTML(operationSchema('NOT.YAZDIM',schemas),{}, {client,code:'NOT.YAZDIM',refs:{}});
 assert.match(note,/type="checkbox" data-multi-path="etiketler" value="IMALAT"/);
 assert.doesNotMatch(note,/multiple/);
});
test('atölye işinin çalışan listesi CEO ve ofis çalışanını içermez',()=>{
 const c={...client,admin:false,context:{gorulebilen_kisiler:['K001','K017','K041']},people:[{kimlik:'K001',ad:'CEO',yaka:'BEYAZ'}, {kimlik:'K017',ad:'Atölye Çalışanı',yaka:'MAVI'}, {kimlik:'K041',ad:'Ofis Çalışanı',yaka:'BEYAZ'}]};
 const html=formHTML(operationSchema('IS.ATADIM',schemas),{}, {client:c,code:'IS.ATADIM',refs:{}});
 assert.match(html,/value="K017"/);
 assert.doesNotMatch(html,/value="K001"|value="K041"/);
});
test('alan denetimi yanlış bilgiyi yalnız genel mesajla bırakmaz, yerini verir',()=>{
 const schema=operationSchema('GOREV.ATADIM',schemas);
 const issues=validationIssues({gorevler:[{ad:'Kontrol',nereye:'PROJE',onay_gerekli:true,zaman_degeri:0}]},schema);
 assert.ok(issues.some(i=>i.path==='gorevler.0.onaylayan'));
 assert.ok(issues.some(i=>i.path==='gorevler.0.kisi'));
 assert.ok(issues.some(i=>i.path==='gorevler.0.zaman_degeri'));
 const html=formHTML(schema.properties.gorevler.items,{olcum:'SAAT'},{client,code:'GOREV.ATADIM',refs:{}});
 assert.match(html,/Tahmini Süre \(Saat\)/);
 assert.match(html,/value="PROJE"[^>]*>Proje İçi/);
});
