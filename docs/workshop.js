import {esc,idOf,arr,button,badge,panel,table,modal,toast,hours,date,time,headingCase,empty} from './ui.js';
import {OPERATIONS} from './actions.js';
import {fileList} from './office.js';
import {bindForm,cleanValue,validationIssues,showValidation,openOperation} from './forms.js';
import {operationComplete,operationMessage,operationTone} from './client.js';
import {workName,workRecipients,teamMembers,workActionAllowed,dropPosition,placedQueue,queueIssue,workDefinition} from './workshop_model.js';

const operations=['IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.DEVAM_ONAYLADIM','IS.ONAYLADIM','IS.REDDETTIM','IS.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM','IS.IPTAL_ETTIM'];
const context=(w,r)=>[r.proje?w.name(r.proje):w.name(r.kategori),r.etap?w.name(r.etap):'',r.parca_kodu].filter(x=>x&&x!=='—').join(' · ');
const team=w=>teamMembers(w.c,w.value('EKIP',w.state.unit));
const list=(w,p)=>arr(w.value('LISTE',p)?.isler);
const actionButtons=(w,r)=>operations.filter(code=>w.can(code)&&workActionAllowed(code,r,team(w))&&(!['IS.ONAYLADIM','IS.REDDETTIM'].includes(code)||r.tamamlayan!==w.c.person)).map(code=>button(OPERATIONS[code].title,'operation',{code,id:idOf(r),kind:'IS'},code.endsWith('IPTAL_ETTIM')?'danger':code.endsWith('ONAYLADIM')?'success':'secondary')).join('');

export function workshopView(w){
 if(!w.c.manager)return w.clock()+panel('İş Listem',w.auto(w.value('LISTE',w.c.person)?.isler??[]));
 const pool=arr(w.value('HAVUZ',w.state.unit)).filter(r=>!r.ana_is),people=team(w);
 const poolBody=pool.length?'<div class="work-pool">'+pool.map(r=>`<article class="work-pool-item" draggable="${w.can('IS.ATADIM')}" data-job="${esc(idOf(r))}"><div class="work-pool-head"><div class="work-card-title"><strong>${esc(workName(r))}</strong><small>${esc(context(w,r))}</small></div><div class="row-actions">${button('Ayrıntı','inspect',{kind:'IS',id:idOf(r)},'small')}${w.can('IS.ATADIM')&&workActionAllowed('IS.ATADIM',r)?button('Ata','operation',{code:'IS.ATADIM',id:idOf(r),kind:'IS'},'primary small'):''}</div></div><div class="work-meta">${badge(r.durum)}<span>${r.tur==='ANLIK'?'Anlık':hours((r.tahmini_sure_dk??0)/60)}${r.kisi_sayisi>1?' · '+r.kisi_sayisi+' kişi':''}</span>${r.onay_gerekli?'<span>Onay Gerekli</span>':''}</div></article>`).join('')+'</div>':empty('Havuzda İş Yok','Yeni iş tanımladığınızda burada görünür.');
 const peopleBody=people.length?people.map(p=>`<section class="person-list" data-drop-person="${esc(p.kisi)}"><div class="person-list-head"><strong>${esc(p.ad??w.name(p.kisi))}</strong>${badge(p.hal?.durum)}</div><div class="work-queue">${list(w,p.kisi).map((r,i)=>`<article class="person-job" draggable="${w.can('IS.SIRALADIM')}" data-job="${esc(idOf(r))}" data-person="${esc(p.kisi)}"><span class="order">${i+1}</span><div class="job-name"><strong>${esc(workName(r))}</strong><small>${esc(context(w,r))}</small></div>${badge(r.durum)}${button('İşlemler','job-menu',{id:idOf(r),person:p.kisi},'small')}</article>`).join('')||'<div class="work-empty">Henüz Atanmış İş Yok</div>'}</div><div class="work-person-actions">${w.can('IS.PLANSIZ_TANIMLADIM')?button('Plansız İş Ver','work-unplanned',{person:p.kisi},'small'):''}</div></section>`).join(''):empty('Ekipte Çalışan Yok');
 return '<div class="workshop-workspace pool-layout">'+panel('Ekip İş Havuzu',poolBody,w.can('IS.TANIMLADIM')?button('Yeni İş','operation',{code:'IS.TANIMLADIM'},'primary'):'')+panel('Çalışanların Sıralı İşleri',peopleBody)+'</div>';
}

// The same dialog lock covers menus, drag/drop and normal action buttons.
export async function workDialog(w,key,create){
 w.workDialogs??=new Set();if(w.workDialogs.has(key))return;
 w.workDialogs.add(key);let d;
 try{d=await create();d?.addEventListener('close',()=>w.workDialogs.delete(key),{once:true});return d;}
 finally{if(!d)w.workDialogs.delete(key);}
}
function submitDialog(w,d,send,{onStale}={}){
 let busy=false,pending=null,unresolved=null;
 const form=d.querySelector('form'),error=d.querySelector('.form-error'),submit=form.querySelector('[type=submit]'),caption=submit.textContent;
 d.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 form.onsubmit=async e=>{
  e.preventDefault();if(busy)return;busy=true;error.textContent='';
  const controls=[...d.querySelectorAll('button,input,select,textarea')].map(el=>[el,el.disabled]);
  controls.forEach(([el])=>el.disabled=true);submit.textContent='Lütfen Bekleyin…';
  try{
   const result=unresolved?await w.c.retryManagement(unresolved):pending?await w.c.afterAccepted({sonuc:'BASARILI'},pending):await send();
   unresolved=null;
   if(!operationComplete(result)){
    pending=result.olay;error.textContent=operationMessage(result);
    if(['INCELEME_GEREKIYOR','GECERSIZ','ZAMANI_BEKLIYOR'].includes(result.islem_durumu)){d.close();toast(operationMessage(result),operationTone(result));}
    return;
   }
   d.close();toast('İşlem Tamamlandı.');await w.load();
  }catch(ex){unresolved=ex.eventId??unresolved;error.textContent=ex.message;if(ex.issues)showValidation(d,ex.issues.map(i=>({...i,path:i.path.replace(/^isler\.0\./,'').replace(/^(sira|yeni_sira|kime_sira)$/,'position').replace(/^(kisi|kime)$/,'person')})));if(ex.code==='STALE_PREVIEW')await onStale?.();}
  finally{busy=false;controls.forEach(([el,disabled])=>el.disabled=(!!pending||!!unresolved)&&!el.matches('button')?true:disabled);submit.textContent=pending||unresolved?'Sonucu Kontrol Et':caption;}
 };
 d.querySelector('[data-cancel]').onclick=()=>d.close();headingCase(d);
}
const stamp=r=>r?.surum;
const expectations=(person,queue,record)=>({...record?{['IS:'+idOf(record)]:stamp(record)}:{},['LISTE:'+person]:stamp(queue)});
const positionOptions=(max,position,showLast=true)=>max?Array.from({length:max},(_,i)=>`<option value="${i+1}" ${i+1===position?'selected':''}>${i+1}. Sıra${showLast&&i+1===max?' · En Son':''}</option>`).join(''):'<option value="">Önce Çalışanı Seçin</option>';
const preview=(w,person,rows,work,position)=>`<section class="queue-preview"><h3>${esc(w.name(person))} · Oluşacak Sıra</h3><ol>${placedQueue(rows,work,position).map(r=>`<li class="${idOf(r)===idOf(work)?'queue-changed':''}">${esc(workName(r))}</li>`).join('')}</ol>${idOf(rows[0])!==idOf(placedQueue(rows,work,position)[0])&&rows[0]?.durum==='CALISILIYOR'?'<p class="notice">Şu anki işin çalışma süresi kapanır; iş yarım kalır. Yeni işi çalışan başlatır.</p>':''}</section>`;

export async function openWorkMove(w,code,r,defaults={}){
 const source=r.kisi??defaults.source, multi=code==='IS.ATADIM'&&Number(r.kisi_sayisi??1)>1;
 const candidates=workRecipients(w.c).filter(p=>code!=='IS.DEVRETTIM'||idOf(p)!==source);
 let person=defaults.person??(code==='IS.SIRALADIM'?source:''),position=defaults.position??null,queue=null,sourceQueue=null,expected={},serial=0,selected=new Set();
 if(!workActionAllowed(code,r,team(w)))throw new Error('Bu iş için seçilen işlem şu anda kullanılamıyor.');
 const choices=multi?`<fieldset class="choice-list"><legend>Çalışanlar · ${r.kisi_sayisi} Kişi Seçin</legend>${candidates.map(p=>`<label><input type="checkbox" data-worker value="${esc(idOf(p))}"> ${esc(p.ad)}</label>`).join('')}</fieldset>`:`<label class="field"><span>Çalışan *</span><select data-path="person" ${code==='IS.SIRALADIM'?'disabled':''}><option value="">Seçiniz</option>${candidates.map(p=>`<option value="${esc(idOf(p))}" ${idOf(p)===person?'selected':''}>${esc(p.ad)}</option>`).join('')}</select></label>`;
 const d=modal(OPERATIONS[code].title,`<form class="work-form"><div class="operation-context"><span>İlgili İş</span><h3>${esc(workName(r))}</h3><p>${esc(context(w,r))}</p></div><div class="form-error" role="alert"></div>${choices}<label class="field"><span>Yeni Sıra *</span><select data-path="position"><option value="">Önce Çalışanı Seçin</option></select></label><div data-queue-preview></div><footer class="form-footer"><button class="btn" type="button" data-cancel>Vazgeç</button><button class="btn primary" type="submit">Onayla</button></footer></form>`,{wide:true});
 let queues={};
 async function refresh(){
  const token=++serial;const ps=multi?[...selected]:person?[person]:[];
  d.querySelector('[type=submit]').disabled=true;
  const values=await Promise.all(ps.map(async p=>[p,(await w.c.read('LISTE',p,{},true)).deger]));
  if(token!==serial||!d.open)return;
  queues=Object.fromEntries(values);expected={['IS:'+idOf(r)]:stamp(r)};
  for(const [p,q]of values)Object.assign(expected,expectations(p,q));
  if(code==='IS.DEVRETTIM'){sourceQueue=(await w.c.read('LISTE',source,{},true)).deger;expected['LISTE:'+source]=stamp(sourceQueue);}
  if(token!==serial||!d.open)return;
  queue=queues[person];const ends=values.map(([,q])=>arr(q.isler).filter(x=>idOf(x)!==idOf(r)).length+1);
  const commonMax=ends.length?Math.min(...ends):0,max=ends.length?Math.max(...ends):0;
  const current=code==='IS.SIRALADIM'?arr(queue?.isler).findIndex(x=>idOf(x)===idOf(r))+1:max;
  position=Math.max(1,Math.min(max,position??current));
  d.querySelector('[data-path=position]').innerHTML=positionOptions(commonMax,position,commonMax===max)+(max>commonMax?`<option value="${max}" ${position===max?'selected':''}>Her Listede En Son</option>`:'');
  draw();d.querySelector('[type=submit]').disabled=false;
 }
 function draw(){d.querySelector('[data-queue-preview]').innerHTML=Object.entries(queues).map(([p,q])=>preview(w,p,arr(q.isler),r,position)).join('')+(code==='IS.DEVRETTIM'&&sourceQueue?`<p class="notice">${esc(w.name(source))} listesinden çıkarılır. Önceki çalışma süresi korunur.</p>`:'');}
 d.querySelector('[data-path=person]')?.addEventListener('change',e=>{person=e.target.value;position=null;void refresh().catch(e=>{d.querySelector('.form-error').textContent=e.message;});});
 d.querySelectorAll('[data-worker]').forEach(el=>el.onchange=()=>{el.checked?selected.add(el.value):selected.delete(el.value);position=null;void refresh().catch(e=>{d.querySelector('.form-error').textContent=e.message;});});
 d.querySelector('[data-path=position]').onchange=e=>{position=Number(e.target.value);draw();};
 submitDialog(w,d,async()=>{
  const ps=multi?[...selected]:[person];
  if(!ps[0]||multi&&ps.length!==Number(r.kisi_sayisi))throw new Error(multi?`${r.kisi_sayisi} çalışan seçin.`:'Çalışanı seçin.');
  if(ps.some(p=>!candidates.some(x=>idOf(x)===p)))throw new Error('Bu çalışana iş atanamaz.');
  // Motor ortak sırayı kısa listelerde sona sınırlar; önizleme ve denetim aynı yeri kullanır.
  for(const p of ps){const rows=arr(queues[p]?.isler),actual=multi?Math.min(position,rows.length+1):position;const issue=queueIssue(rows,r,actual,{transfer:code==='IS.DEVRETTIM'});if(issue)throw new Error(issue);}
  if(sourceQueue?.isler?.[0]?.onay_beklet&&sourceQueue.isler[0].durum==='ONAY_BEKLIYOR'&&idOf(sourceQueue.isler[0])===idOf(r))throw new Error('Onay bekleyen ilk iş devredilemez.');
  const g=code==='IS.SIRALADIM'?{kisi:person,yeni_sira:position}:code==='IS.DEVRETTIM'?{kimden:source,kime:person,kime_sira:position}:multi?{kisiler:ps,kisi_sayisi:Number(r.kisi_sayisi),sira:position}:{kisi:person,sira:position};
  return w.c.confirmed(code,g,[{tur:'IS',kimlik:idOf(r)}],{expectedTargets:expected});
 },{onStale:async()=>{const latest=(await w.c.read('IS',idOf(r),{},true)).deger;if(!workActionAllowed(code,latest,team(w))){d.close();toast('İşin durumu değişmiş. Güncel işi kontrol edin.',true);await w.load();return;}r=latest;await refresh();}});
 await refresh();return d;
}

export async function openWorkDefinition(w,{person=null}={}){
 const unplanned=!!person,code=unplanned?'IS.PLANSIZ_TANIMLADIM':'IS.TANIMLADIM';
 const source=unplanned?w.c.schemas[code].girdi_semasi:w.c.schemas[code].girdi_semasi.properties.isler.items;
 const values={birim:w.state.unit,nereye:'PROJE',tur:'SURELI',tahmini_sure_dk:60,...!unplanned?{kisi_sayisi:1}:{},onay_gerekli:true,onay_beklet:false,...unplanned?{kisi:person,sira:list(w,person).length+1}:{}};
 const schema=()=>workDefinition(source,values,{unplanned});
 let queue=unplanned?(await w.c.read('LISTE',person,{},true)).deger:null;
 if(unplanned)values.sira=arr(queue?.isler).length+1;
 const d=modal(unplanned?'Plansız İş Ver':'Havuza Yeni İş',`<form class="work-form">${unplanned?`<div class="operation-context"><span>Çalışan</span><h3>${esc(w.name(person))}</h3></div>`:''}<div class="form-error" role="alert"></div><div data-work-fields></div>${unplanned?'<section class="work-placement"><label class="field"><span>Yeni Sıra *</span><select data-path="position"></select></label><div data-queue-preview></div></section>':''}<footer class="form-footer"><button class="btn" type="button" data-cancel>Vazgeç</button><button class="btn primary" type="submit">${unplanned?'Tanımla ve Ata':'Havuza Ekle'}</button></footer></form>`,{wide:true});
 const root=d.querySelector('[data-work-fields]'),draw=()=>{
  const invalid=[...root.querySelectorAll('[aria-invalid=true]')];
  if(invalid.length){const remaining=validationIssues(cleanValue(values,schema()),schema());for(const el of invalid){if(remaining.some(i=>i.path===el.dataset.path))continue;el.removeAttribute('aria-invalid');const field=el.closest('.field,.choice-list');field?.classList.remove('field-invalid');field?.querySelectorAll('.field-message').forEach(x=>x.remove());}if(!root.querySelector('[aria-invalid=true]'))d.querySelector('.form-error').textContent='';}
  if(!values.onay_gerekli)values.onay_beklet=false;
  if(unplanned){values.sira=Math.max(1,Math.min(arr(queue?.isler).length+1,values.sira));d.querySelector('[data-path=position]').innerHTML=positionOptions(arr(queue?.isler).length+1,values.sira);d.querySelector('[data-queue-preview]').innerHTML=preview(w,person,arr(queue?.isler),{kimlik:'@new',is_tanimi:values.is_tanimi||'Yeni İş'},values.sira);}};
 bindForm(root,schema,values,{client:w.c,code,refs:w.refs},draw);draw();
 if(unplanned)d.querySelector('[data-path=position]').onchange=e=>{values.sira=Number(e.target.value);draw();};
 submitDialog(w,d,async()=>{
  const g=cleanValue(values,schema()),issues=validationIssues(g,schema());
  if(g.nereye==='PROJE'&&values.etap===undefined)issues.push({path:'etap',message:'Etap veya Etap Dışı seçin.'});
  if(g.onay_beklet&&!g.onay_gerekli)g.onay_beklet=false;
  if(unplanned){g.kisi=person;g.sira=values.sira;const issue=queueIssue(arr(queue.isler),{kimlik:'@new'},g.sira);if(issue)issues.push({path:'position',message:issue});}
  showValidation(d,issues);if(issues.length)throw new Error([...new Set(issues.map(i=>i.message))].join(' '));
  if(g.etap===null)delete g.etap;
  if(g.tur==='ANLIK')g.tahmini_sure_dk=0;
  return w.c.confirmed(code,unplanned?g:{isler:[g]},[],unplanned?{expectedTargets:expectations(person,queue)}:{});
 },{onStale:async()=>{queue=(await w.c.read('LISTE',person,{},true)).deger;draw();}});
 return d;
}

export function bindWorkshop(w){
 const main=document.querySelector('#main');let dragged=null;
 const clear=()=>main.querySelectorAll('.drop-before,.drop-end').forEach(el=>el.classList.remove('drop-before','drop-end'));
 main.querySelectorAll('[data-job]').forEach(row=>{
  row.ondragstart=e=>{dragged={id:row.dataset.job,person:row.dataset.person};e.dataTransfer.setData('application/irp-job',JSON.stringify(dragged));e.dataTransfer.effectAllowed='move';};
  row.ondragend=()=>{clear();dragged=null;};
 });
 main.querySelectorAll('[data-drop-person]').forEach(target=>{
  const destination=e=>{const row=e.target.closest('.person-job');if(!row||row.dataset.job===dragged?.id)return null;return e.clientY<row.getBoundingClientRect().top+row.offsetHeight/2?row:row.nextElementSibling;};
  target.ondragover=e=>{e.preventDefault();clear();const before=destination(e);(before??target.querySelector('.work-queue')).classList.add(before?'drop-before':'drop-end');};
  target.ondragleave=e=>{if(!target.contains(e.relatedTarget))clear();};
  target.ondrop=async e=>{e.preventDefault();try{
   if(e.target.closest('.person-job')?.dataset.job===dragged?.id)return;
   const data=dragged??JSON.parse(e.dataTransfer.getData('application/irp-job')),person=target.dataset.dropPerson,before=target.querySelector('.drop-before')?.dataset.job??null;
   const position=dropPosition(list(w,person),data.id,before),code=data.person&&data.person!==person?'IS.DEVRETTIM':data.person===person?'IS.SIRALADIM':'IS.ATADIM';
   clear();if(!w.can(code))throw new Error('Bu işlem için yetkiniz bulunmuyor.');
   const record=w.refs.IS.find(r=>idOf(r)===data.id);if(!record)return;
   if(code==='IS.SIRALADIM'&&list(w,person).findIndex(r=>idOf(r)===data.id)===position-1)return;
   await workDialog(w,code+':'+data.id,()=>openWorkMove(w,code,record,{person,position,source:data.person}));
  }catch(ex){toast(ex.message,true);}finally{clear();dragged=null;}};
 });
}

export async function inspectWork(w,id){
 await w.formRefs('IS.DEGISTIRDIM');const r=w.refs.IS.find(r=>idOf(r)===id);if(!r)return;
 const [files,notes]=await Promise.all([w.c.read('WEB_DOSYALAR',id,{tur:'IS'},true),w.c.read('WEB_NOTLAR',id,{tur:'IS'},true)]);
 const facts=[['Proje / Faaliyet',w.name(r.proje??r.kategori)],['Etap',r.etap?w.name(r.etap):'Etap Dışı'],['Çalışan',(r.kisi??r.tamamlayan)?w.name(r.kisi??r.tamamlayan):'Henüz Atanmadı'],['Atayan',r.atayan?w.name(r.atayan):'Henüz Atanmadı'],['İş Türü',r.tur==='ANLIK'?'Anlık':'Süreli'],['Tahmini Süre',hours((r.tahmini_sure_dk??0)/60)],['Onay',r.onay_gerekli?(r.onay_beklet?'Onay Gelmeden Sonraki İşe Geçilemez':'Onay Beklerken Sonraki İşe Geçilebilir'):'Gerekmiyor']];
 const history=[['onay_bekleme_ani','Onaya Gönderildi'],['bitis_ani','Tamamlandı'],['iptal_ani','İptal Edildi']].filter(([k])=>r[k]).map(([k,t])=>`<li>${t} · ${esc(date(r[k]))} ${esc(time(r[k]))}</li>`).join('');
 const d=modal(workName(r),`<div class="work-detail"><div class="work-detail-heading"><p>${esc(context(w,r))}</p>${badge(r.durum)}</div><div class="row-actions work-detail-actions">${actionButtons(w,r)}</div><section><h3>İş Bilgileri</h3><p>${esc(r.is_tanimi??workName(r))}</p><dl class="work-facts">${facts.map(([k,v])=>`<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl></section><section><h3>Önce Bitmesi Gereken İşler</h3>${arr(r.on_isler).length?arr(r.on_isler).map(x=>`<p>${esc(w.name(typeof x==='string'?x:x.kimlik))}</p>`).join(''):'<p class="muted">Önkoşul Yok</p>'}</section>${r.not_?'<section><h3>Düzeltme Gerekçesi</h3><p>'+esc(r.not_)+'</p></section>':''}<section><h3>Notlar ve Dosyalar</h3>${arr(notes.deger).length?arr(notes.deger).map(n=>`<article class="task-note"><p>${esc(n.metin??'')}</p><small>${esc(w.name(n.kim??n.yazan))}</small></article>`).join(''):'<p class="muted">Henüz Not Yok</p>'}${fileList(arr(files.deger))}${button('Not ve İstek Ekle','operation',{code:'NOT.YAZDIM',id,kind:'IS'},'small')}</section><section><h3>İşin Geçmişi</h3>${history?'<ul>'+history+'</ul>':'<p class="muted">Henüz Teslim veya Tamamlama Yok</p>'}</section></div>`,{wide:true});
 d.onclick=async e=>{const el=e.target.closest('[data-action]');if(!el)return;try{if(['file','download-file'].includes(el.dataset.action)){await w.action(el,e);return;}d.close();await w.action(el,e);}catch(ex){toast(ex.message,true);}};headingCase(d);return d;
}
