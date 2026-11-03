import {esc,idOf,arr,hours,date,time,isoDay,badge,panel,table,empty} from './ui.js';
import {displayText} from './presentation.js';

export function summaryTime(value,day){
 if(!value||!Number.isFinite(Date.parse(value)))return '—';
 return (isoDay(new Date(value))===day?'':date(value)+' · ')+time(value);
}
export function summaryTasks(summary,refs=[]){
 return Object.entries(summary?.gorevler??{}).map(([id,snapshot])=>{
  const task=refs.find(r=>idOf(r)===id)??{};
  return {...task,...snapshot,kimlik:id,ad:displayText(task.ad??'Görev Bilgisi Gösterilemiyor',key=>{const ref=refs.find(r=>idOf(r)===key);return ref?.ad??ref?.islem;})};
 }).sort((a,b)=>String(a.atama_ani??'').localeCompare(String(b.atama_ani??''))||a.ad.localeCompare(b.ad,'tr'));
}
const bucketNames={CALISMA:'Çalışma',YENIDEN_ISLEME:'Yeniden İşleme',PLANSIZ:'Plansız Çalışma',BEKLEME:'Bekleme',BEKLEME_ARIZA:'Duruş Beklemesi',BEKLEME_ON_IS:'Ön İş Beklemesi',BEKLEME_ONAY:'Onay Beklemesi',ARIZA:'Duruş',MOLA:'Mola',SABIT_MOLA:'Sabit Mola',GECIS:'İşler Arası Geçiş',TANIMSIZ:'Açıklama Bekleyen Süre',ON_IS_BEKLEME:'Ön İş Beklemesi',ONAY_BEKLEME:'Onay Beklemesi'};

export function dailySummary(w,report,{pending=false}={}){
 if(!report)return empty('Gün Özeti Hazır Değil','Seçili günün bilgilerini yenileyerek tekrar deneyebilirsiniz.');
 const day=report.gun??w.state.day,person=report.kisi??w.state.person,summary=report.ozet??{},tasks=summaryTasks(summary,w.refs.GOREV);
 const clock=(r,key,unneeded=false)=>r[key]?summaryTime(r[key],day):unneeded&&r.tur==='ONAY'?'Gerekmiyor':'—';
 const taskTable=table([
  {label:'Görev',render:r=>`<strong>${esc(r.ad)}</strong><small>${r.tur==='ONAY'?'Teslim Onayı':'Görev'}</small>`},
  {label:'Proje / Etap',render:r=>`<span>${esc(w.name(r.proje))}</span><small>${esc(w.name(r.etap))}</small>`},
  {label:'Durum',render:r=>badge(r.durum)},
  {label:'Atanma',render:r=>clock(r,'atama_ani')},{label:'Kabul',render:r=>clock(r,'kabul_ani',true)},
  {label:'Teslim',render:r=>clock(r,'teslim_ani',true)},{label:'Bitiş',render:r=>clock(r,'bitis_ani')}
 ],tasks);
 const jobs=Object.entries(summary.isler??{}).map(([id,minutes])=>({...w.refs.IS.find(r=>idOf(r)===id),kimlik:id,minutes}));
 const buckets=Object.entries(summary.kovalar??{}).filter(([,minutes])=>Number(minutes)>0).map(([key,minutes])=>({ad:bucketNames[key]??'Diğer Çalışma',minutes}));
 const jobsPanel=jobs.length?panel('Atölye Ve Saha Çalışmaları',table([{label:'İş',render:r=>`<strong>${esc(r.islem??r.is_tanimi??'İş Bilgisi Gösterilemiyor')}</strong>`},{label:'Proje',render:r=>esc(w.name(r.proje))},{label:'Bu Günün Çalışması',numeric:true,render:r=>hours(Number(r.minutes)/60)}],jobs)):'';
 const pendingRows=pending?arr(w.value('GUN_ISLERI',person)):[];
 const pendingPanel=pendingRows.length?panel('Bekleyen Gün İşleri',table([{label:'İşlem',render:r=>r.tur==='GUN_ONAYI'?'Ekip Gün Onayı':'Mesai Sonu Özeti'},{label:'Gün',render:r=>date(r.gun)},{label:'Çalışan / Ekip',render:r=>esc(r.kisiler?.map(id=>w.name(id)).join(', ')??w.name(r.kisi??r.birim))}],pendingRows)):'';
 const overtime=arr(summary.fazla_mesai),overtimePanel=overtime.length?panel('Fazla Mesai',table([{label:'Başlangıç',render:r=>summaryTime(r.baslangic,day)},{label:'Bitiş',render:r=>summaryTime(r.bitis,day)}],overtime)):'';
 return `<section class="daily-summary" data-summary-person="${esc(person)}"><header class="daily-summary-heading"><div><h2>${esc(w.name(person))}</h2><p>${date(day)} · Gün Özeti</p></div>${badge(report.onay_durumu??report.durum)}</header><div class="daily-task-table">${panel('Görevler',taskTable)}</div>${jobsPanel}${buckets.length?panel('Çalışma Süreleri',table([{label:'Çalışma Türü',key:'ad'},{label:'Süre',numeric:true,render:r=>hours(Number(r.minutes)/60)}],buckets)):''}<p class="daily-notes-count">Bu gün yazılan not ve istek: <strong>${arr(summary.notlar).length}</strong></p>${overtimePanel}${pendingPanel}</section>`;
}
