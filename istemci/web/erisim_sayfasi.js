import {accessKey,validatePeople} from './erisim.js';
const error=document.querySelector('#access-error'),status=document.querySelector('#access-status');
const configPromise=fetch('ayar.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Bağlantı ayarı okunamadı.');return r.json();});
// Giriş sorunu olması halinde kullanıcıya görünür; arka planda ret bırakılmaz.
configPromise.catch(e=>{error.textContent=e.message;});
document.querySelector('#access-form').onsubmit=async event=>{
 event.preventDefault();error.textContent='';
 try{
  const file=document.querySelector('#access-file').files[0];
  if(!file||file.size>16384)throw new Error('Küçük JSON erişim dosyasını seçin.');
  const people=validatePeople(JSON.parse(await file.text()));
  const config=await configPromise;
  localStorage.setItem(accessKey(config),JSON.stringify(people));
  const next=new URL(location.href).searchParams.get('sonra');
  location.replace(next==='olaylar.html'?'olaylar.html':'index.html');
 }catch(e){error.textContent=e instanceof SyntaxError?'Dosya okunamadı. JSON erişim dosyasını seçin.':e.message;}
};
document.querySelector('#forget-access').onclick=async()=>{
 try{
  const config=await configPromise;
  localStorage.removeItem(accessKey(config));
  // Günlük/önbellek korunur; yalnız yeniden giriş sağlayan oturumlar kaldırılır.
  const {BrowserStore}=await import('./client.js');
  for(const name of ['irp-is-web-v1','irp-is-web-v1:'+config.senaryo]){
   const store=await BrowserStore.open(name);await store.remove('session');
   for(const person of ['K001','K004','K009','K041'])await store.remove('pin:'+person);
   store.db.close();
  }
  status.textContent='Bu tarayıcıdaki giriş bilgileri kaldırıldı. Açık uygulama ve olay sekmelerini kapatın. Bekleyen işler silinmedi.';
 }catch(e){error.textContent=e.message;}
};
