# 07 · Ortak Web Ekranı

Paket 1.1 · Karar 157: web ve modül ekranları **HTML, CSS ve JavaScript** kullanır. Arka yüzdeki Python iş mantığı korunur. Mobil istemci Flutter'dır; masaüstü ekranı mobil ekranın büyütülmüş kopyası yapılmaz.

## Tek Çalışma Alanı

Tek adres, giriş, menü, kişi ve proje bağlamı kullanılır. Beyaz ERP düzeni sistemin koyu tema tercihini izlemez. Ayrı React uygulaması, iframe, ikinci giriş, modüle özel kişi seçimi veya oturum deposu kurulmaz. Mavi yakanın telefonuna modül düğmesi eklenmez.

`kunye.json` içinde ekranlı modül `on_yuz.tur: UYGULAMA_ICI` bildirir. `YOK` arka plan modülü içindir. Eski `AYRI_UYGULAMA` künye biçimi geriye dönük okunabilir; yeni web çalışma kaydı bunu devreye almaz.

## Ekran Bağlantısı

Giriş dosyası `on_yuz/ekran.js` olarak teslim edilir. Dışa aktardığı `async ac(host)` işlevi şu nesneyi alır:

| Alan | Sözleşme |
|---|---|
| `kok` | Modülün çizim yapacağı DOM kökü. Ortak menü/üst çubuk değiştirilmez. |
| `baglam` | `kisi`, `kisiler`, `birimler`, izinli `projeler`, seçili `proje`, `tarih`, `yonetici`, `yetkili`. Gösterim bağlamıdır; arka yüz yetkisinin yerine geçmez. |
| `istek(yol,{method,body})` | Modülün kendi API'sine göreli yol. Ortak katman mevcut kullanıcı oturumunu taşır, yeniler ve kişi değişince eski cevabı iptal eder. JWT veya şifre modül ekranına verilmez. |
| `projeSec(kimlik)` | İzinli proje bağlamını ortak uygulamada seçer. |
| `yenile()` | Çekirdek okumalarını yeniler. |
| `ui` | Ortak `esc`, `table`, `panel`, `modal`, `toast`, `date`, `hours`, `badge`, `ad`, `gantt` yardımcıları. Kullanıcı metni HTML'e `esc` ile konur. |

`ac` `{dispose(),refresh(baglam)}` döndürür. `dispose` dinleyici, zamanlayıcı ve modül pencerelerini temizler. `refresh` kaydedilmemiş formu silmeden bağlamı yeniler. Navigasyon/kişi değişiminden sonra sonuç çizilmez. Kullanıcı kimlikleri, kişi kodları ve ham olay adları görünür metne yazılmaz; başlık ve rol/ad gösterilir.

```js
export async function ac(host) {
  const veri=await host.istek('/projeler');
  host.kok.textContent='Projeler: '+veri.projeler.length;
  return {dispose(){},refresh(baglam){host.baglam=baglam;}};
}
```

Ekran → modül API'si → `irp_sozlesme.baglanti` → çekirdek/sağlayıcı sırası korunur. Ekran doğrudan SQL veya çekirdek servis kimliği kullanmaz. Arka yüz `Authorization: Bearer <normal kullanıcı>` başlığıyla `cekirdek.oturum` açar. İşlem yetkisini çekirdek, özel modül verisinin görünürlüğünü modül doğrular.

## Çalışma Kaydı Ve Adres

Çekirdek ekibi `moduller/kayit.json` içinde kod, onaylı paket yolu, Python ASGI giriş noktası, menü rolleri, `ekran.js` ve adresi kaydeder. Proje Planlama örneğinde adres `/#modules/proje-planlama`, API `/irp/moduller/M11B/api/...` olur. Gelen paketten adres veya süreç komutu doğrudan çalıştırılmaz; künye/SQL denetiminden geçen uyarlama kayda alınır.

Derin bağlantı veri taşımaz. Künyedeki bağlam ve kimlik, izinli ortak bağlama eşlenir; hedef ekran veriyi kullanıcının gözüyle yeniden okur. Bu sürümün çalışan bağlantısı proje bağlamıdır. Nesne/tezgâh gibi başka bağlamlar genel olarak tamamlanmış sayılmaz. Modül pasifken menüden kalkar ve API kapanır; eski verisi korunur.

## SDK 1.2 İle Güncel Ortak Yardımcılar

- `host.istek` varsayılan olarak JSON döndürür; `responseType:'blob'` ile PDF gibi ikili cevap alınabilir. Başarısızlık `UserError.message` ile gelir; HTTP retlerinde `code` durumun metnidir. Diğer istemci hatalarında kod boş veya `STALE_SESSION` olabilir. Yapılandırılmış ham hata gövdesi bugün taşınmaz; `govde/body/data/detail` tahminleri sözleşme değildir. Böyle bir ihtiyaç ayrıca bildirilir.
- `host.ui.editor()` ortak form/okuma/dosya/indirme araçlarını sağlar. Kaynak örneği güncel geliştirici paketinin `arayuz/ortak/modul_ui.js` dosyasındadır.
- Fiziksel dosya, kalıcı olay zarfı ve gerçek not alıcıları `08_dosya_ve_kalici_istek.md` içindedir. SDK 1.1'de açık bırakılan bu işler 1.2'de uygulanmıştır; kullanım ve izin sınırları korunur.
- Yeni modülün başlangıç belgesi, sahibinin iş tanımına göre hazırlanan `GELISTIRME_TALIMATI.md`'dir. Eski sürüm uyum notu yalnız mevcut modül güncelleniyorsa gerekir. Ortak standart ve örnekler yeni modülün iş kapsamını belirlemez.
