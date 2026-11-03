# Sibernetik IRP telefon uygulaması

Flutter 3.47.6 / Dart 3.13.5. Açılışta yalnız `FiksturBulutu` kullanılır;
Supabase başlatılmaz. Gösteri hesabı **K017**, ilk şifre **123456**.
Kayıtta seçtiğiniz altı rakamlı PIN sonraki açılışlarda çevrimdışı da çalışır.
Gösteri zamanı Python modelinden gelen 22 Ekim 2026 okumalarıdır.

## Çalıştırma ve doğrulama

Bu klasörde:

```powershell
flutter pub get
flutter test
flutter analyze
flutter build web --no-web-resources-cdn
py -3.11 -B -m http.server 8768 --bind 127.0.0.1 --directory build/web
```

`http://127.0.0.1:8768` adresini açın. Web 480 px genişlikle sınırlandırılmış
telefon düzenini kullanır; sistemin açık/koyu görünümünü izler.
Android kamera izni tanımlıdır; bu tur SDK lisansı kabul edilmedi, APK üretilmedi.

## Katmanlar

- `bulut/`: Auth, saat, cihaz kaydı/eşitleme, olay, okuma, sinyal, kanıt ve
  gösteri sıfırlama kapıları. Supabase iskeletine ancak dışarıdan yapılandırılmış
  `SupabaseClient` verilirse erişilebilir; uygulamanın açılışı bunu yapmaz.
- `sahte/`: Python modelinin okuma ve kabul zarflarını oynatır. `sec` ve
  `sinyalVer` testlerden kullanılabilir. Tam bir sunucu/kural motoru değildir.
- `durum/`: tek `ChangeNotifier`, PBKDF2 PIN, kalıcı kayıt, sayaç/günlük,
  okuma önbelleği, sıralı gönderim, 2–60 saniye yeniden deneme ve fotoğraf kuyruğu.
- `ekranlar/telefon/`: kayıt/PIN, iş ve durumları, mola/duruş/tamamlama,
  not, bildirim, günün işleri, menü, günlük ve QR/çizim ekranları.

Dosya deposunda geçici dosya flush edilip asıl dosyanın yerine taşınır.
Web IndexedDB yazımı tamamlanmadan başarı gösterilmez veya olay gönderilmez.
İkinci sekmenin eski sürümle yazması engellenir. Depolama hatası gönderimi kapatır.
PIN yanlış sayacı ve bekleme anı kalıcıdır; 10 yanlış sonrası kayıt sıfırlanırken
gönderilmemiş günlük ve fotoğraflar korunur.

Fotoğraf uzun kenarı 1600 px'e küçülür; SHA-256 son JPEG baytlarından alınır.
Olay kabul edildikten sonra özel `kanitlar` kovası için hazırlanan yol yüklenir.
Sahte bulut baytları yalnız bellekte saklar. Gerçek Storage bu tur denenmedi.

QR kamerası `mobile_scanner` kullanır. Web'de yalnız yerleşik BarcodeDetector
seçilir, CDN'den tarama kodu indirilmez. Destek/izin yoksa metinle çizim açılır.
PNG çizimleri `InteractiveViewer` ile büyütülür. Haritadaki QR ve parça kodu
aynı dosyayı açar. Üç çizimin tamamı sentetiktir.

## Kaynakları yeniden üretme

Depo kökünde:

```powershell
py -3.11 -B codex/calisma/istemci2/fikstur_uret.py
```

Bu klasörde:

```powershell
dart run tool/cizim_uret.dart
flutter test tool/ekran_cikti.dart
```

QR yazdırma sayfası: `assets/cizimler/qr_kartlari.html`.
Son komut Flutter test motorunda yerel PNG üretir; **web ekran görüntüsü değildir**.
Bu oturumda kullanılabilir tarayıcı bulunmadığı için web görüntüleri alınamadı.
Ayrıntılı sonuç: `../../codex/sonuclar/istemci2_SONUC.md`.

Fontlar Flutter SDK'nın yerel Roboto kopyasından alınmıştır; lisans
`assets/fontlar/LISANS.txt` içindedir. `web/irp_offline.js`, ilk çevrimiçi
yükleme tamamlandıktan sonra uygulama kabuğunu, fontları, CanvasKit'i ve çizimleri
çevrimdışı açılış için saklar. Oturum/günlük bu önbelleğe girmez.
`node tool/cevrimdisi_kabuk_test.mjs` derlemedeki kaynaklar ve worker mantığını
Node VM'de sınar; gerçek tarayıcıda worker kurulumu bu oturumda doğrulanamadı.
