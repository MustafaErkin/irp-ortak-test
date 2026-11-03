import {ReadSchedule,RefreshSchedule} from './read_schedule.js';
import {idOf, isoDay, arr} from './ui.js';
import {navigationReads} from './navigation.js';

export const cacheKey = (veri,hedef=null,g={}) => JSON.stringify([veri,hedef,g]);
export const operationComplete = r => r?.islem_durumu==='TAMAMLANDI'&&!r.yerel&&!r.dosya_bekliyor&&!r.ekran_bekliyor;
export const operationTone = r => operationComplete(r)?false:['INCELEME_GEREKIYOR','GECERSIZ'].includes(r?.islem_durumu)?true:'info';
export function operationMessage(r,completed='İşlem tamamlandı.') {
 if(r?.yerel)return 'İşlem bu bilgisayarda saklandı. Bağlantı kurulunca gönderilecek.';
 if(r?.islem_durumu==='INCELEME_GEREKIYOR')return 'İşlem alındı ancak inceleme gerekiyor. Yetkili kişi Olaylar → İnceleme Bekleyenler bölümünden kontrol edebilir.';
 if(r?.islem_durumu==='GECERSIZ')return 'Bu işlem daha sonra geçersiz sayılmış. Güncel bilgileri kontrol edin.';
 if(r?.islem_durumu==='ZAMANI_BEKLIYOR')return 'İşlem alındı. Belirlenen zamanı geldiğinde uygulanacak.';
 if(r?.islem_durumu!=='TAMAMLANDI')return 'İşlem alındı; sonucu henüz doğrulanamadı. Yeniden göndermenize gerek yok, bilgiler güncellenecek.';
 if(r.dosya_bekliyor)return 'İşlem uygulandı. Dosya aktarımı bağlantı gelince tamamlanacak.';
 if(r.ekran_bekliyor)return 'İşlem uygulandı. Görünümün yenilenmesi bekleniyor.';
 return completed;
}
export class UserError extends Error {constructor(message,code='',issues=[]){super(message);this.code=code;this.issues=issues;}}
export function responseMessage(c) {
 const message=c?.mesaj??c?.alan_hatalari?.[0]?.message;
 if(message&&!/Nesnenin durumu bu işleme uygun değil/i.test(message))return String(message).slice(0,500);
 const map={BAYAT:'Bilgi yenilendi. İşlemi güncel bilgiyle tekrar değerlendirin.',DURUM:'İşlem uygulanamadı. Güncel bilgileri yeniden açıp kullanılabilen işlemleri kontrol edin.',YETKI:'Bu işlem için yetkiniz bulunmuyor.',HESAP_BEKLIYOR:'Önceki işlemler hâlâ hesaplanıyor. Bu işlem henüz gönderilmedi; pencereyi kapatmadan yeniden deneyebilirsiniz.',BICIM:'Formdaki bilgileri kontrol edin.',BAKIMDA:'Sistem bakımda. İşleminiz bu bilgisayarda bekliyor.'};
 return map[c?.kod] || map[c?.sonuc] || (c?.neden ? String(c.neden).replace(/^.*IRP\|[^|]+\|/,'').slice(0,220) : 'İşlem tamamlanamadı. Bilgileri kontrol edin.');
}
export function validateConfig(c) {
 let publicKey=typeof c?.supabase_anon==='string' && c.supabase_anon.startsWith('sb_publishable_');
 if(!publicKey && typeof c?.supabase_anon==='string') {try{publicKey=JSON.parse(atob(c.supabase_anon.split('.')[1].replaceAll('-','+').replaceAll('_','/'))).role==='anon';}catch{}}
 let u;try{u=new URL(c.supabase_url);}catch{}
 if(!publicKey || !u || (u.protocol!=='https:' && !['localhost','127.0.0.1'].includes(u.hostname))) throw new UserError('Bağlantı ayarı okunamadı. Uygulama ayarını kontrol edin.');
 return c;
}

export class BrowserStore {
 constructor(db){this.db=db;}
 static async open(name='irp-is-web-v1') {
  const db=await new Promise((resolve,reject)=>{const r=indexedDB.open(name,1);r.onupgradeneeded=()=>r.result.createObjectStore('entries');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(new UserError('Tarayıcıdaki kalıcı depo açılamadı.'));});return new BrowserStore(db);
 }
 async get(key) {return new Promise((resolve,reject)=>{const t=this.db.transaction('entries','readonly'),r=t.objectStore('entries').get(key);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(new UserError('Kalıcı depo okunamadı.'));});}
 async put(key,value,expected,entries=[]) {return new Promise((resolve,reject)=>{const t=this.db.transaction('entries','readwrite'),s=t.objectStore('entries');let conflict=false;const write=()=>{s.put(value,key);for(const [k,v] of entries)s.put(v,k);};
  if(expected!==undefined){const r=s.get(key);r.onsuccess=()=>{if((r.result?.revision??0)!==expected){conflict=true;t.abort();}else write();};}else write();
  t.oncomplete=()=>resolve(value);t.onabort=t.onerror=()=>reject(new UserError(conflict?'Bu çalışma alanı başka sekmede değişti. Yenileyip tekrar deneyin.':'İşlem bu bilgisayara yazılamadı. Gönderilmedi.'));
 });}
 async remove(key){return new Promise((resolve,reject)=>{const t=this.db.transaction('entries','readwrite');t.objectStore('entries').delete(key);t.oncomplete=resolve;t.onerror=reject;});}
}

export class IrpClient extends EventTarget {
 constructor(store,schemas,config={},sample=null) {
  super();this.readSchedule=new ReadSchedule(2);this.refreshSchedule=new RefreshSchedule();this.store=store;this.schemas=schemas;this.config=config;this.sample=sample;this.readonly=!!sample;this.cache=new Map();this.readVersions=new Map();this.session=null;this.person='';this.letter=null;this.online=navigator.onLine;this.subscriptions=new Map();this.queue=Promise.resolve();this.refreshing=null;this.delay=2000;this.files=[];this.signals=null;this.context={};this.pending=0;this.visible=[];this.generation=0;this.requests=new Set();this.writing=false;
 }
 emit(kind,detail={}){this.dispatchEvent(new CustomEvent(kind,{detail}));}
 get today(){return this.sample?.gosterim?.an?.slice(0,10) ?? isoDay(new Date(Date.now()+(this.offset??0)));}
 get people(){return arr(this.cached('KISILER'));}
 get units(){return arr(this.cached('BIRIMLER'));}
 get projects(){return arr(this.cached('PROJELER'));}
 get me(){return this.people.find(x=>idOf(x)===this.person)??{};}
 get roles(){return this.me.roller??[];}
 get manager(){return this.roles.some(x=>['YETKILI','YONETICI','EKIP_LIDERI'].includes(x)) || this.context.yonetilen_birimler?.length>0;}
 get admin(){return this.roles.includes('YETKILI');}
 cached(veri,hedef=null,g={}){return this.cache.get(cacheKey(veri,hedef,g))?.deger;}
 serial(fn){const next=this.queue.then(fn);this.queue=next.catch(()=>{});return next;}
 async core(q){
  if(typeof globalThis.irpCoreCall!=='function') throw new UserError('İstemci çekirdeği yüklenemedi. Sayfayı yenileyin.');
  const r=JSON.parse(await globalThis.irpCoreCall(JSON.stringify(q)));if(!r.ok)throw new UserError(r.error);return r;
 }
 async initCore(state){await this.core({op:'init',kisi:this.person,harf:this.letter,veri:state,semalar:this.schemas});}
 async durable(fn){
  const person=this.person,generation=this.generation;const valid=()=>{if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');};
  const run=async()=>{valid();const key='device:'+person,record=await this.store.get(key)??{revision:0};valid();await this.initCore(record.state);const r=await fn();valid();await this.store.put(key,{state:r.state,revision:record.revision+1},record.revision,r.entries??[]);this.pending=Object.values(r.state.gunluk??{}).filter(x=>x.durum==='BEKLIYOR').length;this.emit('status');return r.value;};
  return this.serial(()=>navigator.locks?navigator.locks.request('irp-device:'+person,run):run());
 }
 async request(path,{body,method='POST',auth=true,timeout=15000,headers={},retryAuth=true}={}) {
  const generation=this.generation;
  if(auth && this.session && this.session.expires_at*1000<Date.now()+60000) await this.refreshSession();
  if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
  const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),timeout);this.requests.add(abort);
  try {
   const res=await fetch(this.config.supabase_url.replace(/\/$/,'')+path,{method,body:body===undefined?undefined:JSON.stringify(body),headers:{apikey:this.config.supabase_anon,...(auth?{Authorization:'Bearer '+this.session?.access_token}:{}),...(body===undefined?{}:{'Content-Type':'application/json'}),...headers},signal:abort.signal,cache:'no-store'});
   if(res.status===401 && auth && retryAuth){await this.refreshSession();return this.request(path,{body,method,auth,timeout,headers,retryAuth:false});}
   const text=await res.text();if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');let value;try{value=text?JSON.parse(text):null;}catch{throw new UserError('Sunucunun cevabı okunamadı.');}
   if(!res.ok){if(path==='/rest/v1/rpc/oku'&&value?.code==='57014')throw new UserError('Bilgiler zamanında alınamadı. Biraz sonra sayfayı yeniden açın.','READ_TIMEOUT');const msg=String(value?.message??value?.error_description??'');if(msg.includes('IRP|'))throw new UserError(responseMessage({kod:msg.split('IRP|')[1]?.split('|')[0],neden:msg}));throw new UserError(auth?'Sunucudan başarılı yanıt alınamadı.':'Giriş yapılamadı. Çalışan kodunu ve şifreyi kontrol edin.',String(res.status));}
   const wasOnline=this.online;this.online=navigator.onLine;if(wasOnline!==this.online)this.emit('status');return value;
  } catch(e){if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');if(e instanceof UserError)throw e;this.online=false;this.emit('status');throw new UserError('Bağlantı kurulamadı. Gönderilmeyen işlemler bu bilgisayarda korunuyor.','NETWORK');}finally{clearTimeout(timer);this.requests.delete(abort);}
 }
 async rpc(name,body){const value=await this.request('/rest/v1/rpc/'+name,{body});if(value?.hesap){this.calculating=value.hesap!=='GUNCEL';clearTimeout(this.calculationTimer);if(this.calculating)this.calculationTimer=setTimeout(()=>this.refresh().catch(()=>{}),5000);this.emit('status');}return value;}
 async saveSession(s){this.session={access_token:s.access_token,refresh_token:s.refresh_token,expires_at:s.expires_at??Math.floor(Date.now()/1000)+(s.expires_in??3600)};if(this.signals){this.signals.session=this.session;this.signals.close();this.signals=null;this.signalKey=null;}await this.store.put('session',{person:this.person,letter:this.letter,session:this.session,scenario:this.config.senaryo??null});if(this.context?.yonetilen_birimler)this.listen();}
 async refreshSession(){if(this.refreshing)return this.refreshing;this.refreshing=this.request('/auth/v1/token?grant_type=refresh_token',{body:{refresh_token:this.session.refresh_token},auth:false}).then(s=>this.saveSession(s)).finally(()=>{this.refreshing=null;});return this.refreshing;}
 async signIn(person,password){
  if(!navigator.onLine)throw new UserError('Giriş ve kişi değişimi için bağlantı gerekiyor.','NETWORK');
  if(this.writing||this.flushing||this.pending)throw new UserError('Önce devam eden işlemin tamamlanmasını bekleyin.');
  const nextPerson=person.trim().toUpperCase();
  // Başarısız giriş, açık kişinin çalışma alanını ve oturumunu değiştirmez.
  const session=await this.request('/auth/v1/token?grant_type=password',{auth:false,body:{email:nextPerson.toLowerCase()+'@calisan.irp',password}});
  if(this.writing||this.flushing||this.pending)throw new UserError('Önce devam eden işlemin tamamlanmasını bekleyin.');
  this.generation++;for(const r of this.requests)r.abort();this.requests.clear();this.signals?.close();this.signals=null;this.signalKey=null;clearTimeout(this.retryTimer);clearTimeout(this.calculationTimer);this.calculating=false;this.refreshing=null;this.cache.clear();this.context={};this.visible=[];
  this.person=nextPerson;await this.saveSession(session);await this.connect();
 }
 async restore(){
  if(this.readonly){this.person='K001';const fixture=this.sample.anlar.gosterim.K001;for(const q of fixture.okumalar)this.cache.set(cacheKey(q.veri,q.hedef,q.g??{}),q.cevap);this.context={};this.emit('ready');return true;}
  const saved=await this.store.get('session');if(!saved)return false;
  this.person=saved.person;this.letter=saved.letter;this.session=saved.session;
  try{await this.connect();}catch(e){
   if(e.code!=='NETWORK')return false;
   const cache=await this.store.get('cache:'+this.person);if(!cache)return false;this.cache=new Map(cache);this.context=this.cached('WEB_BAGLAM')??{};const device=await this.store.get('device:'+this.person);this.pending=Object.values(device?.state?.gunluk??{}).filter(x=>x.durum==='BEKLIYOR').length;this.emit('ready');
  }
  return true;
 }
 async connect(){
  let install=await this.store.get('installation');if(!install){install=crypto.randomUUID();await this.store.put('installation',install);}
  this.deviceKey='MAS-WEB-'+install+'-'+this.person;
  this.letter=await this.rpc('cihaz_kaydol',{cihaz:this.deviceKey});await this.saveSession(this.session);
  const t0=new Date().toISOString(),server=await this.rpc('simdi',{}),t1=new Date().toISOString();this.offset=new Date(server).getTime()-(Date.parse(t0)+Date.parse(t1))/2;
  await this.rpc('cihaz_esitle',{cihaz:this.deviceKey});
  const ids=(await this.read('BUGUNKU_KIMLIKLER',this.letter,{},true)).deger;
  await this.durable(()=>this.core({op:'sync',kimlikler:ids??[],t0,sunucu:server,t1}));
  await this.base();this.listen();this.emit('ready');void this.flush();
 }
 async base(){
  const generation=this.generation;const results=await Promise.allSettled([...['KISILER','BIRIMLER','PROJELER','KODLAR','WEB_BAGLAM'].map(k=>[k]),...navigationReads(this.person)].map(([v,h=null,g={}])=>this.read(v,h,g,true)));
  if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
  const failed=results.slice(0,5).find(r=>r.status==='rejected');if(failed)throw failed.reason;
  this.context=this.cached('WEB_BAGLAM')??{};await this.persistCache();
 }
 async persistCache(){if(!this.readonly)await this.store.put('cache:'+this.person,[...this.cache]);}
 async read(veri,hedef=null,g={},force=false){
  const generation=this.generation,key=cacheKey(veri,hedef,g);
  if(this.readonly){const exact=this.cache.get(key);if(exact)return exact;
   return {deger:null,hesap:'GUNCEL',hesap_ani:this.sample.gosterim.an,ornek_yok:true};
  }
  const old=this.cache.get(key);if(!force && old && Date.now()-(old.fetched??0)<15000)return old;
  if(!navigator.onLine && old)return old;
  const sequence=(this.readVersions.get(key)??0)+1;this.readVersions.set(key,sequence);const r=await this.readSchedule.run(()=>{if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');return this.rpc('oku',{veri,hedef,g});});if(veri==='TELEFON'&&r.deger){const screen=await this.durable(()=>this.core({op:'screen',hal:r.deger.son_hal,isler:r.deger.isler,liste:r.deger.liste}));r.deger={...r.deger,son_hal:screen.son_hal,kapilar:screen.kapilar};}if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');if(this.readVersions.get(key)!==sequence&&this.cache.has(key))return this.cache.get(key);r.fetched=Date.now();this.cache.set(key,r);return r;
 }
 async pageReads(reads){const generation=this.generation;this.visible=reads;const rs=await Promise.allSettled(reads.map(([v,h=null,g={}])=>this.read(v,h,g,true)));if(generation===this.generation)await this.persistCache();return rs.map((r,i)=>r.status==='fulfilled'?{...r.value,veri:reads[i][0],hedef:reads[i][1]}:{veri:reads[i][0],hedef:reads[i][1],error:r.reason.message});}
 async refresh(){
  if(!this.person)return;const generation=this.generation;
  return this.refreshSchedule.run(async()=>{
   if(generation!==this.generation||!this.person)return;
   await this.base();if(generation!==this.generation)return;
   const data=await this.pageReads(this.visible);if(generation!==this.generation)return;
   this.emit('data',{data});if(data.some(r=>r.error))throw new UserError('Bazı bilgiler yenilenemedi. Son okunan bilgiler gösteriliyor.','REFRESH');
  });
 }
 listen(extra=[]){
  if(this.readonly)return;
  const channels=new Set(['kisi:'+this.person,'firma',...(this.context.yonetilen_birimler??[]).map(b=>'birim:'+b),...extra]);
  if(this.signals && [...channels].join('|')===this.signalKey)return;
  this.signals?.close();this.signalKey=[...channels].join('|');this.signals=new Signals(this.config,this.session,channels,()=>{clearTimeout(this.debounce);this.debounce=setTimeout(()=>this.refresh().catch(()=>{}),300);},online=>{this.signalsOnline=online;this.emit('status');});
 }
 async resolveTargets(targets,code,g,expected={}){
  const all=targets.map(x=>({...x}));
  const lists=(await this.core({op:'lists',kod:code,girdiler:g})).value;
  for(const person of lists){if(!all.some(h=>h.tur==='LISTE'&&h.kimlik===person))all.push({tur:'LISTE',kimlik:person});}
  for(const h of all){const r=await this.read(h.tur,h.kimlik,{},true);h.surum=r.deger?.surum;const prior=expected[h.tur+':'+h.kimlik];if(prior!=null&&JSON.stringify(prior)!==JSON.stringify(h.surum))throw new UserError('İş veya sıra değişmiş. Güncel sırayı inceleyip tekrar onaylayın.','STALE_PREVIEW');if(h.surum==null)throw new UserError('Seçili nesne okunamadı. Listeyi yenileyin.');}
  return all;
 }
 async write(...args){if(this.writing)throw new UserError('Devam eden işlem tamamlanıyor.');this.writing=true;this.emit('status');try{return await this._write(...args);}finally{this.writing=false;this.emit('status');}}
 async _write(code,g={},targets=[],{adina=null,files=[],sensitive=null,expectedTargets={}}={}){
  if(this.readonly)throw new UserError('Örnek veri yalnızca görüntülenir. İşlem için canlı çalışma alanına geçin.');
  const witness=this.schemas[code]?.sinif==='TANIKLIK';if(!witness&&(!this.online||!navigator.onLine))throw new UserError('Bu işlem için bağlantı gerekiyor.');
  if(!witness){const journal=(await this.store.get('device:'+this.person))?.state?.gunluk??{};
   if(Object.values(journal).some(x=>x.durum==='GONDERILEMEDI'))throw new UserError('Önceki işlemin sonucu henüz doğrulanmadı. Olaylar → Bu Bilgisayarın İşlemleri bölümündeki Aynı İşlemi Yeniden Gönder düğmesini kullanın.','UNRESOLVED');
  }
  // Tazelik, bağlı nesneleri gerçekten okumaya başladığımız andan ölçülür.
  const readAt=new Date(Date.now()+(this.offset??0)).toISOString();
  let hs=targets;
  if(!witness)hs=await this.resolveTargets(targets,code,g,expectedTargets);
  let phone={son_hal:{},isler:{},liste:[]};
  try{phone=(await this.read('TELEFON',null,{},!witness)).deger??phone;}catch(e){if(!witness)throw e;}
  const descriptors=[];
  for(let i=0;i<files.length;i++){const file=files[i],bytes=await file.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');descriptors.push({ad:file.name,boyut:file.size,tur:file.type||'application/octet-stream',parmak_izi:hash,dosya_kimligi:''});}
  const event=await this.durable(async()=>{
   const r=await this.core({op:'prepare',kod:code,girdiler:g,hedefler:hs,adina,hal:{...phone.son_hal,son_hesap_ani:phone.son_hal?.son_hesap_ani??readAt},isler:phone.isler,liste:phone.liste,baglanti:this.online,okuma_ani:readAt,sabit_mola:phone.son_hal?.durum==='SABIT_MOLADA'});
   descriptors.forEach((d,i)=>d.dosya_kimligi=`F-${r.value.olay_kimligi}/${i+1}`);
   r.value.kanit=descriptors;
   if(code==='NESNE.SURUM_EKLEDIM')r.value.girdiler.dosyalar=[...(g.dosyalar??[]),...descriptors.map(x=>x.dosya_kimligi)];
   if(code==='KAYIT.GECERSIZ_SAYDIM')r.value.duzelttigi_olay=g.hedef;
   r.state.gunluk[r.value.olay_kimligi].olay=r.value;
   if(sensitive)r.state.gunluk[r.value.olay_kimligi].hassas_tur=sensitive.tur;
   if(files.length)r.entries=[['files:'+r.value.olay_kimligi,files]];
   return r;
  });
  // Olay ve dosya baytları aynı kalıcı işlemde yazıldı; şimdi gönderilebilir.
  if(witness){void this.flush();return {sonuc:'BASARILI',yerel:true,olay:event};}
  let result;
  try{try{result=await this.rpc('olay_ekle',{olay:event,hassas_ek:sensitive});}catch(e){if(e.code!=='NETWORK')throw e;result=await this.rpc('olay_ekle',{olay:event,hassas_ek:sensitive});}
   const deadline=Date.now()+12000;
   while(result.kod==='HESAP_BEKLIYOR'&&/^(PROJE|ETAP|PLAN|IS)\./.test(code)&&Date.now()<deadline){await new Promise(r=>setTimeout(r,750));result=await this.rpc('olay_ekle',{olay:event,hassas_ek:sensitive});}
  }
  catch(e){await this.mark(event.olay_kimligi,{sonuc:'BAGLANTI_YOK'},'GONDERILEMEDI');const error=new UserError('İşlemin sonucu alınamadı; kabul edilmiş olabilir. Sonucu Doğrula düğmesi aynı işlemin sonucunu kontrol eder.','UNRESOLVED');error.eventId=event.olay_kimligi;throw error;}
  await this.mark(event.olay_kimligi,result,result.sonuc==='BASARILI'?'GONDERILDI':'RED');
  if(result.sonuc!=='BASARILI')throw new UserError(responseMessage(result),result.kod,result.alan_hatalari??[]);
  return this.afterAccepted(result,event);
 }
 async afterAccepted(result,event){
  const generation=this.generation;let filesPending=false,refreshPending=false;
  // Kabul, yayımlanmış işlem sonucu, ek dosya ve görünüm ayrı aşamalardır.
  const receipt=await this.waitForPublication(event.olay_kimligi);
  try{await this.uploadFiles(event.olay_kimligi);}catch{filesPending=true;}
  if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
  try{await this.refresh();}catch{refreshPending=true;}
  if(generation===this.generation&&(filesPending||refreshPending)){
   this.emit('warning',{message:filesPending?'İşlem kabul edildi. Dosyanın aktarımı bekliyor.':'İşlem kabul edildi. Ekran bilgisi yenileniyor.'});
   clearTimeout(this.retryTimer);this.retryTimer=setTimeout(()=>{if(generation===this.generation)void this.flush();},this.delay);
  }
  if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
  return {...result,olay:event,islem_durumu:receipt.durum,yayin_ani:receipt.yayin_ani,dosya_bekliyor:filesPending,ekran_bekliyor:refreshPending};
 }
 async waitForPublication(id,{timeout=15000,interval=500}={}){
  const generation=this.generation,deadline=Date.now()+timeout;
  do{
   if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
   let r;
   try{r=await this.request('/rest/v1/rpc/islem_sonucu',{body:{olay_kimligi:id},timeout:Math.max(1,Math.min(5000,deadline-Date.now()))});}
   catch(e){if(e.code==='STALE_SESSION')throw e;return {durum:'DOGRULANAMADI'};}
   if(generation!==this.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');
   if(['TAMAMLANDI','INCELEME_GEREKIYOR','GECERSIZ','ZAMANI_BEKLIYOR'].includes(r?.durum))return r;
   if(r?.durum!=='BEKLIYOR')return {durum:'DOGRULANAMADI'};
   this.calculating=true;this.emit('status');
   if(Date.now()>=deadline)break;
   await new Promise(resolve=>setTimeout(resolve,Math.min(interval,deadline-Date.now())));
  }while(Date.now()<deadline);
  return {durum:'BEKLIYOR'};
 }
 async retryManagement(id,sensitive=null){
  if(this.writing||!navigator.onLine)throw new UserError('Bu işlem için bağlantı ve boş işlem sırası gerekiyor.');
  this.online=true;
  this.writing=true;this.emit('status');try{
   const journal=await this.store.get('device:'+this.person),entry=journal?.state?.gunluk?.[id];
   if(!entry||entry.durum!=='GONDERILEMEDI')throw new UserError('Bu işlem yeniden gönderilecek durumda değil.');
   if(entry.hassas_tur&&!sensitive)throw new UserError('Tutarı yeniden girin. Tutar bu bilgisayarda tutulmaz.');
   const result=await this.rpc('olay_ekle',{olay:entry.olay,hassas_ek:sensitive});
   await this.mark(id,result,result.sonuc==='BASARILI'?'GONDERILDI':'RED');
   if(result.sonuc!=='BASARILI')throw new UserError(responseMessage(result),result.kod,result.alan_hatalari??[]);
   return this.afterAccepted(result,entry.olay);
  }finally{this.writing=false;this.emit('status');}
 }
 async mark(id,result,status){return this.durable(()=>this.core({op:'result',kimlik:id,sonuc:result,durum:status}));}
 async confirmed(code,g={},targets=[],options={}){
  const result=await this.write(code,g,targets,options);if(!result.yerel||!this.online)return result;
  const id=result.olay.olay_kimligi,until=Date.now()+30000;
  while(Date.now()<until){await this.flush();let entry=(await this.store.get('device:'+this.person))?.state?.gunluk?.[id];if(entry?.durum==='GONDERILDI'){return this.afterAccepted(entry.sonuc,result.olay);}if(entry&&entry.durum!=='BEKLIYOR')throw new UserError(responseMessage(entry.sonuc));if(!this.online)throw new UserError('İşlem bu bilgisayarda bekliyor. Bağlantı kurulunca gönderilecek.','NETWORK');await new Promise(r=>setTimeout(r,150));}
  throw new UserError('İşlem gönderim kuyruğunda bekliyor. Durum güncellendiğinde devam edin.');
 }
 async flush(){
  if(this.readonly||!this.session)return;if(this.flushing)return this.flushPromise;
  this.flushing=true;
  const run=(async()=>{try{
   const record=await this.store.get('device:'+this.person),journal=Object.values(record?.state?.gunluk??{}).sort((a,b)=>(a.olay.oldugu_an+a.olay.olay_kimligi).localeCompare(b.olay.oldugu_an+b.olay.olay_kimligi));
   for(const x of journal){if(x.durum==='BEKLIYOR'){const r=await this.rpc('olay_ekle',{olay:x.olay,hassas_ek:null});if(r.sonuc==='BAKIMDA')throw new UserError(responseMessage(r),'NETWORK');await this.mark(x.olay.olay_kimligi,r,r.sonuc==='BASARILI'?'GONDERILDI':'HATA');if(r.sonuc!=='BASARILI')this.emit('warning',{message:responseMessage(r)});}
    if((await this.store.get('device:'+this.person))?.state?.gunluk?.[x.olay.olay_kimligi]?.durum==='GONDERILDI')await this.uploadFiles(x.olay.olay_kimligi);
   }
   this.delay=2000;await this.refresh();
  }catch(e){clearTimeout(this.retryTimer);this.retryTimer=setTimeout(()=>this.flush(),this.delay);this.delay=Math.min(this.delay*2,60000);this.emit('warning',{message:e.message});}
  finally{this.flushing=false;this.emit('status');}})();
  this.flushPromise=run;
  try{return await run;}finally{if(this.flushPromise===run)this.flushPromise=null;}
 }

 async uploadFiles(id){const files=await this.store.get('files:'+id);if(!files?.length)return;for(let i=0;i<files.length;i++){
  const f=files[i],path=id+'/'+(i+1)+'-'+f.name;
  const res=await fetch(this.config.supabase_url+'/storage/v1/object/kanitlar/'+path.split('/').map(encodeURIComponent).join('/'),{method:'POST',headers:{apikey:this.config.supabase_anon,Authorization:'Bearer '+this.session.access_token,'Content-Type':f.type||'application/octet-stream','x-upsert':'false'},body:f});
  if(!res.ok&&res.status!==409)throw new UserError('Dosya yüklemesi bekliyor. Bağlantı gelince yeniden denenecek.','NETWORK');
 }await this.store.remove('files:'+id);}
 async fileUrl(id){const r=await this.read('DOSYA',id,{},true);const d=r.deger;if(!d)throw new UserError('Dosya bulunamadı veya erişiminiz yok.');const name=d.ad??'dosya',path=d.yol??`${d.olay??id.split('/')[0].replace(/^F-/,'')}/${id.split('/').pop()}-${name}`;const s=await this.request('/storage/v1/object/sign/kanitlar/'+path.split('/').map(encodeURIComponent).join('/'),{body:{expiresIn:120}});return this.config.supabase_url+'/storage/v1'+s.signedURL;}
 async journal(){return Object.values((await this.store.get('device:'+this.person))?.state?.gunluk??{}).reverse();}
 async signOut(){if(this.writing||this.flushing||this.pending)throw new UserError('Önce devam eden işlemin tamamlanmasını bekleyin.');this.generation++;for(const r of this.requests)r.abort();this.requests.clear();this.signals?.close();clearTimeout(this.retryTimer);clearTimeout(this.calculationTimer);await this.store.remove('session');this.session=null;this.person='';this.cache.clear();this.context={};this.emit('signedout');}
}

class Signals {
 constructor(config,session,channels,changed,status){Object.assign(this,{config,session,channels,changed,status});this.closed=false;this.delay=2000;this.connect();}
 connect(){if(this.closed)return;let url=new URL(this.config.supabase_url);url.protocol=url.protocol==='https:'?'wss:':'ws:';url.pathname='/realtime/v1/websocket';url.search=new URLSearchParams({apikey:this.config.supabase_anon,vsn:'1.0.0'});const ws=this.ws=new WebSocket(url);let ref=0;
  const send=(topic,event,payload,join_ref=null)=>{if(ws.readyState===1)ws.send(JSON.stringify({topic,event,payload,ref:String(++ref),join_ref}));};
  ws.onopen=()=>{for(const channel of this.channels){const topic='realtime:irp-web-'+channel;send(topic,'phx_join',{config:{broadcast:{ack:false,self:false},presence:{key:''},postgres_changes:[{event:'INSERT',schema:'public',table:'degisim_sinyalleri',filter:'kanal=eq.'+channel}],private:false},access_token:this.session.access_token},String(ref+1));}this.heartbeat=setInterval(()=>send('phoenix','heartbeat',{}),25000);};
  ws.onmessage=e=>{let m;try{m=JSON.parse(e.data);}catch{return;}if(m.event==='phx_reply'&&m.payload?.status==='ok'&&m.topic!=='phoenix'){this.delay=2000;this.status(true);this.changed();}if(m.event==='postgres_changes')this.changed();if(m.event==='phx_error'||m.event==='phx_close'||m.event==='phx_reply'&&m.payload?.status==='error')ws.close();};
  ws.onerror=()=>ws.close();ws.onclose=()=>{clearInterval(this.heartbeat);if(this.closed)return;this.status(false);this.retry=setTimeout(()=>this.connect(),this.delay);this.delay=Math.min(60000,this.delay*2);};
 }
 close(){this.closed=true;clearTimeout(this.retry);clearInterval(this.heartbeat);this.ws?.close();}
}
