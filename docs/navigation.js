import {arr} from './ui.js';

export const navigationReads=person=>[['ONAY_LISTESI'],['BILDIRIMLER',person],['GUN_ISLERI',person],['WEB_GOREVLER',null,{kisi:person}]];
export function navigationCounts(client){
 if(client.readonly)return {};
 const tasks=client.cached('WEB_GOREVLER',null,{kisi:client.person});
 const approvals=client.cached('ONAY_LISTESI'),notifications=client.cached('BILDIRIMLER',client.person);
 return {tasks:tasks==null?null:arr(tasks).filter(r=>r.kisi===client.person&&r.tur!=='ONAY'&&!['BITTI','IPTAL'].includes(r.durum)).length,approvals:approvals==null?null:arr(approvals).length,notifications:notifications==null?null:arr(notifications).filter(r=>!r.gorulme_ani).length};
}
