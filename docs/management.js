import {esc,idOf,arr,num,money,hours,date,badge,button,panel,table,empty} from './ui.js';

const colors=['#527fb8','#71a69c','#a592bf','#c1a169','#7d9db2','#a4b4c4','#8bad82','#b9949c'];
const sum=values=>values.reduce((a,n)=>a+(Number(n)||0),0);
function bars(rows,{percent=false}={}){
 const max=percent?100:Math.max(1,...rows.map(r=>Number(r.value)||0));
 return rows.length?`<div class="report-bars">${rows.map((r,i)=>`<div class="report-bar"><div><span>${esc(r.name)}</span><strong>${esc(r.text??hours(r.value))}</strong></div><div class="report-bar-track"><i style="width:${Math.max(0,Math.min(100,100*(Number(r.value)||0)/max))}%;background:${colors[i%colors.length]}"></i></div></div>`).join('')}</div>`:empty();
}

export function portfolio(w){
 const rows=w.c.projects.map(p=>({...p,...w.value('PROJE_DURUM',idOf(p))}));
 return `<section class="workspace-intro"><div><span class="eyebrow">Yönetim Özeti</span><h2>Şirketin Genel Görünümü</h2><p>Projelerin ilerlemesi, emek ve maliyet sonuçları.</p></div>${button('Projeleri İncele','navigate',{page:'projects'},'primary')}</section>`+
 w.metrics([['Projeler',num(rows.length),'Portföydeki projeler'],['Gerçekleşen Emek',hours(sum(rows.map(r=>r.harcanan_emek))),'Projelere yazılan çalışma'],['İşçilik ve Tezgâh',money(sum(rows.map(r=>r.maliyet))),'Örnek portföyün toplam maliyeti'],['Ekip',num(w.c.people.length),'Firma çalışanı']])+
 `<div class="stack portfolio-stack"><div class="equal-columns">${panel('Projelere Harcanan Emek',bars(rows.map(r=>({name:r.ad,value:r.harcanan_emek}))))}${panel('Proje Bütçelerinin Tüketimi',bars(rows.map(r=>({name:r.ad,value:r.butce_tuketimi,text:num(r.butce_tuketimi)+'%'})),{percent:true}))}</div>${panel('Proje Portföyü',table([{label:'Proje',render:r=>`<strong>${esc(r.ad)}</strong><small>${esc(r.kod??idOf(r))}</small>`},{label:'Durum',render:r=>badge(r.durum)},{label:'Teslim',render:r=>date(r.teslim_tarihi??r.bitis)},{label:'İlerleme',render:r=>w.progress(r.yuzde)},{label:'Gerçekleşen Emek',numeric:true,render:r=>hours(r.harcanan_emek)},{label:'Maliyet',numeric:true,render:r=>money(r.maliyet)},{label:'',render:r=>button('Aç','project-open',{id:idOf(r)},'small')}],rows))}</div>`;
}

export function staffing(w){
 const range={bas:w.state.bas,bit:w.state.bit},capacity=w.value('BIRIM_DOLULUGU',null,range),distribution=arr(w.value('PERSONEL_DAGILIMI',null,range)),where=w.value('KIM_NEREDE',null,range),units=w.value('SAAT_NEREYE_GITTI',null,range);
 if(!capacity||!Object.keys(capacity).length)return panel('Personel Dağılımı',empty('Henüz Çalışma Dağılımı Yok','İşler planlanıp çalışma geldikçe birim ve kişi dağılımları oluşacak.'));
 const names=w.c.sample?.gosterim?.kalem_adlari??{};
 const itemName=id=>names[id]??w.name(id);
 const matrix=(value,person=false)=>{
  const entries=Object.entries(value??{}),columns=[...new Set(entries.flatMap(([,v])=>Object.keys(v??{})))];
  return table([{label:person?'Çalışan / Birim':'Birim',render:r=>`<strong>${esc(w.name(r.id.split(':')[0]))}</strong>${person?'<small>'+esc(w.name(r.id.split(':')[1]))+'</small>':''}`},...columns.map(id=>({label:itemName(id),numeric:true,render:r=>r.values[id]?hours(r.values[id]):'—'})),{label:'Toplam',numeric:true,render:r=>`<strong>${hours(sum(Object.values(r.values)))}</strong>`}],entries.map(([id,values])=>({id,values})),{key:'id'});
 };
 return `<div class="equal-columns">${panel('Birimlerin Planlanan Doluluğu',bars(Object.entries(capacity).map(([id,r])=>({name:w.name(id),value:r.kapasite?100*r.planli/r.kapasite:0,text:hours(r.planli)+' / '+hours(r.kapasite)})),{percent:true}))}${panel('Çalışma Saati Nereye Gitti',bars(distribution.map(r=>({name:r.ad??itemName(r.kalem),value:r.saat}))))}</div><div class="stack report-section">${panel('Çalışanların İş Dağılımı',matrix(where,true))}${panel('Birimlerin Çalışma Dağılımı',matrix(units))}</div>`;
}

export function sampleProjects(w){
 const s=w.state,p=w.c.projects.find(p=>idOf(p)===s.project),status=w.value('PROJE_DURUM',s.project)??{},stages=arr(w.value('ETAPLAR',s.project));
 if(!p)return empty();
 return `<section class="project-summary"><div class="project-monogram">${esc((p.kod??idOf(p)).slice(-2))}</div><div><span class="eyebrow">${esc(p.kod??idOf(p))}</span><h2>${esc(p.ad)}</h2><p>${esc(p.musteri??'')}</p></div><div class="toolbar">${badge(status.durum)}</div></section>`+
 w.metrics([['Proje İlerlemesi',num(status.yuzde)+'%','Tamamlanan plan emeği'],['Gerçekleşen Emek',hours(status.harcanan_emek),'Hedef: '+hours(status.hedef)],['Maliyet',money(status.maliyet),'Bütçe: '+money(status.butce)],['Teslim',date(status.bitis),'Planlanan proje bitişi']])+
 (status.hikaye?`<div class="project-insight">${esc(status.hikaye)}</div>`:'')+
 `<div class="stack">${panel('Etapların Durumu',table([{label:'Etap / Birim',render:r=>`<strong>${esc(r.ad)}</strong><small>${esc(w.name(r.birim))}</small>`},{label:'Başlangıç',render:r=>date(r.baslangic)},{label:'Bitiş',render:r=>date(r.bitis)},{label:'Hedef',numeric:true,render:r=>hours(r.hedef)},{label:'Gerçekleşen',numeric:true,render:r=>hours(r.harcanan)},{label:'İlerleme',render:r=>w.progress(r.yuzde)},{label:'Bütçe Tüketimi',numeric:true,render:r=>num(r.butce_tuketimi)+'%'},{label:'Durum',render:r=>badge(r.durum)}],stages))}${panel('Etap Bazında İlerleme',bars(stages.map(r=>({name:r.ad,value:r.yuzde,text:num(r.yuzde)+'%'})),{percent:true}))}</div>`;
}

export function sampleReports(w){
 const s=w.state,g={ay:s.bas.slice(0,7)+'-01'},range={bas:s.bas,bit:s.bit},projectRange=w.c.sample.gosterim.proje_donemleri[s.project];
 const cost=w.value('PROJE_MALIYETI',s.project,g),labour=w.value('PROJE_ISCILIGI',s.project,{...range,kirilim:'BIRIM'}),estimate=arr(w.value('TAHMIN_GERCEK',s.project,projectRange));
 return `<div class="stack">${panel('Aylık İşçilik ve Maliyet',table([{label:'Maliyet Kalemi',render:r=>`<strong>${esc(r.ad)}</strong>`},{label:'Çalışma',numeric:true,render:r=>hours(r.saat)},{label:'Tutar',numeric:true,render:r=>money(r.tutar)}],cost?.satirlar??[]))}${panel('Birimlerin Projeye Katkısı',w.auto(labour))}${panel('İşlerin Tahmini ve Gerçekleşen Emeği',table([{label:'İş',render:r=>`<strong>${esc(r.islem)}</strong><small>${esc(w.name(r.birim))}</small>`},{label:'Tahmin',numeric:true,render:r=>hours(r.tahmin/60)},{label:'Gerçekleşen',numeric:true,render:r=>hours(r.gercek/60)},{label:'Fark',numeric:true,render:r=>r.suruyor?'Sürüyor':r.fark==null?'—':num(r.fark)+'%'},{label:'Durum',render:r=>badge(r.durum)}],estimate))}</div>`;
}

export function samplePerformance(w){
 const s=w.state,range={bas:s.bas,bit:s.bit},p=w.value('PERFORMANS',s.person,range);
 if(!p)return empty();
 const rows=w.c.sample.gosterim.performans_kisileri.map(id=>({id,...w.value('PERFORMANS',id,range)}));
 return w.metrics([['Zamanında Teslim',num(p.zamaninda)+' / '+num(p.teslim),'Teslim edilen görevler'],['Kalite Geri Dönüşü',num(p.kalite_ret),'Doğrulanmış değerlendirmeler'],['Çözüm Emeği',hours(p.cozum_saat),'Sorun kaynaklı görevler'],['Proje Dışı Katkı',hours(p.katki_saat),'Diğer çalışma alanları']])+panel('Ekibin Performans Görünümü',table([{label:'Çalışan',render:r=>`<strong>${esc(w.name(r.id))}</strong>`},{label:'Teslim',numeric:true,key:'teslim'},{label:'Zamanında',numeric:true,key:'zamaninda'},{label:'Kalite Geri Dönüşü',numeric:true,key:'kalite_ret'},{label:'Çözüm',numeric:true,render:r=>hours(r.cozum_saat)},{label:'Katkı',numeric:true,render:r=>hours(r.katki_saat)},{label:'Değerlendirme',render:r=>r.kesinlesmedi?'Bekleyen Pay Var':'Kesinleşti'}],rows,{key:'id'}));
}
