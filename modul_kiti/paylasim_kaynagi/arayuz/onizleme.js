import * as ui from './ortak/ui.js';
import {setDisplayResolver} from './ortak/presentation.js';
import {ac} from './on_yuz/ekran.js';

// Bu dosya üretim kabuğu değildir. Ağ/oturum yerine yalnız açıkça sentetik
// görünüş verisi verir. Modüle kopyalanacak kalıp on_yuz/ekran.js içindedir.
const projects=[{kimlik:'DEMO-01',ad:'Örnek Montaj Hattı'},{kimlik:'DEMO-02',ad:'Örnek Paketleme Makinesi'}];
const context={kisi:{kimlik:'K004',ad:'Yönetici'},kisiler:[{kimlik:'K004',ad:'Yönetici'}],birimler:[],projeler:projects,proje:'DEMO-01',tarih:'2026-10-31',yonetici:true,yetkili:false};
ui.installUiBehavior();
setDisplayResolver(id=>context.kisiler.find(p=>p.kimlik===id)?.ad??projects.find(p=>p.kimlik===id)?.ad);
let page;
const host={kok:document.querySelector('#module-preview'),baglam:context,
 ui:{...ui,ad:id=>context.kisiler.find(p=>p.kimlik===id)?.ad??'İlgili Kişi'},
 projeSec:id=>{if(projects.some(p=>p.kimlik===id))context.proje=id;},
 yenile:async()=>{},
 istek:async path=>{
  const mode=document.querySelector('#preview-mode').value;
  if(mode==='error')throw new Error('Bu örnek görünümde bilgiler alınamadı. Yeniden deneyin.');
  const project=projects.find(p=>path.includes(encodeURIComponent(p.kimlik)));
  if(!project)throw new Error('Örnek proje bulunamadı.');
  return {proje:project,etaplar:mode==='empty'?[]:[
   {kimlik:'ORNEK-ETAP-1',ad:'Teknik Hazırlık',bitis:'2026-11-06',sorumlu:'K004',durum:'ONAYLI'},
   {kimlik:'ORNEK-ETAP-2',ad:'Üretim Planı',bitis:'2026-11-13',sorumlu:'K004',durum:'TASLAK'}]};
 }};
async function mount(){page?.dispose();host.kok.innerHTML='';page=await ac(host);}
document.querySelector('#preview-project').onchange=async event=>{context.proje=event.target.value;await page.refresh({...context});};
document.querySelector('#preview-mode').onchange=()=>page.refresh({...context});
document.querySelector('#preview-refresh').onclick=()=>page.refresh({...context});
document.querySelector('#preview-remount').onclick=mount;
window.addEventListener('pagehide',()=>page?.dispose(),{once:true});
await mount();
