# 08 · Fiziksel Dosya Ve Kalıcı İstek

Paket 1.2 · Ürün SQL 154 · T28. Bu ek, mevcut sahiplik ve normal kullanıcı sınırını genişletmez.

## Özel Dosyalar

Künyede `kapilar.dosyalar:true` gerekir. Ekran, ortak modül API'sinden dosyayı yükler; modül arka yüzü `oturum.dosya_yukle(kayit,ad,icerik,tur)` kullanır. `icerik` boş olmayan `bytes` ve en fazla 1 MB'dır. Cevap `kimlik`, `ad`, `konum:irp-dosya:MF-…`, `boyut`, `parmak_izi` içerir. İç kimlik kullanıcıya gösterilmez.

MVP'de baytlar mevcut web sunucusunun özel `.runtime/modul_dosyalari/` dizininde; metadata ortak SQL'de durur. Dizin statik web kökünün dışındadır. Yeni dış depolama hizmeti veya herkese açık bağlantı oluşturulmaz. Sunucu taşınırken bu dizin ayrıca korunmalıdır; üretim dosya altyapısının tamamlandığı iddia edilmez.

Her modül `GET /api/dosya-yetkisi?kayit=<JSON>&yazma=true|false` ucunu aynı normal kullanıcı oturumu ve iç geçit denetimiyle sağlar. İzin, modülün gerçek iş nesnesi üzerinden verilir. Ortak `modul_platformu.dosya_api.kur` bu taşıma uçlarını sağlar; modül yalnız nesne izin fonksiyonunu yazar. Bütün `MF-…` dosyaları aynı izinle açılmaz.

`oturum.dosya_oku(kimlik)` güncel izni yeniden denetler; cevap gerçek base64 içerik, tür, ad, boyut ve SHA-256 içerir. Servis gözü dosya okuyamaz/yükleyemez. Başka modül dosyası için künye bağımlılığı ve dosya sahibinin izni birlikte gerekir. Teknik devirde hedef modül kendi yetkili dosya kopyasını ve kaynak eşlemesini oluşturur; gizli tedarikçi teklifi teknik girdiye taşınmaz.

Model simülatörü gerçek dosya aktarımını taklit ederek kabul vermez; `URUN_SQL_GEREKLI` döner. Gerçek SQL/geçit testinde yükleme, indirme, tekrar, izin reddi ve bütünlük doğrulanmalıdır.

## Kalıcı Olay Zarfı

`olay_gonder(...,istek_kimligi='PROJE.ACTIM:'+proje)` isteğe bağlıdır. Bu seçenek kullanılıyorsa modül sayacı `zarf(kisi,istek,aday_olay)` metodunu sağlar. Metot, **ağ isteğinden önce**, aynı kişi/istek için tam zarfı kendi şemasında işlemsel olarak saklar ve tekrarında aynı zarfı döndürür. Farklı karar aynı istek kimliğiyle gönderilemez. Hassas ek desteklenmez. Örnek gerçek uygulama: `M11A/m11a/baglanti.py`, göç 004.

Çekirdeğin kabulünden sonra yanıt kaybolsa ve modül süreci yeniden başlasa da aynı olay kimliği, içerik ve zaman yeniden gider. Çekirdeğin tekrar cevabı esas alınır. Proje adı/müşteri benziyor diye var olan proje dönüştürülmüş sayılmaz. Kalıcı kimlik çakışırsa yeni olay üretilmez; istek korunarak hata verilir. Bu yöntem bütün modül HTTP işlemlerinin kendiliğinden tekrar güvenli olduğu anlamına gelmez.

## Özel Bildirim Ve Not Alıcıları

Henüz çekirdek projesi olmayan teklif için bildirim nesnesi `{'tur':'MODUL','modul':'M10','kimlik':'…'}` olabilir. Bildirim kuralı künyede MODUL türüyle bildirilir. `modul` bildirimi yazan modülle aynı olmalı; alıcılar modülün menü rolü ve istihdam denetiminden geçer. Sahte proje açılmaz. Ekranda başlık/gerekçe gösterilir.

`NOT_ALICILARI` normal kullanıcı okumasıdır: not görünürlüğünü ve her alıcı görevinin görünürlüğünü denetler. `alicilar` gerçek görev, kişi, durum ve kabul anını; `liste_tam` görünmeyen alıcı olup olmadığını bildirir. Sıra numarası tahmini veya on kişi sınırı kullanılmaz. Künyede kişisel veri beyanı gerekir. Kabul, çekirdeğin mevcut `GOREV.KABUL_ETTIM` işlemidir.
