// Karar 157: ortak web içinde HTML/CSS/JavaScript ekranı. İş kuralları Python
// modülünde, gerçekleşme/onaylı plan çekirdekte kalır. Ayrı oturum deposu yoktur.
export async function ac(host){const page=new Planlama(host);await page.load();return page;}
const F=(key,label,type='text',extra={})=>({key,label,type,...extra});

class Planlama{
 constructor(host){Object.assign(this,host);this.ed=this.ui.editor();this.tab='ozet';this.version=0;this.dirty=false;this.closed=false;this.drafts=new Map();this.dialogs=new Set();
  this.kok.onclick=e=>{const b=e.target.closest('[data-modul-islem]');if(b&&!b.disabled)void this.action(b.dataset.modulIslem,b).catch(error=>{if(!this.closed){this.error=error.message;this.render();}});};
  this.kok.onchange=e=>{if(e.target.matches('[data-proje]')){if(this.plan&&this.dirty)this.drafts.set(this.baglam.proje,structuredClone(this.plan));this.baglam.proje=e.target.value;this.projeSec(e.target.value);this.plan=this.drafts.get(e.target.value)??null;this.dirty=!!this.plan;void this.load();}else this.input(e.target);};
  this.kok.oninput=e=>this.input(e.target);
 }
 dispose(){this.closed=true;this.version++;clearTimeout(this.timer);for(const d of this.dialogs)d.close();this.dialogs.clear();this.kok.onclick=this.kok.onchange=this.kok.oninput=null;}
 refresh(context){this.baglam={...context,proje:this.baglam.proje};if(this.dirty||this.busy||this.dialogs.size)return;clearTimeout(this.timer);this.timer=setTimeout(()=>{if(!this.closed)void this.load();},400);}
 get p(){return this.baglam.projeler.find(p=>this.ui.idOf(p)===this.baglam.proje);}
 path(suffix=''){return '/projeler/'+encodeURIComponent(this.baglam.proje)+suffix;}
 input(el){
  if(this.plan&&(el.name==='neden'||el.hasAttribute('data-gerekce')||el.name==='kanit')){this.plan.degisiklik??={};if(el.name==='kanit')this.plan.degisiklik.kanitlar=el.value?[Number(el.value)]:[];else this.plan.degisiklik[el.name==='neden'?'neden':'gerekce']=el.value;this.dirty=true;return;}
  const row=el.closest('[data-plan-sira]');if(!row||!this.plan)return;
  const item=this.plan.satirlar[Number(row.dataset.planSira)];if(!item||!el.name)return;
  item[el.name]=el.type==='number'?Number(el.value):el.value||null;this.dirty=true;
 }
 async load(){
  const version=++this.version;if(!this.baglam.proje&&this.baglam.projeler.length){this.baglam.proje=this.ui.idOf(this.baglam.projeler[0]);this.projeSec(this.baglam.proje);}
  if(this.tab==='ayarlar'){try{this.settings=await this.istek('/ayarlar/sablonlar');if(version===this.version&&!this.closed)this.render();}catch(error){this.error=error.message;this.render();}return;}
  if(!this.p){this.render();return;}
  try{
   this.error='';const summary=await this.istek(this.path());if(version!==this.version||this.closed)return;this.summary=summary;
   if(summary.devir){
    if(this.tab==='plan'&&!this.dirty){
     this.plan=await this.istek(this.path('/plan'));this.templates=this.plan.satirlar.filter(s=>!s.etap);
     if(!this.baglam.yetkili||this.plan.satirlar.some(s=>s.etap))this.plan.satirlar=this.plan.satirlar.filter(s=>s.etap);
     this.documents=await this.istek(this.path('/klasorler'));
    }
    if(this.tab==='gantt')this.chart=await this.istek(this.path('/gantt'));
    if(this.tab==='gorevler'){this.tasks=await this.istek(this.path('/gorevler'));this.gate=await this.istek(this.path('/kapi'));}
    if(this.tab==='notlar')this.notes=await this.istek(this.path('/notlar'));
    if(this.tab==='belgeler')this.documents=await this.istek(this.path('/klasorler'));
    if(this.tab==='girdiler')this.source=await this.istek(this.path('/siparis-kaynagi'));
   }
   if(version===this.version&&!this.closed)this.render();
  }catch(error){if(version===this.version&&!this.closed){this.error=error.message;this.render();}}
 }
 select(name,value,rows,{blank='Seçin',nameOf=r=>r.ad,key=r=>this.ui.idOf(r)}={}){const e=this.ui.esc;return `<select name="${e(name)}"><option value="">${e(blank)}</option>${rows.map(r=>`<option value="${e(key(r))}" ${key(r)===value?'selected':''}>${e(nameOf(r))}</option>`).join('')}</select>`;}
 render(){
  if(this.closed)return;const {esc:e,panel,empty,date,table}=this.ui,p=this.p;
  if(this.tab==='ayarlar'){this.renderSettings();return;}
  if(!p){this.kok.innerHTML=(this.baglam.yetkili?'<button class="btn" data-modul-islem="tab" data-tab="ayarlar">Planlama Ayarları</button>':'')+empty('Önce Bir Proje Oluşturun','Projeyi açtıktan sonra planlamaya buradan devam edebilirsiniz.');return;}
  const context=`<div class="module-context"><label class="field"><span>Proje</span><select data-proje ${this.busy?'disabled':''}>${this.baglam.projeler.map(x=>`<option value="${e(this.ui.idOf(x))}" ${this.ui.idOf(x)===this.baglam.proje?'selected':''}>${e(x.ad)}</option>`).join('')}</select></label><span class="muted">${e(p.kod??'')} · ${date(p.teslim_tarihi)}</span></div>`;
  const tabs=[['ozet','Proje Devri'],['girdiler','Sipariş Girdileri'],['plan','Plan Hazırlama'],['gantt','Plan Ve Gerçekleşen'],['gorevler','Görevler'],['notlar','Bilgi Notları'],['belgeler','Belgeler'],...(this.baglam.yetkili?[['ayarlar','Planlama Ayarları']]:[])];
  let body='';
  if(!this.summary?.devir){
   body=panel('Proje Ekibine Devir',`<div class="panel-body"><h2>${e(p.ad)}</h2><p>Projenin planını ve ekip çalışmalarını hazırlayın.</p>${this.summary?.izinler?.devri_baslatabilir?'<button class="btn primary" data-modul-islem="baslat">Proje Devrini Başlat</button>':'<p class="muted">Devri proje sorumlusu veya yetkili başlatabilir.</p>'}</div>`);
  }else if(this.tab==='ozet'){
   body=panel('Proje Devri',`<div class="panel-body"><h2>${e(p.ad)}</h2><dl class="detail-list"><div><dt>Sorumlu</dt><dd>${e(this.summary.sorumlu_adi??this.ui.ad(p.sorumlu))}</dd></div><div><dt>Devir Başlangıcı</dt><dd>${date(this.summary.devir.baslama_ani)}</dd></div><div><dt>Hedef Teslim</dt><dd>${date(p.teslim_tarihi)}</dd></div></dl><div class="action-strip"><button class="btn primary" data-modul-islem="tab" data-tab="plan">Planı Hazırla</button><button class="btn" data-modul-islem="tab" data-tab="gantt">Gerçekleşeni Gör</button></div></div>`);
   body+=panel('Açılış Adımları',table([{label:'Adım',render:r=>e(r.ad)},{label:'Durum',render:r=>r.tamam?'Tamamlandı':e(r.aciklama??'Bekliyor')}],this.summary.acilis?.adimlar??[]))+`<div class="toolbar">${this.summary.izinler?.sunum_kaydedebilir?'<button class="btn" data-modul-islem="sunum">Açılış Toplantısını İşle</button>':''}${this.summary.izinler?.sorumlu_degistirebilir?'<button class="btn" data-modul-islem="sorumlu">Proje Sorumlusunu Değiştir</button>':''}</div>`;
  }else if(this.tab==='girdiler'){
   const input=this.source?.girdiler;
   body=panel('Siparişten Gelen Teknik Girdiler',`<div class="panel-body">${input?`<p>${e(input.konu??p.ad)}</p><h3>Gereksinimler</h3>${(input.gereksinimler??[]).map(r=>`<p>${e(r.metin)}</p>`).join('')||'<p>Gereksinim girilmemiş.</p>'}<h3>Kapsama Dahil</h3><p>${(input.kapsam?.dahil??[]).map(e).join(' · ')||'—'}</p><h3>Kapsam Dışı</h3><p>${(input.kapsam?.haric??[]).map(e).join(' · ')||'—'}</p>`:'<p>Bu projeye henüz siparişten teknik girdi aktarılmadı.</p>'}${this.summary?.izinler?.plan_degistirebilir?'<button class="btn" data-modul-islem="girdi-aktar">Sipariş Girdilerini Aktar</button>':''}</div>`);
  }else if(this.tab==='plan')body=this.planBody();
  else if(this.tab==='gantt'){
   const stages=this.chart?.etaplar??[];
   body=this.ui.gantt(stages.map(r=>({...r,tur:'ETAP'})))+panel('Etaplar',table([{label:'Etap',render:r=>e(r.ad)},{label:'Birim',render:r=>e(this.ui.ad(r.birim))},{label:'Durum',render:r=>e(r.renk_adi??'Plan bekliyor')},{label:'İlerleme',render:r=>r.ilerleme==null?'—':e(r.ilerleme)+' %'}],stages));
  }else if(this.tab==='gorevler'){
   const tasks=(this.tasks?.etaplar??[]).flatMap(stage=>stage.gorevler??[]);
   body=(this.gate?.durum==='KAPALI'?'<p>Tasarım girdisi bekleniyor.</p>'+(this.gate.gecebilir?'<button class="btn" data-modul-islem="kapi-gec">Gerekçeyle İlerle</button>':''):'')+(this.summary?.izinler?.gorev_atayabilir?`<div class="toolbar" style="margin-bottom:16px"><button class="btn primary" data-modul-islem="gorev">Görev Ata</button></div>`:'')+panel('Proje Görevleri',table([{label:'Görev',render:r=>e(r.ad??'Görev')},{label:'Çalışan',render:r=>e(this.ui.ad(r.kisi))},{label:'Teslim',render:r=>date(r.planlanan_bitis)},{label:'Durum',render:r=>this.ui.badge(r.durum)}],tasks));
  }else if(this.tab==='notlar'){
   const notes=this.notes?.notlar??[];
   body=(this.summary?.izinler?.not_yazabilir?`<div class="toolbar" style="margin-bottom:16px"><button class="btn primary" data-modul-islem="not">Bilgi Notu Ekle</button></div>`:'')+panel('Bilgi Notları',table([{label:'Not',render:r=>e(r.metin_basi)},{label:'Birim',render:r=>e(this.ui.ad(r.alici_birim))},{label:'Yazan',render:r=>e(r.yazan_adi??this.ui.ad(r.yazan))},{label:'',render:r=>`<button class="btn small" data-modul-islem="not-ayrinti" data-id="${e(r.not_kimligi)}">Alıcılar Ve Ayrıntı</button>`}],notes));
  }else if(this.tab==='belgeler'){
   const folders=this.documents?.klasorler??[];
   body=(folders.some(f=>f.dosya_ekleyebilir)?'<div class="toolbar" style="margin-bottom:16px"><button class="btn primary" data-modul-islem="belge">Belge Yükle</button></div>':'')+panel('Proje Belgeleri',table([{label:'Klasör',render:r=>e(r.ad)},{label:'Sorumlu Birim',render:r=>e(this.ui.ad(r.sorumlu_birim))},{label:'Belgeler',render:r=>(r.dosyalar??[]).map(d=>e(d.ad)+(d.konum?.startsWith('irp-dosya:')?` <button class="btn small" data-modul-islem="dosya-ac" data-file="${e(d.konum.slice(10))}">İndir</button>`:'<small>Harici Belge</small>')).join('<br>')||'—'}],folders));
  }
  this.kok.innerHTML=context+`<div class="module-tabs">${tabs.map(([id,name])=>`<button class="btn ${this.tab===id?'primary':''}" data-modul-islem="tab" data-tab="${id}" ${!this.summary?.devir&&!['ozet','ayarlar'].includes(id)?'disabled':''}>${name}</button>`).join('')}</div>`+(this.error?this.ui.errorBox(this.error):'')+body;
  if(this.busy)this.kok.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);
  if(this.tab==='plan'&&!this.summary?.izinler?.plan_degistirebilir)this.kok.querySelectorAll('input,select:not([data-proje])').forEach(el=>el.disabled=true);
  this.kok.querySelectorAll('[data-plan-sira]').forEach(row=>{if(this.plan?.satirlar[Number(row.dataset.planSira)]?.etap)row.querySelector('[name=birim]').disabled=true;});
  this.ui.headingCase(this.kok);
 }
 planBody(){
  const {esc:e,panel,empty,table,date}=this.ui;if(!this.plan)return empty('Plan Açılıyor','');
  const rows=this.plan.satirlar??[],edit=this.summary?.izinler?.plan_degistirebilir??(this.baglam.yetkili||this.summary?.proje?.sorumlu===this.baglam.kisi.kimlik);
  const cols=['Etap','Birim','Başlangıç','Bitiş','Hedef Saat','Sorumlu'];
  const cells=rows.map((s,i)=>`<tr data-plan-sira="${i}"><td><input name="ad" aria-label="Etap Adı" value="${e(s.ad)}"></td><td>${this.select('birim',s.birim,this.baglam.birimler)}</td><td><input name="baslangic" aria-label="Başlangıç" type="date" value="${e(s.baslangic??'')}"></td><td><input name="bitis" aria-label="Bitiş" type="date" value="${e(s.bitis??'')}"></td><td><input name="hedef_saat" aria-label="Hedef Saat" type="number" min="0" step="1" value="${e(s.hedef_saat??0)}"></td><td>${this.select('sorumlu',s.sorumlu,this.baglam.kisiler.filter(x=>x.aktif!==false),{blank:'Birim Sorumlusu'})}</td></tr>`).join('');
  const history=this.plan.cekirdek_surumleri??[];
  const proofs=(this.documents?.klasorler??[]).flatMap(f=>f.dosyalar??[]).filter(d=>d.tur==='PLAN_KANITI');
  return `<div class="toolbar" style="margin-bottom:16px">${edit?'<button class="btn" data-modul-islem="mevcut">Yalnız Mevcut Etaplar</button>'+(!this.plan.b0_var&&this.baglam.yetkili&&this.templates?.length?'<button class="btn" data-modul-islem="sablonlar">Şablon Etapları Ekle</button>':'')+'<button class="btn" data-modul-islem="taslak">Taslağı Kaydet</button><button class="btn primary" data-modul-islem="plan-gonder">Planı Onayla Ve Yayımla</button>':''}</div>`+
   panel(this.plan.b0_var?'Plan Değişikliği':'Başlangıç Planı',`<div class="table-wrap"><table class="data-table module-plan-table"><thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>${cells}</tbody></table></div>`)+
   (this.plan.b0_var?`<div class="module-context" style="margin-top:16px"><label class="field"><span>Değişiklik Nedeni</span>${this.select('neden',this.plan.degisiklik?.neden,[{kod:'MUSTERI_OTELEMESI',ad:'Müşteri Ötelemesi'},{kod:'KARSILIKLI_ANLASMA',ad:'Karşılıklı Anlaşma'}],{key:r=>r.kod})}</label><label class="field"><span>Gerekçe</span><input data-gerekce value="${e(this.plan.degisiklik?.gerekce??'')}" placeholder="Değişikliğin nedenini yazın"></label><label class="field"><span>Plan Kanıtı</span>${this.select('kanit',this.plan.degisiklik?.kanitlar?.[0],proofs,{key:r=>r.kimlik})}</label>${edit?'<button class="btn" data-modul-islem="belge">Plan Kanıtı Yükle</button>':''}</div>`:'')+
   (history.length?panel('Onaylı Planlar',table([{label:'Plan',render:r=>e(r.no)},{label:'Onay',render:r=>date(r.onay_ani)},{label:'Onaylayan',render:r=>e(this.ui.ad(r.onaylayan))},{label:'Gerekçe',render:r=>e(r.gerekce??'İlk Plan')}],history)):'');
 }
 payload(){const r=this.plan;return {satirlar:(r.satirlar??[]).map((x,i)=>({...x,sira:i+1,hedef_saat:Number(x.hedef_saat??0)})),
  neden:this.kok.querySelector('[name=neden]')?.value||r.degisiklik?.neden||null,
  gerekce:this.kok.querySelector('[data-gerekce]')?.value||r.degisiklik?.gerekce||null,kanitlar:r.degisiklik?.kanitlar??[]};}
 async action(action,b){
  if(this.busy)return;
  if(action==='dosya-ac'){this.ed.download(await this.istek('/ortak-dosyalar/'+b.dataset.file));return;}
  if(action==='not-ayrinti'){const value=await this.istek(this.path('/notlar/'+encodeURIComponent(b.dataset.id))),e=this.ui.esc;const d=this.ui.modal('Bilgi Notu Ve Alıcıları',`<p>${e(value.metin)}</p><p>${e(value.gordu_ozeti)}</p>`+this.ui.table([{label:'Alıcı',render:r=>e(r.kisi_adi??this.ui.ad(r.kisi))},{label:'Durum',render:r=>r.gordu?'Gördü':'Henüz Görmedi'}],value.alicilar??[]));this.dialogs.add(d);d.addEventListener('close',()=>this.dialogs.delete(d),{once:true});return;}
  if(action==='kapi-gec')return this.formDialog('Tasarım Girdisi Olmadan İlerleme',[F('gerekce','Gerekçe','textarea',{required:true})],async g=>{await this.istek(this.path('/kapi/gecis'),{method:'POST',body:g});});
  if(action==='girdi-aktar'){const result=await this.istek(this.path('/siparis-kaynagi'),{method:'POST',body:{}});if(result.durum!=='AKTARILDI')throw Error(result.mesaj??'Sipariş girdileri aktarılmadı.');await this.load();return;}
  if(action==='ayar-kaydet'){const body={};for(const group of ['etaplar','klasorler','kategoriler'])body[group]=[...this.kok.querySelectorAll('[data-ayar-grup="'+group+'"]')].map(row=>({kod:row.dataset.kod,...Object.fromEntries([...row.querySelectorAll('select,input')].map(el=>[el.name,el.type==='checkbox'?el.checked:el.value||null]))}));await this.istek('/ayarlar/sablonlar',{method:'PUT',body});this.ui.toast('Planlama ayarları kaydedildi.');await this.load();return;}
  if(action==='sunum')return this.formDialog('Açılış Toplantısı',[F('tarih','Toplantı Tarihi','date',{default:this.baglam.tarih,required:true})],async g=>{await this.istek(this.path('/sunum'),{method:'POST',body:g});});
  if(action==='sorumlu')return this.formDialog('Proje Sorumlusunu Değiştir',[F('sorumlu','Yeni Sorumlu','select',{options:this.baglam.kisiler.filter(k=>k.aktif!==false).map(k=>({value:k.kimlik,label:k.ad})),required:true})],async g=>{await this.istek(this.path('/sorumlu'),{method:'PUT',body:{...g,proje_surum:this.summary.proje.surum}});await this.yenile();});
  if(action==='tab'){if(this.plan&&this.dirty)this.drafts.set(this.baglam.proje,structuredClone(this.plan));this.tab=b.dataset.tab;await this.load();return;}
  if(action==='mevcut'){this.plan.satirlar=this.plan.satirlar.filter(s=>s.etap);this.dirty=true;this.render();return;}
  if(action==='sablonlar'){this.plan.satirlar.push(...this.templates);this.templates=[];this.dirty=true;this.render();return;}
  if(action==='belge'){await this.documentDialog();return;}
  if(action==='gorev'){await this.taskDialog();return;}
  if(action==='not'){await this.noteDialog();return;}
  const payload=['taslak','plan-gonder'].includes(action)?this.payload():null;
  this.busy=true;this.render();let failure='';
  try{
   if(action==='baslat'){await this.istek(this.path('/devir'),{method:'POST',body:{}});this.tab='plan';}
   if(payload){
    await this.istek(this.path('/plan/taslak'),{method:'PUT',body:payload});this.dirty=false;this.drafts.delete(this.baglam.proje);
    if(action==='plan-gonder'){const result=await this.istek(this.path('/plan/gonder'),{method:'POST',body:{}});if(result.degisiklik)throw new Error('Planın bazı satırları tamamlanamadı; güncel durumu kontrol edin.');}
   }
   this.ui.toast(action==='taslak'?'Plan taslağı kaydedildi.':action==='plan-gonder'?'Plan işlemi tamamlandı.':'Proje devri başlatıldı.');
   this.plan=null;await this.yenile();
  }catch(error){failure=error.message;}
  finally{this.busy=false;await this.load();if(failure){this.error=failure;this.render();}}
 }
 async taskDialog(){
  const data=await this.istek(this.path('/gorevler')),docs=await this.istek(this.path('/klasorler'));
  if(this.closed)return;
  const stages=data.etaplar??[],people=this.baglam.kisiler.filter(p=>p.aktif!==false),tgg=(docs.klasorler??[]).flatMap(f=>f.dosyalar??[]).filter(d=>d.tur==='TGG');
  const defs=[F('ad','Görev Adı','text',{required:true}),F('etap','Etap','select',{options:stages.map(r=>({value:r.kimlik,label:r.ad})),required:true}),F('kisiler','Çalışanlar','select',{options:people.map(r=>({value:r.kimlik,label:r.ad})),multiple:true,required:true}),F('teslim_tarihi','Teslim Tarihi','date',{default:this.baglam.tarih,required:true}),F('zaman_degeri','Zaman Değeri (Saat)','integer',{min:1,default:1,required:true}),F('zorluk','Zorluk (1–5)','integer',{min:1,default:3,required:true}),F('oncelik','Öncelik','select',{options:[{value:'NORMAL',label:'Normal'},{value:'YUKSEK',label:'Yüksek'},{value:'ACIL',label:'Acil'}],default:'NORMAL',required:true}),F('is_tanimi','İşin Açıklaması','textarea',{nullable:true}),F('onay_gerekli','Teslimden Sonra Onay Beklesin','checkbox'),F('onaylayan','Onaylayacak Kişi','select',{options:people.map(r=>({value:r.kimlik,label:r.ad})),default:this.baglam.kisi.kimlik,nullable:true}),F('dosya_gerekli','Teslimde Dosya Gerekli','checkbox'),F('tgg','Tasarım Gözden Geçirme Görevi','checkbox'),F('tgg_dosyasi','Tasarım Gözden Geçirme Belgesi','select',{options:tgg.map(r=>({value:r.kimlik,label:r.ad})),numeric:true,nullable:true})];
  return this.formDialog('Proje Görevi Ata',defs,async g=>{const stage=stages.find(r=>r.kimlik===g.etap),result=await this.istek(this.path('/gorevler'),{method:'POST',body:{...g,etap_surum:stage?.surum}});await this.yenile();const rejected=(result.sonuclar??[]).filter(r=>r.sonuc!=='BASARILI');if(rejected.length)this.ui.toast(rejected.map(r=>this.ui.ad(r.kisi)+': '+r.mesaj).join(' · '));else this.ui.toast('Görev atandı.');});
 }
 async noteDialog(){
  const data=await this.istek(this.path('/notlar')),docs=await this.istek(this.path('/klasorler')),tasks=await this.istek(this.path('/gorevler'));
  if(this.closed)return;
  const files=(docs.klasorler??[]).flatMap(f=>f.dosyalar??[]),stages=tasks.etaplar??[],defs=[F('kategori','Konu','select',{options:(data.kategoriler??[]).map(r=>({value:r.kod,label:r.ad})),required:true}),F('alici_birim','İlgili Birim','select',{options:this.baglam.birimler.map(r=>({value:r.kimlik,label:r.ad})),required:true}),F('metin','Bilgi Notu','textarea',{required:true}),F('etap','İlgili Etap','select',{options:stages.map(r=>({value:r.kimlik,label:r.ad})),nullable:true}),F('bagli_gorev','İlgili Görev','select',{options:stages.flatMap(r=>r.gorevler??[]).map(r=>({value:r.kimlik,label:r.ad})),nullable:true}),F('ekler','Proje Belgelerinden Ekler','select',{options:files.map(r=>({value:r.kimlik,label:r.ad})),multiple:true,numeric:true})];
  return this.formDialog('Bölüm Bilgi Notu',defs,async g=>{const result=await this.istek(this.path('/notlar'),{method:'POST',body:g});await this.yenile();this.ui.toast(result.uyari??'Bilgi notu gönderildi.');});
 }
 async documentDialog(){
  const {toast}=this.ui;
  const data=await this.istek(this.path('/klasorler'));if(this.closed)return;
  const folders=data.klasorler.filter(f=>f.dosya_ekleyebilir);
  const types=[['TASARIM_GIRDISI','Tasarım Girdisi'],['RISK_ANALIZI','Risk Analizi'],['TGG','Tasarım Gözden Geçirme'],['TUTANAK','Tutanak'],['PLAN_KANITI','Plan Kanıtı'],['DIGER','Diğer']].map(([value,label])=>({value,label}));
  return this.formDialog('Proje Belgesi Yükle',[F('tur','Belge Türü','select',{options:types,default:this.tab==='plan'?'PLAN_KANITI':'TASARIM_GIRDISI',required:true}),F('dosya','Dosya (En Fazla 1 MB)','file',{required:true}),F('klasor','Klasör','select',{options:folders.map(f=>({value:f.kimlik,label:f.ad})),required:true,numeric:true,default:folders.find(f=>f.kod==='ETUD_ONAY')?.kimlik}),F('aciklama','Açıklama','textarea',{nullable:true})],async g=>{
   const uploaded=await this.istek('/ortak-dosyalar',{method:'POST',body:await this.ed.fileBody(g.dosya,{tur:'PROJE',kimlik:this.baglam.proje})});
   const file=await this.istek(this.path('/dosyalar'),{method:'POST',body:{tur:g.tur,klasor:g.klasor,aciklama:g.aciklama,ad:uploaded.ad,konum:uploaded.konum,parmak_izi:uploaded.parmak_izi}});
   if(this.plan&&g.tur==='PLAN_KANITI'){this.plan.degisiklik??={};this.plan.degisiklik.kanitlar=[file.dosya.kimlik];this.dirty=true;}
   this.documents=await this.istek(this.path('/klasorler'));toast('Belge yüklendi.');
  });
 }
 async formDialog(title,defs,save){const d=this.ui.modal(title,`<form class="module-editor">${this.ed.fields(defs)}<div class="form-error"></div><button class="btn primary" type="submit">Tamamla</button></form>`,{wide:true});this.dialogs.add(d);d.addEventListener('close',()=>this.dialogs.delete(d),{once:true});d.querySelector('form').onsubmit=async event=>{event.preventDefault();const form=event.target;if(this.busy||!form.reportValidity())return;this.busy=true;form.setAttribute('aria-busy','true');const button=form.querySelector('[type=submit]');button.disabled=true;try{await save(this.ed.read(form,defs));if(this.closed)return;d.close();await this.load();}catch(error){form.querySelector('.form-error').textContent=error.message;}finally{this.busy=false;form.removeAttribute('aria-busy');button.disabled=false;if(!this.closed)this.render();}};return d;}
 renderSettings(){const e=this.ui.esc;let body='<button class="btn" data-modul-islem="tab" data-tab="ozet">Projeye Dön</button><h2>Planlama Birim Eşlemeleri</h2>';for(const [group,label,field] of [['etaplar','Etap Şablonları','varsayilan_birim'],['klasorler','Proje Klasörleri','sorumlu_birim'],['kategoriler','Bilgi Notu Konuları','varsayilan_birim']]){const data=this.settings?.[group]??[];body+=this.ui.panel(label,`<div class="table-wrap"><table class="data-table"><thead><tr><th>Ad</th><th>Birim</th>${group==='etaplar'?'<th>Aktif</th>':''}</tr></thead><tbody>${data.map(row=>`<tr data-ayar-grup="${group}" data-kod="${e(row.kod)}"><td>${e(row.ad)}</td><td>${this.select(field,row[field],this.baglam.birimler)}</td>${group==='etaplar'?`<td><input type="checkbox" name="aktif" ${row.aktif?'checked':''}></td>`:''}</tr>`).join('')}</tbody></table></div>`);}this.kok.innerHTML='<div class="module-editor">'+(this.error?this.ui.errorBox(this.error):'')+body+'<button class="btn primary" data-modul-islem="ayar-kaydet">Birim Eşlemelerini Kaydet</button></div>';this.ui.headingCase(this.kok);}
}
