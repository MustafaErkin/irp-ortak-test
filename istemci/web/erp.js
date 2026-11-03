import {Workspace} from './pages.js';
import {esc,idOf,arr,num,hours,date,period,badge,button,empty,panel,table} from './ui.js';
import {NAV,OPERATIONS,actionsFor} from './actions.js';
import {portfolio,staffing,sampleProjects,sampleReports,samplePerformance} from './management.js';

export class ErpWorkspace extends Workspace {
 can(code){
  if(!this.c.admin&&(['PROJE.ACTIM','PROJE.DEGISTIRDIM','PROJE.KAPATTIM','ETAP.TANIMLADIM'].includes(code)||['people','units','machines','calendar','settings'].includes(OPERATIONS[code]?.page)))return !this.c.readonly&&this.c.context.islem_izinleri?.includes(code)===true;
  return super.can(code);
 }
 allowedPages(){
  const pages=super.allowedPages().filter(p=>p!=='modules');
  if(this.c.readonly)return pages;
  if(!this.c.manager)return ['overview','tasks','notifications','projects','objects','leaves','overtime','performance','modules'];
  return [...pages,'modules'];
 }
 async load(){
  if(!this.c.projects.some(p=>idOf(p)===this.state.project))this.state.project=idOf(this.c.projects[0]);
  if(this.c.readonly){
   const meta=this.c.sample.gosterim,s=this.state;
   if(['staffing','performance'].includes(this.page))Object.assign(s,meta.personel_donemi);
   if(this.page==='performance'){
    if(!meta.performans_kisileri.includes(s.person))s.person=meta.performans_kisileri[0];
    s.unit=this.c.people.find(p=>idOf(p)===s.person)?.birim;
   }
   if(this.page==='projects')Object.assign(s,meta.proje_donemleri[s.project]);
   if(this.page==='reports'){
    const months=meta.aylar[s.project]??[];
    if(!months.includes(s.month))s.month=months.includes('2026-11')?'2026-11':months.at(-1);
    if(s.month)Object.assign(s,period(s.month+'-01'));
   }
  }
  await super.load();
 }
 get title(){return this.page==='modules'?'Modüller':super.title;}
 body(){return this.page==='modules'?this.modules():super.body();}
 opButtons(page=this.page){
  if(['overview','tasks','modules','approvals'].includes(page))return '';
  if(page!=='projects')return super.opButtons(page);
  const primary=this.can('PROJE.ACTIM')?button('Yeni Proje','operation',{code:'PROJE.ACTIM'},'primary'):'';
  const other=actionsFor(page).filter(a=>this.can(a.code)&&a.code!=='PROJE.ACTIM');
  return primary+(this.c.projects.length&&other.length?this.more(other,'Proje İşlemleri'):'');
 }
 filters(){
  if(['overview','modules','assign'].includes(this.page))return '';
  if(this.c.readonly){
   const s=this.state,meta=this.c.sample.gosterim,parts=[];
   if(['projects','reports'].includes(this.page))parts.push(this.filterSelect('project','Proje',this.c.projects,s.project));
   if(this.page==='reports')parts.push(this.filterSelect('month','Dönem',(meta.aylar[s.project]??[]).map(m=>({kimlik:m,ad:new Date(m+'-01T12:00:00').toLocaleDateString('tr-TR',{month:'long',year:'numeric'})})),s.month));
   if(this.page==='performance')parts.push(this.filterSelect('person','Çalışan',this.c.people.filter(p=>meta.performans_kisileri.includes(idOf(p))),s.person));
   if(['performance','staffing'].includes(this.page))parts.push(`<span class="filter-info">${date(s.bas)} – ${date(s.bit)}</span>`);
   return `<div class="filter-bar">${parts.join('')}</div>`;
  }
  if(this.page==='projects'&&!this.c.projects.length)return '';
  if(this.page!=='projects')return super.filters();
  return `<div class="filter-bar">${this.filterSelect('project','Proje',this.c.projects,this.state.project)}<label class="search-box"><input type="search" data-search placeholder="Bu projede ara…" aria-label="Bu projede ara"></label></div>`;
 }
 overview(){
  if(this.c.readonly)return portfolio(this);
  const c=this.c,projects=c.projects,tasks=this.refs.GOREV.filter(r=>r.kisi===c.person&&!['BITTI','IPTAL'].includes(r.durum)&&r.tur!=='ONAY');
  const all=this.refs.GOREV.filter(r=>!['BITTI','IPTAL'].includes(r.durum)&&r.tur!=='ONAY'),jobs=this.refs.IS.filter(r=>!['BITTI','IPTAL'].includes(r.durum));
  const intro=c.readonly?'Projelerin ve kaynakların bütün görünümü.':c.admin?'Projeleri başlatın, sorumluları belirleyin ve sonuçları izleyin.':c.manager?'Ekibin işlerini planlayın, dağıtın ve teslimleri değerlendirin.':'Görevlerinizi kabul edin, çalışmanızı teslim edin ve geri bildirimleri izleyin.';
  const quick=c.readonly?button('Proje Sonuçları','navigate',{page:'projects'},'primary'):c.admin?button('Yeni Proje Oluştur','operation',{code:'PROJE.ACTIM'},'primary'):c.manager?button('Görev Ata','navigate',{page:'assign'},'primary'):button('İşlerime Git','navigate',{page:'tasks'},'primary');
  const start=!projects.length&&!c.readonly?`<section class="start-card"><div class="start-symbol">${c.admin?'01':'→'}</div><div><span class="eyebrow">Çalışmaya Hazır</span><h2>${c.admin?'İlk Projenizi Oluşturun':'Henüz Proje Açılmadı'}</h2><p>${c.admin?'Ekibiniz ve firma düzeniniz hazır. Bir proje açarak etapları ve sorumluları belirleyin.':'Size atanan işler ve projeler bu çalışma alanında görünecek.'}</p>${c.admin?button('Proje Oluştur','operation',{code:'PROJE.ACTIM'},'primary'):button('İşlerimi Gör','navigate',{page:'tasks'})}</div></section>`:'';
  const projectTable=table([{label:'Proje',render:r=>`<strong>${esc(r.ad)}</strong><small>${esc(r.kod??idOf(r))}</small>`},{label:'Sorumlu',render:r=>esc(this.name(r.sorumlu))},{label:'Teslim',render:r=>date(r.teslim_tarihi)},{label:'İlerleme',render:r=>this.progress(this.value('PROJE_DURUM',idOf(r))?.yuzde)},{label:'',render:r=>button('Projeyi Aç','project-open',{id:idOf(r)},'small')}],projects);
  return `<section class="workspace-intro"><div><span class="eyebrow">${c.readonly?'Yönetim Özeti':esc(c.me.ad??'Çalışma Alanı')}</span><h2>${c.readonly?'Şirketin Genel Görünümü':'Çalışma Özeti'}</h2><p>${intro}</p></div>${quick}</section>${this.metrics([['Projeler',num(projects.length),'Görünür proje'],['Açık Görevler',num(c.manager?all.length:tasks.length),'Planlanan ve devam eden'],['Atölye İşleri',num(jobs.length),'Tamamlanmayı bekleyen'],['Bekleyen Onaylar',num([...all,...jobs].filter(r=>r.durum==='ONAY_BEKLIYOR').length),'Teslim edilen işler']])}${start}<div class="two-columns">${panel('Projeler',projects.length?projectTable:empty('Henüz Proje Yok','Yeni projeler burada listelenecek.'))}${panel('İşlerim',tasks.length?this.taskTable(tasks.slice(0,6)):empty('Bekleyen Göreviniz Yok','Size verilen yeni görevler burada görünür.'),button('Tüm İşlerim','navigate',{page:'tasks'},'small'))}</div>`;
 }
 projects(){
  if(this.c.readonly)return sampleProjects(this);
  if(!this.c.projects.length)return `<section class="empty-workspace"><div class="empty-project-icon">▱</div><span class="eyebrow">Proje Yönetimi</span><h2>Projelerinizi Buradan Yönetin</h2><p>Proje açıldıktan sonra etaplar, sorumlular, iş planı ve gerçekleşen sonuçlar burada bir araya gelir.</p>${this.can('PROJE.ACTIM')?button('İlk Projeyi Oluştur','operation',{code:'PROJE.ACTIM'},'primary'):''}</section>`;
  const p=this.c.projects.find(r=>idOf(r)===this.state.project);if(!p)return '';
  const es=arr(this.value('ETAPLAR',idOf(p)));
  return `<section class="project-summary"><div class="project-monogram">${esc((p.kod??idOf(p)).slice(-2))}</div><div><span class="eyebrow">${esc(p.kod??idOf(p))}</span><h2>${esc(p.ad)}</h2><p>${esc(this.name(p.sorumlu))} <span>·</span> ${esc(p.musteri??'Müşteri belirtilmedi')}</p></div><div class="toolbar">${this.can('ETAP.TANIMLADIM')?button('Etap Ekle','operation',{code:'ETAP.TANIMLADIM'},'primary'):''}${this.can('GOREV.ATADIM')&&es.length?button('Planlama Görevi Ver','plan-task',{},'secondary'):''}</div></section>${super.projects()}`;
 }
 tasks(){
  const rows=this.refs.GOREV.filter(r=>r.kisi===this.c.person&&r.tur!=='ONAY'),tab=this.state.tab||'open',visible=rows.filter(r=>tab==='all'||tab==='open'&&!['BITTI','IPTAL'].includes(r.durum)||tab==='done'&&r.durum==='BITTI');
  const selected=visible.find(r=>idOf(r)===this.state.selected);
  const detail=selected?`<aside class="task-detail"><span class="eyebrow">Görev Ayrıntısı</span><h2>${esc(selected.ad)}</h2>${badge(selected.durum)}<p class="task-instruction">${esc(selected.is_tanimi||'Ek bir talimat belirtilmedi.')}</p><dl class="detail-list"><div><dt>Proje</dt><dd>${esc(this.name(selected.proje))}</dd></div><div><dt>Etap</dt><dd>${esc(this.name(selected.etap))}</dd></div><div><dt>Teslim Tarihi</dt><dd>${date(selected.teslim_tarihi)}</dd></div><div><dt>Zaman Değeri</dt><dd>${hours(selected.zaman_degeri)}</dd></div><div><dt>Onaylayan</dt><dd>${esc(this.name(selected.onaylayan))}</dd></div></dl><div class="action-strip">${['GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM'].filter(code=>this.available(code,selected)).map(code=>button(OPERATIONS[code].title,'operation',{code,id:idOf(selected),kind:'GOREV'},'primary')).join('')}${button('Not ve @ İstek','operation',{code:'NOT.YAZDIM',id:idOf(selected),kind:'GOREV'})}${button('Dosyalar ve Geçmiş','inspect',{kind:'GOREV',id:idOf(selected)})}</div>${selected.durum==='ONAY_BEKLIYOR'?'<div class="notice">Tesliminiz alındı. Onaylayan kişinin değerlendirmesi bekleniyor.</div>':''}</aside>`:`<aside class="task-detail task-placeholder"><div class="empty-symbol">▤</div><h2>Görevinizi Seçin</h2><p>Talimat, teslim bilgileri ve yapabileceğiniz işlemler burada görünür.</p></aside>`;
  return this.tabs([['open','Açık Görevler'],['done','Tamamlananlar'],['all','Bütün Görevler']])+`<div class="task-workspace">${panel('Görevlerim',this.taskTable(visible))}${detail}</div>`;
 }
 modules(){
  const modules=arr(this.c.context.moduller);
  return modules.length?panel('Devredeki Modüller',table([{label:'Modül',render:r=>`<strong>${esc(r.ad??r.kod)}</strong>`},{label:'Kod',key:'kod'},{label:'Durum',render:()=>badge('ACIK')}],modules)):`<section class="empty-workspace"><div class="empty-project-icon">▦</div><span class="eyebrow">Ortak Çalışma Alanı</span><h2>Modüller</h2><p>Henüz devreye alınmış modül yok. Modüller bağlandığında görev ve yetkilerinize uygun çalışma alanları burada yer alacak.</p></section>`;
 }
 staffing(){return staffing(this);}
 reports(){return this.c.readonly?sampleReports(this):super.reports();}
 performance(){return this.c.readonly?samplePerformance(this):super.performance();}
 logs(){return panel('Bu Bilgisayarın İşlemleri',table([{label:'Tarih',render:r=>date(r.olay?.oldugu_an)},{label:'İşlem',render:r=>esc(OPERATIONS[r.olay?.eylem_kodu]?.title??r.olay?.eylem_kodu)},{label:'Durum',render:r=>badge(r.durum)},{label:'',render:r=>r.durum==='GONDERILEMEDI'?button('Yeniden Gönder','retry-management',{id:r.olay.olay_kimligi},'small'):''}],this.logRows??[]));}
 async action(el,event){
  if(el.dataset.action==='project-open'){this.state.project=el.dataset.id;if(this.page==='projects')await this.load();else location.hash='projects';return;}
  if(el.dataset.action==='plan-task'){
   await this.formRefs();const row=this.newTask();Object.assign(row,{ad:'Etapların İş Planını Hazırlayın',is_tanimi:'Etapların tarihlerini ve emek hedeflerini düzenleyin. İş planını oluşturup değerlendirmeye sunun.',kisi:this.c.projects.find(p=>idOf(p)===this.state.project)?.sorumlu??'K004',etap:this.refs.ETAP.find(e=>e.proje===this.state.project)?.kimlik,dosya_gerekli:false});this.draftRows.push(row);this.draftIndex=this.draftRows.length-1;location.hash='assign';return;
  }
  return super.action(el,event);
 }
}
