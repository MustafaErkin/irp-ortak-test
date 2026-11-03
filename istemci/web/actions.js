// Kodlar sözleşmedir; başlıklar iş uygulamasının dilidir.
const registry = {};
function group(page, rows) {for(const [code,title,target,ref] of rows) registry[code]={code,title,page,target:target||null,ref:ref||null};}
group('tasks',[
 ['GOREV.KABUL_ETTIM','Görevi Kabul Et','GOREV'],['GOREV.TAMAMLADIM','Görevi Teslim Et','GOREV'],
 ['GOREV.DEGISTIRDIM','Görevi Düzenle','GOREV'],['GOREV.IPTAL_ETTIM','Görevi İptal Et','GOREV'],
 ['NOT.YAZDIM','Not ve İstek Ekle',null,'NOT'],['MESAI.GIRDIM','Mesaiye Gir'],['MESAI.CIKTIM','Mesaiden Çık']]);
group('assign', [['GOREV.ATADIM','Görev Ata'],['IS.TANIMLADIM','Havuza İş Tanımla']]);
group('workshop',[
 ['IS.ATADIM','İş Ata','IS'],['IS.SIRALADIM','İşin Sırasını Değiştir','IS'],['IS.DEVRETTIM','İşi Devret','IS'],
 ['IS.PLANSIZ_TANIMLADIM','Plansız İş Ver'],['IS.DEGISTIRDIM','İşi Düzenle','IS'],['IS.BAGLANTI_DUZELTTIM','Proje ve Parça Bağını Düzelt','IS'],
 ['IS.IPTAL_ETTIM','İşi İptal Et','IS'],['IS.BASLADIM','İşe Başla','IS'],['IS.TAMAMLADIM','İşi Tamamla','IS'],
 ['IS.MOLA_VERDIM','Molaya Çık','IS'],['IS.ARIZA_BILDIRDIM','Duruş Bildir','IS'],['IS.DEVAM_ETTIM','İşe Devam Et','IS']]);
group('approvals',[
 ['IS.ONAYLADIM','İşi Onayla','IS'],['IS.REDDETTIM','İşi Düzeltmeye Gönder','IS'],['IS.DEVAM_ONAYLADIM','Duruştan Devamı Onayla','IS'],
 ['GOREV.ONAYLADIM','Teslimi Onayla','GOREV'],['GOREV.REDDETTIM','Teslimi Düzeltmeye Gönder','GOREV']]);
group('day', [['IS.SURE_EKLEDIM','Günü Tamamla','IS'],['KAYIT.GECERSIZ_SAYDIM','Yanlış Saat İşlemini Geçersiz Say',null,'OLAY']]);
group('dayclose',[
 ['GUN_SONU.GONDERDIM','Mesai Sonu Özetini Gönder'],['GUN_SONU.ONAYLADIM','Gün Sonunu Onayla'],['GUN_SONU.IADE_ETTIM','Gün Sonunu İade Et'],
 ['GUN_ONAYI.AYARLADIM','Birimde Gün Onayını Ayarla']]);
group('projects',[
 ['PROJE.ACTIM','Proje Aç'],['PROJE.DEGISTIRDIM','Projeyi Düzenle','PROJE'],['PROJE.KOD_DEGISTIRDIM','Proje Kodunu Değiştir','PROJE'],
 ['PROJE.KAPATTIM','Projeyi Kapat','PROJE'],['PROJE.ERISIM_VERDIM','Proje Erişimi Ver',null,'PROJE'],['PROJE.ERISIM_KALDIRDIM','Proje Erişimini Kaldır',null,'PROJE'],
 ['ETAP.TANIMLADIM','Etap Tanımla'],['ETAP.DEGISTIRDIM','Etabı Düzenle','ETAP'],['PLAN.TARIHLEDIM','Plan Tarihlerini Düzenle'],['PLAN.ONAYLADIM','Plan Sürümünü Onayla']]);
group('objects',[
 ['NESNE.ACTIM','Nesne Aç'],['NESNE.GUNCELLEDIM','Nesneyi Düzenle',null,'NESNE'],['NESNE.ASAMA_GECIRDIM','Aşamayı Değiştir',null,'NESNE'],
 ['NESNE.SURUM_EKLEDIM','Belge Sürümü Ekle','NESNE','NESNE'],['NESNE.SURUM_ONAYLADIM','Belge Sürümünü Onayla','NESNE','NESNE'],['NESNE.SURUM_GERI_CEKTIM','Belge Sürümünü Geri Çek','NESNE','NESNE']]);
group('people',[
 ['KISI.EKLEDIM','Çalışan Ekle'],['KISI.DEGISTIRDIM','Çalışan Bilgisini Düzenle'],['KISI.AYRILDI','Ayrılış İşlemi'],['KISI.YETKINLIK_TANIMLADIM','Yetkinlikleri Düzenle']]);
group('units', [['BIRIM.TANIMLADIM','Birim Tanımla']]);
group('machines',[
 ['TEZGAH.TANIMLADIM','Tezgâh Tanımla'],['TEZGAH.TAKVIM_TANIMLADIM','Tezgâh Takvimini Düzenle'],['TEZGAH.BAKIM_PLANLADIM','Bakım Planla'],
 ['TEZGAH.BAKIM_IPTAL_ETTIM','Bakımı İptal Et',null,'BAKIM'],['TEZGAH.DURUS_BILDIRDIM','Tezgâh Duruşu Bildir'],['TEZGAH.DURUS_BITTI','Tezgâh Duruşunu Bitir']]);
group('calendar',[
 ['TAKVIM.TANIMLADIM','Firma Mesaisini Düzenle'],['TATIL.EKLEDIM','Tatil Ekle'],['TATIL.KALDIRDIM','Tatili Kaldır'],
 ['GUN.TANIMLADIM','Özel Gün Tanımla'],['GUN.KALDIRDIM','Özel Günü Kaldır'],['DURUS.BASLADI','Toplu Duruş Başlat'],['DURUS.BITTI','Toplu Duruşu Bitir',null,'DURUS']]);
group('leaves',[
 ['IZIN.TALEP_ETTIM','İzin Talep Et'],['IZIN.ONAYLADIM','Yönetici Olarak Onayla',null,'IZIN'],['IZIN.IK_ONAYLADIM','İK Olarak Onayla',null,'IZIN'],
 ['IZIN.REDDETTIM','İzin Talebini Reddet',null,'IZIN'],['IZIN.IPTAL_ETTIM','İzni İptal Et',null,'IZIN']]);
group('overtime',[
 ['EK_MESAI.PLANLADIM','Ek Mesai Planla'],['EK_MESAI.ONAYLADIM','Gerçekleşen Mesaiyi Onayla'],['EK_MESAI.IPTAL_ETTIM','Ek Mesaiyi İptal Et',null,'EK_MESAI']]);
group('responsibility',[
 ['GECIKME.DEGERLENDIRDIM','Gecikmeyi Değerlendir',null,'GECIKME'],['SORUMLULUK.DOGRULADIM','Sorumluluğu Doğrula',null,'SORUMLULUK'],
 ['SORUMLULUK.ITIRAZ_ETTIM','Sorumluluğa İtiraz Et',null,'SORUMLULUK'],['SORUMLULUK.ITIRAZI_DEGERLENDIRDIM','İtirazı Değerlendir',null,'ITIRAZ']]);
group('payroll', [['MAAS.GUNCELLEDIM','Maaş ve Saat Bedelini Güncelle']]);
group('notifications', [['BILDIRIM.GORDUM','Bildirimi Aç']]);
group('settings',[
 ['AYAR.DEGISTIRDIM','Firma Ayarını Düzenle'],['AYAR.MAAS_PAYDASI','Maaş Paydasını Düzenle'],['AYAR.ONAY_ORANI','Onay Emeği Oranını Düzenle'],
 ['AYAR.PARCA_KODU_DESENI','Parça Kodu Biçimini Düzenle'],['AYAR.YONLENDIRDIM','Birim İsteklerini Yönlendir'],['KOD.TANIMLADIM','Seçenek Listesini Düzenle'],
 ['YETKI.TANIMLADIM','İşlem Yetkisini Düzenle'],['NESNE_TURU.TANIMLADIM','Nesne Türünü Düzenle'],['MODUL.TANIMLADIM','Modül Künyesini Düzenle']]);
export const OPERATIONS = Object.freeze(registry);
export const OPERATIONAL = Object.freeze({'AYAR.SAAT_KAYDIRDIM':'Gerçek saati kullanan iş uygulamasında test saati düğmesi yoktur (karar 135).','KURULUM.TAMAMLADIM':'Boş firma kurulum paketinin kapanışıdır; normal kullanıcı tek başına gönderemez.'});
export const NAV = [
 ['overview','Genel Bakış','ana','⌂'],['tasks','İşlerim','ana','▤'],['notifications','Bildirimler','ana','♧'],
 ['assign','Görev Atama','operasyon','＋'],['workshop','Görev Yönetimi','operasyon','▥'],['team','Ekip Takibi','operasyon','▥'],['approvals','Onaylar','operasyon','✓'],['day','Kişinin Günü','operasyon','◷'],['dayclose','Gün Sonu','operasyon','◴'],
 ['projects','Projeler ve Plan','is','▱'],['objects','Nesneler ve Belgeler','is','▧'],['leaves','İzinler','is','◫'],['overtime','Fazla Mesai','is','◷'],['responsibility','Gecikme ve Sorumluluk','is','⚑'],
 ['staffing','Personel Dağılımı','sonuc','▦'],['reports','İşçilik ve Maliyet','sonuc','▤'],['performance','Adil Performans','sonuc','◴'],['payroll','Maaş Dağılımı','sonuc','₺'],
 ['people','Çalışanlar','yonetim','♙'],['units','Birimler','yonetim','⊞'],['machines','Tezgâhlar','yonetim','▣'],['calendar','Çalışma Takvimi','yonetim','▦'],['settings','Firma Yönetimi','yonetim','⚙'],['logs','İşlem Günlüğü','yonetim','≡'],['modules','Modüller','moduller','▦']
].map(([id,title,group,icon])=>({id,title,group,icon}));
export const GROUP_LABELS = {ana:'ÇALIŞMA ALANIM',operasyon:'İŞ YÖNETİMİ',is:'PROJE VE KAYNAK',sonuc:'SONUÇLAR',yonetim:'FİRMA',moduller:'MODÜLLER'};
export function actionsFor(page) {return Object.values(OPERATIONS).filter(x=>x.page===page);}
