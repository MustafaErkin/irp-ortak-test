import {workshopView,bindWorkshop,openWorkMove,openWorkDefinition,inspectWork,workDialog} from './workshop.js';
import {workActionAllowed,teamMembers} from './workshop_model.js';
import {operationComplete,operationMessage,operationTone} from './client.js';
import {ErpWorkspace} from './erp.js';
import {taskGroups,taskDetail,fileList} from './office.js';
import {OPERATIONS} from './actions.js';
import {dailySummary} from './daily_summary.js';
import {esc,idOf,arr,money,hours,date,time,badge,button,panel,table,modal,toast,headingCase} from './ui.js';

export class Workflow extends ErpWorkspace {
 render(loading=false){super.render(loading);this.renderOperationState();headingCase(document.querySelector('#main'));const day=document.querySelector('[data-done-date]');if(day)day.onchange=()=>{if(!day.value)return;this.state.doneDay=day.value;this.state.selected='';this.render();};}
 renderOperationState(){
  const doc=globalThis.document;if(!doc)return;
  const header=doc.querySelector('.topbar');if(header)doc.documentElement.style.setProperty('--workspace-header-bottom',header.getBoundingClientRect().bottom+'px');
  for(const b of doc.querySelectorAll('[data-action=operation],[data-action=quick-approve]')){
   const code=b.dataset.code??b.dataset.kind+'.ONAYLADIM',key=code+':'+(b.dataset.id??'');
   if(this.opening?.has(key)||code==='GOREV.KABUL_ETTIM'&&this.accepting?.has(b.dataset.id)){
    b.disabled=true;b.dataset.operationBusy='true';b.textContent=this.accepting?.has(b.dataset.id)?'İşlem Sürüyor…':'Hazırlanıyor…';
   }
  }
 }
 dispose(){this.disposed=true;clearTimeout(this.acceptTimer);super.dispose();}
 async inspect(kind,id){
  this.inspecting??=new Set();const key=kind+':'+id;if(this.inspecting.has(key))return;
  this.inspecting.add(key);let dialog;
  try{dialog=await this.runInspect(kind,id);if(dialog?.addEventListener)dialog.addEventListener('close',()=>this.inspecting.delete(key),{once:true});return dialog;}
  finally{if(!dialog?.addEventListener)this.inspecting.delete(key);}
 }
 body(){if(this.page==='dayclose')return dailySummary(this,this.value('GUN',this.state.person,{gun:this.state.day}),{pending:true});if(this.page==='team')return this.team();return super.body();}
 opButtons(page=this.page){if(['team','workshop'].includes(page))return '';return super.opButtons(page);}
 team(){const rows=teamMembers(this.c,this.value('EKIP',this.state.unit));return panel('Ekip Şu An',table([{label:'Çalışan',render:r=>`<strong>${esc(r.ad??this.name(r.kisi))}</strong>`},{label:'Durum',render:r=>badge(r.hal?.durum)},{label:'Şu Anki İş',render:r=>esc(r.is_?.islem??r.is_?.is_tanimi??'—')},{label:'Başlangıç',render:r=>time(r.hal?.aralik_baslangic??r.hal?.baslangic)},{label:'Bugünkü Çalışma',numeric:true,render:r=>hours((r.calisma_dk??0)/60)}],rows));}
 tasks(){
  const day=this.state.doneDay??this.c.today,groups=taskGroups(this.refs.GOREV,this.c.person,this.c.today,day);
  const tab=this.state.tab||(groups.waiting.length?'waiting':'open'),visible=groups[tab]??groups.open;
  const selected=visible.find(r=>idOf(r)===this.state.selected);
  const detail=selected?taskDetail(this,selected,this.value('GOREV_AYRINTISI',idOf(selected)),this.state.taskSection??'info'):'<div class="task-placeholder"><h2>Görevinizi Seçin</h2><p>Talimat, teslim, notlar ve dosyalar burada görünür.</p></div>';
  const filter=tab==='done'?`<div class="completed-filter">${button('Bugün','tasks-today',{},day===this.c.today?'primary':'secondary')}<label class="field"><span>Tamamlanma Tarihi</span><input type="date" data-done-date value="${esc(day)}" max="${this.c.today}"></label>${button('Tüm Geçmiş','tasks-history',{},day===''?'primary':'secondary')}<span>${visible.length} görev</span></div>`:'';
  return this.tabs([['waiting',`Kabul Bekleyenler (${groups.waiting.length})`],['open',`İşlerim (${groups.open.length})`],['done',`Tamamlananlar (Bugün: ${groups.doneToday})`]],tab)+filter+`<div class="task-workspace">${this.taskTable(visible)}<aside class="task-detail">${detail}</aside></div>`;
 }
 taskTable(rows){if(this.page!=='tasks')return super.taskTable(rows);return table([{label:'Görev',render:r=>`<strong>${esc(r.ad)}</strong><small>${esc(this.name(r.proje??r.kategori))}</small>`},{label:'Teslim',render:r=>date(r.teslim_tarihi)},{label:'Durum',render:r=>badge(r.durum)}],rows,{select:true,kind:'GOREV',selected:this.state.selected});}
 workshop(){return workshopView(this);}
 bindDrag(){bindWorkshop(this);}
 async jobMenu(id){return this.inspect('IS',id);}
 available(code,record){if(['IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.DEGISTIRDIM','IS.IPTAL_ETTIM','IS.ONAYLADIM','IS.REDDETTIM','IS.DEVAM_ONAYLADIM','IS.BAGLANTI_DUZELTTIM'].includes(code)&&record)return workActionAllowed(code,record,arr(this.value('EKIP',this.state.unit)));if(['GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM'].includes(code)&&this.c.pending>0&&!this.accepting?.has(idOf(record)))return false;return super.available(code,record);}
 async operation(code,id,kind){
  this.opening??=new Set();const key=code+':'+(id??'');if(this.opening.has(key))return;
  this.opening.add(key);let dialog;
  const triggers=[...(globalThis.document?.querySelectorAll('[data-action=operation],[data-action=quick-approve]')??[])].filter(b=>(b.dataset.code===code||b.dataset.action==='quick-approve'&&b.dataset.kind+'.ONAYLADIM'===code)&&(!id||b.dataset.id===id));
  const labels=triggers.map(b=>({b,text:b.textContent,disabled:b.disabled}));
  labels.forEach(({b})=>{b.disabled=true;b.textContent='Hazırlanıyor…';});
  try{dialog=await this.runOperation(code,id,kind);if(dialog?.addEventListener)dialog.addEventListener('close',()=>{this.opening.delete(key);if(this.state&&!this.disposed)this.render();},{once:true});return dialog;}
  finally{labels.forEach(({b,text,disabled})=>{b.textContent=text;b.disabled=disabled;});if(!dialog?.addEventListener)this.opening.delete(key);if(this.state&&!this.disposed)this.render();}
 }
 async runOperation(code,id,kind){
  if(['IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.TANIMLADIM'].includes(code)){
   await this.formRefs(code);
   if(code==='IS.TANIMLADIM')return openWorkDefinition(this);
   const r=this.refs.IS.find(r=>idOf(r)===id);if(!r)throw new Error('İş bulunamadı. Listeyi yenileyin.');
   return workDialog(this,code+':'+id,()=>openWorkMove(this,code,r));
  }
  if(code==='GOREV.KABUL_ETTIM'){
   if(this.page==='tasks')this.state.tab||='waiting';
   if(this.accepting?.has(id))return;this.accepting??=new Set();this.accepting.add(id);
   this.render();let keepWaiting=false;
   try{
    const result=await this.c.confirmed(code,{},[{tur:'GOREV',kimlik:id}]);
    if(this.disposed)return;
    if(['BEKLIYOR','DOGRULANAMADI'].includes(result.islem_durumu)){
     keepWaiting=true;this.awaitingAccept??=new Map();this.awaitingAccept.set(id,result.olay.olay_kimligi);
     toast(operationMessage(result),'info');this.scheduleAcceptCheck();
    }else{if(operationComplete(result)&&this.page==='tasks'&&this.state.tab==='waiting'&&this.state.selected===id)this.state.selected=null;toast(operationMessage(result,'Görev kabul edildi.'),operationTone(result));}
    try{await this.load();}catch{toast(operationMessage({...result,ekran_bekliyor:true}),'info');}
   }catch(e){if(!this.disposed)toast(e.message,true);}finally{if(!keepWaiting)this.accepting.delete(id);if(!this.disposed)this.render();}return;
  }
  if(['GOREV.ONAYLADIM','IS.ONAYLADIM'].includes(code)){
   await this.formRefs(code);kind=code.split('.')[0];const record=this.refs[kind].find(r=>idOf(r)===id);if(record)return this.approvalDialog([{kind,record}]);return;
  }
  return super.operation(code,id,kind);
 }
 scheduleAcceptCheck(){
  clearTimeout(this.acceptTimer);if(this.disposed||!this.awaitingAccept?.size)return;
  this.acceptTimer=setTimeout(async()=>{
   try{for(const [id,event] of this.awaitingAccept){
    const result=await this.c.waitForPublication(event,{timeout:2000,interval:500});if(this.disposed)return;
    if(['BEKLIYOR','DOGRULANAMADI'].includes(result.durum))continue;
    if(result.durum==='TAMAMLANDI'){await this.c.refresh();await this.load();}
    this.awaitingAccept.delete(id);this.accepting.delete(id);
    if(result.durum!=='TAMAMLANDI')toast(operationMessage({islem_durumu:result.durum}),true);
   }}catch{/* Bağlantı dönünce aynı olayın sonucu yeniden okunur. */}
   finally{if(!this.disposed){this.render();this.scheduleAcceptCheck();}}
  },2500);
 }
 async approvalDialog(items){
  const done=new Set();let busy=false;
  const attachments=await Promise.all(items.map(async item=>{try{if(item.kind==='GOREV'){item.detail=(await this.c.read('GOREV_AYRINTISI',idOf(item.record),{},true)).deger;return item.detail?.dosyalar??[];}return (await this.c.read('WEB_DOSYALAR',idOf(item.record),{tur:item.kind},true)).deger??[];}catch{return null;}}));
  items=items.map((item,i)=>({...item,attachments:attachments[i]}));
  const d=modal('Teslimi İncele ve Onayla',`${table([{label:'Devam İşi Ver',className:'selection-col',render:r=>`<input type="checkbox" data-follow="${esc(idOf(r.record))}" aria-label="Devam işi tanımla">`},{label:'Teslim Edilen İş',render:r=>`<strong>${esc(r.record.ad??r.record.islem)}</strong><small>${esc(this.name(r.record.proje))}</small><p class="approval-instruction">${esc(r.record.is_tanimi||'Ek talimat yok.')}</p><p><strong>Teslim Notu:</strong> ${esc(r.detail?.gecmis?.filter(x=>x.eylem==='GOREV.TAMAMLADIM').at(-1)?.not||'Eklenmedi.')}</p>`},{label:'Çalışan',render:r=>esc(this.name(r.record.kisi??r.record.tamamlayan))},{label:'İşin Dosyaları',render:r=>r.attachments===null?'Dosyalar okunamadı. Pencereyi yeniden açın.':fileList(r.attachments)}],items)}<div class="form-error" role="alert"></div><footer class="form-footer"><button type="button" class="btn deliver" data-continue>Teslimi Onayla</button></footer>`,{wide:true});
  d.querySelectorAll('[data-action=file],[data-action=download-file]').forEach(b=>b.onclick=async()=>{try{if(b.dataset.action==='file')await this.openFile(b.dataset.id);else await this.downloadFile(b.dataset.id,b.dataset.name);}catch(error){toast(error.message,true);}});
  d.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
  d.querySelector('[data-continue]').onclick=async e=>{
   if(busy)return;const ids=[...d.querySelectorAll('[data-follow]:checked')].map(e=>e.dataset.follow);busy=true;e.target.disabled=true;d.querySelector('[data-close]').disabled=true;
   try{
    for(const item of items){const id=idOf(item.record);if(done.has(id))continue;const result=await this.c.confirmed(item.kind+'.ONAYLADIM',{},[{tur:item.kind,kimlik:id}]);done.add(id);this.approvalSelection.delete(id);if(!operationComplete(result)){d.close();toast(operationMessage(result)+(done.size<items.length?' Kalan teslimler henüz onaylanmadı.':''),operationTone(result));await this.load();return;}}
    d.close();toast('Teslim onaylandı.');try{await this.load();for(const item of items.filter(r=>ids.includes(idOf(r.record))))await this.newFrom(item.kind,idOf(item.record));}catch{toast('Teslim onaylandı. Görünüm veya devam işi hazırlanamadı; Görev Atama ekranından devam edebilirsiniz.');}
   }catch(error){d.querySelector('.form-error').textContent=error.message;e.target.disabled=false;d.querySelector('[data-close]').disabled=false;}finally{busy=false;}
  };
  return d;
 }
 async reviewAssignment(){
  if(this.reviewOpening)return;this.reviewOpening=true;let dialog;
  const controls=[...document.querySelectorAll('#assignment-host input,#assignment-host select,#assignment-host textarea,#assignment-host button')].filter(e=>!e.disabled);
  controls.forEach(e=>e.disabled=true);const unlock=()=>{this.reviewOpening=false;controls.forEach(e=>e.disabled=false);};
  try{dialog=await super.reviewAssignment();if(dialog)dialog.addEventListener('close',unlock,{once:true});return dialog;}finally{if(!dialog)unlock();}
 }
 async approveSelected(){if(this.bulkOpening)return;this.bulkOpening=true;let dialog;try{const rows=arr(this.value('ONAY_LISTESI')).filter(r=>this.approvalSelection.has(idOf(r)));if(!rows.length){toast('Önce onaylayacağınız işleri işaretleyin.',true);return;}await this.formRefs();dialog=await this.approvalDialog(rows.map(record=>({kind:this.refs.GOREV.some(r=>idOf(r)===idOf(record))?'GOREV':'IS',record})));dialog.addEventListener('close',()=>{this.bulkOpening=false;},{once:true});return dialog;}finally{if(!dialog)this.bulkOpening=false;}}
 async downloadFile(id,name){
  const response=await fetch(await this.c.fileUrl(id));if(!response.ok)throw new Error('Dosya indirilemedi. Yeniden deneyin.');
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=name||'dosya';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
 }
 async runInspect(kind,id){
  if(kind==='IS')return inspectWork(this,id);
  if(kind==='GOREV'){
   await this.formRefs();const data=(await this.c.read('GOREV_AYRINTISI',id,{},true)).deger;const r=data?.gorev;if(!r)return;
   if(this.page==='tasks'&&r.kisi===this.c.person){this.state.selected=id;this.state.tab=r.durum==='ATANDI'?'waiting':r.durum==='BITTI'?'done':'open';if(r.durum==='BITTI')this.state.doneDay='';await this.load();return;}
   const d=modal(r.ad,taskDetail(this,r,data,'info'),{wide:true});
   d.querySelector('.dialog-body').addEventListener('click',async e=>{const el=e.target.closest('[data-action]');if(!el)return;try{
    const a=el.dataset.action;
    if(a==='task-section'){d.querySelector('.dialog-body').innerHTML=taskDetail(this,r,data,el.dataset.section);headingCase(d);return;}
    if(a==='file'){await this.openFile(el.dataset.id);return;}
    if(a==='download-file'){await this.downloadFile(el.dataset.id,el.dataset.name);return;}
    d.close();await this.action(el,e);
   }catch(error){toast(error.message,true);}});return d;
  }

  if(kind==='KISI'){
   const person=(await this.c.read('WEB_KISI',id,{},true)).deger;if(!person)return;
   const d=modal(person.ad,panel('Çalışan Bilgileri',this.auto(person)),{wide:true});
   if(this.c.admin)d.querySelector('.detail-list')?.insertAdjacentHTML('beforeend',`<div><dt>Brüt Maaş</dt><dd class="salary-amount">${money(person.brut_maas)}</dd></div>`);return d;
  }
  const d=await super.inspect(kind,id);if(!d)return;
  if(['GOREV','IS'].includes(kind)){
   const primary=document.createElement('div');primary.className='detail-primary-actions';
   d.querySelectorAll('[data-action=detail-op]').forEach(b=>{if(/\.(ONAYLADIM|REDDETTIM)$/.test(b.dataset.code)){b.className='btn '+(b.dataset.code.endsWith('ONAYLADIM')?'deliver':'reject');primary.append(b);}});
   if(primary.children.length)d.querySelector('.dialog-body').prepend(primary);
  }
  headingCase(d);return d;
 }
 auto(data,options={}){return data?.ozet?.gorevler?dailySummary(this,data):super.auto(data,options);}
 renderValue(value,key=''){
  return super.renderValue(value,key);
 }
 async newFrom(...args){const blank=this.draftRows.length===1&&!this.draftRows[0].ad&&!this.draftRows[0].is_tanimi;await super.newFrom(...args);if(blank&&this.draftRows.length>1){this.draftRows.shift();this.draftIndex--;if(this.page==='assign')this.bindAssignment();}}
 async action(el,event){
  try{
   const action=el.dataset.action;
   if(action==='work-unplanned'){return workDialog(this,'plansiz:'+el.dataset.person,async()=>{await this.formRefs('IS.PLANSIZ_TANIMLADIM');return openWorkDefinition(this,{person:el.dataset.person});});}
   if(action==='task-section'){this.state.taskSection=el.dataset.section;this.render();return;}
   if(action==='tasks-today'||action==='tasks-history'){this.state.doneDay=action==='tasks-today'?this.c.today:'';this.state.selected='';this.render();return;}
   if(action==='select-row'&&this.page==='tasks'){this.state.selected=el.dataset.id;this.state.taskSection='info';await this.load();return;}
   if(action==='task-follow'||action==='task-change'){await this.newFrom('GOREV',el.dataset.id,action==='task-change');return;}
   if(action==='download-file'){await this.downloadFile(el.dataset.id,el.dataset.name);return;}

   return await super.action(el,event);
  }catch(error){toast(error.message,true);}
 }
}
