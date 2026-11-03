// Form satırlarını mevcut eylem sözleşmesine çevirir. Hesap sunucuda yapılır.
export function deliveryWeek(day) {
 const d=new Date(day+'T12:00:00Z');
 d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
 const bas=d.toISOString().slice(0,10);d.setUTCDate(d.getUTCDate()+6);
 return {bas,bit:d.toISOString().slice(0,10)};
}
// Başarılı grubun taslakları silinirken kalan satırların ön koşulları kaymaz.
export function remainingDrafts(rows,completedMode) {
 const indexes=rows.map((row,index)=>(row.olcum??'ZAMAN')!==completedMode?index:-1).filter(index=>index>=0);
 return indexes.map(index=>({...rows[index],on_kosul:(rows[index].on_kosul??[]).flatMap(ref=>{
  if(typeof ref!=='object'||ref===null)return [ref];
  const next=indexes.indexOf(ref.satir-1);return next<0?[]:[{satir:next+1}];
 })}));
}
export function assignmentPayload(rows,warnings=[],mode='ZAMAN') {
 const indexes=rows.map((r,i)=>(r.olcum??'ZAMAN')===mode?i:-1).filter(i=>i>=0);
 const mappedWarnings=warnings.filter(w=>indexes.includes(w.satir-1)).map(w=>({...w,satir:indexes.indexOf(w.satir-1)+1}));
 const selected=indexes.map((index,position)=>{
  const item=structuredClone(rows[index]);delete item.olcum;
  item.uyarilar=mappedWarnings.filter(w=>w.satir===position+1);
  item.on_kosul=(item.on_kosul??[]).map(h=>{
   if(typeof h!=='object')return h;
   const next=indexes.indexOf(h.satir-1);
   if(next<0)throw new Error('Farklı ölçümdeki yeni işleri ayrı atayın; ardından oluşan işi ön koşul olarak seçin.');
   if(next===position)throw new Error('Bir iş kendisinin ön koşulu olamaz.');
   return {satir:next+1};
  });
  if(item.nereye==='PROJE_DISI'){delete item.proje;delete item.etap;delete item.parca_kodu;}else delete item.kategori;
  if(!item.onay_gerekli){delete item.onaylayan;item.onay_beklet=false;}
  if(mode==='SAAT'){
   item.onay_beklet??=false;
   item.islem=item.ad;item.tur='SURELI';item.tahmini_sure_dk=Math.round(Number(item.zaman_degeri)*60);item.on_isler=item.on_kosul;
   for(const key of ['ad','kisi','zaman_degeri','zorluk','dosya_gerekli','onaylayan','on_kosul'])delete item[key];
  }else for(const key of ['birim','tezgah','onay_beklet'])delete item[key];
  return Object.fromEntries(Object.entries(item).filter(([,v])=>v!=null));
 });
 return {[mode==='SAAT'?'isler':'gorevler']:selected,uyarilar:mappedWarnings};
}
