# Teknoloji Ve Arayüz Standardı

Kaynak: (K) 140–146, 149–153, 157; çalışan web ve M11B uyarlaması. Bu, mevcut entegrasyonun desteklediği yoldur.

## Teknolojiler

| Katman | Mevcut Yol |
|---|---|
| Web ve modül ekranı | HTML, CSS, JavaScript ES modülleri. Ortak masaüstü ERP; React/iframe/ayrı uygulama kullanılmaz. |
| Modül arka yüzü | İlk çalışan yol Python/FastAPI ve ASGI `paket.modul:app` girişidir. Gelen Python iş mantığı korunur. Bu paket başka arka yüz çalıştırıcısı sağlamaz. |
| Çekirdek | Mevcut Supabase/PostgreSQL motoru ve ortak bağlantı SDK'sı. Modül motorun SQL kaynağını değiştirmez. |
| Modül verisi | Aynı PostgreSQL içinde kendi `mod_<kod>` şeması. Kurulum ayrı sahip ve sınırlı çalışma rolü açar. |
| Telefon | Flutter istemci. Mavi yakanın basit çekirdek yolu korunur; ayrı modül ekranı/düğmesi eklenmez. |

SDK testleri Python 3.11+ ve standart kütüphane kullanır. Mevcut çalışan modül ortamı Python 3.13'tür. [Bağımlılık listesi](arayuz/requirements-ornek.txt) bu ortamdaki sürümleri verir; başka makinedeki kurulum ayrıca doğrulanır. Yeni modüle ihtiyaç olmayan bağımlılıkları sırf örnekte var diye ekleme. Ön yüze CDN, ikinci arayüz çatısı veya ayrı paket derleme zinciri eklenmez.

## Görünüş Ve Davranış

- Arka plan sabit beyaz, `color-scheme: light`; sistemin dark mode tercihi izlenmez.
- Masaüstü iş programı düzeni: ortak sol menü/üst çubuk, proje bağlamı, okunur tablolar, açık filtreler ve birincil işlem. Telefon ekranı büyütülmez.
- `styles.css` ve ardından `erp.css` kullanılır. Bunlar [arayuz/](arayuz/index.html) içinde mevcut webden aynen alınmıştır. Modül için gereken ek sınıflar modüle özgü adla ve dar kapsamla yazılır; genel `body`, `.btn`, `.topbar` ezilmez.
- Düğme, tablo, pencere, tarih, durum rozeti ve ad çözümleme ortak `host.ui` yardımcılarından gelir. Kullanıcının yazdığı metin HTML olarak çalıştırılmaz; `esc`/`textContent` kullanılır.
- Görünür metinde iç nesne/olay kimliği, kişi kodu veya ham olay adı yoktur; kapalı teknik ayrıntı da istisna değildir. Kişi/rol ve iş adları gösterilir. Başlıkların kelime başları büyüktür; “kayıt” yerine “nesne” kullanılır.
- Harfli yuvarlak avatar kullanılmaz. Bağlantı metni “Çevrimiçi / Çevrimdışı”dır; kullanıcıya bulut/anahtar/şema anlatılmaz.
- Sabit üst ve tablo başlıkları opaktır. Pencere içeriği kayar; kapatma düğmesi görünür kalır. Gönderim sürerken çift gönderim ve pencere kapatma engellenir.
- Etiketler ve zorunlu alanlar açık olur. Hata ilgili alanla birlikte anlaşılır yazılır. Boş ekran veri uydurmaz; yükleniyor, boş ve hata halleri ayrılır.
- Otomatik yenileme kaydedilmemiş formu silmez. Kişi değişiminde eski cevap ve modüle ait pencereler kapanır. İşlem sonucu doğrulanmadan başarı mesajı gösterilmez.
- Ortak CSS'de tarihsel `.avatar`/`.technical-details` sınıfı bulunması bunları yeniden kullanma izni değildir; güncel görünürlük kararı yukarıdadır.

Gösteride dosyasız teslim mümkündür; bunu genel iş kuralı olarak “hiç dosya gerekmez”e dönüştürme. Plan değişikliğinin kanıt şartı ile görev teslimindeki dosya şartı ayrı şeylerdir. SDK 1.2 ile gerçek dosya yolu vardır; bir bağlantı/dosya bilgisi eklemek tek başına yükleme kabulü değildir. MVP sınırı 1 MB ve mevcut Mac'in özel dizinidir.

## `ac(host)` Bağlantısı

Teslimin ekran girişi `on_yuz/ekran.js` olur; `export async function ac(host)` sunar. [Kesin sözleşme](irp_sozlesme/sozlesme/07_on_yuz.md) ve [küçük kaynak örneği](arayuz/on_yuz/ekran.js) pakettedir.

| Alan | Kullanım |
|---|---|
| `kok` | Modülün DOM kökü; yalnız bu içerik çizilir. |
| `baglam` | Kişi, kişiler, birimler, izinli projeler, seçili proje, tarih ve mevcut rol bilgisi. Ekran bağlamıdır; arka yüz yetkisi değildir. |
| `istek('/yol', {method, body, responseType})` | Kendi modül API'si. Ortak uygulama normal oturumu taşır/yeniler/iptal eder. Ekran JWT saklamaz. Varsayılan JSON, ikili indirme için `responseType:'blob'`. |
| `projeSec(kimlik)` | Seçilen izinli projeyi ortak bağlama işler. |
| `yenile()` | Çekirdek okumalarını yeniler. |
| `ui` | `esc`, `table`, `panel`, `modal`, `toast`, `date`, `hours`, `badge`, `ad`, `gantt`; `editor()` ortak form/dosya/indirme yardımcısıdır. |

Geri dönüş `{dispose(), refresh(baglam)}` olur. Dinleyiciler/zamanlayıcılar temizlenir; sonlanan ekran tekrar çizilmez. Formlar her veri sinyalinde yeniden kurulmaz. `/irp/moduller/<KOD>/api/...` adresini ortak uygulama yönetir; modül kendi kişisini veya başka modülün adresini seçmez.

`ornekler/M11B/on_yuz/ekran.js` gerçek entegrasyondaki büyük örnektir. Buradan teknik kalıbı al; M11B'ye özgü iş akışını başka modülün gereksinimi sanma. `arayuz/` sayfasının dış kabuğu yalnız önizleme içindir; üretimde modül bu kabuğu kopyalamaz.

## Hata, Dosya Ve Yerel Geliştirme

- `host.istek` başarısızlıkta `UserError` verir: `message` kullanıcıya açıklama, `code` HTTP retlerinde durumun metnidir; diğer istemci hatalarında boş veya `STALE_SESSION` olabilir. Bugün ham yanıt gövdesini ayrı alanda taşımaz; `govde/body/data/detail` tahmini sözleşme değildir. Ayrıntı gerekiyorsa ortak istek yaz.
- PDF gibi ikili cevap için `await host.istek('/.../pdf',{responseType:'blob'})` kullanılır. Dosya açmada mevcut kullanıcı izni korunur, herkese açık URL üretilmez.
- Küçük dosya ekleri ortak `ui.editor()` yardımcısıyla veya SDK 1.2 dosya sözleşmesiyle taşınır. `arayuz/ortak/modul_ui.js` gerçek yardımcı kaynağıdır. Arka yüzde ortak taşıma örneği `ortak_api/modul_platformu/dosya_api.py` içindedir; iş nesnesi iznini modülün normal kullanıcı bağlamı doğrular.
- Bu paketin önizlemesi küçük sentetik kabuktur. Yerel modül API'si kendi ayrı test PostgreSQL ortamında çalışır; canlı firma adresi/şifresi pakette verilmez. Ortak gerçek kurulum entegrasyon ekibinindir.
- PC/Mac üzerinde motor çalıştırma ve bulutu kullanmama konusu MVP sonrası görüşmedir. Güncel teknoloji standardını bu olasılığa göre değiştirme.
