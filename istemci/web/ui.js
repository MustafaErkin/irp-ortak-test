import {displayText,formatVisible} from './presentation.js';

export const esc = (x='') => String(x ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const idOf = x => x?.kimlik ?? x?.kod ?? x?.satir ?? '';
export const titleCase = value => String(value??'').replace(/(^|[\s(/])(\p{L})/gu,(_,space,letter)=>space+letter.toLocaleUpperCase('tr-TR')).replace(/(\s)(Ve|Veya|İle)(?=\s)/gu,(_,space,word)=>space+word.toLocaleLowerCase('tr-TR'));
export function headingCase(root){formatVisible(root);root?.querySelectorAll('h1,h2,h3,legend,.advanced-fields>summary,.field>span,.checkbox-field>span,.detail-list dt,.nav-link>span:last-child,.nav-label,.page-eyebrow,.eyebrow,.topbar-breadcrumb strong,.tab').forEach(el=>{if(el.children.length===0)el.textContent=titleCase(el.textContent);});}
export function installUiBehavior(){
 if(document.documentElement.dataset.uiBehavior)return;document.documentElement.dataset.uiBehavior='true';
 const setOpen=(menu,open)=>{menu.classList.toggle('is-open',open);menu.querySelector('[data-menu-toggle]')?.setAttribute('aria-expanded',String(open));const list=menu.querySelector('.menu-items');if(list)list.hidden=!open;};
 const closeOthers=except=>document.querySelectorAll('.overflow-menu.is-open').forEach(menu=>{if(menu!==except)setOpen(menu,false);});
 document.addEventListener('pointerdown',e=>closeOthers(e.target.closest?.('.overflow-menu')),true);
 document.addEventListener('click',e=>{const button=e.target.closest?.('[data-menu-toggle]');if(button){e.preventDefault();const menu=button.closest('.overflow-menu'),open=!menu.classList.contains('is-open');closeOthers(menu);setOpen(menu,open);}else closeOthers(null);},true);
 document.addEventListener('keydown',e=>{if(e.key==='Escape')closeOthers(null);});
 document.addEventListener('change',e=>{if(e.target.matches?.('input[type=date]'))e.target.blur();});
}
export const arr = x => Array.isArray(x) ? x : x && typeof x === 'object' ? Object.entries(x).map(([kimlik,v])=>typeof v==='object'&&v!==null?{kimlik,...v}:{kimlik,deger:v}) : [];
export const num = (n, digits=1) => n==null || !Number.isFinite(Number(n)) ? '—' : Number(n).toLocaleString('tr-TR',{maximumFractionDigits:digits});
export const money = n => n==null || n==='VERI_EKSIK' ? 'Bilgi eksik' : `${num(n,2)} ₺`;
export const hours = n => n==null ? '—' : `${num(n)} sa`;
export const date = x => !x ? '—' : new Date(String(x).length===10?x+'T12:00:00+03:00':x).toLocaleDateString('tr-TR',{day:'2-digit',month:'short',year:'numeric',timeZone:'Europe/Istanbul'});
export const time = x => !x ? '—' : new Date(x).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'});
export const isoDay = (d=new Date()) => new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Istanbul'}).format(d);
export function period(day=isoDay()) {const [y,m]=day.split('-').map(Number);return {bas:`${y}-${String(m).padStart(2,'0')}-01`,bit:`${y}-${String(m).padStart(2,'0')}-${new Date(y,m,0).getDate()}`};}
export function label(x) { return ({ZAMAN:'Teslim ve zaman değeri',SAAT:'Saat ile ölçülen atölye işi',GENEL_GIDER_PAYI:'Genel gider payı',MAAS_AYLIK:'Aylık maaş',SAAT_UCRETI:'Tezgâh saat bedeli',ACIK:'Açık',ATANDI:'Atandı',KABUL_BEKLIYOR:'Kabul bekliyor',KABUL_EDILDI:'Kabul edildi',BITTI:'Tamamlandı',TAMAMLANDI:'Tamamlandı',ONAY_BEKLIYOR:'Onay bekliyor',REDDEDILDI:'Düzeltme bekliyor',REVIZYONDA:'Revizyonda',IPTAL:'İptal',CALISIYOR:'Çalışıyor',BOS:'Boşta',MESAI_DISI:'Mesai dışında',MOLADA:'Molada',SABIT_MOLADA:'Sabit mola',DEVAM_BEKLIYOR:'Devam bekliyor',ARIZA_BEKLIYOR:'Duruşta',ARIZADA:'Duruşta',CALISMIYOR:'Çalışmıyor',CALISILIYOR:'Çalışıyor',HAVUZDA:'Havuzda',SIRADA:'Sırada',YARIM:'Yarım Kaldı',BEKLEME:'Bekleme',ON_IS_BEKLIYOR:'Ön iş bekliyor',SURUYOR:'Sürüyor',KAPALI:'Kapalı',GECIKTI:'Gecikti',SIPARIS_VERILMELI:'Sipariş verilmeli',SIPARISTE:'Siparişte',GELDI:'Geldi',ISLEMDE:'İşlemde',FASONDA:'Fasonda',KALITE_ONAYLI:'Kalite onaylı',MONTAJA_HAZIR:'Montaja hazır',MONTAJDA:'Montajda',TASLAK:'Taslak',ONAYLI:'Onaylı',GERI_CEKILDI:'Geri çekildi',NORMAL:'Normal',YUKSEK:'Yüksek',ACIL:'Acil',MAVI:'Atölye',BEYAZ:'Masa başı',GUNCEL:'Güncel',BEKLIYOR:'Bekliyor',GONDERILEMEDI:'Gönderilemedi',GONDERILDI:'Gönderildi',HATA:'İnceleme gerekli',YETKILI:'Yetkili',YONETICI:'Yönetici',EKIP_LIDERI:'Ekip lideri',BEYAZ_YAKA:'Beyaz yaka',CALISAN:'Çalışan',MALIYET:'Maliyet',IK:'İnsan kaynakları',PROJE:'Proje',PROJE_DISI:'Proje dışı',KISI:'Kişi',BIRIM:'Birim',TEZGAH:'Tezgâh',NESNE:'Nesne',GOREV:'Görev',IS:'İş',SURELI:'Süreli',ANLIK:'Anlık',TATIL:'Tatil',YARIM_GUN:'Yarım gün',OZEL_MESAI:'Özel mesai',ONAYLANDI:'Onaylandı',ONAY_GEREKMIYOR:'Gün Onayı Gerekmiyor',DEGISTI:'Güncellendi',IADE:'Düzeltme Bekliyor',ONAY:'Onayla',DEGISTIR:'Değiştir',KALDIR:'Kaldır',KABUL:'Kabul',RET:'Ret',FIRMA:'Firma',MUSTERI:'Müşteri isteği',HATA:'Hata',IYILESTIRME:'İyileştirme'})[x] ?? String(x ?? '—').replaceAll('_',' '); }
export function badge(x) {const good=['BITTI','TAMAMLANDI','ONAYLI','GUNCEL','GONDERILDI','CALISIYOR','CALISILIYOR'];const warn=['ONAY_BEKLIYOR','BEKLIYOR','REVIZYONDA','SIPARIS_VERILMELI','MOLADA','SABIT_MOLADA','ON_IS_BEKLIYOR'];const bad=['GECIKTI','REDDEDILDI','IPTAL','HATA','ARIZADA','ARIZA_BEKLIYOR'];return `<span class="badge ${good.includes(x)?'good':warn.includes(x)?'warn':bad.includes(x)?'bad':x==='MESAI_DISI'?'offshift':''}">${esc(label(x))}</span>`;}
export function button(text, action, data={}, type='secondary') {return `<button type="button" class="btn ${type}" data-action="${esc(action)}" ${Object.entries(data).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}>${esc(text)}</button>`;}
export const empty = (title='Gösterilecek nesne yok', detail='Seçili kapsamda henüz bir işlem bulunmuyor.') => `<div class="empty"><span class="empty-symbol">≡</span><strong>${esc(title)}</strong><p>${esc(detail)}</p></div>`;
export const errorBox = e => `<div class="notice bad" role="alert">${esc(e?.message??e)}</div>`;
export function panel(title,body,actions='') {return `<section class="panel"><header class="panel-head"><h2>${esc(title)}</h2><div class="toolbar">${actions}</div></header>${body}</section>`;}
export function table(columns,rows,{key='kimlik',select=false,kind='',selected='',compact=false,rowClass=()=>''}={}) {
 if(!rows?.length) return empty();
 return `<div class="table-scroll"><table class="data-table ${compact?'compact':''}"><thead><tr>${select?'<th class="check-col"></th>':''}${columns.map(c=>`<th class="${esc(c.className??'')} ${c.numeric?'numeric':''}">${esc(titleCase(c.label))}</th>`).join('')}</tr></thead><tbody>${rows.map((r,i)=>{
 const id = typeof key==='function'?key(r):r[key]??idOf(r)??i;
 return `<tr data-kind="${esc(kind)}" data-id="${esc(id)}" ${select?'data-action="select-row" tabindex="0"':''} class="${select&&selected!==''&&id===selected?'selected':''} ${esc(rowClass(r))}">${select?`<td><input type="radio" name="selected-${esc(kind)}" aria-label="Satırı seç" ${id===selected&&selected!==''?'checked':''}></td>`:''}${columns.map(c=>`<td class="${esc(c.className??'')} ${c.numeric?'numeric':''}">${c.render?c.render(r):esc(typeof c.key==='function'?c.key(r):r[c.key])}</td>`).join('')}</tr>`;
 }).join('')}</tbody></table></div>`;
}
export function details(record, fields) {return `<dl class="detail-list">${fields.map(([k,l,render])=>`<div><dt>${esc(l)}</dt><dd>${render?render(record[k]):esc(record[k]??'—')}</dd></div>`).join('')}</dl>`;}
export function toast(message, bad=false) {const el=document.createElement('div');el.className='toast'+(bad==='info'?' info':bad?' bad':'');el.textContent=displayText(message);el.setAttribute('role',bad===true?'alert':'status');document.querySelector('#toasts').append(el);setTimeout(()=>el.remove(),bad?9000:4500);}
export function modal(title, body, {wide=false,footer='',onClose}={}) {
 const d=document.createElement('dialog');d.className='modal'+(wide?' wide':'');
 d.innerHTML=`<header class="dialog-head"><h2>${esc(title)}</h2><button class="icon-button" type="button" data-close aria-label="Kapat">×</button></header><div class="dialog-body">${body}</div>${footer?`<footer class="dialog-footer">${footer}</footer>`:''}`;
 const dismissible=()=>!d.querySelector('[data-close]').disabled;
 const outside=e=>{const r=d.getBoundingClientRect();return e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom;};
 let startedOutside=false;
 d.addEventListener('pointerdown',e=>{startedOutside=e.target===d&&outside(e);});
 d.addEventListener('click',e=>{if(startedOutside&&e.target===d&&outside(e)&&dismissible())d.close();startedOutside=false;});
 d.addEventListener('cancel',e=>{if(!dismissible())e.preventDefault();});
 d.querySelector('[data-close]').onclick=()=>{if(dismissible())d.close();};d.addEventListener('close',()=>{onClose?.();d.remove();});headingCase(d);document.querySelector('#dialogs').append(d);d.showModal();return d;
}
export function downloadCSV(name, columns, rows) {
 const cell=x=>'"'+String(x??'').replaceAll('"','""').replace(/^[=+@-]/,'\t$&')+'"';
 const csv='\ufeff'+[columns.map(c=>cell(c.label)).join(';'),...rows.map(r=>columns.map(c=>cell(typeof c.key==='function'?c.key(r):r[c.key])).join(';'))].join('\r\n');
 const u=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download=name+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);
}
