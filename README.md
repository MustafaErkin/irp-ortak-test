# Sibernetik IRP — Ortak Çekirdek Testi

Mustafa'nın 3 Kasım 2026 tarihli mevcut web sürümünün ortak inceleme deposu.
Bu sürüm henüz tamamlanmış ürün değildir. Amaç çekirdeğin işleyişini ve ekranlarını birlikte düzeltmektir.

- Uygulama: https://mustafaerkin.github.io/irp-ortak-test/
- Bağımsız olay ekranı: https://mustafaerkin.github.io/irp-ortak-test/olaylar.html
- İlk giriş / erişimi kaldırma: https://mustafaerkin.github.io/irp-ortak-test/erisim.html
- Örnek CEO görünümü: https://mustafaerkin.github.io/irp-ortak-test/?kip=gosterim

## Teste Başlama

1. Mustafa'dan erişim JSON dosyasını özel olarak alın. Dosyayı depoya, Issues'a veya yorumlara koymayın.
2. Uygulama bağlantısını kendi bilgisayarınızda açın, dosyayı seçin ve Çalışma Alanını Aç'a basın.
3. Sağ üstten CEO, Yönetici, Ekip Lideri veya Ofis Çalışanı profilini seçin.
4. Olay ekranını aynı tarayıcıda ayrı sekmede açın. Bu pencere yalnız okur ve açıldıktan sonra gelen olayları gösterir. “Alındı” işin tamamlandığı anlamına gelmez.
5. Ortak veride çalışıyoruz. Kendi açtığınız proje adının başına adınızı yazın; diğer testçilerin işlerini değiştirmeyin. Aynı iş üzerinde çalışacaksanız önceden anlaşın.
6. Geri bildirimde rolü, sayfayı, yaptığınız işlemi, beklediğiniz sonucu ve gördüğünüz sonucu yazın. Özel giriş bilgileri veya oturum anahtarları eklemeyin.

Erişim dosyası bu tarayıcıda saklanır. Yalnız mevcut uygulamanın kimlik doğrulama hizmetine giriş için kullanılır; GitHub'a gönderilmez. Test sonrası erişim sayfasındaki kaldırma düğmesi giriş bilgilerini ve saklanan oturumu temizler. Açık uygulama/olay sekmelerini kapatın. Bekleyen işlem günlüğü bu düğmeyle silinmez.

## Bu Paylaşımın Sınırı

Çekirdek gerçek Supabase test ortamına bağlanır; ayrı bir boş firma oluşturulmadı. Mustafa ve telefon da aynı verilere bağlı olabilir. Mac'in açık olması çekirdek ve olay ekranı için gerekmez.

Modüllerin arka yüzü ve hesap açma/başkasının şifresini sıfırlama bu paylaşımda açık değildir. Ekran bunları açıklayıcı mesajla bildirir. Modül kaynakları geliştiricilerin çekirdekle bağlantıyı incelemesi için depodadır. GitHub Pages Python sunucusu çalıştırmaz.

Kaynak kodda son telefon denemesi inceleme için durmaktadır; kurulu telefon APK'sı önceki sürüme geri alınmıştır. Bu depodan yeni APK derlemek, mevcut telefondaki APK'yı yeniden üretmek değildir. SQL162 etkin göçlerde yoktur. Buluta göç, firma sıfırlama veya APK dağıtımı bu paylaşımın parçası değildir.

## Bilinen Açık Sorun

Ekip Lideri'nin iş oluşturma denemesinde ilk gönderim başarısız olmuş, istemci özgün hatayı korumamıştı. Belirsiz gönderim yerel günlükte kişinin diğer yönetim işlemlerini de engelleyebiliyor. Sonucu kontrol etme yolu ve hata mesajları ayrıca incelenmeli. Paylaşım hazırlığı bunu düzeltmiş sayılmaz. Yeni tarayıcının günlüğü farklıdır; eski bilgisayardaki engelin burada görünmemesi kök nedenin çözüldüğünü kanıtlamaz.

Tur1 kabulü kapalı; Tur2/2.1 revizyonlarından sonra kullanıcı sıradakine geçti. Tur3/3.1 atölye/telefon kabulü açık. Sonraki ayrıntılı ekran konusu İletişim ve Belgeler. Ayrıntılı tur-test-feedback rehberi ayrıca hazırlanacak; kendiliğinden yeni bir tur veya tamamlandı sonucu üretmeyin.

## Kod Haritası

| Yol | İçerik |
|---|---|
| `istemci/web/` | HTML/CSS/JavaScript ERP, web istemcisi ve tarayıcı testleri |
| `docs/` | GitHub Pages'e çıkan statik paket; giriş şifresi içermez |
| `urun/veritabani/` | Çekirdek SQL motoru, okuma/yazma kapıları ve göçler |
| `istemci/irp_cekirdek/` | Dart cihaz günlüğü/çekirdeği |
| `istemci/uygulama/` | Flutter telefon kaynakları; mevcut yedek APK ile aynı sürüm değil |
| `referans/` | Donmuş sınama referansı; uygulamayı geçirmek için değiştirmeyin |
| `modul_platformu/`, `moduller/` | Ortak modül geçidi ve üç uyarlanmış modül |
| `onboarding/MODUL_GELISTIRME_KISA.md` | Yeni modül geliştirme talimatı |
| `docs/surum.json` | İlk paylaşımın kaynak ve paket parmak izleri |

Müşteri kaynak belgeleri, kişisel notlar, özel anahtarlar, canlı yedekler ve eski Git geçmişi bu depoya taşınmadı. Mevcut çalışma ağacındaki kaynak değişiklikleri dahil edildi.

## Ekipçe Değişiklik Yapma

Her kişi kendi dalında çalışsın ve pull request açsın. Akış: mevcut durum + kullanıcı eksiği + ek bulunan eksik + çözüm önerisi → uzlaşma → uygulama → teknik kontrol → küçük kullanım testi → feedback → revizyon/kabul. Yeni mimari/motor değişikliğini UI düzeltmesine karıştırmayın. Telefon ve iletişim konuları Mustafa'nın çalışma alanıdır.

Web düzeltmelerinden sonra:

```sh
node --test istemci/web/test/*.test.js
python3 istemci/web/paylasim/guncelle.py
python3 -m http.server 8080 --directory docs
```

Son komutla `http://localhost:8080/` üzerinden kontrol edin. `guncelle.py` statik web dosyalarını ve çevrimdışı önbellek sürümünü yeniler; doğrulanmış derlenmiş Dart köprüsünü korur. Dart çekirdeği değişirse yeni derleme ve çapraz istemci doğrulaması ayrıca gereklidir. SQL güncellemesi otomatik yayımlanmaz.

Ana dal güncellendiğinde Pages `main /docs` kaynağından yayımlanır. Kaynakla birlikte güncel `docs/` değişikliklerini de PR'a ekleyin. Genel bağlantı anahtarı dışında şifre, servis anahtarı veya oturum jetonu eklemeyin.
