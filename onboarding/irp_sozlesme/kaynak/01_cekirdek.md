# 01 · Çekirdek

*Sibernetik IRP çekirdeği · tasarım sürüm 10.2 (28 Ekim 2026) · Yapay zekâ için özet. Kesin hüküm her zaman `kaynak/tasarim/`'dadır.*

## 1. Nedir, ne değildir

Çekirdek, firmanın **insanını, işini, zamanını ve parasını** izleyen ortak motordur. Modüller onun üstüne kurulur; çekirdek modülleri tanımaz.

**Çekirdeğin işi:**
- **Kişiler ve organizasyon:** kişiler, birimler (departman), roller, hiyerarşi; işe giriş ve ayrılış.
- **Proje:** proje; etap (bir departmanın projedeki iş paketi); onaylı plan sürümleri (B0, B1…); iş ve görevin planlanan tarihleri.
- **İş ve görev:**
  - **İş** (atölye, mavi yaka): tanım, atama, sıra, başla, mola, duruş, tamamla, onay, ret, devir, iptal.
  - **Görev** (masa başı, beyaz yaka): atama, kabul, teslim, onay, ret, revizyon, değişiklik.
- **Zaman:** çalışma aralıkları, takvim (firma ve departman), izin, fazla mesai, tezgâh takvimi, bakım ve duruş, gün onayı.
- **Para:** saat maliyeti, maaşın projelere dağılımı, işçilik maliyeti, ay kapanışı.
- **Değerlendirme:** sorumluluk (hata ve gecikme payları), Adil Performans.
- **Erişim ve haber:** yetki, görünürlük (kişisel veri, proje ekibi), bildirim.
- **Ortak nesne katmanı:** Şirketin her nesnesinin (parça, belge…) kimliği, türü, aşaması, sorumlusu, bağları, sürümleri.

**Çekirdeğin işi değil:**
- **Modüllerin kendi işi:** teklif, satın alma, stok, tedarikçi, fason, kalite, servis, muhasebe ve VEGA, İK özlük ve bordro, iletişim ve raporlama.
- **Plan hesaplamak** (hangi iş hangi gün hangi tezgâhta). Çekirdek yalnızca planın **sonucunu** tutar (karar 64, 95).
- **Belgenin içeriği.** Çekirdek yalnızca sürüm mekanizmasını verir (karar 96).
- **Ekranlar.** Ekranlar çekirdeği kullanır.

## 2. Mimari

```
Cihaz (telefon, PC, modülün istemcisi)
  olayı üretir, kendi günlüğüne yazar, kuyruktan gönderir
        │
        ▼
olay_ekle  ── kapı: biçim → kimlik → yetki → bayatlık → durum ──► BASARILI | RED(neden)
        │
        ▼
olaylar  (yalnızca ekleme; güncelleme ve silme yasak)
        │
        ▼
olay_isle (dağıtıcı): etkilenen nesneleri bulur → kurallarla yeniden hesaplar
                      → değişen nesnenin bağımlılarını da hesaplar → değişiklik durunca biter
        │
        ▼
son hal tabloları (türetilmiş): kişi durumu, aralıklar, işler, görevler, etaplar, nesneler, bildirimler…
        │
        ▼
görünümler (gorebilir_mi süzgecinden) → ekranlar ve modüller
```

**Doğruluğun kaynakları:** Yalnızca üç kayıt.
- `olaylar`: yalnızca eklenir.
- `hassas_ekler`: maaş ve ücret tutarları; tutar olayın içinde durmaz.
- `ay_kapanislari`: kapanmış ayların donmuş tutarları.

Geri kalan her tablo bunlardan türetilir, silinip yeniden kurulabilir. **Tek istisna:** `modul_bildirimleri`. Modüllerin bildirim kapısına bıraktığı kalıcı kayıttır; hesabın kaynağı değildir ve yeniden kurmada silinmez.

**Son hal + yeni olay = güncel hal:**
- Bir nesnenin hali, etkin olaylarının `(oldugu_an, olay_kimligi)` sırasıyla uygulanmasıdır: `hal_n = gecis(hal_{n-1}, olay_n)`.
- Yeni olay sıranın sonuna geliyorsa son halin üstüne uygulanır.
- Araya geliyorsa (geç gelen, çevrimdışı) o nesne kendi olaylarından baştan kurulur.
- Bu yüzden sırasız ya da iki kez gelen olay doğru sonuç verir.

## 3. Olayın künyesi (tablo `olaylar`)

| Alan | Tip | Kim yazar | Anlam |
|---|---|---|---|
| `olay_kimligi` | text | Cihaz | Birincil anahtar. Biçim `^K\d{3}-\d{10}-[A-Z]$`: `{kişi}-{YYAAGG}{günlük sıra 4 hane}-{cihaz harfi}`, ör. `K017-2610220014-T` |
| `eylem_kodu` | text | Cihaz | Ne yapıldı. 90 eylem; şemaları `sema/olay_semasi.json` › `eylem_semalari` |
| `eylem_versiyonu` | int | Cihaz | Varsayılan 1; eylemin girdi şeması değişirse artar |
| `kim` | text | Cihaz | Girişteki kullanıcı; oturumla aynı olmalı |
| `adina` | text | Cihaz | Lider çalışan adına yazdıysa çalışan |
| `oldugu_an` | timestamptz | Cihaz | Ne zaman oldu (cihaz saati, bulutla farkı düzeltilmiş). Hesaplar bu sırayla |
| `saat_dilimi` | text | Cihaz | `+03:00` |
| `bildigi_son_hal_ani` | timestamptz | Cihaz | Cihazın son eşitlendiği an |
| `bulut_ulasma_ani` | timestamptz | **Veritabanı** | Sistem ne zaman öğrendi. Cihazın gönderdiği değer silinir |
| `pc_ulasma_ani` | timestamptz | Atölye PC'si | MVP'de boş |
| `neyin_ustunde` | jsonb | Cihaz | `[{tur, kimlik, surum}]`: hedefler. `surum`, kullanıcının gördüğü halin SHA-256 özeti |
| `girdiler` | jsonb | Cihaz | Eyleme özgü alanlar |
| `kanit` | jsonb | Cihaz | `[{dosya_kimligi, parmak_izi}]` |
| `giris_sekli` | text | Cihaz | `LISTE`, `ELLE`, `QR`, `AKTARIM` (yalnızca servis hesabı) |
| `cihaz`, `uygulama_surumu` | text | Cihaz | Kayıtlı cihaz kodu (modülün istemcisinde `MODUL-<kod>`), uygulama sürümü |
| `duzelttigi_olay` | text | Cihaz | Yalnızca `KAYIT.GECERSIZ_SAYDIM`'da |
| `yol` | text | Cihaz | `DISARIDA` ya da `ATOLYE`; MVP'de `DISARIDA` |

Gerçek örnekler: `cekirdek_simulatoru/ornekler/*.girdi.json` içindeki `tur: olay` adımlarının `args[0]`'ı. Örnek: Y100'deki `K009-2610210001-M`, bir `IS.ATADIM`.

## 4. İki tür olay

| | Tanıklık | Yönetim kararı |
|---|---|---|
| Ne | Olan bir şeyin kaydı: mesai giriş ve çıkış, başla, mola, duruş, tamamla, görevi kabul ve teslim, not, bildirimi gördüm | Birinin başkası için verdiği karar: atama, sıra, devir, onay, ret, iptal, görev verme, etap, plan, nesne açma ve aşama geçirme, ayar, ana veri |
| Çevrimdışı | Yazılır, kuyruğa girer | Yazılmaz; yalnızca çevrimiçi ve tazeyken |
| Durum uymazsa | Kabul edilir, şüpheli işaretlenir | `RED(DURUM)` ya da `RED(BAYAT)` |
| Yetki uymazsa | `RED(YETKI)` | `RED(YETKI)` |
| Yetki hangi ana göre | Olayın anındaki rol ve atama | Şimdiki |

```
olay_ekle(e, oturum) → BASARILI | RED(neden)
  biçim (kimlik deseni, eylem şeması, zorunlu girdiler)   → RED(BICIM)
  e.kim = oturum; AKTARIM yalnızca servis                → RED(YETKI)
  yetkili_mi(e.kim, e, an)                               → RED(YETKI)
  aynı kimlik var: içerik aynı → BASARILI (etkisiz); farklı → RED(CAKISMA)
  yönetim kararıysa:
    neyin_ustunde'deki her surum güncel mi?              → RED(BAYAT, güncel hal)
    dayandığı kaydın kabul edilmiş bir olayı bu karardan
      sonra mı sıralanıyor? (AKTARIM muaf)               → RED(BAYAT, SIRA)
    durum kapısı (T3, T8–T10 tabloları)                  → RED(DURUM, neden)
  bulut_ulasma_ani ← bulutun saati; olaylar'a ekle; olay_isle(e)
```

## 5. Nesneler ve kurallar

- **Nesne:** Bir şeyin şu anki hali. İş, görev, bir kişinin bir günü (aralıklar), kişi durumu, etap, proje, ortak nesne.
- **Ortak sütunlar:** `doguran_olay`, `son_olay`, `kural_versiyonu`, `surum` (iş alanlarının kanonik JSON'unun SHA-256'sı; sayaç değil).
- **Doğumlar:** Nesneler olaylardan doğar.
  - `IS.TANIMLADIM` → işler; kimlik tek satırda olayın kendisi, çok satırda `<olay>/n`
  - `GOREV.ATADIM` → görevler `<olay>/n`
  - onaylı görevin teslimi → onay görevi
  - revizyonlu ret → revizyon görevi
  - etiketli not → not görevleri
  - `NESNE.ACTIM` → nesne

  Kaynağı kalkan çocuk `IPTAL` olur.
- **Kural:** "Şu halde şu olay gelirse yeni hal budur" tablosu (T3). Örnekler:
  - İş: `SIRADA` + `IS.BASLADIM` → `CALISILIYOR`
  - İş: `CALISILIYOR` + `IS.TAMAMLADIM` (onaysız) → `BITTI`
- **Yan ürünler:** Kural yeni hali yazarken şunları da üretir: bildirim (R01–R43), aralık, şüpheli, `sonuclar` ("neden?" kaydı: doğuran olay, kural, önceki → yeni).
- **Zincir:** Değişen nesnenin bağımlıları da yeniden hesaplanır. Örnekler:
  - Bir iş bitince onu ön iş olarak bekleyen işler ve işin kişisinin günü.
  - Bir görev bitince onu bekleyenler ve onay ya da revizyon görevleri.

  Değişiklik durunca biter (en çok 50 tur; aşılırsa hata).

**Durum makineleri (T3):**

| Nesne | Durumlar |
|---|---|
| Kişi (mavi yaka) | `MESAI_DISI`, `CALISMIYOR`, `CALISIYOR`, `MOLADA`, `ARIZADA` (ekranda "Duruş"), `SABIT_MOLADA`, `DEVAM_BEKLIYOR`, `ON_IS_BEKLIYOR`, `ONAY_BEKLIYOR` |
| İş | `HAVUZDA` → `SIRADA` → `CALISILIYOR` ⇄ `YARIM` → `ONAY_BEKLIYOR` → `BITTI` ya da `REDDEDILDI`; `ON_IS_BEKLIYOR` (ön iş bitmemiş); her yerden `IPTAL` |
| Görev | `ATANDI` → `ACIK` → `ONAY_BEKLIYOR` → `BITTI` ya da `REDDEDILDI` ya da `REVIZYONDA`; `ON_IS_BEKLIYOR`; `IPTAL` |
| Ortak nesne | Türün tanımındaki aşamalar (veri); son aşama kapalıdır |

## 6. Zaman ve para (kısaca)

- **Kişinin günü:** Mavi yakanın düğme olayları ve takvimden kurulan aralıklar.
  - Kovalar: `CALISMA`, `MOLA`, `SABIT_MOLA`, `BEKLEME_ARIZA`, `BEKLEME_ON_IS`, `BEKLEME_ONAY`, `TANIMSIZ`, `IZIN`, `TEZGAH`…
  - Hiçbir yerde "süre" alanı yazılmaz; süre aralıklardan çıkar.
- **Beyaz yaka:** Süre ölçülmez (karar 78). Görevin zaman değeri, kabul ile teslim arasındaki iş günlerine yayılır.
- **Saat maliyeti:** (aylık maaş + genel gider payı) ÷ ayar `maas_paydasi_saat` (Sibernetik 180).
  - Maaş yoksa sonuç `VERI_EKSIK` olur, sıfır sayılmaz.
  - Mavi yakada projeye giden maliyet: çalışma saati × saat maliyeti.
  - Beyaz yakada: görev payı × saat maliyeti.
  - Kişi tutarlarını ve gerçek işçiliği yalnızca `YETKILI` görür. Tezgâh saat ücretini `MALIYET` rolü de görür.
- **Ay kapanışı:** Kapanan ay donar. Sonradan gelen olayın farkı sonraki açık aya yazılır.

## 7. Yetki ve görünürlük

```
yetkili_mi(K, e, an):
  sabit güvence ihlali → hayır
    (kendi işini onaylayamaz, kendine görev veremez, maaş yalnız YETKILI, en az bir YETKILI kalır…)
  sabit ilişki izin veriyor → evet   (çalışan kendi düğmesi, görevin kişisi teslim, onaylayan onaylar…)
  ilişkideki kişinin üstüyse → evet  (hiyerarşi zinciri: birim ağacı; üst astının yapabildiğini yapar)
  yetki_kurallari(eylem) (veri; satır: eylem, kimler [roller ya da sözde roller], kapsam BIRIM | FIRMA) → evet
  UYELER ayarında projeye bağlı yönetim kararı: projede_yetkili(K, proje) değilse → hayır
    (istisna: projeyi gören nesne sorumlusu kendi nesnesinin aşamasını geçirir
     ve taslak sürüm ekler; karar 99, 103)
  → hayır
```

- **Roller:** `YETKILI`, `YONETICI`, `EKIP_LIDERI`, `CALISAN`, `BEYAZ_YAKA`, `IK`, `MALIYET` (tezgâh ücretini görür). Kişinin yetkinlik listesi rol değildir (karar 106).
- **Sözde roller:** `BIRIM_YONETICISI`, `BIRIM_BASI`, `BIRIM_UYESI`, `PROJE_SORUMLUSU`.
- **Proje ekibi** (ayar `proje_gorunurlugu`: `HERKES` | `UYELER`; Sibernetik `UYELER`), üç basamak:
  1. Projeyi açan, proje sorumlusunu atar.
  2. Departman etap açılarak dahil edilir (varsayılan CEO).
  3. Departman yöneticisi ekibine iş verir; iş verilen kişi dahil olur.

  Bütün projeleri yalnızca genel yönetim görür. Çalışan yalnızca iş verildiği projeleri görür.
- **`gorebilir_mi(K, veri, hedef)`:** Önce kişisel veri kuralı, sonra proje kapısı.
  - Kişisel veri kuralı: kişi kendi verisini görür; üstleri ve `YETKILI` da görür; para yalnızca `YETKILI`.

## 8. Cevap anahtarı

Tasarım, çalışan bir Python modeline çevrildi: 770 test, 213 senaryo dosyası (Modül 3'ün altısı dahil), 131 değişmez kural ("her durumda doğru olmalı"), beş simülasyon. Ürün de modüller de aynı girdiye aynı çıktıyı vermek zorundadır. Simülatörün bu pakette bir kopyası var: `cekirdek_simulatoru/`.

## 9. Nereye bakılır

| Konu | Belge (`kaynak/tasarim/`) |
|---|---|
| Kararlar (her kuralın nedeni) | `00_kararlar.md` (1–99) |
| Tablolar ve sütunlar | `02_veri_modeli.md` (T2) |
| Durum makineleri, yetki, ana veri kapıları | `03_durum_makineleri.md` (T3) |
| Kabul, dağıtıcı, kişinin günü, maliyet, performans | `04_algoritmalar.md` (T4) |
| Fonksiyon adları | `05_fonksiyonlar.md` (T5) |
| Görünürlük, takvim, fazla mesai, izin, tezgâh takvimi, gün sonu, plan sürümü, sorumluluk, **ortak nesne katmanı ve modül sözleşmesi (§12)** | `08_butunsellik_2.md` (T8) |
| Kimlik/kod, duruş ve gecikme, değişiklik işi, servis projesi, **proje ekibi (§6)**, departman takvimi, gün onayı, İK, roller, bilinçli farklar | `09_butunsellik_3.md` (T9) |
| **Plan tarihleri, belge sürümü, modül bildirimi kapısı** | `10_surum_10_1.md` (T10) |
| Bütün senaryolar ve beklenen sonuçları | `kaynak/senaryolar.md` |

Çelişkide sıra: kararlar > T10 > T9 > T8 > T1–T7.
