import {idOf,arr} from './ui.js';

export const workName=r=>r?.islem||r?.is_tanimi||r?.ad||'İş';
export function workRecipients(client) {
 return client.people.filter(p=>p.aktif!==false&&p.yaka==='MAVI'&&(client.admin||client.context.gorulebilen_kisiler?.includes(idOf(p))));
}
export function teamMembers(client,rows) {
 const people=new Map(client.people.map(p=>[idOf(p),p]));
 return arr(rows).filter(r=>r.kisi!==client.person&&people.get(r.kisi)?.aktif!==false&&people.get(r.kisi)?.yaka==='MAVI');
}
export function workActionAllowed(code,r,team=[]) {
 if(!r)return false;
 const done=['BITTI','IPTAL'].includes(r.durum),assigned=!!r.kisi;
 if(code==='IS.ATADIM')return !assigned&&['HAVUZDA','REDDEDILDI'].includes(r.durum);
 if(code==='IS.SIRALADIM')return assigned&&!done&&!(r.durum==='ONAY_BEKLIYOR'&&r.onay_beklet);
 if(code==='IS.DEVRETTIM')return assigned&&!done&&r.durum!=='ONAY_BEKLIYOR';
 if(code==='IS.DEGISTIRDIM')return !done;
 if(code==='IS.IPTAL_ETTIM')return r.durum!=='IPTAL';
 if(['IS.ONAYLADIM','IS.REDDETTIM'].includes(code))return r.durum==='ONAY_BEKLIYOR';
 if(code==='IS.DEVAM_ONAYLADIM'){const p=team.find(p=>p.kisi===r.kisi);const h=p?.hal?.durum==='SABIT_MOLADA'?p.hal.mola_onceki:p?.hal;return h?.durum==='ARIZADA'&&!h.devam_izni&&idOf(p.is_)===idOf(r);}
 if(code==='IS.BAGLANTI_DUZELTTIM')return r.durum!=='IPTAL';
 return true;
}
// "before" is the row below the drop marker, after removing the dragged row.
export function dropPosition(list,id,before=null) {
 const rest=arr(list).filter(r=>idOf(r)!==id);
 const index=rest.findIndex(r=>idOf(r)===before);
 return index<0?rest.length+1:index+1;
}
export function placedQueue(list,work,position) {
 const rest=arr(list).filter(r=>idOf(r)!==idOf(work));
 rest.splice(Math.max(0,Math.min(rest.length,position-1)),0,work);
 return rest;
}
export function queueIssue(list,work,position,{transfer=false}={}) {
 if(!Number.isInteger(position)||position<1||position>arr(list).filter(r=>idOf(r)!==idOf(work)).length+1)return 'Listede geçerli bir sıra seçin.';
 const head=arr(list)[0];
 if(head?.durum==='ONAY_BEKLIYOR'&&head.onay_beklet&&((idOf(head)===idOf(work)&&position!==1)||(idOf(head)!==idOf(work)&&position===1)))return 'İlk iş onay bekliyor. Onay veya düzeltme sonucu gelmeden önüne iş konamaz.';
 if(transfer&&work.durum==='ONAY_BEKLIYOR')return 'Onay bekleyen iş devredilemez.';
 return '';
}
export function workDefinition(schema,values,{unplanned=false,editing=false}={}) {
 const s=structuredClone(schema),p=s.properties;
 if(editing){for(const k of Object.keys(p))if(!['islem','is_tanimi','tahmini_sure_dk','teslim_tarihi','tezgah','tezgah_rolu','on_isler','onay_gerekli','onay_beklet','yetkinlik'].includes(k))delete p[k];}
 else {
  delete p.kisi;delete p.sira;delete p.onaylayan;
  p.nereye={enum:['PROJE','PROJE_DISI']};
  if(values.nereye==='PROJE_DISI'){for(const k of ['proje','etap','parca_kodu'])delete p[k];}
  else {delete p.kategori;p.etap={type:['string','null'],uiNullOption:'Etap Dışı'};}
 }
 if(!editing)p.tur={enum:['SURELI','ANLIK']};
 if(values.tur==='ANLIK')delete p.tahmini_sure_dk;
 if(p.tezgah_rolu)p.tezgah_rolu={enum:['BASLAT','BITIR']};
 const req=editing?[]:[unplanned?'is_tanimi':'islem','birim','nereye','tur',...(values.nereye==='PROJE_DISI'?['kategori']:['proje','etap'])];
 s.required=req;
 s.uiGroups=[
  ['İş Bilgileri',['islem','is_tanimi','birim']],
  ['Nereye Yazılır',['nereye','proje','etap','parca_kodu','kategori']],
  ['Süre ve Tür',['tur','tahmini_sure_dk','teslim_tarihi','kisi_sayisi']],
  ['Atama ve Sıra',['kisi','sira']],
  ['Önkoşul ve Onay',['onay_gerekli','onay_beklet','on_isler']],
  ['Diğer Seçenekler',['tezgah','tezgah_rolu','yetkinlik','planlanan_baslangic','planlanan_bitis','degisiklik'],true]
 ].filter(([,keys])=>keys.some(k=>p[k]));
 return s;
}
