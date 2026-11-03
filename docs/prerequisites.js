// Eksik ana veri yalnız yetkili kişinin normal olayıyla tamamlanır.
// Mevcut firma türleri ve olayları korunur; sıfırlama veya servis anahtarı yoktur.
export async function ensureDocumentType(client,load=async()=>{
 const response=await fetch(new URL('./cekirdek_onkosullari.json',import.meta.url));
 if(!response.ok)throw new Error('Belge türü hazırlığı okunamadı.');return response.json();
}){
 if(client.context.nesne_turleri?.length)return;
 if(!client.admin)throw new Error('Belge türü henüz hazırlanmamış. CEO rolüyle Nesne Aç işlemini bir kez açarak hazırlığı tamamlayın.');
 client.context=(await client.read('WEB_BAGLAM',null,{},true)).deger;
 if(client.context.nesne_turleri?.length)return;
 const {belge}=await load();
 await client.write('NESNE_TURU.TANIMLADIM',belge);
 if(!client.context.nesne_turleri?.length)throw new Error('Belge türü gönderildi. Görünüm yenilenince Nesne Aç işlemini yeniden açın.');
}
