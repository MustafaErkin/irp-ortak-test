import {workRecipients,workDefinition} from './workshop_model.js';
import {prerequisiteOptions} from './office.js';
import {planReview,planStamp} from './plan_review.js';
import {icon} from './icons.js';
import {operationMessage,operationTone} from './client.js';
import {esc, label, idOf, arr, isoDay, modal, toast, titleCase, headingCase} from './ui.js';
import {OPERATIONS} from './actions.js';
import {projectOpen,projectLabel,projectOperations,projectIssues} from './project_model.js';
import {ensureDocumentType} from './prerequisites.js';
import {parseTemporal,displayTemporal,validTemporal,leavePayload,LEAVE_TYPES,overtimeTargets,bindTemporalInput,bindDatePicker} from './temporal.js';

export const FIELD_LABELS = {
 ad:'Ad',kod:'Kod',kisi:'Çalışan',kisiler:'Çalışanlar',kime:'Devralan',kimden:'Devreden',kime_sira:'Devralanın listesindeki sıra',kimden_yeni_is:'Devredene verilecek iş',birim:'Birim',basi:'Birim sorumlusu',ust_birim:'Üst birim',yaka:'Çalışma biçimi',roller:'Roller',giris_tarihi:'İşe giriş tarihi',ayrilis_tarihi:'Ayrılış tarihi',gecerli_baslangic:'Geçerlilik başlangıcı',gerekce:'Gerekçe',aciklama:'Açıklama',not:'Not',metin:'Notunuz',etiketler:'İstek bırakılacak birimler',proje:'Proje',etap:'Etap',sorumlu:'Sorumlu',ana_proje:'Ana proje',ek:'Kod eki',musteri:'Müşteri',baslangic_tarihi:'Başlangıç tarihi',teslim_tarihi:'Teslim tarihi',teslim_saati:'Teslim saati',kesin_kabul_tarihi:'Kesin kabul tarihi',baslangic:'Başlangıç',bitis:'Bitiş',hedef_saat:'Hedef emek (saat)',hedef:'İlgili nesne',hedefler:'Planlanacak işler',degisenler:'Değiştirilecek bilgiler',nereye:'Emeğin yazılacağı yer',kategori:'Proje dışı faaliyet',parca_kodu:'Parça kodu',is_tanimi:'İşin açıklaması',islem:'Yapılacak iş',gorevler:'Görevler',isler:'İşler',tur:'Tür',tahmini_sure_dk:'Tahmini süre (dakika)',zaman_degeri:'Zaman değeri (saat)',zorluk:'Zorluk',oncelik:'Öncelik',onay_gerekli:'Tamamlandığında onay gerekli',onay_beklet:'Onay gelmeden sıradaki işe geçilmesin',onaylayan:'Onaylayan',dosya_gerekli:'Teslimde dosya gerekli',sorun_kaynakli:'Sorunu çözmek için veriliyor',on_kosul:'Önce bitmesi gereken görevler',on_isler:'Önce bitmesi gereken işler',kisi_sayisi:'Gereken kişi sayısı',sira:'Listedeki sıra',yeni_sira:'Yeni sıra',tezgah:'Tezgâh',tezgah_rolu:'Tezgâh işlemi',planlanan_baslangic:'Planlanan başlangıç',planlanan_bitis:'Planlanan bitiş',yetkinlik:'Gereken yetkinlik',yetkinlikler:'Yetkinlikler',is_bitti:'Bu aralıkta iş tamamlandı',makine_bitis_ani:'Makinenin durduğu an',neden:'Neden',gecikme_nedeni:'Gecikme nedeni',gecikme_aciklamasi:'Gecikme açıklaması',revizyon_ver:'Ayrı bir revizyon görevi ver',sebep_olan:'Sebep olan',yeni_teslim_tarihi:'Revizyonun teslim tarihi',sorumlular:'Sorumluluk dağılımı',kimlik:'İlgili kişi veya nesne',yuzde:'Pay (%)',karar:'Karar',satir:'Dağılım satırı',tarih:'Tarih',gun:'Gün',gunler:'Günler',ozet_surumu:'Günün özet sürümü',tanimsiz_aciklama:'Açık kalan süre için açıklama',gerekli:'Gün sonu onayı gerekli',ek_mesai:'Ek mesai',mesai_baslangic:'Mesai başlangıcı',mesai_bitis:'Mesai bitişi',calisma_gunleri:'Çalışma günleri',sabit_molalar:'Sabit molalar',bas:'Başlangıç saati',bit:'Bitiş saati',takvim:'Birim mesaisi',takvim_gecerli:'Birim mesaisinin başlangıcı',vardiyalar:'Tezgâhın çalışma aralıkları',kapsam:'Kapsam',deger:'Değer',anahtar:'Ayar',aktif:'Kullanımda',liste:'Seçenek listesi',ust:'Üst seçenek',eylem_kodu:'İşlem',kimler:'Yetkili roller',acabilenler:'Nesne açabilecekler',asamalar:'Aşamalar',baslangic_asamasi:'İlk aşama',son_asamalar:'Bitiş aşamaları',gecisler:'Aşama geçişleri',den:'Önceki aşama',e:'Sonraki aşama',baglanabilir_turler:'Bağlanabilecek nesne türleri',surum_onaylayanlar:'Belge sürümü onaylayabilecekler',baglar:'Bağlı nesneler',yeni_asama:'Yeni aşama',dosyalar:'Ekli dosyalar',surum_no:'Sürüm numarası',surum_adi:'Sürüm adı',servis_kimligi:'Modül servis adı',cihaz_harfi:'Modülün cihaz harfi',degisiklik:'Kaynak iş ve değişiklik nedeni',kaynak:'Kaynak iş',bildirimler:'Bildirimler',iptal:'Ayrılış işlemini geri al',tutar:'Tutar (₺)',HAFTA_ICI:'Hafta içi',CUMARTESI:'Cumartesi',PAZAR:'Pazar',TATIL:'Tatil',gun_sonu_raporu_zorunlu:'Gün sonu özeti gerekli',gun_sonu_hatirlatma:'Gün sonu hatırlatması',izin_ik_onayi:'İzinde İK onayı',proje_gorunurlugu:'Proje görünürlüğü',sessiz_kabul_is_gunu:'Sessiz kabul (iş günü)',standart_gunluk_saat:'Standart günlük saat',fazla_mesai_katsayilari:'Fazla mesai katsayıları',son:'Son aşama',talimat:'Talimat',oran:'Oran',onaylayanlar:'Onaylayanlar',gun_sonu:'Gün sonu',seviye:'Seviye'
};
for(const key of Object.keys(FIELD_LABELS))FIELD_LABELS[key]=titleCase(FIELD_LABELS[key]);
FIELD_LABELS.degisiklik='Asıl İş Ve Değişiklik Nedeni';FIELD_LABELS.kaynak='Asıl İş';
Object.assign(FIELD_LABELS,{saat_belirle:'Saat Belirle',baslangic_saati:'Başlangıç Saati',bitis_saati:'Bitiş Saati'});
const S = {type:'string'}, N={type:'number'}, I={type:'integer'}, B={type:'boolean'}, D={type:'string',format:'date'}, DT={type:'string',format:'date-time'};
const object=properties=>({type:'object',properties});
const array=items=>({type:'array',items});
const permission=object({kimler:array(S),kapsam:{enum:['BIRIM','FIRMA']}});

export function operationSchema(code,schemas,values={}) {
 const root=structuredClone(schemas[code]?.girdi_semasi??object({}));root.properties??={};
 const p=root.properties;
 const task=schemas['GOREV.ATADIM']?.girdi_semasi?.properties?.gorevler?.items;
 const work=schemas['IS.TANIMLADIM']?.girdi_semasi?.properties?.isler?.items;
 const project=schemas['PROJE.ACTIM']?.girdi_semasi;
 if(code==='KISI.DEGISTIRDIM')p.degisenler=object({ad:S,birim:S,roller:array(S),yaka:{enum:['MAVI','BEYAZ']},giris_tarihi:D});
 if(code==='GOREV.DEGISTIRDIM')p.degisenler=object(Object.fromEntries(Object.entries(task.properties).filter(([k])=>!['degisiklik','tur','birim','kisi_sayisi','islem','is_tanimi','on_isler','tezgah_rolu','tahmini_sure_dk'].includes(k))));
 if(code==='IS.DEGISTIRDIM')p.degisenler=object(Object.fromEntries(Object.entries(work.properties).filter(([k])=>!['degisiklik','gorevler','ad','zorluk','zaman_degeri','dosya_gerekli','kisi','onaylayan'].includes(k))));
 if(code==='PROJE.DEGISTIRDIM')p.degisenler=object(Object.fromEntries(Object.entries(project.properties).filter(([k])=>['ad','musteri','teslim_tarihi','baslangic_tarihi','kesin_kabul_tarihi','sorumlu'].includes(k))));
 if(code==='ETAP.DEGISTIRDIM')p.degisenler=object(Object.fromEntries(Object.entries(schemas['ETAP.TANIMLADIM'].girdi_semasi.properties).filter(([k])=>k!=='proje')));
 if(code==='NESNE.GUNCELLEDIM')p.degisenler=object({ad:S,kod:S,sorumlu:S,baglar:schemas['NESNE.ACTIM'].girdi_semasi.properties.baglar});
 if(code==='SORUMLULUK.DOGRULADIM'||code==='SORUMLULUK.ITIRAZI_DEGERLENDIRDIM')p.gerekce=S;
 if(code==='PLAN.ONAYLADIM')p.gerekce=S;
 if(code==='PROJE.KOD_DEGISTIRDIM'){delete p.ek;root.properties={kod:p.kod,gerekce:p.gerekce};}
 if(code==='IS.MOLA_VERDIM'||code==='GOREV.TAMAMLADIM')p.not=S;
 if(code==='GOREV.TAMAMLADIM')root.properties={not:p.not,...Object.fromEntries(Object.entries(p).filter(([key])=>!['not','gecikme_nedeni','gecikme_aciklamasi'].includes(key))),gecikme_nedeni:p.gecikme_nedeni,gecikme_aciklamasi:p.gecikme_aciklamasi};
 if(code==='GOREV.REDDETTIM'){
  delete p.sebep_olan;
  if(p.sorumlular?.items?.properties){const fields=p.sorumlular.items.properties;p.sorumlular.items.properties=Object.fromEntries(['tur','kimlik','yuzde'].map(key=>[key,fields[key]]));}
  if(!values.revizyon_ver)for(const k of ['yeni_teslim_tarihi','zaman_degeri','kime','sebep_olan'])delete p[k];
  else root.required=[...new Set([...(root.required??[]),'yeni_teslim_tarihi','zaman_degeri','kime'])];
  root.uiGroups=[['Düzeltme Gerekçesi',['not']],['Sorumluluk',['sorumlular'],true],['Ayrı Revizyon Görevi',['revizyon_ver','kime','yeni_teslim_tarihi','zaman_degeri']]];
 }

 if(code==='NESNE_TURU.TANIMLADIM'){
  p.acabilenler=permission;p.asamalar=array(object({kod:S,ad:S,son:B}));p.asamalar.items.required=['kod','ad'];
  p.gecisler.items.properties.kimler=permission;p.surum_onaylayanlar=permission;
 }
 if(code==='AYAR.DEGISTIRDIM'){
  const key=values.anahtar;
  p.deger=key==='fazla_mesai_katsayilari'?object({HAFTA_ICI:N,CUMARTESI:N,PAZAR:N,TATIL:N}):['gun_sonu_raporu_zorunlu','gun_sonu_hatirlatma','izin_ik_onayi'].includes(key)?B:key==='proje_gorunurlugu'?{enum:['HERKES','UYELER']}:N;
 }
 if(code==='PROJE.ACTIM'){
  delete p.kimlik;
  root.uiGroups=[['Proje Bilgileri',['ad','kod','musteri']],['Sorumluluk ve Takvim',['sorumlu','baslangic_tarihi','teslim_tarihi']],['Diğer Seçenekler',['ana_proje','ek','kesin_kabul_tarihi','aktif'],true]];
 }
 if(code==='ETAP.TANIMLADIM')root.uiGroups=[['Etap Bilgileri',['proje','ad','birim','sorumlu']],['İş Planı',['baslangic','bitis','hedef_saat']]];
 if(code==='IS.TANIMLADIM'){
  const item=p.isler.items;
  const order=['islem','is_tanimi','birim','nereye','proje','etap','parca_kodu','tur','tahmini_sure_dk','teslim_tarihi','onay_gerekli','onay_beklet','tezgah','on_isler','planlanan_baslangic','planlanan_bitis','yetkinlik','tezgah_rolu','kisi_sayisi','kategori','degisiklik'];
  item.properties=Object.fromEntries(order.filter(k=>item.properties[k]).map(k=>[k,item.properties[k]]));
  item.required=['islem','birim','nereye','tur'];
 }
 if(code==='IS.DEGISTIRDIM')p.degisenler=workDefinition(p.degisenler,values.degisenler??{},{editing:true});
 if(code==='IS.BAGLANTI_DUZELTTIM')p.degisenler.properties.etap.uiNullOption='Etap Dışı';
 if(code==='DURUS.BASLADI')p.kapsam=array(S);
 if(code==='IZIN.TALEP_ETTIM'){
  p.tur={enum:LEAVE_TYPES.map(t=>t.value)};p.baslangic=D;p.bitis=D;p.saat_belirle=B;
  if(values.saat_belirle||values.tur==='SAATLIK'){
   p.baslangic_saati={...S,format:'time'};p.bitis_saati={...S,format:'time'};
   root.required=[...root.required,'baslangic_saati','bitis_saati'];
  }
 }
 // Şemanın genel string alanlarına da aynı tarih/saat denetimi uygulanır.
 function temporalFields(node){for(const [key,field]of Object.entries(node.properties??{})){
  if(field.properties)temporalFields(field);else if(field.items?.properties)temporalFields(field.items);
  else if(!field.enum&&(field.type==='string'||Array.isArray(field.type)&&field.type.includes('string'))){const kind=inputType(key,code,field);if(['date','time','datetime-local'].includes(kind))field.format=kind==='datetime-local'?'date-time':kind;}
 }}const result=structuredClone(root);temporalFields(result);
 return result;
}
export function getPath(value,path){return path.split('.').filter(Boolean).reduce((v,k)=>v?.[k],value);}
export function setPath(value,path,next){const keys=path.split('.');let obj=value;keys.slice(0,-1).forEach((k,i)=>{obj[k]??=/^\d+$/.test(keys[i+1])?[]:{};obj=obj[k];});if(next===undefined)delete obj[keys.at(-1)];else obj[keys.at(-1)]=next;}
export function cleanValue(value,schema){
 if(schema.type==='object'||schema.properties){const out={};for(const [k,v]of Object.entries(value??{})){const s=schema.properties?.[k];if(!s)continue;const c=cleanValue(v,s);if(c!==undefined)out[k]=c;}return out;}
 if(schema.type==='array'){if(!Array.isArray(value))return undefined;return value.map(x=>cleanValue(x,schema.items??S)).filter(x=>x!==undefined);}
 if(value===''||value===undefined)return undefined;
 return value;
}
export function requiredFields(schema,values={}) {
 const required=new Set(schema.required??[]);
 for(const rule of schema.allOf??[]){const cond=rule.if;if(!cond)continue;
  const matches=(cond.required??[]).every(key=>values[key]!==undefined)&&Object.entries(cond.properties??{}).every(([key,test])=>values[key]===undefined||('const' in test?values[key]===test.const:test.enum?test.enum.includes(values[key]):true));
  for(const key of (matches?rule.then:rule.else)?.required??[])required.add(key);
 }
 return [...required].filter(key=>schema.properties?.[key]);
}
export function validationIssues(value,schema,path='') {
 const issues=[],name=titleCase(FIELD_LABELS[path.split('.').at(-1)]??'Alan');
 const add=(message,p=path)=>issues.push({path:p,message});
 if(value===undefined||value===null)return issues;
 if(schema.properties){
  for(const key of requiredFields(schema,value)){const v=value[key];if(v===undefined||v===null&&!schema.properties[key]?.type?.includes?.('null')||typeof v==='string'&&!v.trim())add((FIELD_LABELS[key]??titleCase(key))+' gerekli.',path?path+'.'+key:key);}
  for(const [key,v]of Object.entries(value))if(schema.properties[key])issues.push(...validationIssues(v,schema.properties[key],path?path+'.'+key:key));
 }
 if(Array.isArray(value)){
  if(schema.minItems&&value.length<schema.minItems)add(name+' için en az bir satır gerekli.');
  if(schema.uniqueItems&&new Set(value.map(v=>JSON.stringify(v))).size!==value.length)add(name+' içinde tekrar eden seçim var.');
  value.forEach((v,i)=>issues.push(...validationIssues(v,schema.items??{},path?path+'.'+i:String(i))));
 }
 if(schema.enum&&!schema.enum.includes(value))add(name+' için geçerli bir seçenek seçin.');
 if(['number','integer'].includes(schema.type)){
  if(typeof value!=='number'||!Number.isFinite(value)||schema.type==='integer'&&!Number.isInteger(value))add(name+' sayısal olmalı.');
  if(schema.minimum!=null&&value<schema.minimum)add(name+` en az ${schema.minimum} olmalı.`);
  if(schema.maximum!=null&&value>schema.maximum)add(name+` en çok ${schema.maximum} olmalı.`);
 }
 if(schema.pattern&&typeof value==='string'&&!new RegExp(schema.pattern).test(value))add(name+' biçimini kontrol edin.');
 if(['date','date-time','time'].includes(schema.format)&&!validTemporal(value,schema.format==='date-time'?'datetime-local':schema.format))add(name+(schema.format==='time'?' için 24 saat biçiminde geçerli bir saat girin (09:30).':' için tam ve geçerli bir tarih girin (gün.ay.yıl).'));
 return issues;
}
export const validate=(value,schema,path='')=>validationIssues(value,schema,path).map(i=>i.message);
export function showValidation(root,issues){
 root.querySelectorAll('[aria-invalid]').forEach(e=>e.removeAttribute('aria-invalid'));
 root.querySelectorAll('.field-invalid').forEach(e=>e.classList.remove('field-invalid'));
 root.querySelectorAll('.field-message').forEach(e=>e.remove());let first;
 for(const issue of issues){const el=[...root.querySelectorAll('[data-path],[data-choice-group]')].find(e=>(e.dataset.path??e.dataset.choiceGroup)===issue.path);if(!el)continue;
  const field=el.closest('.field,.checkbox-field,.choice-list,.field-group')??el;field.classList.add('field-invalid');el.setAttribute('aria-invalid','true');
  if(!field.querySelector('.field-message')){const message=document.createElement('small');message.className='field-message';message.textContent=issue.message;field.append(message);}
  for(let parent=field.parentElement;parent&&parent!==root;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
  first??=el;
 }
 if(first){first.scrollIntoView({block:'center',behavior:'smooth'});(first.matches('input,select,textarea')?first:first.querySelector('input,select,textarea'))?.focus({preventScroll:true});}
}

const isWorkRecipient=(code,key)=>['IS.ATADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM'].includes(code)&&['kisi','kisiler','kime','kimden'].includes(key);
export function refOptions(key,path,ctx,values){
 const c=ctx.client,code=ctx.code;
 const named=(rows,extra='')=>rows.map(x=>({value:idOf(x),text:(x.ad??x.islem??x.is_tanimi??x.kod??idOf(x))+(extra&&x[extra]?' · '+label(x[extra]):'')}));
 if(key==='kisi'&&code==='MAAS.GUNCELLEDIM'&&ctx.costKind==='SAAT_UCRETI')return named(ctx.refs.TEZGAH??[]);
 if(isWorkRecipient(code,key))return named(workRecipients(c));
 if(key==='sorumlu'&&['PROJE.ACTIM','PROJE.DEGISTIRDIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM'].includes(ctx.code)){const allowed=c.context.sorumlu_adaylari?.[ctx.code]??[];return named(c.people.filter(p=>allowed.includes(idOf(p))||ctx.code.endsWith('DEGISTIRDIM')&&idOf(p)===ctx.record?.sorumlu));}
 if(key==='kisi'&&code==='GOREV.ATADIM')return named(c.people.filter(p=>p.aktif!==false&&idOf(p)!==c.person&&(c.context.atama_adaylari??[]).includes(idOf(p))));
 if(key==='onaylayan'&&code.startsWith('GOREV.')){const parent=getPath(values,path.split('.').slice(0,-1).join('.'))??values;return named(c.people.filter(p=>p.aktif!==false&&idOf(p)!==parent.kisi));}
 if(key==='kime'&&code==='GOREV.REDDETTIM')return named(c.people.filter(p=>p.aktif!==false));
 if(['kisi','kime','kimden','onaylayan','sorumlu','basi','sebep_olan'].includes(key))return named(c.people);
 if(key==='kisiler')return named(c.people);
 if(['birim','ust_birim','etiketler','kapsam'].includes(key))return key==='kapsam'?[{value:'FIRMA',text:'Firma geneli'},...named(c.units)]:named(c.units);
 if(['proje','ana_proje'].includes(key))return c.projects.filter(x=>key==='ana_proje'||projectOpen(x)||idOf(x)===values.proje&&ctx.locked?.proje).map(x=>({value:idOf(x),text:projectLabel(x)}));
 if(key==='etap'){const parent=getPath(values,path.split('.').slice(0,-1).join('.'))??values;return named((ctx.refs.ETAP??[]).filter(x=>parent.proje&&x.proje===parent.proje));}
 if(key==='tezgah')return named(ctx.refs.TEZGAH??[]);
 if(['on_kosul','on_isler','kimden_yeni_is'].includes(key)){const mode=values.olcum??'ZAMAN',kind=key==='on_kosul'&&mode!=='SAAT'?'GOREV':'IS';return [...(ctx.taskRows??[]).flatMap((x,i)=>i===ctx.taskRowIndex||(x.olcum??'ZAMAN')!==mode?[]:[{value:'@row:'+i,text:'* '+(x.ad||'Yeni İş'),draft:true}]),...named(key==='kimden_yeni_is'?(ctx.refs[kind]??[]).filter(r=>idOf(r)!==idOf(ctx.record)):prerequisiteOptions(ctx.refs[kind]??[],getPath(values,path)??[],idOf(ctx.record)))];}
 if(key==='hedef')return named(ctx.refs[OPERATIONS[code]?.ref]??[],'durum');
 if(key==='kaynak')return named(ctx.refs[values.olcum==='SAAT'||code.startsWith('IS.')?'IS':'GOREV']??[]);
 if(key==='kimlik'){
  const parent=getPath(values,path.split('.').slice(0,-1).join('.'))??{};
  return named(ctx.refs[parent.tur]??(parent.tur==='KISI'?c.people:parent.tur==='BIRIM'?c.units:[]));
 }
 if(key==='tur'&&['NESNE.ACTIM'].includes(code))return named(arr(c.context.nesne_turleri));
 if(key==='tur'&&code.startsWith('IZIN.'))return LEAVE_TYPES;
 if(['roller','kimler'].includes(key))return [...new Set(['YETKILI','YONETICI','EKIP_LIDERI','CALISAN','BEYAZ_YAKA','IK','MALIYET','BIRIM_YONETICISI','BIRIM_BASI','PROJE_SORUMLUSU',...arr(c.cached('KODLAR')).filter(x=>x.liste==='ROL').map(x=>x.kod)])].map(value=>({value,text:label(value)}));
 if(['yetkinlik','yetkinlikler'].includes(key))return named(arr(c.cached('KODLAR')).filter(x=>x.liste==='YETKINLIK'));
 if(['neden','gecikme_nedeni'].includes(key)&&!['DURUS.BASLADI','TEZGAH.DURUS_BILDIRDIM'].includes(code))return arr(c.cached('KODLAR')).filter(x=>x.liste==='DURUS_NEDENI').map(x=>({value:x.kod,text:x.ad??x.kod}));
 if(key==='kategori')return named(arr(c.cached('KODLAR')).filter(x=>x.liste==='PD'));
 if(key==='yeni_asama')return arr(c.context.nesne_turleri).flatMap(t=>(t.asamalar??[]).map(a=>({value:typeof a==='string'?a:a.kod,text:typeof a==='string'?label(a):a.ad??label(a.kod)})));
 if(['baslangic_asamasi','son_asamalar','den','e'].includes(key))return (values.asamalar??[]).map(a=>({value:a.kod,text:a.ad??a.kod}));
 if(key==='baglanabilir_turler')return named(arr(c.context.nesne_turleri));
 if(key==='eylem_kodu')return Object.values(OPERATIONS).map(a=>({value:a.code,text:a.title}));
 return null;
}
function inputType(key,code,schema){
 const type=Array.isArray(schema.type)?schema.type.find(x=>x!=='null'):schema.type;
 if(type==='integer'||type==='number')return 'number';
 if(schema.format==='date')return 'date';
 if(schema.format==='time')return 'time';
 if(schema.format==='date-time'||['planlanan_baslangic','planlanan_bitis','makine_bitis_ani'].includes(key))return 'datetime-local';
 if(['mesai_baslangic','mesai_bitis','teslim_saati','bas','bit'].includes(key)||code.startsWith('EK_MESAI.')&&['baslangic','bitis'].includes(key))return 'time';
 if(['gun','tarih','giris_tarihi','ayrilis_tarihi','teslim_tarihi','yeni_teslim_tarihi','baslangic_tarihi','kesin_kabul_tarihi','takvim_gecerli'].includes(key))return 'date';
 if(['baslangic','bitis'].includes(key))return code.startsWith('ETAP.')?'date':'datetime-local';
 if(key==='gecerli_baslangic')return code.startsWith('KISI.DEGISTIRDIM')?'datetime-local':'date';
 return 'text';
}
const longFields=new Set(['metin','not','aciklama','gerekce','talimat','is_tanimi','gecikme_aciklamasi','tanimsiz_aciklama']);

export function formHTML(schema,values,ctx,path=''){
 schema={...schema,required:requiredFields(schema,getPath(values,path)??values)};
 if(schema.uiGroups)return schema.uiGroups.map(([title,keys,advanced])=>{const subset={...schema,uiGroups:null,properties:Object.fromEntries(keys.filter(k=>schema.properties[k]).map(k=>[k,schema.properties[k]])),required:(schema.required??[]).filter(k=>keys.includes(k))};const content=(title==='Sorumluluk'?'<p class="form-help">Bu dağılım ayrı revizyon açmadan da yapılabilir. Yetkiniz dışındaki sorumluluk önerileri ilgili üst tarafından doğrulanır.</p>':'')+formHTML(subset,values,ctx,path);return advanced?`<details class="advanced-fields" data-form-section="${esc(title)}"><summary>${esc(title)}</summary>${content}</details>`:`<section class="form-section" data-form-section="${esc(title)}"><h3>${esc(title)}</h3>${content}</section>`;}).join('');
 if(schema.properties){const req=new Set(schema.required??[]);return `<div class="form-grid">${Object.entries(schema.properties).map(([key,s])=>{
  if(key==='proje'&&ctx.code==='PLAN.ONAYLADIM'&&ctx.record)return '';
  if(key==='hedef'&&OPERATIONS[ctx.code]?.target)return '';
  if(key==='kisi'&&ctx.code==='IZIN.TALEP_ETTIM')return '';
  if(key==='saat_belirle'&&values.tur==='SAATLIK')return '';
  if(key==='ozet_surumu'||key==='dosyalar'&&ctx.code==='NESNE.SURUM_EKLEDIM')return '';
  const p=path?path+'.'+key:key,v=getPath(values,p),name=key==='not'&&ctx.code==='GOREV.TAMAMLADIM'?'Teslim Notu':key==='not'&&ctx.code==='GOREV.REDDETTIM'?'Düzeltme Gerekçesi':key==='revizyon_ver'?'Ayrı Revizyon Görevi Aç':key==='zaman_degeri'&&values.olcum==='SAAT'?'Tahmini Süre (Saat)':titleCase(FIELD_LABELS[key]??label(key));
  if(ctx.locked?.[key]&&v!=null)return `<label class="field"><span>${esc(name)}</span><input data-path="${esc(p)}" readonly value="${esc(key==='proje'?projectLabel(ctx.client.projects.find(x=>idOf(x)===v)??{ad:'Proje'}):ctx.client.people.find(x=>idOf(x)===v)?.ad??'Çalışan')}"></label>`;
  if(s.type==='object'||s.properties)return `<fieldset class="field-group full"><legend>${esc(name)}${req.has(key)?' *':''}</legend>${formHTML(s,values,ctx,p)}</fieldset>`;
  if(s.type==='array'&&s.items?.properties)return `<fieldset class="field-group full"><legend>${esc(name)}${req.has(key)?' *':''}</legend>${(v??[]).map((_,i)=>`<div class="repeat-row"><div class="repeat-head"><strong>${esc(name)} ${i+1}</strong><button type="button" class="text-button" data-remove="${esc(p)}" data-index="${i}">Sil</button></div>${formHTML(s.items,values,ctx,p+'.'+i)}</div>`).join('')}<button type="button" class="btn small" data-add="${esc(p)}">＋ Satır ekle</button></fieldset>`;
  const attrs=`data-path="${esc(p)}" ${req.has(key)?'data-required="true"':''}`;
  const actualType=Array.isArray(s.type)?s.type.find(x=>x!=='null'):s.type;
  if(actualType==='boolean')return `<label class="checkbox-field"><input type="checkbox" ${attrs} ${v===true?'checked':''}> <span>${esc(name)}</span></label>`;
  if(actualType==='array'){
   const options=refOptions(key,p,ctx,values);if(options!==null){const drafts=options.some(o=>o.draft);return `<fieldset class="choice-list full" data-choice-group="${esc(p)}"><legend>${esc(name)}${req.has(key)?' *':''}</legend><div class="choice-options">${options.length?options.map((o,i)=>`${i>0&&options[i-1].draft&&!o.draft?'<hr class="choice-divider" aria-hidden="true">':''}<label><input type="checkbox" data-multi-path="${esc(p)}" value="${esc(o.value)}" ${(v??[]).some(x=>(typeof x==='object'?'@row:'+(x.satir-1):x)===o.value)?'checked':''}><span>${esc(o.text)}</span></label>`).join(''):'<small>Seçilebilecek başka iş yok.</small>'}</div>${drafts?'<small class="choice-note">* Bu atamada hazırlanan, henüz atanmamış iş.</small>':''}</fieldset>`;}
   if(key==='calisma_gunleri'||key==='gunler')return `<fieldset class="field days"><legend>${esc(name)}</legend>${['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'].map((d,i)=>`<label><input type="checkbox" data-day-path="${esc(p)}" value="${i+1}" ${(v??[]).includes(i+1)?'checked':''}>${d}</label>`).join('')}</fieldset>`;
   return `<label class="field"><span>${esc(name)}${req.has(key)?' *':''}</span><input ${attrs} data-array="true" value="${esc((v??[]).map(x=>typeof x==='object'?'Satır '+(x.satir??''):x).join(', '))}" placeholder="Virgülle ayırın"></label>`;
  }
  let options=s.enum?.map(value=>({value,text:key==='anahtar'?(FIELD_LABELS[value]??label(value)):key==='eylem_kodu'?(OPERATIONS[value]?.title??label(value)):label(value)}))??refOptions(key,p,ctx,values);
  if(key==='tur'&&ctx.code==='IZIN.TALEP_ETTIM')options=LEAVE_TYPES;
  if(key==='nereye')options=[{value:'PROJE',text:'Proje İçi'},{value:'PROJE_DISI',text:'Proje dışı'}];
  if(key==='tur'&&!options&&!s.enum&&ctx.code==='BIRIM.TANIMLADIM')options=[{value:'ATOLYE',text:'Atölye'},{value:'MASA_BASI',text:'Masa başı'}];
  if(key==='tur'&&!options&&!s.enum&&ctx.code.includes('IS.'))options=[{value:'SURELI',text:'Süreli iş'},{value:'ANLIK',text:'Anlık işlem'}];
  if(options!==null&&options!==undefined){const combined=isWorkRecipient(ctx.code,key)||options.some(o=>o.value===v)||v==null?options:[{value:v,text:label(v)},...options];return `<label class="field"><span>${esc(name)}${req.has(key)?' *':''}</span><select ${attrs}><option value="">${s.uiNullOption?'Seçiniz':key==='etap'?'Etap Dışı':'Seçin'}</option>${s.uiNullOption?`<option value="@none" data-null-option ${v===null?'selected':''}>${esc(s.uiNullOption)}</option>`:''}${combined.map(o=>`<option value="${esc(o.value)}" ${v===o.value?'selected':''}>${esc(o.text)}</option>`).join('')}</select></label>`;}
  if(longFields.has(key))return `<label class="field full"><span>${esc(name)}${req.has(key)?' *':''}</span><textarea ${attrs} rows="3">${esc(v??'')}</textarea></label>`;
  const it=inputType(key,ctx.code,s),val=v??'';
  if(['date','time','datetime-local'].includes(it))return `<label class="field"><span>${esc(name)}${req.has(key)?' *':''}</span><span class="temporal-control"><input ${attrs} type="text" inputmode="numeric" data-temporal="${it}" value="${esc(displayTemporal(v,it))}" placeholder="${it==='date'?'GG.AA.YYYY':it==='time'?'Örnek: 09:30':'GG.AA.YYYY 09:30'}" autocomplete="off">${it==='date'?`<span class="calendar-picker" title="Takvimden Seç">${icon('calendar')}<input tabindex="-1" type="date" data-date-picker="${esc(p)}" value="${esc(validTemporal(v,'date')?v:'')}" aria-label="${esc(name)} için takvimden seç"></span>`:''}</span></label>`;
  return `<label class="field"><span>${esc(name)}${req.has(key)?' *':''}</span><input ${attrs} type="${it}" value="${esc(val)}" ${it==='number'?`step="${actualType==='integer'?'1':'any'}" ${s.minimum!=null?`min="${s.minimum}"`:''} ${s.maximum!=null?`max="${s.maximum}"`:''}`:''}></label>`;
 }).join('')}</div>`;}
 return '';
}

export function bindForm(container,getSchema,values,ctx,onChange=()=>{}) {
 function render(focusPath){
  const open=new Set([...container.querySelectorAll('details[open][data-form-section]')].map(d=>d.dataset.formSection));
  const focused=container.contains(document.activeElement)?document.activeElement.dataset.path:null;
  const dialog=container.closest('dialog'),scroll=dialog?.scrollTop;
  container.innerHTML=formHTML(getSchema(),values,ctx);
  ctx.afterRender?.(container);
  container.querySelectorAll('details[data-form-section]').forEach(d=>{d.open=open.has(d.dataset.formSection);});
  const focus=[...container.querySelectorAll('[data-path]')].find(e=>focusPath?e.dataset.path.startsWith(focusPath):e.dataset.path===focused);
  if(focus){for(let p=focus.parentElement;p&&p!==container;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;focus.focus({preventScroll:true});}
  if(dialog)dialog.scrollTop=scroll;
  if(focusPath)focus?.scrollIntoView({block:'nearest'});
container.querySelectorAll('[data-temporal]').forEach(bindTemporalInput);container.querySelectorAll('[data-date-picker]').forEach(p=>bindDatePicker(p.closest('.temporal-control').querySelector('[data-temporal]'),p));headingCase(container);}
 function change(e){const el=e.target,path=el.dataset.path;
  if(el.dataset.datePicker){if(validTemporal(el.value,'date')){setPath(values,el.dataset.datePicker,el.value);const text=[...container.querySelectorAll('[data-path]')].find(x=>x.dataset.path===el.dataset.datePicker);if(text)text.value=displayTemporal(el.value,'date');onChange();}return;}
  if(el.dataset.multiPath){const p=el.dataset.multiPath,old=getPath(values,p)??[],key=x=>typeof x==='object'?'@row:'+(x.satir-1):x;let next=old.filter(x=>key(x)!==el.value);if(el.checked)next.push(el.value.startsWith('@row:')?{satir:Number(el.value.slice(5))+1}:el.value);setPath(values,p,next);onChange();return;}
  if(el.dataset.dayPath){const p=el.dataset.dayPath,set=new Set(getPath(values,p)??[]);el.checked?set.add(Number(el.value)):set.delete(Number(el.value));setPath(values,p,[...set].sort());onChange();return;}
  if(!path||el.readOnly||el.type==='file')return;let v;
  if(el.type==='checkbox')v=el.checked;else if(el.multiple)v=[...el.selectedOptions].map(x=>x.value);else if(el.dataset.array)v=el.value.split(',').map(x=>x.trim()).filter(Boolean);else if(el.type==='number')v=el.value===''?undefined:Number(el.value);else v=el.value===''?undefined:el.value;
  if(el.tagName==='SELECT'&&el.selectedOptions[0]?.hasAttribute('data-null-option'))v=null;
  if(el.dataset.temporal)v=parseTemporal(el.value,el.dataset.temporal);
  if(Array.isArray(v))v=v.map(x=>String(x).startsWith('@row:')?{satir:Number(String(x).slice(5))+1}:x);
  setPath(values,path,v);const field=path.split('.').at(-1);if(field==='kisi'&&ctx.code.startsWith('GOREV.')){const parent=getPath(values,path.split('.').slice(0,-1).join('.'))??values;if(parent.onaylayan===v)delete parent.onaylayan;}if(field==='proje'){const prefix=path.split('.').slice(0,-1);setPath(values,[...prefix,'etap'].join('.'),undefined);}onChange();if(['anahtar','tur','proje','nereye','olcum','saat_belirle','onay_gerekli','revizyon_ver'].includes(field)||field==='kisi'&&ctx.code.startsWith('GOREV.'))render();
 }
 container.addEventListener('input',change);container.addEventListener('change',e=>{if(e.target.tagName==='SELECT'||e.target.dataset.datePicker)change(e);});
 container.addEventListener('click',e=>{if(e.target.dataset.datePicker){try{e.target.showPicker?.();}catch{}}const add=e.target.closest('[data-add]'),remove=e.target.closest('[data-remove]');if(add){const path=add.dataset.add,a=getPath(values,path)??[];a.push({});setPath(values,path,a);render(path+'.'+(a.length-1)+'.');onChange();}if(remove){const path=remove.dataset.remove,rows=getPath(values,path),index=Number(remove.dataset.index);rows.splice(index,1);render(rows.length?path+'.'+Math.min(index,rows.length-1)+'.':null);if(!rows.length)[...container.querySelectorAll('[data-add]')].find(b=>b.dataset.add===path)?.focus({preventScroll:true});onChange();}});
 render();return {render};
}

export async function openOperation(client,code,{record=null,refs={},defaults={},onDone,actingFor=null}={}){
 const op=OPERATIONS[code];if(!op)throw new Error('İşlem tanımlı değil');
 const values=structuredClone(defaults);
 if(code==='NESNE.ACTIM')await ensureDocumentType(client);
 const today=client.today;
 if(operationSchema(code,client.schemas,values).properties.gecerli_baslangic?.type?.includes('null'))values.gecerli_baslangic??=null;
 if(record){if(op.ref)values.hedef??=idOf(record);if(['KISI.DEGISTIRDIM','KISI.AYRILDI','KISI.YETKINLIK_TANIMLADIM','MAAS.GUNCELLEDIM'].includes(code))values.kisi??=idOf(record);if(code.startsWith('TEZGAH.'))values.tezgah??=idOf(record);}
 if(code==='KISI.DEGISTIRDIM'||code==='GOREV.DEGISTIRDIM'||code==='IS.DEGISTIRDIM'||code==='IS.BAGLANTI_DUZELTTIM'||code==='PROJE.DEGISTIRDIM'||code==='ETAP.DEGISTIRDIM'||code==='NESNE.GUNCELLEDIM')values.degisenler??={};
 if(code==='KISI.DEGISTIRDIM')values.gecerli_baslangic??=null;
 if(code==='MAAS.GUNCELLEDIM')values.gecerli_baslangic??=today;
 if(record&&values.degisenler){const allowed=operationSchema(code,client.schemas,values).properties.degisenler?.properties??{};for(const key of Object.keys(allowed))if(record[key]!==undefined&&key!=='gecerli_baslangic')values.degisenler[key]=structuredClone(record[key]);}
 const originalChanges=structuredClone(values.degisenler??{});
 if(code==='IZIN.TALEP_ETTIM'){values.kisi=client.person;values.baslangic??=today;values.bitis??=today;}
 if(code.startsWith('GUN_SONU.')){values.kisi??=record?.kisi??client.person;values.gun??=today;}
 if(code==='GOREV.REDDETTIM')values.revizyon_ver??=false;
 if(code==='IS.ATADIM'||code==='IS.PLANSIZ_TANIMLADIM')values.sira??=1;
 if(code==='PROJE.ACTIM'){values.sorumlu??=client.people.find(p=>p.roller?.includes('YONETICI')&&!p.roller.includes('YETKILI'))?.kimlik??client.person;values.baslangic_tarihi??=today;}
 if(code==='ETAP.TANIMLADIM'){values.baslangic??=today;values.bitis??=client.projects.find(p=>idOf(p)===values.proje)?.teslim_tarihi??today;values.hedef_saat??=0;values.sorumlu??=client.projects.find(p=>idOf(p)===values.proje)?.sorumlu??null;}
 if(code==='PLAN.ONAYLADIM')values.proje??=record?.proje??idOf(record);
 let reviewedPlan=code==='PLAN.ONAYLADIM'?(await client.read('PLAN',values.proje,{surumler:true},true)).deger:null;
 const schema=()=>{const s=operationSchema(code,client.schemas,values);if(reviewedPlan?.surumler?.length)s.required=[...new Set([...(s.required??[]),'gerekce'])];return s;};
 if(['PROJE.ACTIM','ETAP.TANIMLADIM'].includes(code)&&!client.context.sorumlu_adaylari?.[code]?.includes(values.sorumlu))values.sorumlu=client.person;
 if(code==='BIRIM.TANIMLADIM')values.basi??=null;
 const isOvertime=['EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM'].includes(code);
 const requiredTarget=op.target;
 const fixedTarget=!!record&&(projectOperations.has(code)||code.startsWith('GOREV.')||code.startsWith('IS.')||code==='NOT.YAZDIM');
 const locked=projectOperations.has(code)?{proje:!!defaults.proje,kisi:code==='PROJE.ERISIM_KALDIRDIM'&&!!defaults.kisi}:{};
 let target=record&&requiredTarget?idOf(record):null;
 const optionsForTarget=refs[requiredTarget]??[];
 const canAttach=['NOT.YAZDIM'].includes(code),canFiles=['NOT.YAZDIM','GOREV.TAMAMLADIM','NESNE.SURUM_EKLEDIM'].includes(code);
 const d=modal(op.title,`<form id="operation-form" novalidate><div class="form-error" role="alert"></div>${requiredTarget&&!fixedTarget?`<label class="field full"><span>${esc(label(requiredTarget))} *</span><select id="operation-target" data-path="_target"><option value="">Seçin</option>${(record?[record,...optionsForTarget.filter(x=>idOf(x)!==idOf(record))]:optionsForTarget).map(x=>`<option value="${esc(idOf(x))}" ${idOf(x)===target?'selected':''}>${esc(x.ad??x.islem??x.is_tanimi??idOf(x))}</option>`).join('')}</select></label>`:''}${canAttach?`<div class="form-grid" ${fixedTarget?'style="display:none"':''}><label class="field"><span>Notun bağlı olduğu tür</span><select id="note-kind"><option value="NESNE">Nesne / parça</option><option value="GOREV">Görev</option><option value="IS">Atölye işi</option><option value="PROJE">Proje</option></select></label><label class="field"><span>Bağlı nesne *</span><select id="note-target" data-path="_note"></select></label></div>`:''}${fixedTarget?`<div class="operation-context"><span>İlgili ${code.startsWith('GOREV.')||refs.GOREV?.some(r=>idOf(r)===idOf(record))?'Görev':refs.IS?.some(r=>idOf(r)===idOf(record))?'İş':kindLabel(record)}</span><h3>${esc(record.ad??record.islem??record.is_tanimi??record.kod??'Seçili İş')}</h3></div>`:''}${reviewedPlan?'<div id="plan-review-host">'+planReview(reviewedPlan)+'</div>':''}${code==='GOREV.TAMAMLADIM'?`<p class="notice">${esc(record?.is_tanimi||'Çalışmanızın sonucunu teslim edin.')}<br>${record?.onay_gerekli?'Teslimden sonra onay beklenecek.':'Teslimden sonra görev tamamlanacak.'}</p>`:''}${code==='GOREV.REDDETTIM'?'<p class="notice">Ayrı Revizyon Görevi seçilmezse aynı görev, gerekçenizle çalışana döner. Seçilirse ayrı bir görev açılır; asıl iş revizyon bitene kadar bekler.</p>':''}<div id="schema-fields"></div>${isOvertime?'<label class="field full"><span>İlgili İş *</span><select id="overtime-target" data-path="_overtime"><option value="">Önce çalışanı seçin</option></select></label><p class="notice">'+(code==='EK_MESAI.PLANLADIM'?'Gelecekte yapılacak ek mesaiyi planlayın.':'Son 7 gün içinde gerçekleşmiş ek mesaiyi onaylayın.')+'</p>':''}${canFiles?`<label class="field full file-field"><span>Dosya ve fotoğraflar${code==='NESNE.SURUM_EKLEDIM'||record?.dosya_gerekli?' *':''}</span><input id="operation-files" data-path="${code==='NESNE.SURUM_EKLEDIM'?'dosyalar':'_files'}" type="file" multiple><small>Dosya seçerek veya bu alana bırakarak ekleyebilirsiniz. İsteğe bağlıdır.</small></label>`:''}${code==='MAAS.GUNCELLEDIM'?'<div class="form-grid"><label class="field"><span>Maliyet türü</span><select id="cost-kind"><option value="MAAS_AYLIK">Aylık maaş</option><option value="SAAT_UCRETI">Tezgâh saat bedeli</option><option value="GENEL_GIDER_PAYI">Genel gider payı</option></select></label><label class="field"><span>Tutar (₺) *</span><input id="cost-amount" data-path="_amount" type="number" min="0" step="0.01" required></label></div>':''}<footer class="form-footer"><button type="button" class="btn" data-cancel>Vazgeç</button><button class="btn primary" type="submit">${esc(op.title)}</button></footer></form>`,{wide:true});
 const fileField=d.querySelector('.file-field');
 const ctx={client,code,refs,record,locked,costKind:'MAAS_AYLIK',afterRender:code==='GOREV.TAMAMLADIM'?container=>{container.querySelector('[data-path=gecikme_nedeni]')?.closest('.field').before(fileField);}:null};const root=d.querySelector('#schema-fields');
 function fillOvertime(){const select=d.querySelector('#overtime-target');if(!select)return;const previous=select.value;const targets=overtimeTargets(refs,values.kisi);select.innerHTML='<option value="">'+(targets.length?'İşi seçin':'Bu çalışana atanmış iş bulunamadı')+'</option>'+targets.map(r=>`<option value="${esc(r.tur+':'+r.kimlik)}">${esc(r.ad)}</option>`).join('');if(targets.some(r=>r.tur+':'+r.kimlik===previous))select.value=previous;}
 const form=bindForm(root,schema,values,ctx,fillOvertime);fillOvertime();
 for(const key of ['kisi','kisiler','kime','kimden'])if(isWorkRecipient(code,key)&&values[key]!=null){const options=refOptions(key,key,ctx,values),allowed=new Set(options.map(o=>o.value));if(Array.isArray(values[key]))values[key]=values[key].filter(id=>allowed.has(id));else if(!allowed.has(values[key]))delete values[key];}
 if(['IS.ATADIM','IS.DEVRETTIM'].includes(code))form.render();
 d.querySelector('#cost-kind')?.addEventListener('change',e=>{ctx.costKind=e.target.value;delete values.kisi;form.render();});
 d.querySelector('#operation-target')?.addEventListener('change',e=>{target=e.target.value;if(op.ref)values.hedef=target;});
 if(fileField){fileField.ondragover=e=>{e.preventDefault();fileField.classList.add('drop-over');};fileField.ondragleave=()=>fileField.classList.remove('drop-over');fileField.ondrop=e=>{e.preventDefault();fileField.classList.remove('drop-over');d.querySelector('#operation-files').files=e.dataTransfer.files;};}
 if(fileField&&(code==='NESNE.SURUM_EKLEDIM'||record?.dosya_gerekli))fileField.querySelector('small').textContent='Dosya seçebilir veya buraya bırakabilirsiniz. Teslimde en az bir dosya gereklidir.';
 d.querySelector('[data-cancel]').onclick=()=>d.close();
 function fillNote(){const kind=d.querySelector('#note-kind')?.value;if(!kind)return;const rows=kind==='PROJE'?client.projects:refs[kind]??[];d.querySelector('#note-target').innerHTML='<option value="">Seçin</option>'+rows.map(x=>`<option value="${esc(idOf(x))}" ${record&&idOf(x)===idOf(record)?'selected':''}>${esc(x.ad??x.islem??idOf(x))}</option>`).join('');}
 if(canAttach&&record){const kind=client.projects.some(x=>idOf(x)===idOf(record))?'PROJE':refs.GOREV?.some(x=>idOf(x)===idOf(record))?'GOREV':refs.IS?.some(x=>idOf(x)===idOf(record))?'IS':'NESNE';d.querySelector('#note-kind').value=kind;}
 d.querySelector('#note-kind')?.addEventListener('change',fillNote);fillNote();
 if(canAttach){const chooser=document.createElement('div');chooser.className='mention-chooser';chooser.hidden=true;root.after(chooser);root.addEventListener('input',e=>{if(e.target.dataset.path!=='metin')return;chooser.hidden=!/@[^\s@]*$/.test(e.target.value);if(!chooser.hidden)chooser.innerHTML='<strong>Birime İstek Bırak</strong>'+client.units.map(u=>`<button type="button" data-mention="${esc(idOf(u))}">@${esc(u.ad)}</button>`).join('');});chooser.onclick=e=>{const b=e.target.closest('[data-mention]');if(!b)return;const unit=client.units.find(u=>idOf(u)===b.dataset.mention);values.etiketler=[...new Set([...(values.etiketler??[]),idOf(unit)])];values.metin=(values.metin??'').replace(/@[^\s@]*$/,'@'+unit.ad+' ');form.render();chooser.hidden=true;root.querySelector('[data-path=metin]').focus();};}
 let unresolved=null,submitted=null;
 let busy=false;d.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 d.querySelector('form').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;const error=d.querySelector('.form-error'),submit=d.querySelector('[type=submit]');error.textContent='';submit.disabled=true;d.querySelector('[data-close]').disabled=true;d.querySelector('[data-cancel]').disabled=true;
  try{
  if(unresolved){submit.textContent='Sonuç doğrulanıyor…';const result=await client.retryManagement(unresolved);d.close();unresolved=null;try{await onDone?.(result,submitted);}catch{result.ekran_bekliyor=true;}toast(operationMessage(result),operationTone(result));return;}
  let g=cleanValue(values,operationSchema(code,client.schemas,values));
   if(code==='PROJE.KOD_DEGISTIRDIM'&&record?.ek)g.ek=record.ek;
   if(g.degisenler)g.degisenler=Object.fromEntries(Object.entries(g.degisenler).filter(([k,v])=>JSON.stringify(v)!==JSON.stringify(originalChanges[k])));
   if(code==='IS.DEGISTIRDIM'&&g.degisenler.onay_gerekli===true)g.degisenler.onay_beklet=values.degisenler.onay_beklet===true;
   if(code==='DURUS.BASLADI'&&g.kapsam?.includes('FIRMA'))g.kapsam='FIRMA';
   const files=[...(d.querySelector('#operation-files')?.files??[])];
   if(code==='NESNE.SURUM_EKLEDIM'&&files.length)g.dosyalar??=[];
   if(code==='GUN_SONU.ONAYLADIM'){for(const item of g.gunler?.length?g.gunler:[g]){const day=(await client.read('GUN',item.kisi,{gun:item.gun},true)).deger;item.ozet_surumu=day?.ozet_surumu??day?.surum;}}
   const validationSchema=schema();if(code==='GUN_SONU.ONAYLADIM')delete validationSchema.properties.ozet_surumu;if(code==='PROJE.KOD_DEGISTIRDIM')validationSchema.properties.ek=S;const issues=validationIssues(code==='NESNE.SURUM_EKLEDIM'&&files.length?{...g,dosyalar:[...(g.dosyalar??[]),'F-YUKLEME/1']}:g,validationSchema);showValidation(root,issues);const errors=issues.map(i=>i.message);
   if(requiredTarget&&!target){const message='İşlemin bağlı olduğu nesneyi seçin.';errors.unshift(message);issues.push({path:'_target',message});}
   if(code==='IS.ATADIM'&&!g.kisi&&!g.kisiler?.length){const message='İşi vereceğiniz çalışanı seçin.';errors.unshift(message);issues.push({path:'kisi',message});}
   if(record?.dosya_gerekli&&code==='GOREV.TAMAMLADIM'&&!files.length){const message='Bu görevin tesliminde dosya gerekli.';errors.unshift(message);issues.push({path:'_files',message});}
   if(g.degisenler&&!Object.keys(g.degisenler).length)errors.unshift('Değiştirmek istediğiniz bilgiyi doldurun.');
   const hs=requiredTarget?[{tur:requiredTarget,kimlik:target}]:[];
   if(isOvertime){const selected=d.querySelector('#overtime-target').value,match=overtimeTargets(refs,g.kisi).find(r=>r.tur+':'+r.kimlik===selected);if(!match){const message='Bu çalışanın ek mesai yapacağı işi seçin.';errors.unshift(message);issues.push({path:'_overtime',message});}else hs.push({tur:match.tur,kimlik:match.kimlik});}
   if(!issues.length&&code==='IZIN.TALEP_ETTIM')g=leavePayload(g,client.person);
   if(!issues.length&&(isOvertime||code==='IZIN.TALEP_ETTIM')){
    const start=Date.parse(isOvertime?`${g.tarih}T${g.baslangic}:00+03:00`:g.baslangic),end=Date.parse(isOvertime?`${g.tarih}T${g.bitis}:00+03:00`:g.bitis);
    if(!(start<end)){errors.push('Bitiş, başlangıçtan sonra olmalı.');issues.push({path:'bitis',message:'Bitiş, başlangıçtan sonra olmalı.'});}
    const now=Date.now()+(client.offset??0);
    if(code==='EK_MESAI.PLANLADIM'&&start<=now){const message='Planın başlangıcı şu andan sonra olmalı.';errors.push(message);issues.push({path:'baslangic',message});}
    if(code==='EK_MESAI.ONAYLADIM'&&(end>now||start<now-7*86400000)){const message='Gerçekleşen mesai, son 7 gün içinde ve bitmiş bir aralık olmalı.';errors.push(message);issues.push({path:end>now?'bitis':'tarih',message});}
   }
   if(canAttach){const kind=d.querySelector('#note-kind').value,id=d.querySelector('#note-target').value;if(!id){const message='Notun bağlı olduğu nesneyi seçin.';errors.unshift(message);issues.push({path:'_note',message});}else hs.push({tur:kind,kimlik:id});}
   if(code==='NESNE.SURUM_EKLEDIM'||code==='NESNE.SURUM_ONAYLADIM'||code==='NESNE.SURUM_GERI_CEKTIM')g.hedef=target;
   let sensitive=null;if(code==='MAAS.GUNCELLEDIM'){const amount=d.querySelector('#cost-amount').value;if(amount===''||!Number.isFinite(Number(amount))||Number(amount)<0){const message='Geçerli bir tutar girin.';errors.unshift(message);issues.push({path:'_amount',message});}sensitive={nesne_tur:client.people.some(x=>idOf(x)===g.kisi)?'KISI':'TEZGAH',nesne_kimlik:g.kisi,tur:d.querySelector('#cost-kind').value,tutar:amount,gecerli_baslangic:g.gecerli_baslangic??today};}
   if(projectOperations.has(code)&&!issues.length){
    const projects=(await client.read('PROJELER',null,{},true)).deger??[];
    const pid=g.proje??record?.proje??idOf(record);
    const stages=pid?arr((await client.read('ETAPLAR',pid,{},true)).deger):[];
    const plan=code==='PLAN.ONAYLADIM'?(await client.read('PLAN',pid,{surumler:true},true)).deger:{};
    if(reviewedPlan&&planStamp(plan)!==planStamp(reviewedPlan)){reviewedPlan=plan;d.querySelector('#plan-review-host').innerHTML=planReview(plan);form.render();throw new Error('Plan değişmiş. Güncellenen özeti inceleyip tekrar onaylayın.');}
    const tasks=code==='PROJE.KAPATTIM'?arr((await client.read('WEB_GOREVLER',null,{},true)).deger):[];
    const works=code==='PROJE.KAPATTIM'?arr((await client.read('WEB_ISLER',null,{},true)).deger):[];
    const more=projectIssues(code,g,{projects,record,stages,plan,tasks,works});issues.push(...more);errors.push(...more.map(i=>i.message));
   }
   showValidation(d,issues);
   if(errors.length)throw new Error([...new Set(errors)].join(' '));
   submit.disabled=true;submit.textContent='Lütfen bekleyin…';d.querySelector('[data-close]').disabled=true;d.querySelector('[data-cancel]').disabled=true;
   submitted=structuredClone(g);
   const result=await client.confirmed(code,g,hs,{files,sensitive,adina:code==='IS.SURE_EKLEDIM'?(actingFor??record?.kisi??g.kisi):null});
   d.close();toast(operationMessage(result),operationTone(result));try{await onDone?.(result,g);}catch{toast('İşlem kabul edildi. Ekranı yenileyerek son durumu görebilirsiniz.','info');}
  }catch(ex){
   if(ex.eventId)unresolved=ex.eventId;else if(unresolved&&ex.code&&ex.code!=='NETWORK'&&ex.code!=='UNRESOLVED')unresolved=null;
   if(ex.issues?.length){showValidation(d,ex.issues);error.textContent=ex.message;}
   else if(ex.code==='DURUM'&&isOvertime){const message='Saat aralığı çalışma takvimi, onaylı izin veya başka ek mesaiyle çakışıyor olabilir. Tarihi ve saatleri kontrol edin.';showValidation(d,[{path:'tarih',message},{path:'baslangic',message},{path:'bitis',message}]);error.textContent=message;}
   else if(ex.code==='DURUM'&&code==='IZIN.TALEP_ETTIM'){const message='İzin tarihlerini ve işe giriş tarihinizi kontrol edin. Geçmiş talep yalnız içinde bulunduğunuz hafta için yapılabilir.';showValidation(d,[{path:'baslangic',message},{path:'bitis',message}]);error.textContent=message;}
   else error.textContent=ex.message;error.scrollIntoView({block:'nearest'});submit.disabled=false;submit.textContent=unresolved?'Sonucu Doğrula':op.title;root.querySelectorAll('input,select,textarea').forEach(el=>{if(unresolved){el.dataset.beforeRetryDisabled??=String(el.disabled);el.disabled=true;}else if(el.dataset.beforeRetryDisabled){el.disabled=el.dataset.beforeRetryDisabled==='true';delete el.dataset.beforeRetryDisabled;}});d.querySelector('[data-close]').disabled=false;d.querySelector('[data-cancel]').disabled=false;}finally{busy=false;}
 };
 return d;
}

function kindLabel(record){return record?.proje?'Etap':'Proje';}
