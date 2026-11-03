# Gösteri Yedeği Ve Geri Dönüş

31 Ekim 2026 · Karar 167 · Kullanım testiyle bağımsız hazırlık.

Bu araç aynı sürümlerin kurulu olduğu MVP firmasının iş verisini geri getirmek içindir. Kullanıcı hesaplarını, parolaları, dış servis ayarlarını veya uygulama kodunu taşımaz. Yeni Supabase projesine hesap göçü ve üretim felaket kurtarma sistemi değildir.

## Neleri Alır?

- Çekirdeğin olayları, ücret ekleri, kişiler, projeler, işler, onaylar, son haller, cihaz eşlemeleri ve hesaplama durumu.
- Kurulu modüllerin özel tablolarının tamamı; siparişin donmuş kopyası/PDF baytları, sayaçlar, planlar ve ortak dosya bilgileri dahil.
- Ortak modül dosya yoluna yüklenmiş fiziksel dosyalar ve üretilmiş PDF'ler.
- Çekirdek olaylarına eklenen kanıtların Supabase `kanitlar` kovasındaki baytları; eski/geçersiz sayılmış olayların ekleri dahil.

Telefon/tarayıcıdaki henüz gönderilmemiş işlemler ve kişisel şablonlar yalnız cihazdadır; sunucu yedeğinde bulunmaz. Harici bağlantıyla gösterilen, MVP dosya yoluna yüklenmemiş dosyaların yalnız veritabanındaki adresleri korunur. Auth kullanıcıları ve veritabanı rol parolaları arşive alınmaz; mevcut hesap ve modül kurulumunun devam etmesi gerekir.

## Yedek Alma

Repo kökünden, mevcut özel ortam dosyası yalnız komut içinde yüklenir. Aşağıdaki örnekte `gosteri_001` daha önce bulunmayan bir klasör adı olmalı. Aynı adın üzerine yazılmaz.

```sh
(
  set -a
  . "$HOME/irp_gizli/supabase.env"
  set +a
  "$HOME/.irp_venv/bin/python" -I -B urun/veri/gosteri_yedegi.py \
    --al "$HOME/irp_gizli/gosteri_yedekleri/gosteri_001" \
    --modul-dizini "$HOME/irp_gosteri/.runtime/modul_dosyalari"
)
```

Araç kaynakta yalnız okur. Bütün tablolar aynı veritabanı anından alınır. Dosyaların boyutu ve SHA-256 özeti, yani içeriğini temsil eden parmak izi, denetlenir. Dosya yüklemesi henüz bitmediyse/eksikse yedek başarısız olur; tamamlanmış klasör bırakmaz. Tekrar denenebilir.

Gösteri başlangıç noktası alınırken önce telefon/web gönderimlerinin bitmesi, ardından yeni işlem yapılmaması gerekir. Bu, yedekten sonra üretilen işlerin yedeğin içinde olduğu sanılmasını önler. Kullanım testi sürerken yedeği geri yükleme veya firmayı boşaltma yapılmaz.

Arşiv git/web dışında, yalnız sahibinin açabildiği klasöre yazılır: klasör `700`, parçalar `600`. Ücret ve ticari bilgiler içerdiği için GitHub'a veya test paylaşım paketine eklenmez. Anahtar ve bağlantı bilgisi arşive/çıktıya yazılmaz.

## Bağlantısız Denetleme

```sh
"$HOME/.irp_venv/bin/python" -I -B urun/veri/gosteri_yedegi.py \
  --denetle "$HOME/irp_gizli/gosteri_yedekleri/gosteri_001"
```

Bu işlem veritabanına/depolara bağlanmaz. Eksik veya değişmiş tablo/dosya parçasını reddeder. Özet denetimi bozulmayı bulur; arşivin kimden geldiğini doğrulayan dijital imza değildir. Yalnız kendi oluşturduğumuz özel yedekler kullanılır.

## Geri Yükleme Koşulları

Geri yükleme bütün iş verisinin yerini alır. Önce ayrı ortamda prova edilir. Mevcut kullanım firmasına bu hazırlık sırasında uygulanmadı.

1. Web ve modül servisleri durur; telefon/tarayıcı yeni işlem göndermez. Cihazlardaki bekleyen işler önce ele alınır. Aynı firmanın `irp-motor-saat`, `irp-motor-bekleyen` ve `irp-motor-log-temizle` zamanlayıcıları kapatılır; araç açık zamanlayıcıyı reddeder.
2. Hedefte aynı çekirdek göçleri, aynı modüller/sürümler/göçler, tablo-kısıt-tetik yapıları ve modül etkinlik/giriş rolü durumları bulunur. Kaynak kodun uyumlu sürümü korunur. Yeni/eksik modül veya farklı tablo yapısı varsa araç yazmaz.
3. Giriş hesabı–kişi eşlemeleri aynı olmalıdır. Araç yeni hesap/parola oluşturmaz. Yalnız mevcut `TEST` kurulumuna döner.
4. Bağlantılar komut ortamına ayrı hedef adlarıyla yüklenir: `IRP_YEDEK_HEDEF_DB`, `IRP_YEDEK_HEDEF_URL`, `IRP_YEDEK_HEDEF_SERVIS`. Kaynak değişkenlere otomatik dönüş yoktur. Hedefin modül dosya dizini de açıkça verilir.
5. Geri yükleme komutu, durmuş servisleri ve veri değişimini açıkça belirtir:

```sh
"$HOME/.irp_venv/bin/python" -I -B urun/veri/gosteri_yedegi.py \
  --geri-yukle "$HOME/irp_gizli/gosteri_yedekleri/gosteri_001" \
  --modul-dizini "$HOME/irp_gosteri/.runtime/modul_dosyalari" \
  --servisler-durdu --yerine-koy
```

Bu komut, yukarıdaki hedef ortam değişkenleri ayarlanmadan çalışmaz. Buraya sır değerleri yazılmaz. Veritabanı ve depo adreslerindeki Supabase proje kimlikleri de eşleşmelidir; araç iki farklı projeyi birleştiren ayarı reddeder.

Önce dosyalar doğrulanıp hedefte tamamlanır. Aynı kimlikte farklı dosya varsa üzerine yazılmaz. Veritabanının tamamı tek işlemde değişir; hata olursa tablolar, kısıtlar, tetikler ve dizi başlangıçları birlikte geri alınır. Kısıtlar devre dışı bırakılmaz: döngülü ilişkiler yüklenene kadar ertelenir ve işlem bitmeden gerçekten doğrulanır. Başarısızlıkta diskte/kovada henüz başvurulmayan fazladan dosya kalabilir; bunlar var olan dosyaların yerine geçmez.

Sonra servisler/zamanlayıcı açılır; web yeniden açılıp rol/proje/modül/dosya ve yeni işlem kontrol edilir. Telefon/tarayıcının eski yerel kuyruğu ve sunucuya göre ileri durumdaki önbelleği ayrıca ele alınmadan teste devam edilmez. Araç cihazları kendiliğinden sıfırlamaz.

## Ayrı Ortamda Teknik Prova

```sh
bash istemci/mac_derle.sh web --gosteri-yedek-sina
```

Bu özel seçenek web derleme/dağıtım yoluna girmez. Yalnız yeni yerel test veritabanları, geçici geçitler ve dosya dizinleri kullanır; canlı ayar dosyasını okumaz. Kaynak firma kapanıp silindikten sonra uyumlu yeni test firmasında geri dönüş denenir. Aynı giriş hesaplarını temsil etmek için yalnız yerel taklit hesap eşlemeleri eşitlenir; gerçek Auth'a dokunulmaz.

Gerçek üç modülle teklif/onay/sipariş/proje/devir, şartname ve üretilmiş PDF'ler; ayrıca çekirdek dosya eki sınanır. Bütün tablo içerikleri karşılaştırılır, normal kapılardan okunur, yeni müşteri/proje açılır. Bozuk/eksik bayt, sürüm/hesap farkı, yabancı anahtar ve son aşama dizi hataları da denenir. Kaynak salt okunur bağlantıyla, geri dönüş ise yalnız uygulama sahibi rollerinin üyesi olan, `superuser` olmayan kullanıcıyla sınanır.

Sonuç: [makine çıktısı](../../codex/sonuclar/gosteri_yedegi_sonuc.json). Canlı Supabase dosya yetkileri/geri dönüşü ve gerçek S25 kuyruğu bu yerel provayla doğrulanmış sayılmaz; kullanım turundan sonra gösteri hazırlığında ele alınır.

Eski `senaryo1_hazirla.py --temiz-baslat` modül kurulmuş firmayı artık reddeder. Bütünleşik boş başlangıç hazırlığı ayrı kalan iştir; bu yedek aracı mevcut firmayı kendiliğinden boşaltmaz.

Teknik dayanak: PostgreSQL 17 [COPY](https://www.postgresql.org/docs/17/sql-copy.html), [işlem yalıtımı](https://www.postgresql.org/docs/17/transaction-iso.html), [ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html) ve [ALTER SEQUENCE](https://www.postgresql.org/docs/17/sql-altersequence.html). Hesaplar ve parolalar yerine yalnız uygulama tabloları/baytları taşınır; üretilen sütunları veritabanı yeniden hesaplar.
