// Yalnız ortak test dağıtımının giriş uyarlaması. İş motoruna müdahale etmez.
export const ROLES = {K001:'CEO', K004:'Yönetici', K009:'Ekip Lideri', K041:'Ofis Çalışanı'};
export function accessKey(config) {
 return 'irp-ortak-test-erisim:'+new URL('.',import.meta.url).pathname+':'+config.senaryo;
}
export function validatePeople(value) {
 if(!Array.isArray(value))throw new Error('Mustafa’nın verdiği erişim JSON dosyasını seçin.');
 const people=Object.entries(ROLES).map(([kod,etiket])=>{
  const matches=value.filter(p=>p?.kod===kod);
  if(matches.length!==1||typeof matches[0].sifre!=='string'||!matches[0].sifre.trim())throw new Error('Dosyada dört web profilinin giriş bilgileri bulunmalı.');
  return {kod,etiket,sifre:matches[0].sifre};
 });
 return people;
}
export async function loadSharedConfig() {
 const response=await fetch('ayar.json',{cache:'no-store'});
 if(!response.ok)throw new Error('Bağlantı ayarı okunamadı.');
 const config=await response.json();
 if(!config.ortak_test)return config;
 let people;
 try{people=validatePeople(JSON.parse(localStorage.getItem(accessKey(config))));}catch{}
 if(!people){
  const target=new URL('erisim.html',import.meta.url);
  target.searchParams.set('sonra',location.pathname.endsWith('olaylar.html')?'olaylar.html':'index.html');
  location.replace(target.href);
  throw new Error('Test erişimi hazırlanıyor.');
 }
 return {...config,gosteri_kisileri:people};
}
