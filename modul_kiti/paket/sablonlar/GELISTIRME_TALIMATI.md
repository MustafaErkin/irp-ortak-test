# Modül Geliştirme Talimatı · <Kod Ve Ad>

Bu belge modülün işini tanımlar. `irp_sozlesme/` içindeki Modül Sözleşmesi ortak sınırları belirler; bu talimatla değişmez.

## Kaynak Ve Kapsam

- Şartname N:P/T maddeleri, görüşme ve ekip kararları:
- Kullanıcının tamamlayacağı iş ve başlangıç/son durumu:
- Bu teslimin kapsamı ve sonraya ayrılan işler:

## Veri Sahipliği

| Bilgi / Davranış | Sahibi | Kullanılacak Okuma / Olay / Sağlayıcı | Kanıt |
|---|---|---|---|
| | Çekirdek / bu modül / başka modül | | |

Çekirdek kataloğunda `urunde_mevcut`, `urun_kaynagi` ve `simulator` ayrı incelenir. Katman etiketi tek başına özellik yokluğu değildir. Eksik veri sıfır veya hazır plan sayılmaz. Çekirdek kuralı ya da başka modülün tablosu kopyalanmaz.

## Ekran Ve Yetki

- Ortak HTML/CSS/JavaScript ekranı, beyaz ERP; `on_yuz/ekran.js` ve `ac(host)` sözleşmesi.
- Hangi rol hangi projede hangi işi yapabilir? Menü izni, proje görünürlüğü ve işlem yetkisi ayrı yazılır.
- Ana ekranlar, seçili proje, kaydedilmemiş form, kişi/oturum değişimi, ret ve bağlantı kesilmesi davranışı.
- Genel service_role, kullanıcı şifresi ve modüle özel giriş ekranı kullanılmaz.

## Bağımlılık Ve Kurulum

- Künye kodu/harfi/sürümü, özel şema ve ileri SQL göçleri.
- Sağlanan/tüketilen okumaların adları, parametreleri, izinleri ve eksik/kapalı sağlayıcı sonucu.
- Kullanılan Python sürümü ve sabitlenmiş bağımlılıklar; paket dışı servis gereksinimi varsa önceden değerlendirilir.
- İstenen çekirdek değişiklikleri `istekler/` altında ayrı kimlikle ve kaynak/kanıtla yazılır; onay varsayılmaz.

## Kabul Senaryoları

1. Kullanıcının gerçek işi baştan sona: hazırlık → karar → sonuç.
2. Yetkili ve yetkisiz kişi/proje; kişisel veri ve para sınırı.
3. Tekrar kurulum, aynı olayın tekrarı, bayat karar, yarıda kalan işlem.
4. Kişi/oturum değişimi ve kapalı modül/sağlayıcı; eski veri korunur.
5. Simülatör ve ayrı gerçek SQL firmasında aynı girdinin beklenen sonucu. Modelde bulunmayan kapı için sahte başarı üretilmez.

Teslimde `TESLIM.md`, künye, göçler, kod, testler, senaryolar, beklentiler ve açık istekler bulunur. Çalışan ekran veya HTTP 200 tek başına kabul değildir.
