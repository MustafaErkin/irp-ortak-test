# Güncel Modül Sözleşmesi Ve Sahiplik

Kaynak: (K) 87, 95, 104, 129, 131, 140, 144, 151, 153–160, 162–163; T18, T26–T28. Ayrıntılı teknik sözleşme [irp_sozlesme/](irp_sozlesme/BASLA.md) içindedir. Bu dosya ortak kuralları ve güncel uygulama sınırını özetler.

## Üç Sorumluluk

| Sahip | Neyi Yönetir? |
|---|---|
| Çekirdek | Kişi, birim, rol/yetki, proje, etap, iş/görev, kabul/teslim/onay, gerçekleşen süre, ortak ilerleme, onaylı plan ve sürümleri, ücret/maliyet görünürlüğü. |
| Ortak bağlantı / çekirdek ekibi | Tek giriş/menü/bağlam, modül kurulumu, dar servis kimliği, sağlayıcı yönlendirmesi; ortak dosya/bildirim/not kapılarının sürümlenmesi. |
| Modül | Kendi iş alanının kuralı ve özel verisi. Örneğin satın alma siparişi, kalite denetimi, bakım planı; mevcut M10 teklifi/M11A bütçesi/M11B plan taslağı aynı sahiplik ilkesini gösterir. |

İki modülün bir bilgiyi istemesi onu otomatik olarak çekirdeğe taşımaz. Ticari bilgi sahibi modül tarafından yayımlanabilir; motor başka modülün tablosunu okumaz. Çekirdeğin kimliği modülde değer olarak tutulur; çekirdek tablosuna yabancı anahtar kurulmaz.

## Bağlantı Ve Yetki

- Ekran → modülün Python API'si → `irp_sozlesme.baglanti` → çekirdek veya kayıtlı sağlayıcı sırası kullanılır.
- Kullanıcı olayını insanın normal oturumu yazar. Modül kuralının sonucu bildirimdir; servis gözü insan yerine iş olayı yazmaz.
- Menü izni, projeyi görme ve işlem yapma yetkisi ayrı denetlenir. Projeyi görmek maaş veya bütçe tutarını görme yetkisi vermez.
- Satış/muhasebeye gereken projeler mevcut `PROJE.ERISIM_VERDIM` yoluyla yetkili tarafından açılır. Bütün projeleri otomatik açan rol politikası eklenmez.
- Mevcut sözde roller arasında `PROJE_SORUMLUSU` vardır; geçerli yetki kapsamları `FIRMA` ve `BIRIM`dir. `PROJE` diye yeni kapsam uydurulmaz.
- Gösteri firmasında yeni etap açma CEO'da kalır; Yönetici mevcut etapları planlar. Modül kurulumu yeni yetkiyi kendiliğinden vermez.
- Servis rolü yalnız kendi şeması ve beyan edilmiş dar kapılar içindir. Genel `service_role` veya çekirdek veritabanı şifresi modüle verilmez. Şema sahibi ile çalışma rolü ayrıdır; çalışma rolü göç çalıştırmaz.

## Ortak Verinin Tek Kaynağı

PLAN/GANTT çekirdekte vardır. Modül bunların ikinci motorunu kurmaz. Onaylı B0/B1… numarası, onaylayan, zaman, gerekçe ve etap görüntüsü çekirdekten okunur; modül dışındaki onaylar da aynı listede görünür. Modülün taslak/kanıt/not bilgisi kendi şemasında kalabilir.

Gantt'ta etap özeti bütün gerçekleşenden; alt görev ayrıntısı kişinin izninden gelir. Proje ilerlemesi mevcut ortak tanımdır (N:P0019); hazır parça sayısı/toplam parça gibi başka bir oranla değiştirilmez. Ölçülen atölye saati, beyaz yakanın zaman değeri ve maaş payı aynı veri değildir.

## Sağlayıcı Okumaları

Tüketici, adı hem `kapilar.okumalar` hem `bagimliliklar[].okumalar` içinde bildirir. Sağlayıcı `saglananlar` ile ad/parametre/görme/para/kişisel veri bilgisini yayımlar. Aynı SDK, aynı normal kullanıcı oturumuyla yönlendirir. Sağlayıcı kendi izinlerini de doğrular. Adres/anahtar kod içine gömülmez; modül tablosuna doğrudan girilmez.

Künye adının varlığı yanıt alanlarının birlikte kabul edildiğini kanıtlamaz. Yeni alan veya devir davranışı gerekiyorsa iki modülün talimatında/senaryosunda karşılaştırılır. Kapalı sağlayıcı, yetki reddi ve eksik bilgi ayrı sonuçlardır; bilinmeyen tutar sıfır, eksik plan hazır sayılmaz.

## Değişiklik Ve Kabul

`irp_sozlesme/` içindeki **Modül Sözleşmesi** ortak sınırları belirler. Modüle özel **Modül Geliştirme Talimatı** iş kapsamını belirler; ortak sözleşmeyi değiştiremez. Bu geliştirici paketi ikisini birlikte kullanmak için başlangıç, güncel durum ve örnekler sağlar. Gelen “çekirdekte olmalı” maddesi kaynak/sahiplik değerlendirmesinden geçmeden onaylı çekirdek işi değildir.

Durum sırası: **değerlendirildi → uygulandı → gerçek senaryo geçti → kullanıcı kabulü**. Çalışan ekran, HTTP 200 veya simülatör sonucu bu sıranın tamamı değildir. Yeni istek [geri dönüş şablonuyla](sablonlar/GERI_DONUS.md) bildirilir; ihtiyaç karşılanana kadar ilgili özellik bekleyen/kapalı tutulur.
