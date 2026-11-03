# 02 · Modül sözleşmesi

*Sibernetik IRP çekirdeği · sürüm 10.2 · Bir modülün çekirdeğe nasıl bağlanacağının tam tarifi. Kaynak: T8 › 12, T9 › 6, T10, kararlar 72, 87, 91, 95–99. Şemalar: `sema/olay_semasi.json`, `sema/modul_bildirimi_semasi.json`.*

## 0. Üç cümle

1. **Çekirdek modülleri tanımaz; bilgi çekirdekten modüle akar.** Çekirdek modül tablolarını okumaz.
2. **Modül çekirdeğe yalnızca beş kapıdan dokunur:** okuma, olay, nesne uzantısı, plan sonucu, bildirim kapısı (aşağıda 2–6). Belge sürümü olay kapısının bir kullanımıdır (7).
3. **Modül çekirdeğin hiçbir tablosuna doğrudan yazmaz**, çekirdeğin bir kuralını kendi içinde tekrar etmez. Örnekler: kapasite, maaş, kişinin günü, görünürlük.

## 1. Kimlikler: modül tablosu neyi taşır

Modülün tabloları çekirdekteki kayıtlara **kimlikle** bağlanır. Çekirdeğin ana verisi modülde **kopyalanmaz**:
- Kişi, birim, rol.
- Proje ve etap.
- Tezgâh, takvim, izin.
- Ortak nesne (parça, belge…).

Gerekirse okunur. Okunan değer önbellekte tutulabilir; kaynak her zaman çekirdektir.

| Kayıt | Kimlik | Not |
|---|---|---|
| Kişi | `K017` (kişi kodu) | Bu sürümde kod = kimlik |
| Birim | `IMALAT`, `PLANLAMA`… | Kod = kimlik |
| Tezgâh | `CNC-02` | Kod = kimlik |
| Proje | **kimlik** (görünen kod ayrı: `2509084`, ek: "Servis") | Kod değişebilir, kimlik değişmez (karar 77). QR kimliği taşır |
| Etap | Doğuran olayın kimliği | |
| İş (atölye) | Tek satırlı tanımda doğuran olayın kimliği; çok satırlıda `<doğuran olay>/<n>`, ör. `K004-2610200031-M/1` | |
| Görev | `<doğuran olay>/<n>` | |
| Ortak nesne | Doğuran `NESNE.ACTIM` olayının kimliği | İsteğe bağlı `kod` (parça kodu) ayrı; değişebilir |
| Olay | `K017-2610220014-T` | |

**Veritabanı notu:** Çekirdeğin nesne tabloları türetilmiştir; silinip olaylardan yeniden kurulabilir. Bu yüzden modül tablosu çekirdek kimliğini **değer olarak** taşır. Çekirdeğin türetilmiş tablolarına sert yabancı anahtar kısıtı konmaz. Kaydın varlığı, çekirdekten okunarak doğrulanır.

## 2. Kapı 1 · Okuma

Modül her zaman **kullanıcının kimliğiyle** okur. Çekirdek, görünürlük kuralını uygular: kişisel veri, para ve proje ekibi.

Başvuru modelinde dış okuma kapısı:

```
oku(d, kim, veri, hedef=None, **parametre)     # model/irp/gorunum_v7.py
```

| `veri` | `hedef` | Parametre | Ne döner |
|---|---|---|---|
| `PROJE`, `ETAP` | kimlik | | Kayıt |
| `PROJE_DURUM`, `ETAP_DURUM` | kimlik | | Gösterge; `YETKILI` değilse parasal alanlar çıkarılır |
| `PLAN` | proje | | Onaylı plan sürümleri ve karşılaştırma (B0, B1) |
| `GANTT` | proje | `bas`, `bit` | Etaplar, işler, görevler: plan ve gerçekleşen aralık, durum, sapma |
| `PLAN_CAKISMALARI` | kaynak (kişi ya da tezgâh) | `bas`, `bit` | Planlanan aralıkları kesişen iş ve görev çiftleri |
| `IS`, `GOREV` | kimlik ya da kişi | | Tek kayıt ya da kişinin görebildiği kayıtları |
| `NESNE` | nesne kimliği | | Nesnenin ana gövdesi: tür, ad, proje, bağlar, aşama, aşama geçmişi, sorumlu |
| `SURUMLER`, `GECERLI_SURUM` | nesne | `t` (isteğe bağlı) | Sürümler; geçerli sürüm |
| `UYGUNLUK` | kişi | `bas`, `bit` | Kişi müsait mi; değilse nedeni (izin nedeni yetkisize "müsait değil" görünür) |
| `KIM_NEREDE`, `SAAT_NEREYE_GITTI` | | `bas`, `bit` | Personel panoları |
| `PERFORMANS`, `BIRIM_PERFORMANS` | kişi ya da birim | `bas`, `bit` | Adil Performans |
| `GUN` | kişi | `gun` | Gün özeti ve onay durumu |
| `IZIN`, `FAZLA_MESAI` | kişi | | Kayıtlar |
| `MAAS`, `SAAT_MALIYETI` | kişi (`SAAT_MALIYETI`'nde tezgâh da) | `ay` ya da `gun` | Yalnızca `YETKILI` |
| `NOT`, `DOSYA` | kimlik | | Kayıt |
| `BILDIRIMLER` | kişi | | Bildirim kutusu: çekirdeğin ve modüllerin bildirimleri |
| `HAM_OLAY` | kişi | | Ham olaylar: kişi kendi olaylarını, `YETKILI` hepsini görür |

**Sürüm 10.2'de eklenen okumalar** (T11 › 7). Hepsi okuyanın kimliğiyle ve görünürlük kurallarıyla çalışır:

| `veri` | Parametre | Dönen | Kim görür |
|---|---|---|---|
| `KISILER` | `birim` | kimlik, ad, birim, yaka, roller, aktif, yetkinlikler | Herkes |
| `BIRIMLER` | | Birim ağacı, yöneticiler, takvim özeti | Herkes |
| `TEZGAHLAR` | `birim` | kod, ad, birim, aktif, vardiyalar | Herkes |
| `TAKVIM` | `tur` (`KISI` \| `BIRIM` \| `TEZGAH`), `kimlik`, `bas`, `bit` | Çalışma ve kapalı aralıklar, nedeniyle | Herkes; kişinin izni yetkisize `MUSAIT_DEGIL` |
| `ETAPLAR` | `proje` | Etaplar | Projeyi gören |
| `NESNELER` | `proje`, `tur`, `kod` | Nesnelerin ana gövdesi | Projeyi gören |
| `TOP_KIMDE` | `nesne` | Aşama, sorumlu, ne zamandan beri | Nesneyi gören |
| `KAPASITE` | `kisi`, `bas`, `bit` | Saat | `UYGUNLUK` ile aynı |
| `TEZGAH_UYGUNLUK`, `TEZGAH_GOSTERGESI` | `tezgah`, `bas`, `bit` | Uygunluk ve nedeni; kullanılabilir saat (onaylı ek mesai dahil), gerçekleşen, duruş | Herkes |
| `TEZGAH_UCRETI` | `tezgah`, `gun` | Tezgâhın saat ücreti | `YETKILI`, `MALIYET` |
| `ISCILIK_MALIYETI` | `proje`, `bas`, `bit` | İşçilik ve tezgâh tutarı | `YETKILI` |
| `LISTE` | `kisi` | Kişinin iş listesi ve `surum`'u (`IS.ATADIM` için) | Kişi, üstleri, `YETKILI` |
| `KAYNAK_YUKU` | `tur` (`TEZGAH` \| `KISI`), `kimlik`, `bas`, `bit` | Bütün projelerin plan aralıkları | Herkes; görünmeyen proje `ERISIM_DISI`, görünmeyen kişi işi `MESGUL` diye ayrıntısız |

- **Tanımsız okuma:** Böyle bir `veri` yoksa `TANIMSIZ_VERI` döner, görünürlük hatası değil.
- **Biçimin ayrıntısı:** Parametreler ve dönen JSON `cekirdek_simulatoru/KULLANIM.md`'dedir.

## 3. Kapı 2 · Olay (çekirdekte bir şey yapmak)

Modül çekirdekte bir şey yapacaksa (nesne açmak, aşama geçirmek, iş tanımlamak, plan yazmak…) bunu **kullanıcının yaptığı bir olay** olarak, ekranların kullandığı yoldan gönderir:

```
modul_yaz(d, kim, olay)   # = olay_ekle(olay, oturum=kim); olay.kim = kim olmalı; AKTARIM yasak
```

- **Künye tam olmalı** (`01_cekirdek.md` › 3).
  - Modülün istemcisi bir cihazdır. Olay kimliğini kişi, gün, günlük sıra ve **modüle ayrılan cihaz harfiyle** üretir (`MODUL.TANIMLADIM.cihaz_harfi`; bu harf normal cihaza verilmez). Künyede `cihaz` = `MODUL-<kod>`. Günlük sırayı `HAM_OLAY` ile eşitler.
  - `giris_sekli` `LISTE`, `ELLE` ya da `QR` olur.
- **Bayatlık:** Yönetim kararında `neyin_ustunde`'ye hedefin **okunduğu andaki `surum`'u** yazılır. Modül, kullanıcının ekranda gördüğü kaydı okurken `surum`'u da alır ve olayda gönderir. Arada kayıt değiştiyse `RED(BAYAT)` döner; modül yeniden okur. Kararın dayandığı kaydın sonradan sıralanan bir olayı varsa `RED(BAYAT, SIRA)` döner: saat farkını yeniden ölç, ekranı yenile, yeni anla yeni olay gönder. **Birbirine dayanan olaylar artan anla gönderilir; aynı ana iki karar yazılmaz.**
- **Ret nedenleri:** `BICIM`, `YETKI`, `DURUM`, `BAYAT`, `CAKISMA`. Modül bunları kullanıcıya anlaşılır biçimde gösterir.
- **Tanıklık mı, yönetim kararı mı:** `sema/olay_semasi.json` › `eylem_semalari.<eylem>.sinif`. Yönetim kararı çevrimdışı gönderilmez.

**Modül 3 gibi bir modülün sık kullanacağı olaylar:** Girdi şemaları `sema/olay_semasi.json`'da.

| Olay | Ne için | Not |
|---|---|---|
| `NESNE.ACTIM` | Parçanın (ya da başka bir ortak nesnenin) çekirdekte kaydını açmak | Girdiler: `tur`, `ad`, `sorumlu`, isteğe bağlı `proje`, `baglar`, `kod`. Nesnenin projesi `proje`'dir; boşsa `baglar`'daki tek `PROJE` bağıdır; çelişirse `RED(BICIM)`. Yazabilen: türün `acabilenler`'i |
| `NESNE.ASAMA_GECIRDIM` | Aşama değiştirmek (ör. `SIPARISTE` → `GELDI`) | Girdiler: `hedef`, `yeni_asama`, `gerekce`. Yazabilen: geçişin `kimler`'i; nesnenin sorumlusu ve üstleri. UYELER'de projeyi gören sorumlu, projede yetkili olmasa da kendi nesnesinin aşamasını geçirir (karar 103) |
| `NESNE.GUNCELLEDIM` | Ad, bağ, sorumlu, kod | `degisenler` |
| `IS.TANIMLADIM` | İçeride yapılacak işlemleri (operasyonları) atölye işi olarak tanımlamak | Bir olayda çok satır (`isler`); havuz birimi, proje, etap, `parca_kodu` ya da `neyin_ustunde`'de NESNE bağı, tahmini süre, tezgâh, ön işler, isteğe bağlı plan tarihleri ve gereken `yetkinlik` (atamayı engellemez; karar 106) |
| `IS.DEGISTIRDIM`, `IS.IPTAL_ETTIM`, `IS.BAGLANTI_DUZELTTIM` | İş tanımını düzeltmek | Kurallar T3 › 2 ve 5 |
| `PLAN.TARIHLEDIM` | Hesaplanan planı yazmak | Bölüm 5 |
| `GOREV.ATADIM` | Masa başı birine görev vermek (ör. satın alma sorumlusuna) | Kendine görev verilemez |
| `NOT.YAZDIM` | Bir kayda (proje, iş, görev, ortak nesne) not, `@` ile birime yönlendirme | Kaydı gören yazar; yönlendirilen kişiye not görevi doğar |
| `NESNE.SURUM_EKLEDIM` / `ONAYLADIM` / `GERI_CEKTIM` | Belge sürümü | Bölüm 7 |

**Yetki:**
- **Hangi kural:** Hangi rolün hangi eylemi yazabileceği, kullanılan kurulumun yetki tablosundadır. Sibernetik'in varsayılanı `sema/olay_semasi.json` › `varsayilan_yetki_tablosu`'nda ve T3 › 4, T8 › 14, T9 › 13, T10 › 4'te.
- **Proje ekibi (UYELER ayarı):** Projeye bağlı yönetim kararını yazan projede yetkili olmalıdır. Projede yetkili olanlar: proje sorumlusu, projede etabı olan birimin yöneticisi ya da bunların üstleri, genel yönetim. İş verilen kişinin birimi de projede olmalıdır (T9 › 6.2).

## 4. Kapı 3 · Nesne uzantısı (modülün kendi ayrıntısı)

Şirketin ortak nesneleri çekirdekte bir **ana gövdeye** sahiptir. Modülü ilgilendiren ayrıntı **modülün kendi tablosundadır** ve nesnenin çekirdekteki kimliğini taşır (karar 72).

```
çekirdek: nesneler      (kimlik, tur, ad, kod, proje, baglar, asama, asama_gecmisi, sorumlu, olusturan…)
modül:    m3_satin_alma (siparis_no, nesne_kimligi → çekirdek, tedarikci, birim_fiyat, miktar, termin, durum…)
modül:    m3_fason      (fason_no, nesne_kimligi → çekirdek, tedarikci, operasyon, gidis, donus…)
```

- **Bir nesnenin birden çok modülde boyutu olabilir.** Örnek: aynı parçanın satın alma, kalite ve montaj kayıtları.
- **Nesne türü veridir:** `NESNE_TURU.TANIMLADIM` (`YETKILI`). Alanları:
  - `kod`, `ad`
  - `asamalar`: sıralı, son aşamalar işaretli
  - `baslangic_asamasi`
  - `gecisler`: `[{den, e, kimler}]`
  - `baglanabilir_turler`
  - `acabilenler`
  - `surum_onaylayanlar`
- **Sibernetik'in örnek türü `PARCA`** (T11 › 3):
  - Aşamalar sırayla: `SIPARIS_VERILMELI`, `SIPARISTE`, `FASONDA`, `GELDI`, `ISLEMDE`, `KALITE_ONAYLI`, `MONTAJA_HAZIR`, `MONTAJDA` (son). Hangi aşamadan hangisine geçilebildiği türün geçiş tablosundadır.
  - **Kısa yollar:**
    - "stokta": `SIPARIS_VERILMELI` → `MONTAJA_HAZIR`
    - "içeride yap": `SIPARIS_VERILMELI` → `ISLEMDE`
  - **Fason:**
    - parçanın tamamı: `SIPARIS_VERILMELI` → `FASONDA` → `GELDI`
    - tek bir operasyon: `ISLEMDE` ↔ `FASONDA`
  - **Geçişler:** Planlama ve satın alma (`BEYAZ_YAKA`, `YONETICI`) ilerletir; imalat liderleri `ISLEMDE`'den ilerletir.

  Modül başka bir aşama dizisine ihtiyaç duyarsa **türü değiştirmeyi önerir**; kendi tablosunda paralel bir aşama tutmaz.
- **Kapılar:**
  - Geçiş türde tanımlı olmalı.
  - Bağ, türün bağlanabilir türlerinden olmalı.
  - Son aşamadaki nesne geçirilemez.
  - Aynı tür, ad ve proje tekrarlanamaz.
  - Bir nesne kodu bir kez kullanılır.
- **"Top kimde":** Her nesnenin aşaması, sorumlusu ve o aşamada ne zamandan beri durduğu (`top_kimde`).
- **İş ve görev bir nesneye bağlanabilir** (`neyin_ustunde`'de `{tur: NESNE, kimlik}`). Eski `parca_kodu` metni, kodu o metin olan `PARCA` nesnesiyle eşlenir.

## 5. Kapı 4 · Plan sonucu

**Planı hesaplamak modülün işidir;** sonucu çekirdekte tutulur (karar 64, 95).

```
PLAN.TARIHLEDIM  girdiler:
  hedefler: [{tur: IS | GOREV, kimlik, planlanan_baslangic, planlanan_bitis}]   # en az 1
  kaynak:   "Modül 3 planlayıcı"   (isteğe bağlı metin)
  gerekce:  (isteğe bağlı)
```

- **Kapılar:**
  - Toplu olay bütün olarak kabul ya da reddedilir; biri uymazsa hiçbiri yazılmaz.
  - Hedef `BITTI` ya da `IPTAL` olamaz.
  - Başlangıç bitişten önce olmalı.
- **Yetki:** Sibernetik'te `YONETICI`, `EKIP_LIDERI`, `YETKILI`. UYELER ayarında yazan, her hedefin projesinde yetkili olmalıdır.
- **Planlamanın girdileri:**
  - kişi uygunluğu (`UYGUNLUK`) ve kapasite
  - tezgâh uygunluğu, göstergesi ve kaynak yükü (`TEZGAH_UYGUNLUK`, `TEZGAH_GOSTERGESI`, `KAYNAK_YUKU`; bölüm 2)
  - işlerin tahmini süreleri, ön işleri, tezgâhları
  - etap tarihleri ve onaylı plan sürümü (`PLAN`)
- **Planlamanın çıktıları:** `GANTT` ve `PLAN_CAKISMALARI` aynı plandan okunur. Çakışma yalnızca uyarıdır; uç uca değen aralık çakışma sayılmaz. `GANTT` satırında `tezgah`, `kisi`, `gecikme_takvim_dk`, `gecikme_mesai_dk` vardır. Görünmeyen projenin tarafı `ERISIM_DISI` olarak ayrıntısız döner.
- **Onaylı plan sürümü** (B0, B1; `PLAN.ONAYLADIM`) etap düzeyindedir, proje sorumlusu onaylar (karar 65, 91). Plan tarihleri bundan ayrıdır.

## 6. Kapı 5 · Bildirim kapısı

Modülün kendi kuralı tetiklendiğinde (sipariş gecikti, fason geç kaldı, teslim günü yaklaşıyor…) haber vermenin yolu budur. **Olay değildir;** olay günlüğüne girmez (karar 97). Şema: `sema/modul_bildirimi_semasi.json`.

```
modul_bildirimi_birak(servis_kimligi, modul, kural, kayit, alicilar, metin, onem, an)
modul_bildirimi_kaldir(servis_kimligi, modul, kural, kayit, an)

kayit:     {tur: PROJE | IS | GOREV | NESNE, kimlik, modul_kaydi?}   # modul_kaydi: modülün kendi kaydının metni
alicilar:  [{tur, kimlik}], tur ∈ KISI | BIRIM_YONETICILERI | ROL | PROJEDE_YETKILILER | NESNE_SORUMLUSU
onem:      BILGI | UYARI
an:        geçmiş olabilir (modülün kaydının anı), gelecek olamaz
```

- **Modül tanımı:** Önce `YETKILI`, modülü bir olayla tanımlar: `MODUL.TANIMLADIM` (`kod`, ör. `M3`; `ad`; `servis_kimligi`; `aktif`; isteğe bağlı `cihaz_harfi`, tekil ve değişmez). Kapıya yalnızca o servis kimliği, **yalnızca kendi modül koduyla** bırakabilir.
- **Alıcılar:** Bırakma anında kişilere çevrilir. Kaydın projesini göremeyen, ayrılmış ya da istihdam dışı kişi listeden çıkar. Kimse kalmazsa bildirim bırakılmaz. Kapının cevabı süzülenleri nedeniyle verir: `suzulenler: [{kisi, neden}]`; neden `PROJEYI_GOREMEZ`, `AYRILDI` ya da `ISTIHDAM_DISI`.
- **Tekillik:** Anahtar `<modul>/<kural>/<kayit>/<alici>`.
  - Aynı anahtarla tekrar bırakılırsa metin güncellenir, görülme korunur.
  - `kaldir` bildirimi geçersiz kılar. Kaldırılmış anahtar yeniden bırakılırsa bildirim geri gelir.
- **Kişi tarafı:** Kişi bildirimi açınca cihaz `BILDIRIM.GORDUM` olayını yazar; bu bir insan olayıdır. Çekirdeğin ve modüllerin bildirimleri aynı kutuda görünür (`BILDIRIMLER`).
- **Kalıcılık:** Modül bildirimleri çekirdeğin yeniden hesabında silinmez.

## 7. Belge sürümü (olay kapısının kullanımı)

Belgeyi (teknik resim, ürün ağacı, şema) tanımlamak modülün işidir; sürüm mekanizması çekirdekte, her nesne türü için aynıdır (karar 96, 99).

- `NESNE.SURUM_EKLEDIM` (`hedef`, `dosyalar` (en az bir), `surum_adi`, `aciklama`): taslak sürüm. Numarayı bulut verir.
  - Yazabilen: nesnenin sorumlusu (projeyi görüyorsa, UYELER'de de), üstleri, `YETKILI`.
- `NESNE.SURUM_ONAYLADIM` (`hedef`, `surum_no`): türün `surum_onaylayanlar`'ı. Boşsa sorumlunun üstleri onaylar. Ekleyen kendi sürümünü onaylayamaz.
- `NESNE.SURUM_GERI_CEKTIM` (`hedef`, `surum_no`, `gerekce`).
- **Okuma:** `GECERLI_SURUM` = en büyük numaralı, onaylı, geri çekilmemiş sürüm. Taslağı yalnızca ekleyen, sorumlu ve üstleri, onaylayabilecekler görür.
- **Bildirim:** Geçerli sürüm değişince R43 şu açık iş ve görevlerin kişilerine gider: nesneye bağlı olanlar ve nesneyle bağ ilişkisi olan nesnelere (tek basamak, iki yön) bağlı olanlar. Kişi başına bir bildirim.

Modül 3'ün "geçerli revizyonla mı çalışılıyor?" sorusu `GECERLI_SURUM` ile cevaplanır.

## 8. Para

- **Modülün tutarları** (fiyat, fason bedeli, nakliye, stok değeri) modülün kendi tablosundadır. Muhasebeye kendi yolundan gider (M8, VEGA).
- **Gerçek işçilik maliyeti ve kişinin saat maliyeti** çekirdekten okunur, yalnızca `YETKILI` görür. **Tezgâh saat ücretini** `MALIYET` rolü de okur (`TEZGAH_UCRETI`). Modül bunları yeniden hesaplamaz. Planlama için kendi **standart işçilik oranını** tutabilir; bu bir varsayımdır, maaşın kopyası değildir (karar 104).
- **Eksik veri sıfır değildir.** Çekirdek bilinmeyen ücreti `VERI_EKSIK` döndürür; modül de bilinmeyen tutarı sıfır saymaz.

## 9. Yapılmaz

- Çekirdeğin bir tablosuna doğrudan yazmak.
- Olayı kullanıcı olmadan, modülün kendi adına yazmak. Tek istisna bildirim kapısıdır; o da olay değildir.
- `AKTARIM` giriş şekliyle olay yazmak.
- Görünürlük süzgecini atlayıp ham tabloyu okumak.
- Çekirdeğin ana verisini (kişi, proje, birim, tezgâh, takvim) modülde ikinci kez tutmak ve oradan yönetmek.
- Çekirdeğin bir kuralını modülde tekrar etmek. Örnekler: kapasiteyi, uygunluğu, çalışılan saati, maaş payını hesaplamak.
- Ortak nesnenin aşamasını modül tablosunda ayrıca tutmak.
- Var olan bir çekirdek olayının alanını başka anlamda kullanmak.

## 10. İlkeler

- **Akıllı, kapsayıcı, kolay (karar 93):** Şartnamenin "onaylı", "doğrulanmış" maddeleri her adımı onaylatmak diye değil, haksız sonuç çıkmasın diye okunur. Kural arkada çalışır; ekranda kişiye en fazla bir soru sorulur; kimse bir şey yapmasa da sistem çalışır.
- **Mavi yaka için az düğme, tek yol.** Seçim lidere bırakılır.
- **Olayları zengin tut.** O anda kaydedilmeyen bilgi sonradan geri gelmez.
- **Sistem olay yazmaz.** Olay insanın yaptığıdır; modülün otomatik kararı olay değil, en fazla bir bildirimdir.

## 11. Çekirdeğin bilerek bıraktığı sınırlar

- Plan hesaplamak modülde; çekirdek sonucu tutar (karar 64, 95).
- İletişim (yazışma, e-posta, dönemsel raporlar) ayrı modülde (karar 87). Çekirdekte not ve bildirim var.
- İK özlük, bordro, izin bakiyesi İK modülünde (karar 87). Çekirdekte onaylı izin var.
- Belgenin içeriği modülde; sürüm mekanizması çekirdekte (karar 96).
- Bilinçli farklar listesi: T9 › 12 (F1–F14).
