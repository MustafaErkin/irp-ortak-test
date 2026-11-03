import {esc,idOf,arr,date,time,hours,badge,button,label,table,isoDay} from './ui.js';

export function taskGroups(rows,person,today,doneDay=today){
 const own=rows.filter(r=>r.kisi===person&&r.tur!=='ONAY');
 const done=own.filter(r=>r.durum==='BITTI');
 const onDay=(r,day)=>!!r.bitis_ani&&isoDay(new Date(r.bitis_ani))===day;
 return {waiting:own.filter(r=>r.durum==='ATANDI'),open:own.filter(r=>!['ATANDI','BITTI','IPTAL'].includes(r.durum)),done:done.filter(r=>!doneDay||onDay(r,doneDay)),doneToday:done.filter(r=>onDay(r,today)).length};
}
export function assignmentSchema(base,row){
 const s=structuredClone(base),pool=row.olcum==='SAAT';
 const hidden=pool?['kisi','zorluk','dosya_gerekli','onaylayan']:['birim','tezgah','onay_beklet'];
 hidden.push(...(row.nereye==='PROJE_DISI'?['proje','etap','parca_kodu']:['kategori']));
 if(!row.onay_gerekli)hidden.push('onaylayan','onay_beklet');
 for(const key of hidden)delete s.properties[key];
 s.required=[...new Set([...(s.required??[]).filter(k=>!hidden.includes(k)&&k!=='etap'),row.nereye==='PROJE'?'proje':'kategori',pool?'birim':'kisi',...(!pool&&row.onay_gerekli?['onaylayan']:[])])];
 if(pool)s.properties.zaman_degeri={type:'number',minimum:1/60};
 // Seçilmemiş etap ile bilinçli Etap Dışı seçimi ayrıdır; motorda etap yine isteğe bağlıdır.
 if(s.properties.etap){s.properties.etap={...s.properties.etap,type:['string','null'],uiNullOption:'Etap Dışı'};s.required.push('etap');}
 const groups=[['İş Bilgileri',['olcum','ad','is_tanimi','nereye','proje','etap','parca_kodu','kategori']],['Atama ve Tarih',['kisi','birim','teslim_tarihi','teslim_saati','zaman_degeri','zorluk','oncelik']],['Teslim Koşulları',['on_kosul','onay_gerekli','onaylayan','onay_beklet','dosya_gerekli']]];
 const used=new Set(groups.flatMap(g=>g[1]));
 s.uiGroups=[...groups,['Diğer Seçenekler',Object.keys(s.properties).filter(k=>!used.has(k)),true]];
 return s;
}
export function prerequisiteOptions(rows,selected=[],own=''){
 const keep=new Set(selected.filter(x=>typeof x==='string'));
 return rows.filter(r=>idOf(r)!==own&&(keep.has(idOf(r))||!['BITTI','IPTAL'].includes(r.durum)&&!['ONAY','NOT'].includes(r.tur)));
}
export function draftLinkIssues(rows){
 const issues=[],edges=rows.map(r=>(r.on_kosul??[]).filter(h=>h&&typeof h==='object').map(h=>h.satir-1));
 const add=(index,message)=>issues.push({index,path:'on_kosul',message});
 edges.forEach((refs,i)=>refs.forEach(j=>{if(!rows[j]||i===j)add(i,'Bir iş kendisine veya silinmiş bir taslağa bağlanamaz.');else if((rows[i].olcum??'ZAMAN')!==(rows[j].olcum??'ZAMAN'))add(i,'Farklı ölçümdeki yeni işleri ayrı atayın; sonra oluşan işi önkoşul seçin.');}));
 const visiting=new Set(),done=new Set();
 function visit(i){if(visiting.has(i)){add(i,'Önkoşullar birbirini bekleyen bir döngü oluşturuyor. Bağlardan birini kaldırın.');return;}if(done.has(i)||!rows[i])return;visiting.add(i);edges[i].forEach(visit);visiting.delete(i);done.add(i);}
 rows.forEach((_,i)=>visit(i));return issues;
}
export const previewable=file=>/\.(pdf|png|jpe?g|gif|webp|txt)$/i.test(file.ad??'');
export function fileList(files){
 return files.length?`<ul class="task-files">${files.map(f=>`<li><span>${esc(f.ad??'Dosya')}</span><div>${previewable(f)?button('Aç','file',{id:idOf(f)},'small'):''}${button('İndir','download-file',{id:idOf(f),name:f.ad??'dosya'},'small')}</div></li>`).join('')}</ul>`:'<p class="muted">Dosya eklenmedi.</p>';
}
export function assignmentReview(rows,name){
 return table([{label:'Proje / Etap',render:r=>esc(name(r.proje??r.kategori))+(r.nereye==='PROJE'?'<small>'+esc(r.etap?name(r.etap):'Etap Dışı')+'</small>':'')},{label:'İş',render:(r)=>`<strong>${esc(r.ad)}</strong>`},{label:'Çalışan / Havuz',render:r=>esc(name(r.olcum==='SAAT'?r.birim:r.kisi))+(r.olcum==='SAAT'?' Havuzu':'')},{label:'Teslim',render:r=>date(r.teslim_tarihi)},{label:'Emek',render:r=>hours(r.zaman_degeri)},{label:'Teslim Koşulları',render:r=>`${r.onay_gerekli?'Onay: '+esc(name(r.onaylayan??r.birim)):'Onaysız'}<small>${r.dosya_gerekli?'Dosya gerekli':'Dosya isteğe bağlı'}</small>${r.on_kosul?.length?'<small>Önce: '+[...new Set(r.on_kosul.map(h=>typeof h==='object'?rows[h.satir-1]?.ad??'Yeni İş':name(h)))].map(esc).join(', ')+'</small>':''}`}],rows);
}
export function taskDetail(w,r,data,section='info'){
 const id=idOf(r),loaded=!!data,notes=arr(data?.notlar),files=arr(data?.dosyalar),history=arr(data?.gecmis);
 const controls=['GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM','GOREV.ONAYLADIM','GOREV.REDDETTIM'].filter(code=>w.can(code)&&w.available(code,r));
 const titles={'GOREV.KABUL_ETTIM':r.tur==='NOT'?'İsteği Kabul Et':'Görevi Kabul Et','GOREV.TAMAMLADIM':'Görevi Teslim Et','GOREV.ONAYLADIM':'Teslimi Onayla','GOREV.REDDETTIM':'Düzeltmeye Gönder'};
 const actions=controls.map(code=>button(titles[code],'operation',{code,id,kind:'GOREV'},code.endsWith('TAMAMLADIM')||code.endsWith('ONAYLADIM')?'deliver':code.endsWith('REDDETTIM')?'reject':'primary')).join('');
 const deps=(r.on_kosul??[]).map(key=>w.refs.GOREV.find(x=>idOf(x)===key)??w.refs.IS.find(x=>idOf(x)===key)??{ad:'Görme yetkiniz dışındaki iş',durum:null});
 const ret=[...history].reverse().find(x=>x.eylem==='GOREV.REDDETTIM');
 const context=`<dl class="detail-list"><div><dt>Çalışan</dt><dd>${esc(w.name(r.kisi))}</dd></div><div><dt>İşi Veren</dt><dd>${esc(w.name(r.veren))}</dd></div><div><dt>${r.nereye==='PROJE_DISI'?'Faaliyet':'Proje'}</dt><dd>${esc(w.name(r.nereye==='PROJE_DISI'?r.kategori:r.proje))}</dd></div>${r.nereye==='PROJE'?`<div><dt>Etap</dt><dd>${esc(r.etap?w.name(r.etap):'Etap Dışı')}</dd></div>`:''}<div><dt>Teslim Tarihi</dt><dd>${date(r.teslim_tarihi)}${r.teslim_saati?' · '+esc(r.teslim_saati):''}</dd></div><div><dt>Zaman Değeri</dt><dd>${hours(r.zaman_degeri)}</dd></div><div><dt>Teslim Koşulu</dt><dd>${r.dosya_gerekli?'Dosya gerekli':'Dosya isteğe bağlı'} · ${r.onay_gerekli?'Onay: '+esc(w.name(r.onaylayan)):'Onaysız'}</dd></div></dl>`;
 const status=r.durum==='ON_IS_BEKLIYOR'?'<div class="notice warn">Önkoşullar tamamlanmadan teslim yapılamaz.</div>':r.durum==='ONAY_BEKLIYOR'?'<div class="notice">Teslim edildi. Onay bekleniyor.</div>':r.durum==='REDDEDILDI'?`<div class="notice warn">Aynı görevi düzeltip yeniden teslim edin.${ret?.not?'<p>'+esc(ret.not)+'</p>':''}</div>`:r.durum==='REVIZYONDA'?'<div class="notice">Ayrı revizyon görevinin tamamlanması bekleniyor.</div>':r.durum==='BITTI'?'<div class="notice">Bu görev tamamlandı.</div>':'';
 const links=[...(r.kaynak?[['Kaynak Görev',r.kaynak]]:[]),...(r.degisiklik?.kaynak?[['Değişikliğin Kaynağı',r.degisiklik.kaynak]]:[]),...(r.revizyon_gorevi?[['Revizyon Görevi',r.revizyon_gorevi]]:[])].map(([title,key])=>`<p class="task-link">${title}: ${w.refs.GOREV.some(x=>idOf(x)===key)?button(w.name(key),'inspect',{kind:'GOREV',id:key},'small'):esc(w.name(key))}</p>`).join('');
 let body;
 if(section==='notes')body=`${w.can('NOT.YAZDIM')?button('Not ve @ İstek Yaz','operation',{code:'NOT.YAZDIM',kind:'GOREV',id},'primary'):''}<p class="muted task-note-help">@ ile birime istek bırakabilirsiniz. İsteğin kabulü, işin tamamlandığı anlamına gelmez.</p>${!loaded?'<p>Notlar okunuyor…</p>':notes.length?notes.map(n=>{const recipients=data.istekler?.[idOf(n)];return `<article class="task-note"><header><strong>${esc(w.name(n.yazan??n.kim))}</strong><small>${date(n.an)} ${time(n.an)}</small></header><p>${esc(n.metin)}</p>${recipients?.ozet?.toplam?`<p class="request-summary">${recipients.ozet.toplam} Alıcıya İletildi · ${recipients.ozet.kabul} İsteği Kabul Etti · ${recipients.ozet.bekleyen} Kabul Bekliyor${recipients.ozet.iptal?' · '+recipients.ozet.iptal+' İptal':''}</p>`:''}${recipients?.alicilar?.length?'<ul class="request-status">'+recipients.alicilar.map(a=>`<li>${esc(w.name(a.kisi))} · ${a.gordu?'İsteği Kabul Etti':a.durum==='IPTAL'?'İstek İptal':'Kabul Bekliyor'}</li>`).join('')+'</ul>':''}${recipients?.ozet?'':recipients?.liste_tam===false?'<small>Yalnız görme yetkiniz olan alıcıların durumu gösteriliyor.</small>':n.etiketler?.length&&!recipients?.alicilar?.length?'<p class="notice warn">İstek iletilecek uygun alıcı bulunamadı. Yöneticiniz birim yönlendirmesini kontrol edebilir.</p>':''}${n.etiketler?.length&&recipients?.ozet?.toplam===0?'<p class="notice warn">İstek iletilecek uygun alıcı bulunamadı. Yöneticiniz birim yönlendirmesini kontrol edebilir.</p>':''}</article>`;}).join(''):'<p class="muted task-note-empty">Bu göreve henüz not yazılmadı.</p>'}`;
 else if(section==='files')body=`<h3>Dosyalar</h3>${loaded?fileList(files):'<p>Dosyalar okunuyor…</p>'}<h3>Durum Geçmişi</h3>${history.length?'<ol class="task-history">'+history.map(x=>`<li><strong>${esc(x.baslik)}</strong><small>${date(x.an)} ${time(x.an)} · ${esc(w.name(x.kim))}</small>${x.not?'<p>'+esc(x.not)+'</p>':''}</li>`).join('')+'</ol>':'<p class="muted">Geçmiş okunuyor…</p>'}${links}`;
 else {const lastDelivery=[...history].reverse().find(x=>x.eylem==='GOREV.TAMAMLADIM');body=`<p class="task-instruction">${esc(r.is_tanimi||'Ek talimat belirtilmedi.')}</p>${context}${deps.length?'<h3>Önkoşullar</h3><ul class="task-dependencies">'+deps.map(x=>`<li><span>${esc(x.ad)}</span>${x.durum?badge(x.durum):'<small>Durumu görüntülenemiyor</small>'}</li>`).join('')+'</ul>':''}${lastDelivery?`<section class="delivery-content"><h3>Son Teslim</h3><small>${date(lastDelivery.an)} ${time(lastDelivery.an)}</small><p>${esc(lastDelivery.not||'Teslim notu eklenmedi.')}</p><h3>Görevin Dosyaları</h3>${fileList(files)}</section>`:''}${links}`;}
 const management=w.can('GOREV.ATADIM')?`<details class="task-management"><summary>Görev İşlemleri</summary><p>Aynı görevin bilgilerini düzenleyebilir veya kaynak göreve bağlı yeni bir iş hazırlayabilirsiniz.</p><div class="toolbar">${w.available('GOREV.DEGISTIRDIM',r)?button('Bilgileri Düzenle','operation',{code:'GOREV.DEGISTIRDIM',id,kind:'GOREV'}):''}${r.durum==='BITTI'?button('Devam İşi Hazırla','task-follow',{id}):''}${r.durum!=='IPTAL'?button('Değişiklik İşi Hazırla','task-change',{id}):''}${w.available('GOREV.IPTAL_ETTIM',r)?button('Görevi İptal Et','operation',{code:'GOREV.IPTAL_ETTIM',id,kind:'GOREV'}):''}</div></details>`:'';
 return `<header class="task-heading"><h2>${esc(r.ad)}</h2>${badge(r.durum)}</header>${status}${w.accepting?.has(id)?'<div class="notice operation-wait" role="status">İşleminiz sürüyor, lütfen bekleyin.</div>':''}${actions?`<div class="action-strip">${actions}</div>`:''}<nav class="task-sections" aria-label="Görev Ayrıntısı">${[['info','Bilgiler'],['notes','Notlar ve İstekler'],['files','Dosyalar ve Geçmiş']].map(([key,title])=>button(title,'task-section',{section:key},section===key?'active':'secondary')).join('')}</nav><div class="task-section-body">${body}</div>${management}`;
}
