# Web İş Uygulaması

T20–T23, karar 141–152. Bilgisayara özel HTML/CSS/JavaScript arayüzü; sabit açık tema.
Telefon uygulamasından ayrı ekran düzeni, aynı Supabase motoru ve Dart istemci çekirdeği.

## Çalıştırma

Depo kökünde:

```sh
bash istemci/mac_derle.sh web --tam-sinama
```

Paket `~/irp_gosteri/web` altında güncellenir; mevcut `ayar.json` korunur.
`~/irp_gosteri/baslat.command` yerel sunucuyu açar. Adres `http://localhost:8080/`;
buluta bağlanmayan örnek veri `http://localhost:8080/?kip=gosterim`.

İleri veritabanı göçü ve çalışan paketi birlikte güncellemek için:

```sh
bash istemci/mac_derle.sh web --tam-sinama --bulut-guncelle --calistir --canli-sina
```

`--bulut-guncelle` mevcut kurulum betiğini sıfırlama seçeneği olmadan çalıştırır.
`--calistir` yalnız `~/irp_gosteri` içinden çalışan IRP sunucusunu yeniden başlatır.
`--canli-sina` mevcut bulutta dört rolle yalnız giriş ve okuma denemesi yapar; iş olayı göndermez.

## Senaryo 1

Yalnız ayrı yerel firmada tam gösteri akışını sınamak için:

```sh
bash istemci/mac_derle.sh web --senaryo1-sina
```

Bu akış SQL motorunu, web formlarını ve APK'nın Dart çekirdeğiyle telefon teslimini kullanır. Kişisel telefona bağlanmaz. Sonra CEO Örnek Veri ekranları da sınanır.

Mevcut test bulutunu gerçekten boş başlangıca geçirmek için açıkça eklenen seçenek:

```sh
bash istemci/mac_derle.sh web --senaryo1-sina --senaryo1-hazirla --calistir --canli-sina
bash istemci/mac_derle.sh apk
```

`--senaryo1-hazirla` eski iş verisini önce özel yerel klasöre yedekler; altı kişi hazır, proje/etap/iş/görev sıfır olacak şekilde firmayı değiştirir. Auth hesapları korunur. Normal web komutu bu işlemi yapmaz. Yeni senaryo kimliği eski cihaz günlüğünü silmeden ayrı depo seçer. Yeni APK'nın kurulması USB ile `bash istemci/mac_derle.sh kur` yolundadır.

Web: CEO, Yönetici, Ekip Lideri, Ofis Çalışanı. Telefon: Atölye Çalışanı, Ekip Lideri, Saha Çalışanı. Lider aynı kişidir.

Bağımsız olay penceresi `http://localhost:8080/olaylar.html`; Mac'teki `~/irp_gosteri/olaylar.command` da bu adresi açar. Ana uygulamadaki kişi değişimi izleyiciyi etkilemez. İzleyici açıldıktan sonra gelen gerçek olayları gösterir; işlem üretmez.

## Parçalar

| Dosya | Görevi |
|---|---|
| `app.js`, `pages.js`, `erp.js`, `styles.css`, `erp.css` | Giriş, gezinme, çekirdek iş sayfaları, profesyonel ERP düzeni |
| `workflow.js`, `task_templates.js` | Kabul/teslim/onay akışı, ayrı ekip takibi, kişi ve tarayıcıya özel görev şablonları |
| `management.js` | CEO örnek portföyü, dönemli maliyet ve dağılım tabloları/grafikleri |
| `olaylar.html`, `olaylar.js` | Ana uygulamadan bağımsız, kendi oturumuyla salt okuyan canlı olay penceresi |
| `actions.js`, `forms.js`, `assignment.js` | 89 kullanıcı eylemi, Türkçe formlar, çok satırlı atama ve özet |
| `kopru.dart` | Sınanmış `irp_cekirdek` paketini JavaScript'e açar; kuralları yeniden hesaplamaz |
| `client.js` | Auth, aynı RPC kapıları, kişi başına kalıcı günlük, dosya ve olayın atomik yazımı, sinyaller |
| `service_worker.js` | Yalnız uygulama dosyalarının çevrimdışı açılması; ayar/RPC/oturum yanıtı önbelleğe girmez |
| `sunucu.py` | Mevcut yerel dosya sunucusu ve yalnız yetkili için hesap açma/şifre sıfırlama ucu |
| `derle.py`, `yayinla.py` | Anahtarsız derleme ve kontrollü dağıtım |

İş verileri yalnız `public.oku` ve `public.olay_ekle` üzerinden gider. Yeni seçim/listeler
`150_web_is_okumalari.sql` içindedir; mevcut görme kurallarını kullanır. Göç 151, çalışan ayrıntısına yalnız YETKILI için güncel aylık brüt maaşı ekler; maaş görme yetkisinin devri MVP sonrası kararıdır (151). Maaş tutarı
günlükte tutulmaz. Başarısız yönetim gönderimi aynı olay kimliğiyle yeniden denenebilir.

Hesap yönetimi için yerel sunucu, kullanıcının jetonuyla `WEB_HESAPLAR` okumasını
doğruladıktan sonra mevcut Supabase Auth yönetici arayüzünü kullanır. Servis anahtarı
ve veritabanı bağlantısı yalnız sunucu sürecindedir. Bunun için Mac'teki Python
ortamında `psycopg` gerekir. Sunucunun iş hesabı veya alternatif iş motoru yoktur.

## Sınamalar ve Kaynak

`test/tarayici.py --tam`: ayrı PostgreSQL test firması, gerçek SQL kapıları, ayrı
Chrome profili; bütün sayfalar, bütün formlar, görev teslim/onayı, dosyalar, atölye,
belge sürümü, çevrimdışı yeniden açma ve gönderim. Auth ve sinyal taşıması yereldir.
`test/hesap_sina.py`: ayrıcalıklı hesap yolunun yetki ve eşleme denetimleri.
`node --test test/*.test.js`: şema kapsamı, atama bağlantıları, form ve güvenlik kontrolleri.
Canlı bulutta yazmalı prova yapılmaz. Telefonun kişisel ekranı kullanılmaz.

İşleyişin kaynakları T20'de listelenen üç sunumdur. Sonraki kararlar eski sunum
ayrıntılarından üstündür. Kapsam 91 çekirdek eyleminden 89 kullanıcı işlemidir;
kurulum kapanışı ve test saati mevcut işletim yolunda kalır. Bilinçli olarak
MVP sonrasına ertelenen motor/modül işleri kendi planında izlenir.

## Kullanım Düzeltmelerini Kurma

Kullanım düzeltmeleri gerçek SQL/Chrome ile doğrulandı; SQL 151 ve paket mevcut çalışan ortama kuruldu. Mevcut iş verisini koruyarak yeniden denetlemek ve kurmak için:

```sh
bash istemci/mac_derle.sh web --senaryo1-sina --bulut-guncelle --calistir --canli-sina
```

Yerel Senaryo 1 ve CEO örnek ekranları geçmeden paket kopyalanmaz veya bulut güncellenmez. Komutta `--senaryo1-hazirla` yoktur; mevcut firma sıfırlanmaz. Sonuç dosyası `codex/sonuclar/kullanim_duzeltmeleri_SONUC.md`.

Görev Şablonlarım ve Planlama Görevi Metni yalnız aynı kişi, firma ve tarayıcı için IndexedDB'de saklanır; yeni bulut tablosu veya iş olayı üretmez. Başka cihazda görünmez, tarayıcı verisi temizlenirse silinir. Ücret görme ve değiştirme izinleriyle rol/personel/ekip yönetiminin tamamının devredilmesi MVP sonrası çekirdek planında (30) durur.


## Test 2 Ekran Düzenlemeleri

Boş atama başlangıcı, düğmeyle yönetilen işlem menüleri, kaydırılan pencere içeriği, okunur gün sonu tablosu ve menüde bekleyen sayıları T23'tedir. Yeni kullanıcı Test 3 senaryosu yoktur; mevcut otomatik akışlar güncellenmiştir. `daily_summary.js` mevcut özet değerlerini ad/saat tablolarına, `navigation.js` mevcut okumaları menü sayılarına dönüştürür. Yeni SQL kapısı yoktur. Safari denemesi isteğe bağlıdır:

```sh
bash istemci/mac_derle.sh web --safari-sina
```

Safari otomasyon oturumu açılamazsa bu açıkça yazılır; Safari geçti sayılmaz ve tarayıcı ayarı değiştirilmez. Sonuç `codex/sonuclar/test2_SONUC.md`.
