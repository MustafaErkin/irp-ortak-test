# Modül Geliştirme Talimatı · Kısa

SDK 1.2 · Ortak web standardı · Sürüm 1

1. İş kapsamı için `specification.md`yi, ortak teknik kurallar için bu dosyayı esas al. Eski paketin toplu okuma listesini uygulama; geçmişi, örnek modülleri ve çekirdek envanterini tarama.
2. `specification.md`yi tekrar yazma; ayrıca geliştirme talimatı, uyum raporu veya uzun plan üretme. Belirtilen modülü geliştir; yeni iş kuralı ekleme.
3. Arka yüzü Python 3.13 + FastAPI/ASGI ile yaz. Giriş noktasını `paket.modul:app` biçiminde bildir; bağımlılık sürümlerini sabitle.
4. Ön yüzü HTML/CSS/JavaScript ES modülleriyle yaz. React, iframe, CDN veya ayrı ön yüz derleme zinciri kurma.
5. Sabit beyaz masaüstü ERP düzeni kullan; sistemin koyu temasını izleme. Ortak stil ve düğme/tablo/pencere yardımcılarını kullan; genel stilleri ezme.
6. Ekranı `on_yuz/ekran.js` içinde `export async function ac(host)` ile sun; `{dispose(), refresh(baglam)}` döndür.
7. Yalnız `host.kok` içine çiz. Kendi girişini, kişi seçimini, ana menünü veya oturum deposunu oluşturma.
8. `host.baglam` içindeki kişi, kişiler, birimler, izinli projeler, seçili proje ve tarihi kullan. Projeyi `host.projeSec(kimlik)` ile seç; bu bağlamı arka yüz yetkisi sayma.
9. Kendi API'ne `host.istek('/goreli-yol', {method, body})` ile git; ortak yenileme için `host.yenile()` kullan. Token, sunucu adresi veya başka modül adresi gömme.
10. `host.ui` içindeki `esc`, `table`, `panel`, `modal`, `toast`, `date`, `hours`, `badge`, `ad`, `gantt` ve gerektiğinde `editor()` kullan. Kullanıcı metnini güvenli çiz.
11. İkili indirmede `host.istek`e `responseType:'blob'` ver. Hataları `message/code` ile ele al; yapılandırılmış hata gövdesi varsayma.
12. Kişi değişimi/ekrandan ayrılmada eski istek ve pencereleri temizle; geç cevabı çizme. Normal yenilemede kaydedilmemiş taslağı silme. Çift gönderimi engelle.
13. Kullanıcıya kişi/nesne kodu, ham olay adı veya teknik dosya yolu gösterme; adları kullan. Başlıkları okunur, sabit üst satırları opak yap; boş/yükleniyor/hata durumlarını ayır.
14. Çekirdeğe yalnız `irp_sozlesme.baglanti` üzerinden bağlan. `Cekirdek.ac(kunye_yolu, sayac=...)` kullan; arka yüzde normal Bearer oturumunu `cekirdek.oturum(anahtar)` ile aç. SDK'yı yeniden yazma/çatallama; yalnız kullandığın çağrının kesin imzasına gerektiğinde bak.
15. İhtiyaç duyduğun ortak verinin ve kuralların bu bağlantıyla sağlanacağını varsay; bunları modülde yeniden kurma. Çağrıyı `oturum.oku(ad, hedef, **girdiler)` ile yap, `.deger/.guncel` sonucunu kullan. Kesin adı/şeması verilmemiş ihtiyacı tek adaptörde yalıtıp kısa entegrasyon beklentisi olarak bildir; var/yok araştırmasına girme veya sahte çekirdek yazma.
16. Kullanıcı eylemini `oturum.olay_gonder(eylem, girdiler, ...)` ile gönder; sürüm denetiminde `oturum.hedef(...)` kullan. Kişi, saat ve olay kimliğini SDK'ya bırak. Bayat kararda yeniden oku; otomatik yeni karar gönderme.
17. Menü erişimi, proje görünürlüğü ve işlem yetkisini ayrı denetle. Kullanıcının verisini normal oturumla oku; servis kimliğiyle ekrana veri verme veya insan adına olay yazma.
18. Kendi verini yalnız `mod_<kod>` şemasında tut; ortak tablolara SQL/yabancı anahtar kurma. Uygulanmış göçü değiştirme; ileri göç ekle. Adres/şifreleri ortam ayarından al.
19. Başka modülün bilgisini aynı SDK'nın kayıtlı sağlayıcı okumasıyla al; doğrudan tablo/HTTP bağlantısı kurma. Kapalı/yetkisiz/eksik bilgiyi sıfır veya başarılı sonuç sayma.
20. Dosya gerekiyorsa SDK'nın `oturum.dosya_yukle(...)` / `dosya_oku(...)` yolunu kullan; MVP sınırını 1 MB tut. Yalnız ad/adres saklayıp dosya yüklenmiş deme. Nesne iznini koru.
21. Üretim sayacını kendi şemanda kalıcı tut; `sonraki(kisi,gun)` ve kalıcı istekte `zarf(kisi,istek,aday_olay)` sağla. Zarfı ağdan önce sakla; tekrarda aynısını gönder. Kısmi toplu işte satır sonuçlarını sakla.
22. `kunye.json`da kod/sürüm, okuma/olay/sağlayıcı bağımlılıkları, bildirim/dosya kullanımı, roller, özel şema ve kişisel/para verisini bildir. Ekran türünü `UYGULAMA_ICI` yap; verilen kod/cihaz harfini kullan.
23. Yalnız kendi modülünü ve kullandığı bağlantı yollarını sına; test taklitlerini test ortamında tut. Çalıştırmadığın testi geçti sayma; kullanıcı kabulünü kendin verme.
24. Kod, künye, ileri göçler, sabit bağımlılıklar ve testleri teslim et. `TESLIM.md`ye yalnız giriş noktası/ortam değişkeni adları, çalıştırılan test sonuçları ve açık entegrasyon ihtiyaçlarını kısa yaz. Sırları ekleme.
