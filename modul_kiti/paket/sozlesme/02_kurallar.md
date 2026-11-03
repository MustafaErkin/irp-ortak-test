# 02 · Kurallar: yap ve yapma

Kuralların tamamı ve sınamaları `kaynak/18_modul_sozlesmesi.md` › 3'te (K-1…K-34). Burada modül yazarı için olanlar, nedenleriyle.

## 1. Veri

| Yap | Yapma | Neden |
|---|---|---|
| Çekirdeğin kaydını kimliğiyle, **değer olarak** tut (`nesne_kimligi text`) | Çekirdeğin tablosuna yabancı anahtar koyma | Çekirdeğin tabloları olaylardan yeniden kurulabilir; sert bağ kırılır |
| Kişiyi, birimi, projeyi, tezgâhı, takvimi **çekirdekten oku**; gerekirse önbellekte tut | Bunları modülde ikinci kez tutup oradan yönetme | Tek doğru kaynak çekirdektir; iki kaynak ayrışır |
| Modülün kendi verisini (tedarikçi, fiyat, ölçüm, miktar, raf…) **kendi tablonda** tut | Ortak nesnenin aşamasını kendi tablonda ayrıca tutma | Parçanın aşaması tek yerdedir: çekirdekte. İki modül aynı parçayı ilerletebilir; aşama karışmaz |
| Miktarı modülde tut; aşama "tamamı" için ilerler | Kısmi teslim için çekirdekte paralel aşama arama | Aşama nesne başına tektir; kısmi durum modülün kendi bilgisidir |
| Çekirdeğin kod listelerine (`YETKINLIK`, `ARIZA`…) künyeden kod ekle | Çekirdeğe yeni liste açmaya çalışma | Çekirdeğin listeleri sabittir; modülün listesi modülün tablosundadır |

## 2. Olay

| Yap | Yapma | Neden |
|---|---|---|
| Kullanıcının yaptığı işi **kullanıcının oturumuyla** gönder | Olayı modülün adına, servis gözüyle yazma | Olay insanın yaptığıdır; çekirdek yetkiyi kişiye göre denetler |
| Yönetim kararında okuduğun **sürümü** `neyin_ustunde`'ye koy | Sürümsüz karar gönderme | Kullanıcı eski ekrana bakarak karar vermesin (bayatlık) |
| `BAYAT` gelince yeniden oku, kullanıcıya göster, yeniden sor | Kendiliğinden yeniden gönderme | Karar değişen kayda göre yeniden verilmeli |
| Ağ hatasında aynı zarfı yeniden gönder (katman yapar) | Aynı iş için yeni kimlikle ikinci olay kurma | Aynı zarf tekrardır, yeni zarf ikinci iştir |
| Birbirine dayanan olayları sırayla gönder (katman an'ı artırır) | Aynı ana iki karar yazma | Aynı ana dayanan karar `BAYAT, SIRA` alır |
| Modülün kuralının sonucunu **bildirim** olarak bırak | "Sipariş gecikti" diye olay yazma | Sistem olay yazmaz; olay insanın tanıklığıdır |

**Modülün yazamadığı eylemler:**
- **Kurulum eylemleri:** `MODUL.TANIMLADIM`, `NESNE_TURU.TANIMLADIM`, `KOD.TANIMLADIM`, `YETKI.TANIMLADIM`. Künyeden kurulumda yazılır (`03_kunye.md`).
- **Firmanın ayarları ve denetimi:** `AYAR.*`, `PROJE.ERISIM_*`, `KAYIT.GECERSIZ_SAYDIM`… Yalnızca çekirdeğin ekranlarından yazılır.
- **Mavi yakanın düğmeleri:** `IS.BASLADIM`, `IS.MOLA_VERDIM`, `IS.TAMAMLADIM`, `MESAI.*`, `DURUS.*`… Mavi yakanın tek yolu çekirdeğin telefonudur.

Tam liste `arac/cekirdek_katalogu.json`'da; künye denetleyicisi yakalar.

## 3. Okuma ve görünürlük

| Yap | Yapma | Neden |
|---|---|---|
| Kullanıcıya gösterilecek her şeyi **kullanıcının gözüyle** oku | Servis gözüyle okuduğunu ekrana koyma | Görünürlüğü (proje ekibi, kişisel veri, para) çekirdek uygular; modül ikinci bir görünürlük kuralı yazmaz |
| `YETKI` hatasında kullanıcıya "göremiyorsunuz" de | Hatanın etrafından dolaşma | Gizlilik kuralı şartnamenindir |
| Sorumlu olmanın projeyi göstermediğini bil | Sorumluya projeyi kendin açma | Projeyi görmek proje ekibindendir (karar 103) |
| `guncel` değilse "hesaplanıyor" göster | Eski veriyi güncel gibi gösterme | Çekirdek geç gelen olayı arkada hesaplarken veri birkaç saniye eski olabilir |

## 4. Nesne, tür, rol

| Yap | Yapma | Neden |
|---|---|---|
| Modülün kendi nesnesini **tür olarak** künyede tanımla. Aşamalar ve geçişler veridir | Tür için çekirdeğe kod isteme | Yeni tür çekirdekte kod değişmeden çalışır |
| Başka türe (ör. `PARCA`) **kendi tablonla** uzan (`tur_uzantilari`) | Sahibi olmadığın türü yeniden tanımlama | Her türün tek sahibi vardır. `PARCA` ve `BELGE` çekirdeğindir |
| Türe aşama **ekle**; kaldıracaksan önce içindeki nesneleri taşı | İçinde nesne duran aşamayı kaldırma | Çekirdek reddeder |
| Modülün rolünü künyede tanımla (ör. `KALITECI`) | Çekirdeğin rolünü yeniden tanımlama | Rol veridir. Rolün yapabildiğini o rolü taşıyanın üstleri de yapabilir |
| Gizli kalması gerekeni (ör. teklif) modülde tut | Çekirdeğe **projesiz** nesne açma | Projesiz nesneyi firmada herkes görür, mavi yaka dahil |

## 5. Bildirim

| Yap | Yapma | Neden |
|---|---|---|
| Kuralı tekrar tekrar çalıştır; bırak ya da kaldır | Bildirimi bir kez gönderip unutma | Tekillik anahtarı aynı bildirimi iki kez üretmez; durum düzelince kaldır |
| Metne yalnızca kaydın kendi bilgisini yaz | Metinde başka projeden söz etme | Süzgeç kaydın projesine bakar, metnin içine bakmaz |
| Modül kapanacaksa önce kendi açık bildirimlerini kaldır | Pasif modülün bildirimlerini kutuda bırakma | Pasifleşince kendiliğinden düşmezler |

## 6. Para ve kişisel veri

- **Beyan:** Kişisel veri ya da para okuyan, tutan ya da yazan modül künyede beyan eder:
  - `kisisel_veri`: alan ve tutulma nedeni (KVKK)
  - `para: true`

  Beyansız modül bunlara dokunamaz; denetleyici yakalar.
- **Ne kimde:**
  - Maaş ve saat maliyeti yalnızca yetkilinin gözüyle okunur.
  - Para servis gözüyle okunmaz. Para okuyan iş (ör. muhasebeye aktarım) yetkilinin oturumuyla, onun bastığı düğmeyle yapılır.
- **Eksik değer:** Bilinmeyen tutar sıfır sayılmaz. Çekirdek `VERI_EKSIK` der, modül de öyle gösterir.

## 7. Modüller arası

- **Şema:** Başka modülün tablosunu okuma. Göç denetleyicisi yakalar.
- **Ortak bilgi:** İki yoldan biriyle paylaşılır:
  1. Çekirdeğe istek: iki modül de ihtiyaç duyuyorsa ve omurgaya aitse (kişi, proje, saat, top kimde).
  2. Sağlayan modül okuma yayımlar (`saglananlar`), tüketen künyesinde anar (`bagimliliklar`).
- **Bağımlılık:** Her zaman isteğe bağlıdır. Sağlayan modül kapalıyken tüketen çalışmaya devam eder; ekranda "bilgi yok" görünür.
- **Etkileşim:** Modüller birbirini çekirdeğin olayları üzerinden etkiler. Örnek: satın alma parçayı `GELDI`'ye geçirir; kalite modülü bunu görüp kendi kuralını çalıştırır.

## 8. Ölçüt: akıllı, kapsayıcı, kolay

- **Doğrulama maddeleri:** Şartnamedeki "onaylı", "doğrulanmış" maddeleri her adımı onaylatmak diye değil, haksız sonuç çıkmasın diye okunur.
- **Ekrandaki yük:** Kural arkada çalışır. Ekranda kişiye en fazla bir soru sorulur.
- **Kimse bir şey yapmasa da:** Sistem çalışır.
- **Mavi yaka:** Az düğme, tek yol. Seçimi ekip lideri yapar.
