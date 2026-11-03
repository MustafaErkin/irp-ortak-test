# IRP çekirdeği

Python başvuru modelinin saf Dart çevirisidir. Flutter ve ağ bağlantısı gerektirmez.
Çevrilen fonksiyonların başında kaynak dosya ve satır numarası vardır.

```powershell
dart pub get
dart test
dart analyze
dart run tool/vektor_kosucu.dart
```

Komutları bu klasörde çalıştırın. Koşucu bu klonun `referans/cevap_anahtari/`
altındaki bütün senaryo ve Modül 3 girdilerini tarar. Cihaz ve saf sorgu
vektörlerini karşılık gelen beklenen dosyalarla karşılaştırır. Tek dosya argümanı
verilirse JSON raporu o dosyaya yazılır. Referansı değiştirmez, Python çalıştırmaz.

```dart
import 'package:irp_cekirdek/irp_cekirdek.dart';

final cihaz = Cihaz('K017', 'T', SistemSaati(), yerelDepo: BellekDeposu());
final olay = await cihaz.olayYaz('MESAI.GIRDIM', {}, baglanti: false);
final ekran = cihaz.ekranHali({});
await cihaz.gonderimDongusu(SahteBulut());
```

`An`, anı ve yerel farkı birlikte tutar. `an`, `gun` ve `gunAni` modeldeki
`+03:00` yorumunu kullanır. `Saat` test saati, `SistemSaati` gerçek saat kaynağıdır.
JSON alan adları ve modelin hata türü/nedeni korunur.

`YerelDepo.oku/yaz` eşzamanlıdır. Sayaç artırma ile kalıcı yazım arasında
`await` yoktur. Her depo dosyasının tek bir cihaz sahibi ve tek isolate içinde
kullanılması gerekir. Süreçler veya isolate'lar arası ortak sayaç kilidi yoktur.
`sayaciEsitle` dışarıdan alınmış bulut kimliklerini kabul eder.
`Bulut.olayEkle`, `olayYaz` ve `gonderimDongusu` gelecekteki ağ uygulaması için
`Future` döndürür. Bu turdaki tek bulut uygulaması `SahteBulut` ağ kullanmaz.

Dosya sistemi olan hedeflerde ayrıca
`package:irp_cekirdek/dosya_deposu.dart` içe aktarılır ve
`DosyaDeposu('.../cihaz.json')` verilir. Önce aynı dizindeki geçici dosya yazılıp
flush edilir, sonra asıl dosyanın yerine taşınır. Web bu giriş dosyasını kullanmaz.
Telefon/web kalıcılık katmanı `../uygulama/lib/durum/` içindedir.
Uygulama çekirdeği `BellekDeposu` ile çalıştırır, işlem sonunda bütün cihaz
durumunu dosya/IndexedDB'ye kaydeder ve bu yazımı beklemeden gönderime geçmez.

İstemci 2'de `tanikliYaz(kod, sonHal, eylemSemalari: katalog, hedefler: [...],
girdiler: {...})` eklendi. Katalog `referans/eylem_semalari.json` kaynağıdır.
Kişi günü dışındaki `TANIKLIK` eylemleri aynı sayaç, zarf ve günlükle yazılır.
`CALISAN` eylemleri bu kapıyı kullanamaz; onların düğme kapısı `olayYaz` içindedir.
Yeni yol yönetim kararı kabul etmez. Mevcut model vektörleri korunmuştur.

`depoKayboldu` model gibi yalnız belleği ve cihaz harfini sıfırlar. Kaybolan
deponun yerine yeni depoyla, çevrimiçi kayıt sonucu alınan yeni harfle devam edilir.
Harf ayrı kayıt bilgisidir; sayaç/günlük JSON'una eklenmez.

SHA-256 için `ozet(x)` verilen veriyi aynen özetler. İş nesnesi için önce
`isAlanlari(x)` ile B36 alanları çıkarılır. Liste özeti doğrudan sıralı dizidendir.
Vektör karşılaştırıcısı B36 alanlarını dışlar, sayılarda `1e-6` tolerans uygular;
eksik alan, `null`, boş dizi ve boole değerlerini birbirine dönüştürmez.

Ek geçiş örneklerini yeniden üretmek için depo kökünde
`py -3.11 -B codex/calisma/istemci1/gecis_ornekleri.py` kullanılır.
Modelde görülen ve korunan ayrıntılar `codex/sonuclar/istemci1_SONUC.md` içindedir.
