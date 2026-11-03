import {icon} from './icons.js';
import {ModuleWorkspace} from './modules.js';
import {esc,idOf,arr,date,hours,num,button,panel,table,empty,badge,toast} from './ui.js';
import {openOperation} from './forms.js';
import {bindTemporalInput,bindDatePicker,displayTemporal,parseTemporal,validTemporal} from './temporal.js';
import {projectOpen,projectRange,planningTask,projectOperations,sortProjectJobs} from './project_model.js';

export class ProjectWorkspace extends ModuleWorkspace {
 constructor(client){super(client);this.projectList=true;this.projectFilter='open';this.rangeProject=null;const onData=this.onData;this.c.removeEventListener('data',onData);this.onData=()=>{if(this.pendingProject&&this.c.projects.some(p=>idOf(p)===this.pendingProject.id)){this.state.project=this.pendingProject.id;this.pendingProject=null;this.projectList=false;void this.load();}else onData();};this.c.addEventListener('data',this.onData);}
 can(code){if(code==='PROJE.KOD_DEGISTIRDIM')return !this.c.readonly&&(this.c.admin||this.c.context.islem_izinleri?.includes(code)===true);return super.can(code);}
 opButtons(page=this.page){return page==='projects'&&!this.c.readonly?'':super.opButtons(page);}
 render(loading=false){
  // Canlı veri yenilenirken kullanıcının yazdığı tarih ve imleci yerinde kalsın.
  if(!loading&&this.page==='projects'&&document.activeElement?.matches('#project-period input'))return;
  super.render(loading);if(this.page==='projects'&&!this.c.readonly)document.querySelector('.page-heading p')?.remove();
 }
 filters(){return this.page==='projects'&&!this.c.readonly?'':super.filters();}
 async load(){
  if(this.page==='projects'&&!this.c.readonly&&this.state.project){
   const id=this.state.project,generation=this.c.generation;
   if(this.rangeProject!==id){
    this.rangeProject=id;const version=this.rangeVersion=(this.rangeVersion??0)+1;
    try{
     const stages=arr((await this.c.read('ETAPLAR',id,{},true)).deger);
     if(this.page!=='projects'||generation!==this.c.generation||id!==this.state.project)return;
     if(this.rangeVersion===version)Object.assign(this.state,projectRange(this.c.projects.find(p=>idOf(p)===id),stages,this.c.today));
    }catch{this.rangeProject=null;/* Ana yükleme ilgili erişim/bağlantı hatasını gösterir. */}
   }
  }
  return super.load();
 }
 projectButton(title,code,record,kind='PROJE',style='small'){
  return this.can(code)?button(title,'operation',{code,id:idOf(record),kind},style):'';
 }
 projects(){
  if(this.c.readonly)return super.projects();
  if(this.pendingProject){const p=this.c.projects.find(x=>idOf(x)===this.pendingProject.id);if(p){this.state.project=idOf(p);this.projectList=false;this.pendingProject=null;}else return panel('Proje İşlemi Alındı',`<div class="panel-body"><h3>${esc(this.pendingProject.ad)}</h3><p>İşlem kabul edildi. Proje bilgileri henüz yenilenemedi; tekrar proje açmanıza gerek yok.</p>${button('Bilgileri Yenile','project-refresh',{},'primary')}</div>`);}
  const p=this.c.projects.find(x=>idOf(x)===this.state.project);
  if(this.projectList||!p){
   const rows=this.c.projects.filter(x=>projectOpen(x)===(this.projectFilter==='open'));
   return `<div class="project-list-actions"><div class="tabs">${[['open','Açık'],['closed','Kapalı']].map(([key,title])=>button(title,'project-filter',{filter:key},this.projectFilter===key?'primary':'secondary')).join('')}</div>${this.can('PROJE.ACTIM')?button('Yeni Proje','operation',{code:'PROJE.ACTIM'},'primary'):''}</div>`+panel('Projeler',rows.length?table([
    {label:'Proje',render:r=>`<strong>${esc(r.ad)}</strong><small>${esc([r.kod,r.ek].filter(Boolean).join(' · '))}</small>`},
    {label:'Sorumlu',render:r=>esc(this.name(r.sorumlu))},{label:'Teslim',render:r=>date(r.teslim_tarihi)},
    {label:'Durum',render:r=>projectOpen(r)?'Açık':'Kapalı'},
    {label:'İşlem',render:r=>button('Projeyi Aç','project-open',{id:idOf(r)},'small')}],rows):empty(this.projectFilter==='open'?'Açık Proje Yok':'Kapalı Proje Yok',''));
  }
  const es=arr(this.value('ETAPLAR',idOf(p))),status=this.value('PROJE_DURUM',idOf(p))??{},active=projectOpen(p),tab=this.state.tab||'stages';
  let body;
  if(tab==='jobs')body=this.projectJobs(p);
  else if(tab==='team')body=this.projectTeam(p,es);
  else if(tab==='objects')body=this.objects();
  else body=this.projectPlan(p,es,status);
  return `<div class="project-breadcrumb">${button('← Projeler','project-list',{},'secondary')}</div><section class="project-summary"><div><span class="eyebrow">${esc([p.kod,p.ek].filter(Boolean).join(' · '))} · ${active?'Açık':'Kapalı'}</span><h2>${esc(p.ad)}</h2><p>${esc(this.name(p.sorumlu))} · Teslim: ${date(p.teslim_tarihi)}</p></div><div class="toolbar">${active?this.projectButton('Düzenle','PROJE.DEGISTIRDIM',p):''}${this.projectButton('Kodu Değiştir','PROJE.KOD_DEGISTIRDIM',p)}${active?this.projectButton('Projeyi Kapat','PROJE.KAPATTIM',p):''}</div></section>${!active?'<p class="notice">Bu proje kapalı. Geçmiş bilgileri görüntüleniyor.</p>':''}${this.metrics([['Proje İlerlemesi',status.yuzde==null||!Number.isFinite(Number(status.yuzde))?'Plan Bekliyor':num(status.yuzde)+'%',''],['Harcanan Emek',hours(status.harcanan_emek??status.harcanan_saat),''],['Hedef Emek',hours(es.reduce((n,e)=>n+Number(e.hedef_saat??0),0)),''],['Etap Dışı Harcanan Emek',hours(status.etap_disi?.harcanan_emek),'Proje toplamına dahildir']])}${this.tabs([['stages','Etaplar ve Plan'],['jobs','İşler'],['team','Ekip'],['objects','Belgeler']],'stages')}<div class="project-workspace stack">${body}</div>`;
 }
 projectPlan(p,es,status){
  const active=projectOpen(p),plan=this.value('PLAN',idOf(p),{surumler:true})??this.value('PLAN',idOf(p))??{},versions=plan.surumler??[];
  const stageTable=table([{label:'Etap',render:e=>`<strong>${esc(e.ad)}</strong><small>${esc(this.name(e.birim))}</small>`},{label:'Sorumlu',render:e=>esc(this.name(e.sorumlu))},{label:'Başlangıç',render:e=>date(e.baslangic)},{label:'Bitiş',render:e=>date(e.bitis)},{label:'Hedef Emek',render:e=>hours(e.hedef_saat)},{label:'İlerleme',render:e=>this.progress(status.etaplar?.[idOf(e)]?.yuzde)},{label:'İşlemler',render:e=>active?`<div class="row-actions">${this.projectButton('Düzenle','ETAP.DEGISTIRDIM',e,'ETAP')}${this.can('GOREV.ATADIM')?button('Planlama Görevi Ver','stage-plan-task',{id:idOf(e)},'small'):''}</div>`:''}],es);
  const approve=active&&es.length&&this.can('PLAN.ONAYLADIM')?button(versions.length?'Yeni Plan Sürümünü Onayla':'İlk Planı Onayla','operation',{code:'PLAN.ONAYLADIM',id:idOf(p),kind:'PROJE'},'primary'):'';
  const compare=table([{label:'Etap',render:e=>esc(e.ad)},...[[plan.B0,'İlk Onaylı Plan'],[plan.son_onayli,'Son Onaylı Plan'],[plan.guncel,'Güncel Plan']].map(([map,title])=>({label:title,render:e=>{const x=map?.[idOf(e)];return x?`${date(x.baslangic)} – ${date(x.bitis)}<small>${hours(x.hedef_saat)} hedef emek</small>`:'—';}})),{label:'Gerçekleşen',render:e=>{const x=plan.gerceklesen?.[idOf(e)],done=arr(this.value('GANTT',idOf(p),{bas:this.state.bas,bit:this.state.bit})).find(a=>a.tur==='ETAP'&&a.kimlik===idOf(e));return `${done?.gerceklesen_baslangic?date(done.gerceklesen_baslangic)+' – '+(done.gerceklesen_bitis?date(done.gerceklesen_bitis):'Devam ediyor'):'Bu dönemde gerçekleşen tarih yok'}<small>${hours(x?.harcanan_emek)} harcanan emek</small>`;}},{label:'Değişiklik',render:e=>{const old=plan.son_onayli?.[idOf(e)];if(!old)return versions.length?'Yeni etap':'Henüz onaylanmadı';const changes=[];if(old.baslangic!==e.baslangic)changes.push('Başlangıç');if(old.bitis!==e.bitis)changes.push('Bitiş');if(Number(old.hedef_saat)!==Number(e.hedef_saat))changes.push('Hedef emek');if(old.birim!==e.birim)changes.push('Birim');if(old.ad!==e.ad)changes.push('Ad');return changes.length?changes.join(', ')+' değişti':'Değişiklik yok';}}],es);
  const history=versions.length?`<details class="project-history"><summary>Plan Geçmişi (${versions.length})</summary>${versions.map((v,i)=>`<details><summary>${i===0?'İlk Onaylı Plan':'Plan Sürümü '+(i+1)} · ${date(v.onay_ani)} · ${esc(this.name(v.onaylayan))}</summary><p>${esc(v.gerekce||'İlk plan onayı')}</p>${table([{label:'Etap',key:'ad'},{label:'Başlangıç',render:e=>date(e.baslangic)},{label:'Bitiş',render:e=>date(e.bitis)},{label:'Hedef Emek',render:e=>hours(e.hedef_saat)}],Object.values(v.etaplar??{}))}</details>`).join('')}</details>`:'<p class="notice">Henüz onaylı plan yok. Etap tarihleri hazırlanan planı gösteriyor.</p>';
  return panel('Etaplar',es.length?stageTable:empty('Henüz Etap Yok','Etap Ekle düğmesiyle başlayabilirsiniz.'),active&&this.can('ETAP.TANIMLADIM')?button('Etap Ekle','operation',{code:'ETAP.TANIMLADIM'},'primary'):'')+this.projectChart(p,es,plan)+panel('Plan Karşılaştırması',`<div class="panel-body">${approve?'<div class="toolbar">'+approve+'</div>':''}</div>${compare}<div class="panel-body">${history}</div>`);
 }
 projectChart(p,es,plan){
  const {bas,bit}=this.state,lo=Date.parse(bas+'T00:00:00Z'),hi=Date.parse(bit+'T00:00:00Z')+86400000,span=hi-lo;
  const actual=arr(this.value('GANTT',idOf(p),{bas,bit}));
  const bar=(a,b,kind)=>{if(!a||!b||!span)return '';const x=Date.parse(String(a).slice(0,10)+'T00:00:00Z'),y=Date.parse(String(b).slice(0,10)+'T00:00:00Z')+86400000;if(!Number.isFinite(x+y)||y<=lo||x>=hi)return '';return `<span class="project-bar ${kind}" style="left:${100*(Math.max(x,lo)-lo)/span}%;width:${Math.max(.5,100*(Math.min(y,hi)-Math.max(x,lo))/span)}%" title="${esc(date(a)+' – '+date(b))}"></span>`;};
  const rows=es.filter(e=>{const approved=plan.son_onayli?.[idOf(e)],done=actual.find(a=>a.tur==='ETAP'&&a.kimlik===idOf(e));return [[e.baslangic,e.bitis],[approved?.baslangic,approved?.bitis],[done?.gerceklesen_baslangic,done?.gerceklesen_bitis??this.c.today]].some(([a,b])=>a&&b&&String(a).slice(0,10)<=bit&&String(b).slice(0,10)>=bas);});
  const timeline=rows.map(e=>{const old=plan.son_onayli?.[idOf(e)],done=actual.find(a=>a.tur==='ETAP'&&a.kimlik===idOf(e));return `<div class="project-timeline-row"><div><strong>${esc(e.ad)}</strong><small>${date(e.baslangic)} – ${date(e.bitis)}</small></div><div class="project-tracks"><div>${bar(e.baslangic,e.bitis,'current')}</div><div>${bar(old?.baslangic,old?.bitis,'approved')}</div><div>${bar(done?.gerceklesen_baslangic,done?.gerceklesen_bitis??this.c.today,'actual')}</div></div></div>`;}).join('');
  return panel('Tarih Çizelgesi (Gantt)',`<div class="panel-body"><form class="project-period" id="project-period" novalidate>${[["bas","Başlangıç",bas],["bit","Bitiş",bit]].map(([key,title,value])=>`<label class="field">${title}<span class="temporal-control"><input type="text" name="${key}" data-temporal="date" inputmode="numeric" value="${esc(this.periodDraft?.project===idOf(p)?this.periodDraft[key]:displayTemporal(value,"date"))}" placeholder="GG.AA.YYYY" autocomplete="off"><span class="calendar-picker" title="Takvimden Seç">${icon('calendar')}<input tabindex="-1" type="date" data-period-picker="${key}" value="${esc(value)}" aria-label="${title} için takvimden seç"></span></span></label>`).join("")}<button class="btn" type="submit">Göster</button>${button('Tüm Proje Dönemi','project-range',{},'secondary')}<span class="project-period-error" role="alert"></span></form><div class="project-legend"><span class="current">Hazırlanan Güncel Plan</span><span class="approved">Son Onaylı Plan</span><span class="actual">Gerçekleşen</span></div><div class="project-chart-axis"><span>${date(bas)}</span><span>${date(bit)}</span></div>${timeline||empty(es.length?'Bu Dönemde Etap Yok':'Henüz Etap Yok','')}</div>`);
 }
 projectJobs(p){
  const rows=[...this.refs.GOREV.map(x=>({...x,kind:'GOREV'})),...this.refs.IS.map(x=>({...x,kind:'IS'}))].filter(x=>x.proje===idOf(p)),filter=this.jobHistory?'IPTAL':null;
  return panel(this.jobHistory?'İptal Edilen İşler':'Projenin İşleri',table([{label:'İş',render:r=>`<strong>${esc(r.ad??r.islem??r.is_tanimi)}</strong><small>${esc(r.etap?this.name(r.etap):'Etap Dışı')}</small>`},{label:'Sorumlu',render:r=>esc(this.name(r.kisi))},{label:'Durum',render:r=>badge(r.durum)},{label:'Ayrıntı',render:r=>button('İncele','inspect',{kind:r.kind,id:idOf(r)},'small')}],sortProjectJobs(rows.filter(r=>filter?r.durum===filter:r.durum!=='IPTAL'))),button(this.jobHistory?'İşlere Dön':'İptal Edilenler','project-job-history',{},'secondary'));
 }
 projectTeam(p,es){
  const members=new Map();
  for(const e of es)if(e.sorumlu)members.set(e.sorumlu,'Etap sorumlusu');
  for(const x of [...this.refs.GOREV,...this.refs.IS].filter(x=>x.proje===idOf(p)))for(const id of [x.kisi,...(x.kisiler??[])].filter(Boolean))members.set(id,'İş verilen çalışan');
  if(p.sorumlu)members.set(p.sorumlu,'Proje sorumlusu');
  const access=this.value('PROJE',idOf(p),{ekip:true})?.ek_erisim??[];
  const ids=Array.isArray(access)?access.map(x=>typeof x==='string'?x:x.kisi):Object.keys(access);
  for(const id of ids)members.set(id,members.has(id)?members.get(id)+' · Ek erişim':'Ek erişim');
  return panel('Birimler ve Sorumlular',table([{label:'Etap',key:'ad'},{label:'Birim',render:e=>esc(this.name(e.birim))},{label:'Sorumlu',render:e=>esc(this.name(e.sorumlu))}],es))+panel('Proje Ekibi',table([{label:'Çalışan',render:r=>esc(this.name(r.id))},{label:'Projeyle İlişkisi',key:'relation'},{label:'İşlem',render:r=>ids.includes(r.id)&&this.can('PROJE.ERISIM_KALDIRDIM')?button('Ek Erişimi Kaldır','project-remove-access',{id:r.id},'small'):''}],[...members].map(([id,relation])=>({id,relation}))),this.can('PROJE.ERISIM_VERDIM')?button('Ek Erişim Ver','operation',{code:'PROJE.ERISIM_VERDIM',id:idOf(p),kind:'PROJE'},'secondary'):'');
 }
 bind(){
  super.bind();const form=document.querySelector('#project-period');if(!form)return;
  form.querySelectorAll('[data-temporal]').forEach(bindTemporalInput);
  form.querySelectorAll('[data-period-picker]').forEach(p=>bindDatePicker(form.elements[p.dataset.periodPicker],p));
  const remember=()=>{this.periodDraft={project:this.state.project,bas:form.elements.bas.value,bit:form.elements.bit.value};};form.oninput=remember;
  form.querySelectorAll('[data-period-picker]').forEach(picker=>{picker.onclick=()=>{try{picker.showPicker?.();}catch{}};picker.onchange=()=>{form.elements[picker.dataset.periodPicker].value=displayTemporal(picker.value,'date');remember();};});
  form.onsubmit=e=>{e.preventDefault();const a=parseTemporal(form.elements.bas.value,'date'),b=parseTemporal(form.elements.bit.value,'date');const invalidStart=!validTemporal(a,'date'),invalidEnd=!validTemporal(b,'date');form.elements.bas.setAttribute('aria-invalid',String(invalidStart));form.elements.bit.setAttribute('aria-invalid',String(invalidEnd||a>b));if(invalidStart||invalidEnd||a>b){form.querySelector('[role=alert]').textContent=invalidStart||invalidEnd?'Geçerli bir tarih girin (GG.AA.YYYY).':'Bitiş başlangıçtan önce olamaz.';(invalidStart?form.elements.bas:form.elements.bit).focus();return;}this.periodDraft=null;this.rangeProject=this.state.project;this.rangeVersion=(this.rangeVersion??0)+1;form.elements.bas.blur();form.elements.bit.blur();Object.assign(this.state,{bas:a,bit:b});void this.load();};
 }
 async runOperation(code,id,kind){
  if(!projectOperations.has(code)||this.c.readonly)return super.runOperation(code,id,kind);
  await this.formRefs(code);
  const p=this.c.projects.find(x=>idOf(x)===this.state.project),record=kind==='ETAP'?this.refs.ETAP.find(x=>idOf(x)===id):this.c.projects.find(x=>idOf(x)===id)??p;
  const defaults={};if(['ETAP.TANIMLADIM','PLAN.ONAYLADIM','PROJE.ERISIM_VERDIM','PROJE.ERISIM_KALDIRDIM'].includes(code)&&p)defaults.proje=idOf(p);
  if(code==='ETAP.TANIMLADIM')defaults.sorumlu=p?.sorumlu;
  if(code==='PROJE.ERISIM_KALDIRDIM'&&this.accessPerson)defaults.kisi=this.accessPerson;
  if(code==='PROJE.KOD_DEGISTIRDIM'){defaults.proje=idOf(record);defaults.kod=record?.kod;}
  return openOperation(this.c,code,{record:code==='PROJE.ACTIM'?null:record,refs:this.refs,defaults,onDone:async(result,g)=>{
   if(code==='PROJE.ACTIM'){this.state.project=result.olay?.girdiler?.kimlik??g.kimlik??(idOf(this.c.projects.find(x=>x.kod===g.kod&&(x.ek??'')===(g.ek??'')))||g.kod);this.pendingProject={id:this.state.project,ad:g.ad};this.projectList=false;this.rangeProject=null;this.state.tab='stages';if(this.page!=='projects'){location.hash='projects';return;}}
   this.rangeProject=null;await this.load();
  }});
 }
 async action(el,event){
  const action=el.dataset.action;
  if(action==='project-refresh'){el.disabled=true;try{await this.c.refresh();await this.load();}catch{toast('Proje oluşturuldu; bilgiler henüz yenilenemedi. Biraz sonra tekrar deneyin.',true);el.disabled=false;}return;}
  if(action==='project-open'){this.periodDraft=null;this.projectList=false;this.state.tab='stages';this.rangeProject=null;return super.action(el,event);}
  if(action==='project-list'){this.projectList=true;this.render();return;}
  if(action==='project-filter'){this.projectFilter=el.dataset.filter;this.render();return;}
  if(action==='project-range'){this.periodDraft=null;this.rangeProject=null;await this.load();return;}
  if(action==='project-job-history'){this.jobHistory=!this.jobHistory;this.render();return;}
  if(action==='project-remove-access'){this.accessPerson=el.dataset.id;try{return await this.operation('PROJE.ERISIM_KALDIRDIM',this.state.project,'PROJE');}finally{this.accessPerson=null;}}
  if(action==='stage-plan-task'){
   if(this.planning)return;this.planning=true;el.disabled=true;
   try{await this.formRefs();const stage=this.refs.ETAP.find(x=>idOf(x)===el.dataset.id),p=this.c.projects.find(x=>idOf(x)===stage?.proje);if(!stage||!projectOpen(p))throw Error('Etap açık bir projeye ait olmalı.');
    const row={...this.newTask(),teslim_tarihi:this.c.today,zaman_degeri:1,zorluk:2,onaylayan:this.c.person,...planningTask(stage,p)};
    if(this.draftRows.length===1&&!this.draftRows[0].ad&&!this.draftRows[0].is_tanimi)this.draftRows=[];
    this.draftRows.push(row);this.draftIndex=this.draftRows.length-1;location.hash='assign';
   }catch(error){toast(error.message,true);}finally{this.planning=false;el.disabled=false;}return;
  }
  return super.action(el,event);
 }
}
