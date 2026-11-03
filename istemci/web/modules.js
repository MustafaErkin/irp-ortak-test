import {Workflow} from './workflow.js';
import {esc,idOf,arr,button,panel,empty,errorBox,table,modal,toast,date,time,hours,badge,headingCase} from './ui.js';
import {UserError} from './client.js';
import {displayText} from './presentation.js';
import {editorTools} from './modul_ui.js';

// Tek oturum kullanılır. Modül erişim/yenileme anahtarı tutmaz; kişi değişince
// eski istek iptal edilir ve cevabı yeni kişinin ekranına dönemez.
export async function moduleRequest(client,path,{method='GET',body,signal,retry=true,responseType='json'}={}){
 if(client.config?.ortak_test)throw new UserError('Modüllerin uzaktan bağlantısı bu paylaşımda açık değil. Çekirdek testine devam edebilirsiniz.');
 const generation=client.generation,write=!['GET','HEAD'].includes(method);
 const valid=()=>{if(generation!==client.generation)throw new UserError('Çalışma kişisi değişti.','STALE_SESSION');};
 if(client.readonly)throw new UserError('Bu çalışma alanı çevrimiçi kullanılır.');
 if(client.session?.expires_at*1000<Date.now()+60000)await client.refreshSession();valid();
 if(!client.session?.access_token)throw new UserError('Çalışma alanına giriş yapın.');
 if(write&&client.writing)throw new UserError('Devam eden işlem tamamlanıyor.');
 const abort=new AbortController();client.requests.add(abort);
 const cancel=()=>abort.abort();signal?.addEventListener('abort',cancel,{once:true});
 if(signal?.aborted)cancel();
 const timer=setTimeout(cancel,45000);
 if(write){client.writing=true;client.emit('status');}
 let unauthorized=false;
 try{
  const response=await fetch(path,{method,headers:{Authorization:'Bearer '+client.session.access_token,...(body===undefined?{}:{'Content-Type':'application/json'})},
   body:body===undefined?undefined:JSON.stringify(body),signal:abort.signal,cache:'no-store'});
  valid();
  if(response.status===401&&retry){unauthorized=true;}
  else{
   if(response.ok&&responseType==='blob'){const value=await response.blob();valid();return value;}
   let value;try{value=await response.json();}catch{throw new UserError('Çalışma alanının yanıtı okunamadı.');}valid();
   if(!response.ok){const detail=(value?.hatalar??[]).map(x=>x.mesaj).filter(Boolean).slice(0,4).join(' ');throw new UserError(displayText((value?.mesaj??value?.message??'İşlem tamamlanamadı.')+(detail?' '+detail:'')),String(response.status));}
   return value;
  }
 }catch(error){valid();if(error instanceof UserError)throw error;if(abort.signal.aborted)throw new UserError('İşlem kesildi. Sonucu kontrol edip yeniden değerlendirin.');throw new UserError('Çalışma alanına ulaşılamıyor. Bağlantıyı kontrol edin.');}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);client.requests.delete(abort);if(write){client.writing=false;client.emit('status');}}
 if(unauthorized){await client.refreshSession();valid();return moduleRequest(client,path,{method,body,signal,retry:false,responseType});}
}

export class ModuleWorkspace extends Workflow{
 constructor(client){super(client);this.moduleDataListener=()=>{if(this.page==='modules')void this.refreshModuleRegistry();};client.addEventListener('data',this.moduleDataListener);}
 dispose(){this.moduleDisposed=true;this.c.removeEventListener('data',this.moduleDataListener);this.closeModule();super.dispose();}
 async refreshModuleRegistry(){
  if(this.moduleMetadataRequest)return;
  const generation=this.c.generation;
  this.moduleMetadataRequest=(async()=>{
   try{
    const rows=(await moduleRequest(this.c,'/irp/moduller')).moduller??[];
    if(this.moduleDisposed||generation!==this.c.generation||this.page!=='modules')return;
    this.moduleRows=rows;const row=rows.find(r=>r.yol===location.hash.split('/')[1])??null;
    this.moduleRow=row;
    if(!row){this.closeModule();super.render();}
   }catch{/* Bağlantı kesintisi doğrulanmış pasifleştirme değildir; eldeki form korunur. */}
  })().finally(()=>this.moduleMetadataRequest=null);
  await this.moduleMetadataRequest;
 }
 closeModule(){this.moduleAbort?.abort();this.moduleInstance?.dispose?.();this.moduleInstance=null;this.moduleCode=null;}
 async navigate(page){if(page!=='modules')this.closeModule();return super.navigate(page);}
 get title(){return this.page==='modules'&&this.moduleRow?this.moduleRow.ad:super.title;}
 async load(){
  if(this.page!=='modules')return super.load();
  const generation=this.c.generation;
  this.moduleError='';
  try{this.moduleRows=(await moduleRequest(this.c,'/irp/moduller')).moduller??[];}
  catch(error){this.moduleError=error.message;this.moduleRows=[];}
  if(generation!==this.c.generation)return;
  const slug=location.hash.split('/')[1];
  this.moduleRow=this.moduleRows.find(r=>r.yol===slug)||null;
  if(!this.moduleRow)this.closeModule();
  return super.load();
 }
 modules(){
  if(this.moduleError)return errorBox(this.moduleError);
  if(this.moduleRow)return `<div id="module-workspace" aria-live="polite">${empty('Çalışma Alanı Açılıyor','')}</div>`;
  return this.moduleRows?.length?`<div class="module-cards">${this.moduleRows.map(row=>`<section class="panel module-card"><div class="panel-body"><span class="eyebrow">İş Alanı</span><h2>${esc(row.ad)}</h2><p>Projenizin ilgili çalışmalarını aynı çalışma alanında yönetin.</p><a class="btn primary" href="#modules/${esc(row.yol)}">Çalışma Alanını Aç</a></div></section>`).join('')}</div>`:
   empty('Henüz Modül Devrede Değil','Devreye alınan iş alanları burada görünecek.');
 }
 filters(){return this.page==='modules'?'':super.filters();}
 render(loading=false){
  if(this.page==='modules'&&this.moduleInstance&&this.moduleCode===this.moduleRow?.kod&&document.querySelector('#module-workspace')?.isConnected&&!loading){
   this.moduleInstance.refresh?.(this.moduleContext());return;
  }
  super.render(loading);
  if(this.page==='modules'&&this.moduleRow&&!loading)void this.mountModule();
 }
 moduleContext(){return {kisi:structuredClone(this.c.me),kisiler:structuredClone(this.c.people),birimler:structuredClone(this.c.units),
   projeler:structuredClone(this.c.projects),proje:this.state.project,tarih:this.c.today,yonetici:this.c.manager,yetkili:this.c.admin};}
 async mountModule(){
  const row=this.moduleRow,root=document.querySelector('#module-workspace');if(!row||!root)return;
  this.closeModule();const abort=this.moduleAbort=new AbortController(),generation=this.c.generation;
  try{
   const page=await import('/moduller/'+encodeURIComponent(row.kod)+'/'+encodeURIComponent(row.ekran));
   if(abort.signal.aborted||generation!==this.c.generation||!root.isConnected)return;
   this.moduleCode=row.kod;
   const api=(path,options={})=>{
    if(!path.startsWith('/')||path.includes('..')||path.includes('://'))throw new UserError('İşlem yolu uygun değil.');
    return moduleRequest(this.c,'/irp/moduller/'+row.kod+'/api'+path,{...options,signal:abort.signal});
   };
   const sharedUi={esc,idOf,arr,button,panel,empty,errorBox,table,modal,toast,date,time,hours,badge,headingCase,
      ad:id=>this.name(id),gantt:rows=>this.gantt(rows)};
   const instance=await page.ac({kok:root,baglam:this.moduleContext(),istek:api,
    projeSec:id=>{if(!this.c.projects.some(p=>idOf(p)===id))return;this.state.project=id;},
    yenile:()=>this.c.refresh(),ui:{...sharedUi,editor:()=>editorTools(sharedUi)}});
   if(abort.signal.aborted||generation!==this.c.generation||!root.isConnected){instance?.dispose?.();return;}
   this.moduleInstance=instance;
  }catch(error){if(!abort.signal.aborted&&root.isConnected)root.innerHTML=errorBox(error.message??'Çalışma alanı açılamadı.');}
 }
}
