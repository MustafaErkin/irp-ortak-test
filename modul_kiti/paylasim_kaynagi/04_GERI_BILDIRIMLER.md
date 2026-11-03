# Mevcut Üç Modülün Geri Bildirimleri · İlgili İş İçin Başvuru

Bu dosya bütün yeni modüllere verilecek görev listesi değildir. Yalnız bu alanla bağımlılığı olan geliştirici başvurur. Kaynak: T26–T28, (K) 156–160/162 ve 25 isteğin değerlendirmesi. Ayrıntılı durum/sahiplik [durum/geri_bildirimler.json](durum/geri_bildirimler.json) içindedir. “Üründe var”, “ilk pilotta doğrulandı”, “açık ortak iş” ve “modülün kullanıcı kabulü” farklı durumlardır. Teknik düzeltme geçen bir madde bile bütün modül kabul edilmiş anlamına gelmez.

## M10 · Teklif

| İstek | Güncel Cevap Ve Modülün Yapacağı |
|---|---|
| M10-01 | SDK 1.2/SQL 154 projesiz özel MODUL bildirimi sağlar (I06); M10 onay bildirimi gerçek SQL'de geçti. Sahte proje açılmaz; iş/alıcı kuralı M10'dadır. |
| M10-02 | Ortak SDK sağlayıcı taşıması ve M10→M11A→M11B gerçek iş zinciri sınandı (I05). Yeni teslim kendi parametre/yanıt/izin uyumunu ayrıca sınar. |
| M10-03 | Ticari katalog/kapanış/temin geçmişi ilgili modüllerindir (I10). Ortak çekirdek kod listesine veya olayına otomatik taşıma; geri besleme döngüsü ayrı tasarlanacak. |
| M10-04 | PROJE_ISCILIGI BIRIM/YETKINLIK üründe var; model/semantik kapsamı sınırlı (I01/I08). Atölye saatini bütün ofis emeği/maaşı gibi kullanma; ihtiyacın olan anlam ve dönem örneğini yaz. |
| M10-05 | SDK 1.2 ile özel teklif dosyası gerçek yükleme/indirme ve izin/bütünlük denetimi var (I06). MVP 1 MB; dosya bilgisi tutmak tek başına aktarım değildir. |
| M10-06 | PROJELER üründe ve paket uyarlamasında var (I01/I03). İzinli listeyi kullan. SATIS rolüne bütün projeleri açma; gerekli özel proje erişimini yetkili kurar. |

## M11A · Sipariş Ve Bütçe

| İstek | Güncel Cevap Ve Modülün Yapacağı |
|---|---|
| M11A-01 | Muhasebenin ilgili projeye erişimi mevcut özel izinle kurulur (I03). MUHASEBE rolü bütün projeleri veya maaşları kendiliğinden görmez. |
| M11A-02 | Mevcut MVP'de M10 kazanılan sürüm tüketimi ortak SDK yolundadır ve gerçek zincir geçti (I05). Yeni teslimde doğrudan özel HTTP yolunu ürün bağlantısı yapma. |
| M11A-03 | Hazır parça sayısı oranı ortak proje ilerlemesi değildir (I11). Ana ilerleme için çekirdek göstergesini kullan (N:P0019); bütçe dolumunu ayrı göster. |
| M11A-04 | PROJE_ISCILIGI, PROJE_MALIYETI, TAHMIN_GERCEK üründe var (I01/I08). Tarih penceresi/ay ve saat anlamını doğru kullan; modelde olmayanı etap toplamından uydurma. |
| M11A-05 | M3 bu teslimde yok; satın alma/fason tutarı M3 verisidir (I05/I10). Sağlayıcı yoksa bilgi eksik göster, sıfır maliyet veya tamam bütçe sayma. |
| M11A-06 | Teklif sürümü–proje dönüşüm bağı M11A'nın özel verisidir (I10). PROJE.ACTIM'a sözleşmesiz kaynak alanı ekleme; şemanın ek alanı kabul etmesi onu resmî alan yapmaz. |
| M11A-07 | Gerçek dosya/PDF ve teknik devir SDK 1.2 ile uygulandı (I06). Donmuş ticari kopya korunur; özel tedarikçi teklifi teknik girdiye taşınmaz. |
| M11A-08 | Paket 1.1'de çoklu künye, ortak sahte firma ve özel anahtarlı yerel yetkili ucu var (I01). Test ucunu canlı API'ye taşıma; bütün ürün-model karşılaştırması tamam sanma. |
| M11A-09 | Proje açılışındaki bazı retler hâlâ genel (I09). Ön okumadan kesin “kod kullanılıyor” nedeni çıkartma; gerçek hata ve senaryoyu gönder. |

## M11B · Proje Devri Ve Planlama

| İstek | Güncel Cevap Ve Modülün Yapacağı |
|---|---|
| M11B-01 | SQL 153 etap özetini görünür görevlerden bağımsız topluyor (I04); iki kullanıcı ve özel görev ayrıntısı sınandı. Eksik görevleri tahminle tarama, görünürlüğü modülde genişletme. |
| M11B-02 | PLAN/GANTT gerçek üründe var (I01). Eski T16 katman uyarısından yeni motor ihtiyacı çıkartma; güncel katalog ve isteğe bağlı alanları kullan. |
| M11B-03 | PLAN(...,surumler=True) ortak B0/B1… listesini veriyor (I04). Güncel örnek 0.1.2; yerel neden/kanıt ortak numarayla ilişkilendirilir, dış onay da görünür. |
| M11B-04 | PROJELER ve ortak proje bağlamı izinli yeni projeyi getiriyor (I01/I02/I03). Güncel 0.1.2 kaynak örneği bu yolu kullanır; yalnız devir tablosunu bütün proje listesi sayma. |
| M11B-05 | SDK 1.2 gerçek fiziksel dosya/kanıt yolunu sağlar (I06). Ortak dosya nesnesi, normal kullanıcı izni ve 1 MB sınırı kullanılır. |
| M11B-06 | NOT_ALICILARI ile gerçek alıcı/kabul dökümü uygulandı; 13 alıcı ve kabul gerçek SQL'de sınandı (I07). liste_tam görünmeyen alıcı durumunu belirtir; sıra numarası tahmin edilmez. |
| M11B-07 | V17 artık mevcut PROJE_SORUMLUSU sözde rolünü kabul ediyor (I03). Kapsam FIRMA/BIRIM. Gösteride CEO etap açar; Yönetici mevcut etapları planlar. Kurulum yetki önerilerini otomatik uygulamaz. |
| M11B-08 | Kişinin kendi başlangıç/bitiş tahmini ortak çekirdek işidir, MVP sonrasına ayrıldı (I12; güncel N:T0296). Modülde yeni PLANLANDI durumu/ayrı görev motoru ekleme. |
| M11B-09 | Nota atanmak bütün projeye otomatik erişim vermez (I03/I07). Gerekirse mevcut projeye özel izin yetkili tarafından açılır; yalnız nota/ekine dar erişimin biçimi henüz kesinleşmedi. |
| M11B-10 | Etap sorumlusu mevcut kuralda projeyi görür. Karar 103 nesne sorumlusu içindir; etapla karıştırma. Eski senaryodaki PROJEYI_GOREMEZ beklentisini güncel kaynakla yeniden değerlendir. |

## Entegrasyon Sonrası Durum

Üç modülün beyaz ERP ekranları, M10→M11A ve M11A→M11B gerçek sağlayıcı/plan/teknik dosya devri, normal görev teslim/onayı, özel dosya/bildirim/not yolu teknik olarak uygulandı ve sınandı (160). Kullanıcı kabulü ayrı aşamadır. Gelen 0.2.0 kolu eski SDK 1.1 tabanındadır; en büyük sürüm numarası mevcut entegrasyon değişikliklerini içerdiğini kanıtlamaz. Yeni modül geliştirirken bu üç modülü kendiliğinden yeniden uyarlama.

Kişinin kendi tarih tahmini ve ticari geri besleme MVP sonrasıdır. Satın alma modülü henüz yok; eksik maliyet sıfır değildir. Yeni bir ihtiyaç, kendi modülünün talimatı ve somut geri dönüşüyle değerlendirilir.

## Cevap 1'den Ek İhtiyaç · M11B-11

Ortak `host.istek` hatalarında yapılandırılmış gövdenin belgeli bir alanla taşınması istendi. Güncel kod yalnız `message/code` veriyor; bu açık sınır kabul edildi, uygulama bu belge turunda yapılmadı. Yukarıdaki 25 tarihsel isteğe ek bir geri dönüştür. Yeni modül aynı ihtiyacı duyarsa M11B-11'i referans alır; `govde/body/data/detail` alanlarını tahmin etmez.
