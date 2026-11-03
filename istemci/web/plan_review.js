import {esc,hours,table} from './ui.js';
import {displayTemporal} from './temporal.js';
export const planStamp=p=>JSON.stringify([p?.guncel??{},p?.surumler??[]]);
const planDate=value=>esc(displayTemporal(value,'date')||'—');
function changes(plan,row){
 if(row.total)return '';
 const old=plan.son_onayli?.[row.id];
 if(!old)return plan.surumler?.length?'Yeni etap':'İlk onay';
 const labels={ad:'Ad',baslangic:'Başlangıç',bitis:'Bitiş',hedef_saat:'Hedef emek'};
 const format=(key,value)=>key==='baslangic'||key==='bitis'?planDate(value):esc(value);
 return Object.keys(labels).filter(key=>String(old[key])!==String(row[key]))
  .map(key=>`${labels[key]}: ${format(key,old[key])} → ${format(key,row[key])}`).join('<br>')||'Değişiklik yok';
}
export function planReview(plan){
 const rows=Object.entries(plan.guncel??{}).map(([id,e])=>({id,...e}));
 const displayRows=rows.length>1?[...rows,{id:'total',total:true,ad:'Toplam',hedef_saat:rows.reduce((n,r)=>n+Number(r.hedef_saat??0),0)}]:rows;
 return `<section class="plan-review"><h3>Onaylanacak Plan</h3>${table([
  {label:'Etap',key:'ad'},
  {label:'Başlangıç',render:r=>r.total?'':planDate(r.baslangic)},
  {label:'Bitiş',render:r=>r.total?'':planDate(r.bitis)},
  {label:'Hedef Emek',render:r=>hours(r.hedef_saat)},
  {label:'Önceki Onaydan Değişiklik',render:r=>changes(plan,r)}
 ],displayRows,{key:'id',rowClass:r=>r.total?'plan-review-total':''})}</section>`;
}
