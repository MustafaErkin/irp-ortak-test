# SPEC · M1.1A Sipariş alma ve muhasebeye devir · Faz 1

*Modül kodu (geçici): `M11A` · Paket: `irp_sozlesme` 1.0 · çekirdek 10.2 · 29 Ekim 2026*

*Kaynaklar:*
- *A ekibi çıktısı `M1.1A_siparis_alma_muhasebeye_devir.md` (15 Ekim; `projeler/hamdike/cikti/`) ve kaynak akışı `yazilim_akislari/M1.1A_…`.*
- *IRP Karar Haritası: M1.1A kartı, kapılar, "bütçenin üç katmanı", modüller arası arayüzler.*
- *M1.0 çıktısı (kurallar 4–6) ve M1.0'ın SPEC'i. Yazılmış M1.1B modülü (`~/Downloads/m11b`) ve onun SPEC'i.*

*Bu belgedeki çekirdek davranışları paketteki simülatörde denenerek yazıldı. M1.0, M1.1A ve M1.1B aynı sistemde çalışır; aralarındaki sözleşme Ek D'dedir ve M1.0'ın SPEC'inde birebir aynıdır.*

---

## 0. Bu belgeyi okuyan Claude Code için

- **Yalnızca M1.1A'yı yaz.** M1.0, M1.1B ya da başka bir modülün kodunu yazma. M1.0'dan yalnızca Ek D'deki sözleşmeyle okursun; testlerde M1.0'ın yerine Ek D.5'teki örneği veren sahte bir sağlayıcı kullanırsın.
- **Önce sözleşmeyi oku:** Çekirdekle ilgili her işten önce `irp_sozlesme/BASLA.md`'yi ve oradaki okuma sırasını oku. `irp_sozlesme/` içindeki hiçbir dosyayı değiştirme.
- **Öncelik:** `irp_sozlesme/` kuralları bu belgeden önce gelir. Çelişki olursa sözleşmeye uy, çelişkiyi `istekler/` altına yaz ve modülün sahibine söyle.
- **Etrafından dolaşma:** Çekirdek bir şeyi vermiyorsa taklit etme, başka yoldan alma (BASLA › Kural 10). Bilinen eksikler bölüm 13'te.
- **Kök talimat:** Modülün köküne `CLAUDE.md` koy. İçine `irp_sozlesme/BENIOKU.md` › 2'deki dört satırı ve "Modülün tarifi `SPEC.md`'dedir" satırını yaz.
- **Ekler doğrulandı:**
  - Ek A'daki künye `kunye_denetle.py`'den 0 hata, 0 uyarıyla geçti. M1.0 ve M1.1B künyeleriyle kayıt denetiminde de 0 hata verdi.
  - Ek B'deki göçler G01–G09'dan geçti; PostgreSQL 17'de koştu, değişmezlik tetikleyicileri sınandı.
  - Ek D.10'daki zemin ve Ek C'deki ortak zemin betiği simülatörde koştu.

---

## 1. Ne ve neden

Teklif siparişe dönüşünce iki iş aynı anda başlar: muhasebeye devir (M1.1A) ve proje ekibine devir (M1.1B). M1.1A'nın işleri:
1. Kazanan teklifi tek tıkla siparişe dönüştürür.
2. Proje kodunu verir, projeyi çekirdekte açar.
3. Teklifin maliyetini başlangıç bütçesi, takvimini başlangıç planı olarak dondurur.
4. Ticari koşulları muhasebeye devreder.
5. Bütçe izlemesini açar. Bütçe kesin kabule kadar yaşar.

**Öncelikler (kullanıcının kararı):**
- **Öncelikli:** Tek tıkla siparişe dönüştürme ve bütçe izlemesi.
- **Basit:** Ticari devir ve muhasebeye devir; birer form ve bildirim.
- **Sonraki faz:** VEGA ile otomatik eşleşme.
- **Düşük:** Ödeme, teminat, fatura tarihi uyarıları.

**Başarı şöyle görünür:**
- Satış yöneticisi kazanılan teklifin üstünde "Siparişe dönüştür" der. PO'yu ve sözleşmeyi kaydeder, proje açılır: kod `2611001`.
- M1.1B aynı projeyi hemen devralabilir: proje çekirdekte tarihleri ve sorumlusuyla vardır, başlangıç planı M1.1A'dan okunabilir.
- PO gelmediyse proje yine açılır; "PO bekleniyor" işareti kalır.
- Eksik ticari bilgi devri durdurmaz. Muhasebe eksik listesini görür ve tamamlar, VEGA kart kodlarını yazar, devri tamamlar.
- Sözleşme tutarı ve başlangıç bütçesi hiç değişmez. Kapsam değişince güncel tutar ve güncel bütçe gerekçe ve belgeyle değişir.
- Proje ekranının üstünde dolum ile ilerleme yan yana durur. Dolum ilerlemeyi eşikten fazla geçerse satış yöneticisine ve CEO'ya uyarı gider.
- Kesin kabulde bütçe kilitlenir; fark kalem bazında kalır.

---

## 2. Kapsam

### 2.1 Faz 1'de var

1. **Siparişe dönüştür penceresi:** M1.0'ın kazanılan sürümünden açılır; önizleme ve dönüştürme.
   - **Kapı:** Yalnızca gönderilmiş ve kazanılmış sürüm.
   - **Proje:** Kod verilir. Uzun sipariş adı kalıptan üretilir.
   - **Sipariş belgeleri:** PO no ve dosyası, imzalı sözleşme; "PO bekleniyor" işareti.
   - **Çekirdeğe:** Kullanıcının gözüyle `PROJE.ACTIM`. Ek iş ve serviste ana proje bağı.
2. **Teklifin donmuş kopyası:**
   - başlangıç bütçesi (dört kalem)
   - saat ücretleri
   - başlangıç planı (tarihlenmiş)
   - gereksinimler, kapsam, talep dosyaları
   - müşteriye giden PDF
3. **Ticari devir formu:** ödeme takvimi, teminat, faturalama biçimi, teslim şekli, yurt içi / ihracat, teşvik. Eksikler işaretli.
4. **Muhasebeye devret:**
   - Devir durumu: devredildi → muhasebe gördü → eksik var → tamam.
   - Eksik bilgi listesi: eksik → istendi → alındı.
   - `TICARI_DEVIR` bildirimi.
5. **Muhasebe gelen kutusu:**
   - devredilen projeler
   - eksikler
   - VEGA cari kart ve proje kart kodu (elle)
   - yaklaşan ödeme ve teminat tarihleri sütunu
6. **Tutar değişikliği formu:** yeni güncel tutar, güncel bütçe, gerekçe, belge; `TUTAR_DEGISTI` bildirimi.
7. **Bütçe şeridi ve paneli:**
   - dolum ile ilerleme yan yana
   - dört kalemin çubukları
   - sözleşme tutarı ile güncel tutar, değişiklik kayıtları
   - ekip liderlerine yalnızca yüzdeler
8. **Bütçe ölçümü ve `BUTCE_SAPMASI` uyarısı;** bildirimleri toparlayan kural işi.
9. **Bütçeler listesi** (CEO, satış, muhasebe): bütün projelerin şeridi.
10. **Kesin kabulde kapanış:** kalem bazında fark; kapanış sonrası düzeltme satırı.
11. **Ayarlar:** proje kodu ve sipariş adı kalıbı, sapma eşiği, yedek saat ücretleri.
12. **Sağlanan dört okuma** (Ek D.7):
    - `M11A.BASLANGIC_PLANI`
    - `M11A.TEKLIF_GIRDILERI`
    - `M11A.BUTCE_YUZDELERI`
    - `M11A.PROJE_BUTCESI`
13. **Ortak geliştirme ortamı betiği** (Ek D.11, Ek C).

### 2.2 Faz 1'de yok

- **Malzeme ve fason gerçekleşeni:** M3'ün proje bazında sipariş tutarları gelince eklenir (istek M11A-05). Faz 1'de "bilgi yok (M3)".
- **Genel gider gerçekleşeni:** Formül belirlenmedi (S-8). Faz 1'de "formül yok".
- **VEGA:** otomatik eşleşme ve fatura tutarıyla doğrulama.
- **Kalan maliyet tahmini ve sapma nedenleri:** M8'in işi.
- **Tarih uyarıları bildirim olarak:** Düşük öncelik. Faz 1'de gelen kutusunda sütun.
- **Kesin kabul tarihinin M7'den gelmesi:** Faz 1'de kapanışı muhasebe elle yapar.
- **Kapanış farkının M1.0'ın öğrenme katmanına gitmesi:** Döngü (Ek D.3, M11A-06). Fark `M11A.PROJE_BUTCESI`'nde durur.
- **Projeyi M1.1B'de kendiliğinden devre almak:** M1.1B devri elle başlatır (M11B-04). Başlangıç planını M11A'dan okuması M1.1B'nin sonraki işidir.
- **Takvimi M1.1A'da güncellemek:** Başlangıç planı donmuştur. Plan M1.1B'de B0 olarak hazırlanır.
- **Mevcut (teklifsiz) projeye bütçe açmak:** Projenin M1.1A kaydı yoksa ekran "Bu projenin M1.1A kaydı yok" der.

### 2.3 Yapılmayacaklar

Aşağıdakilerden biri olursa testler geçse bile iş yanlıştır:
- **Gönderilmemiş ya da kazanılmamış sürümü** siparişe dönüştürmek. Kapıdan gerekçeyle geçiş yoktur.
- **Sözleşme tutarını, başlangıç bütçesini ya da teklifin donmuş kopyasını değiştirmek** (tetikleyici korur).
- **Çekirdekten para okumak** (`ISCILIK_MALIYETI`, `PROJE_MALIYETI`, `SAAT_MALIYETI`), maaşı ya da saat maliyetini taklit etmek. Tahmini işçilik, çekirdeğin saatleri × tekliften donmuş saat ücretidir (karar 104).
- **Servis gözüyle para ya da saat okumak;** bütçe ölçümünü arka planda servis gözüyle yapmak. Ölçüm kullanıcının gözüyledir.
- **Tutarları** `SATIS`, `MUHASEBE`, `YETKILI` dışındaki birine göstermek; bildirim metnine ya da yüzde okumalarına koymak.
- **Görünürlük kuralı yazmak.** Projeye ait her şeyden önce kullanıcının gözüyle `PROJE` okunur. Muhasebe projeyi göremiyorsa modül ona projeyi açmaz (M11A-01).
- **Parçanın aşamasını, etabı ya da saati** modülün tablosunda ikinci kez tutmak. Ölçüm yalnızca yüzdeleri saklar.
- **Başka modülün şemasını okumak;** M1.0'ın verisine Ek D.4 dışında bir yoldan ulaşmak.
- **Ayrı bir bildirim kutusu kurmak.** Bildirimler çekirdeğin kutusundadır.

---

## 3. Kimlik

| Alan | Değer | Not |
|---|---|---|
| `kod` | `M11A` | **Geçici.** Kesin kodu Mustafa verir |
| `cihaz_harfi` | `Q` | **Geçici.** M3 `P`, M1.1B `R` aldı |
| `olay_yolu` | `ARKA_YUZ` | Tek olayı (`PROJE.ACTIM`) arka yüz gönderir |
| `servis_kimligi` | `SRV-M11A` | Bildirim ve servis okuması (`PROJE`) |
| Şema | `mod_m11a` | |
| `on_yuz.tur` | `AYRI_UYGULAMA` | Derin bağlantı: `PROJE` bağlamında `/proje/{kimlik}` |
| Rol | `MUHASEBE` (Muhasebe ve finans) | M1.1A'nın rolü |
| Kullandığı rol | `SATIS` | M1.0'ın rolü; M1.1A bu yüzden M1.0'a bağımlıdır (R09) |

---

## 4. Teknoloji ve klasör düzeni

### 4.1 Yığın

M1.0 ve M1.1B ile aynı:
- **Dil:** Python 3.15 (`uv venv --python 3.15`; `requires-python = ">=3.11"`).
- **Arka yüz:** FastAPI, Pydantic v2, psycopg 3, eksiz uvicorn. ORM yok; para `Decimal`.
- **İstemci:** M1.0'a giden istekler `httpx` ile.
- **Ön yüz:** React 18, TypeScript, Vite; UI kütüphanesi yok; görünüş Ek D.12.
- **Test:** pytest, vitest.

### 4.2 Klasör düzeni

```
<modül kökü>/
  irp_sozlesme/  CLAUDE.md  SPEC.md  kunye.json (Ek A)  pyproject.toml
  veritabani/            001_m11a.sql, 002_varsayilanlar.sql (Ek B)
  m11a/
    ayarlar.py  baglanti.py (Cekirdek.ac, TabloSayac)  vt.py
    saglayicilar.py      M1.0'a giden tek kapı (Ek D.4): M10Saglayici arayüzü, HTTP ve sahte uygulaması
    depo/
    alan/                donusturme, kod (proje kodu, sipariş adı), tarih, butce, olcum, eksik, devir,
                         tutar, kapanis, bildirim, kurallar, yetki, saglanan
    api/
    komutlar.py
  testler/  (sabitler/M10.KAZANAN_SURUM.json: Ek D.5)
  senaryolar/  istekler/  on_yuz/
  gelistirme/            docker-compose.yml, sema_ac.sql, ornek_ayarlar.sql, ortak_zemin.py (Ek C), BENIOKU.md
  TESLIM.md
```

**Saf fonksiyonlar** (`alan/kod.py`, `alan/tarih.py`, `alan/butce.py`, `alan/olcum.py`, `alan/eksik.py`) veritabanına ve çekirdeğe dokunmaz.

### 4.3 Ortam değişkenleri

| Değişken | Ne |
|---|---|
| `IRP_CEKIRDEK`, `IRP_TABAN`, `IRP_ANON`, `IRP_SERVIS` | Bağlantı katmanı; kodda okunmaz |
| `M11A_VERITABANI`, `M11A_TEST_VERITABANI` | PostgreSQL (docker: `localhost:54331`) |
| `M11A_KUNYE` | Varsayılan `kunye.json` |
| `M11A_GELISTIRME` | `1` ise geliştirme girişi |
| `M11A_KURAL_ARALIGI_DK` | Kural işinin aralığı; varsayılan 15; `0` kapatır |
| `M11A_SAGLAYICI_M10` | M1.0'ın API tabanı (`http://localhost:8010/api`). Boşsa M1.0 kapalı sayılır |
| `VITE_M10_ADRES`, `VITE_M11B_ADRES` | Ön yüzdeki geçiş bağlantıları (`http://localhost:5180`, `http://localhost:5173`) |

---

## 5. Sınır: ne nerede

| Kavram | Nerede | Nasıl |
|---|---|---|
| Teklif, müşteri, fiyat, maliyet kırılımı, takvim | M1.0 | `M10.KAZANAN_SURUM` (Ek D.5), kullanıcının anahtarıyla, yalnızca dönüştürmede |
| Teklifin donmuş kopyası, bütçe, ticari koşullar, devir | M1.1A | `mod_m11a` (bölüm 7) |
| Proje, kodu, sorumlusu, tarihleri | Çekirdek | `PROJE.ACTIM` ile açılır; `PROJE` ile okunur. M1.1A çekirdekteki projeyi değiştirmez (`PROJE.DEGISTIRDIM` yalnızca `YETKILI`'dir, denendi) |
| Projeye harcanan saat | Çekirdek | `PROJE_DURUM` › `etaplar[].harcanan_emek` ve `harcanan_emek`. Tutarlar `YETKILI` olmayana maskeli gelir (denendi); M1.1A tutarı kullanmaz |
| Etabın birimi | Çekirdek | `ETAPLAR {proje}` |
| Parçanın aşaması | Çekirdek | `NESNELER {proje}`; yalnızca `tur == 'PARCA'` sayılır |
| Başlangıç planı (etaplar, B0) | M1.1B | M1.1A tarihlenmiş teklif takvimini sağlar; etap yazmaz |
| Muhasebeye haber | Çekirdeğin bildirim kapısı | `TICARI_DEVIR`, `TUTAR_DEGISTI`, `BUTCE_SAPMASI` |

**Saat:** Modülün kayıtlarındaki anlar ve "bugün" `cekirdek.simdi()`'den alınır.

---

## 6. Roller, yetki ve görünürlük

**Projeye ait her uç** önce kullanıcının gözüyle `PROJE`'yi okur. `YETKI` gelirse 403 "Bu projeyi göremiyorsunuz" döner ve modülün o projeye ait hiçbir kaydı gösterilmez. Kişinin rolü `KISILER`'den, istek başına bir kez okunur.

| İş | Modülün kuralı |
|---|---|
| Siparişe dönüştürmek | `SATIS` ya da `YETKILI`. M1.0 da kendi kuralını uygular (Ek D.5). Çekirdek `PROJE.ACTIM`'ı `SATIS` (M1.0'ın yetki önerisi) ve `YETKILI` için kabul eder (denendi) |
| PO ve sözleşme kaydı, ticari devir formu | `SATIS`, `MUHASEBE`, `YETKILI` |
| Muhasebeye devretmek | `SATIS`, `YETKILI` |
| Devri almak, eksikleri yönetmek, VEGA kodları, devri tamamlamak | `MUHASEBE`, `YETKILI` |
| Tutar değişikliği | `SATIS`, `YETKILI` |
| Bütçeyi kapatmak, kapanış sonrası düzeltme | `MUHASEBE`, `YETKILI` |
| **Tutarları görmek** (bütçe, ticari koşullar, ödeme ve teminat tutarları, `M11A.PROJE_BUTCESI`) | `SATIS`, `MUHASEBE`, `YETKILI` |
| Yüzdeleri, proje özetini, başlangıç planını, kapsamı, müşteri PDF'ini görmek | Projeyi gören herkes ("ekip liderleri yalnızca yüzdeleri görür"; "müşteriye giden PDF'i herkes açabilir") |
| Muhasebe gelen kutusu | `MUHASEBE`, `YETKILI` |
| Bütçeler listesi | `SATIS`, `MUHASEBE`, `YETKILI` |
| Ayarlar | `YETKILI` |

### Görünürlük bulgusu (denendi; istek M11A-01, KRITIK)

Sibernetik'te proje görünürlüğü `UYELER`'dir. Bunun dört sonucu var:
- **Muhasebe (K060) açılan projeyi göremiyor.** Bildirim `suzulenler: [{kisi: K060, neden: PROJEYI_GOREMEZ}]` ile süzülüyor. Muhasebenin gelen kutusunda o proje görünmüyor.
- **Projeyi açan satış yöneticisi** sorumluyu başkası yaparsa projeyi kendisi göremiyor.
- **Satış yöneticisi muhasebeye görev atayamıyor** (`GOREV.ATADIM` → `YETKI`). Bu yüzden "görev vererek ekibe almak" yolu yok.
- **Projeyi görmenin tek yolu** yetkilinin çekirdeğin ekranından `PROJE.ERISIM_VERDIM` yazmasıdır.

Modülün davranışı:
1. **Sorumlu:** Dönüştürme penceresinde varsayılan sorumlu dönüştüren kişidir. Başkası seçilirse uyarı çıkar: "Projeyi açtıktan sonra siz göremeyebilirsiniz; ticari devir formunu siz dolduracaksanız sorumlu siz kalın, sonra M1.1B'den değiştirilir."
2. **Süzülen muhasebe:** `TICARI_DEVIR` bırakılınca cevaptaki `alicilar` ve `suzulenler` devir kaydına yazılır. Ekranda gösterilir: "Muhasebede bu projeyi gören kimse yok (K060: projeyi göremiyor). Yetkili, çekirdeğin Proje erişimi ekranından erişim vermeli."
3. **Kural işi:** Süzülen alıcı kaldıkça bildirimi yeniden bırakır. Erişim verilince bildirim ulaşır (tekillik metni günceller, denendi).

---

## 7. Kayıtlar (modülün tabloları)

SQL'in tamamı Ek B'de.

| Tablo | Ne tutar |
|---|---|
| `olay_sayaci` + `olay_sirasi()` | Olay kimliğinin kişi ve gün başına sırası |
| `sayaclar` + `sayac_ilerlet()` | Proje kodunun ve yıllık sipariş sırasının sayacı |
| `ayarlar`, `saat_ucretleri` | Kalıplar, eşik; teklifte işçiliği olmayan birimler için yedek saat ücreti |
| `projeler` | Projenin M1.1A kaydı: durum, teklif sürümü (tekil), müşteri, ana proje, sorumlu, satış yöneticisi, sipariş, teslim ve kesin kabul tarihleri, yıllık sıra, PO, sözleşme, VEGA kodları, para birimi, sözleşme ve güncel tutar, kurlar, donmuş teklif, PDF, açılış, bütçe durumu ve kapanış |
| `butce_satirlari` | Dört kalem: başlangıç (donmuş) ve güncel |
| `proje_saat_ucretleri` | Tekliften donmuş birim saat ücretleri |
| `baslangic_plani` | Tarihlenmiş teklif takvimi |
| `dosya_kayitlari` | PO, sözleşme, teminat mektubu, tutar değişikliği belgesi, fatura: ad, konum, parmak izi |
| `ticari_kosullar`, `odeme_satirlari`, `teminatlar` | Ticari devir formu |
| `devirler`, `eksik_bilgiler` | Muhasebeye devir ve eksik listesi |
| `tutar_degisiklikleri` | Eski ve yeni güncel tutar, eski ve yeni güncel bütçe, gerekçe, belge |
| `butce_olcumleri` | Ölçüm: yalnızca yüzdeler, kapsam, eşik, uyarı, ücreti bilinmeyen saat |
| `acik_bildirimler` | Çekirdekte açık duran bildirimlerimiz (kaldırmak için) |
| `kapanis_farklari`, `kapanis_sonrasi_duzeltmeler` | Kesin kabulde kalem bazında fark; sonra gelen fatura |

**Değişmezler:**
- Sözleşme tutarı, para birimi, teklif sürümü, donmuş teklif, kurlar ve PDF'in parmak izi değişmez (tetikleyici).
- Başlangıç bütçesi değişmez (tetikleyici). Güncel bütçe ve güncel tutar yalnızca tutar değişikliği formuyla değişir.
- Bir teklif sürümü bir kez dönüştürülür (`teklif_surumu` tekil).
- Bütçe `KAPALI` iken tutar değişikliği yapılmaz (modülün kuralı, 409).

**Kişisel veri ve para:**
- Donmuş teklifteki müşteri iletişim kişileri kişisel veridir ve beyanlıdır.
- Modül para tutar (`para: true`). Çekirdekten para okumaz.

---

## 8. Akışlar

### 8.1 Siparişe dönüştürmek

**Giriş:** M1.0'ın sürüm sayfasındaki "Siparişe dönüştür" `/donustur?surum=<kimlik>` açar (M1.0 › 8.12).

**Önizleme** (`GET /api/donustur/onizleme?surum=`):
1. Kullanıcı `SATIS` ya da `YETKILI` değilse 403.
2. Bu sürüm zaten dönüştürülmüşse (`projeler.teklif_surumu`) projenin kendisi döner ve pencere "Bu teklif 2611001 olarak açıldı" der.
3. `M10Saglayici.kazanan_surum(anahtar, surum)` çağrılır (Ek D.4). Hata eşlemesi D.4'teki tablodadır. Önemli olanlar:
   - 409 `KAPI` ise "Yalnızca gönderilmiş ve kazanılmış teklif siparişe dönüştürülür."
   - `SAGLAYICI_YOK` ise "Teklif modülüne (M1.0) ulaşılamıyor; dönüştürme şu an yapılamaz."
4. M1.1A kapıyı ayrıca denetler: `durum == GONDERILDI` ve `talep_durumu == KAZANILDI`.
5. Ekrana önerilen değerler gelir:
   - proje kodu ve sipariş adı
   - proje adı (teklifin konusu)
   - müşteri
   - sorumlu (dönüştüren)
   - sipariş tarihi (bugün)
   - teslim ve kesin kabul tarihleri (aşağıda)
   - bütçe kırılımı ve sözleşme tutarı
   - tarihlenmiş takvim
   - ek iş ve serviste ana proje

**Proje kodu** (saf fonksiyon `alan/kod.py`):
- **Kalıp:** `proje_kodu_deseni` (varsayılan `{YY}{AA}{SIRA3}`) ve `proje_kodu_sira_kapsami` (`YIL` ya da `AY`, varsayılan `YIL`).
- **Değerler:** `YY` ve `AA` sipariş tarihinden gelir. Sıra `sayac_ilerlet('PROJE_KODU', '2026')`'dan ya da `AY` kapsamında `'2026-11'`'den gelir.
- **Örnek:** 02.11.2026'daki ilk sipariş `2611001`.
- **Önizleme sayacı ilerletmez.** Sayacın o anki değerine bakar. Kod dönüştürmede verilir.
- **Elle kod:** Kullanıcı kodu elle de yazabilir (S-1: kod teklifte verilmiş olabilir). Elle kod `^[0-9A-Za-z-]{2,20}$`.
- **Kod değişmez:** Proje açıldıktan sonra kod değişmez (M1.1A `PROJE.KOD_DEGISTIRDIM` yazmaz).

**Sipariş adı** (yalnızca gösterim; saklanmaz, alanlarından kurulur):
- **Kalıp:** `siparis_adi_deseni`, varsayılan `{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}`.
- **Değerler:** `YILLIK_SIRA` siparişin yıllık sırasıdır (`sayac_ilerlet('SIPARIS', '2026')`). `PO` yoksa `PO-BEKLENIYOR` yazılır.
- **Örnek:** `2026-001-2611001___Autoliv-710 Projesi Burç Çakma Ekipmanı_PO1246789`.

**Tarihler** (saf fonksiyon `alan/tarih.py`, Ek D.2'nin kuralı):
- **Teslim** = sipariş tarihi + 7 × `teslim_suresi_hafta` − 1.
- **Kayma** = `teslim_suresi_hafta` − `takvim_teslim_hafta` (en az 0).
- **Kesin kabul** = takvimde `KESIN_KABUL` varsa sipariş tarihi + 7 × (`KESIN_KABUL`'ün başlangıcı + süresi + kayma) − 1; yoksa boş.
- **Başlangıç planı:** Her satır için başlangıç = sipariş + 7 × `baslangic_hafta`, bitiş = sipariş + 7 × (`baslangic_hafta` + `sure_hafta`) − 1. Kayma satırlara eklenmez; plan teklifteki gibidir, M1.1B B0'da düzenler.
- **Örnek:** Sipariş 02.11.2026, Ek D.5. Teslim 16.05.2027; kayma 3; kesin kabul 23.05.2027.

| Etap | Başlangıç | Bitiş |
|---|---|---|
| ACILIS | 02.11.2026 | 08.11.2026 |
| MEK_TASARIM | 09.11.2026 | 13.12.2026 |
| OTO_TASARIM | 09.11.2026 | 27.12.2026 |
| SATIN_ALMA | 30.11.2026 | 24.01.2027 |
| IMALAT | 21.12.2026 | 07.02.2027 |
| MEK_MONTAJ | 01.02.2027 | 07.03.2027 |
| ELK_YAZILIM | 08.02.2027 | 21.03.2027 |
| TEST_FAT | 15.03.2027 | 04.04.2027 |
| SEVK_KURULUM | 05.04.2027 | 25.04.2027 |
| KESIN_KABUL | 26.04.2027 | 02.05.2027 |

**Dönüştürme** (`POST /api/donustur`): `{surum, proje_kodu?, proje_adi, sorumlu, siparis_tarihi, teslim_tarihi, kesin_kabul_tarihi?, po_no?, po_dosyasi?, sozlesme_dosyasi?}`. Dosyalar `{ad, konum, parmak_izi?}` biçimindedir.

1. **Yetki ve kapı:** Kullanıcı `SATIS` ya da `YETKILI` değilse 403. `M10.KAZANAN_SURUM` **yeniden** okunur, önizleme eski olabilir. Kapı yeniden denetlenir.
2. **Ek iş ve servis:** Kaynak `EK_IS` ya da `SERVIS` ise `ana_proje` = `bagli_proje`. Kullanıcının gözüyle `PROJE` okunur; `YETKI` gelirse 403.
3. **Doğrulama:**
   - sorumlu `KISILER`'de aktif
   - teslim ≥ sipariş tarihi
   - kesin kabul verilmişse ≥ teslim
   - proje adı boş değil
4. **Kod:** Kod elle verilmediyse sayaçtan alınır. Modülün tablosunda varsa sıradaki alınır. Yıllık sıra ilerletilir.
5. **Niyet yazılır** (tek işlem, commit). `projeler` satırı `ACILIYOR` durumunda açılır:
   - `donmus_teklif` = cevabın PDF'siz hali; `pdf` = base64 çözülmüş baytlar
   - sözleşme ve güncel tutar = `fiyat`
   - `butce_satirlari`: başlangıç = güncel = `toplamlar.kalemler`
   - `proje_saat_ucretleri`: işçilik satırlarından
   - `baslangic_plani`
   - PO ve sözleşmenin `dosya_kayitlari`'ı
   - `ticari_kosullar`'ın boş satırı
   - `satis_yoneticisi` = dönüştüren
   - PDF'in parmak izi baytlardan yeniden hesaplanır; cevaptakiyle uyuşmazsa 502 `BEKLENMEYEN`
6. **Çekirdeğe:** Kullanıcının gözüyle `PROJE.ACTIM` gönderilir (Ek D.9): `{kimlik: kod, kod, ad, musteri, sorumlu, baslangic_tarihi, teslim_tarihi, kesin_kabul_tarihi?, ana_proje?}`.
7. **Cevap:**
   - **`BASARILI`:** Satır `ACIK` olur, `acilis_olayi` yazılır. Cevap: proje, sipariş adı, eksik listesi önizlemesi, M1.1B'ye geçiş (8.11).
   - **`REDDEDILDI / DURUM`:** Kod çekirdekte kullanılıyor (denendi). Satır ve çocukları silinir (tek işlem). 409 `KOD_KULLANILIYOR` ve sıradaki önerilen kod döner.
   - **`REDDEDILDI / YETKI`:** Silinir. 403 "Çekirdekte proje açma yetkiniz yok (`PROJE.ACTIM`)".
   - **Ana proje hatası** (ana projenin kendi ana projesi var): `DURUM` ile reddedilir (denendi). Silinir, 409 `ANA_PROJE`.
   - **`CekirdekHatasi('BAGLANTI')`:** Satır `ACILIYOR` kalır, 503 döner. Pencerede "Yeniden dene" görünür.
8. **"Yeniden dene"** (`POST /api/donustur/{proje}/yeniden-dene`): Kullanıcının gözüyle `PROJE` okunur.
   - Varsa ve `kod`, `musteri` uyuşuyorsa `ACIK` yapılır. `acilis_olayi` boş kalır; günlüğe "PROJE okumasıyla doğrulandı" yazılır.
   - `YETKI` ya da yok ise `PROJE.ACTIM` yeniden gönderilir.
   - `ACILIYOR` satır yalnızca açan kişiye, "Açılış tamamlanmadı" olarak görünür. Hiçbir listeye ve okumaya girmez.

**Çifte dönüştürme:** `teklif_surumu` tekildir. İkinci dönüştürme olay göndermeden 409 `ZATEN_DONUSTU` alır ve projeyi gösterir.

### 8.2 PO ve sözleşme

- **"PO bekleniyor":** `po_no` boşsa projede, gelen kutusunda ve `BUTCE_YUZDELERI`'nde bu işaret görünür. Kapıyı kapatmaz.
- **Sonradan girmek:** PO no ve dosyası, sözleşme dosyası `PUT /api/projeler/{p}/siparis` ile sonradan girilir (`SATIS`, `MUHASEBE`, `YETKILI`). Sipariş adı buna göre değişir. İlgili eksik satırı kendiliğinden `ALINDI` olur (8.3).
- **Adlandırma:** Müşterinin bize verdiği PO yazılımda **müşteri siparişi**dir. Tedarikçiye verdiğimiz **satın alma siparişi**dir (M3).

### 8.3 Ticari devir formu ve eksik bilgi

- **Yeri:** Proje kartında "Ticari" sekmesi. Yalnızca tutarları görenlere açılır.
- **Form:**
  - ödeme takvimi satırları: koşul (`SIPARIS`, `SEVK`, `ON_KABUL`, `KESIN_KABUL`, `TARIH`, `DIGER`), tarih (`TARIH`'te zorunlu), tutar, para birimi, açıklama
  - teminat gerekli mi (`VAR` / `YOK`); varsa teminat satırları: tür, tutar, para birimi, banka, bitiş tarihi, mektubun dosya kaydı
  - faturalama biçimi (`PESIN`, `KADEMELI`, `SEVKTE`, `ON_KABULDE`, `KESIN_KABULDE`, `HAKEDIS`) ve notu
  - teslim şekli (serbest metin; öneriler: Exwork, FCA, DAP, yerinde kurulum)
  - yurt içi / ihracat
  - teşvik (`VAR` / `YOK`); varsa belge no
  - notlar
- **Ödeme toplamı:** Ödeme satırlarının sözleşme para birimindeki toplamı güncel tutardan farklıysa uyarı çıkar: "Ödeme takvimi güncel tutarla tutmuyor". Durdurmaz.
- **Eşzamanlılık:** `ticari_kosullar.surum` ile, 409 `DEGISTI`.

**Otomatik eksik alanları** (saf fonksiyon `alan/eksik.py`; kod → koşul):

| Alan kodu | Eksik sayılır |
|---|---|
| `PO` | PO no boş |
| `SOZLESME` | Sözleşme dosyası yok |
| `ODEME_TAKVIMI` | Ödeme satırı yok |
| `FATURALAMA` | Faturalama biçimi boş |
| `TESLIM_SEKLI` | Teslim şekli boş |
| `IHRACAT` | Yurt içi / ihracat seçilmedi |
| `TESVIK` | Teşvik seçilmedi, ya da `VAR` ve belge no boş |
| `TEMINAT` | Teminat gerekli mi seçilmedi, ya da `VAR` ve teminat satırı yok |

- **Ekran:** Eksik alanlar her zaman işaretli görünür.
- **Satırlar ne zaman açılır:**
  - Devirden **önce** `eksik_bilgiler` satırı açılmaz.
  - Devirde her eksik alan için `EKSIK` satırı açılır.
  - Devirden sonra her kayıtta yeniden hesaplanır: dolan alanın satırı `ALINDI`, yeniden boşalanın satırı `EKSIK` olur, yoksa açılır.
- **Elle satır:** Muhasebe elle satır ekler (alanı boş; ör. "Teşvik satır numarası müşteriden istenecek").
- **Satırın durumu:**
  - `EKSIK` → `ISTENDI`: kimden (`MUSTERI`, `SATIS`, `DIGER`) zorunlu.
  - `ISTENDI` → `ALINDI`.
  - Otomatik satır `ALINDI`'ya yalnızca alan dolunca geçer. Elle satırı muhasebe kapatır.

### 8.4 Muhasebeye devir ve gelen kutusu

**"Muhasebeye devret"** (`SATIS`, `YETKILI`; projede bir kez):
1. `devirler` satırı `DEVREDILDI` olarak yazılır. Eksik satırları açılır (8.3).
2. `TICARI_DEVIR` bırakılır:
   - **kayıt:** `{tur: PROJE, kimlik, modul_kaydi: "ticari devir"}`
   - **alıcılar:** `[{tur: ROL, kimlik: MUHASEBE}]`
   - **metin:** `"<kod> <proje adı> · Ticari devir: <n> eksik"`
   - **önem:** `BILGI`
3. Cevaptaki `alicilar` ve `suzulenler` devir satırına yazılır. Süzülen varsa ekranda 6'daki uyarı çıkar.
4. **Bildirim başarısız olursa** devir geri alınmaz; `bildirim_birakildi` yanlış kalır, kural işi telafi eder.

**Devir durumu:**
- **Devri aldım:** `MUHASEBE` ya da `YETKILI` "Devri aldım" der. Açık eksik varsa durum `EKSIK_VAR`, yoksa `MUHASEBE_GORDU` olur; görme anı yazılır.
- **Sonrası:** Durum her değişiklikte bu ikisi arasında yeniden hesaplanır.
- **Devri tamamla:** Açık eksik yoksa ve VEGA cari kart ve proje kart kodu doluysa "Devri tamamla" `TAMAM` yapar. `TICARI_DEVIR` kaldırılır.
- **`TAMAM` geri alınmaz.** Sonradan çıkan eksik, ekranda eksik olarak görünür ama durum değişmez.

**VEGA kodları:**
- Muhasebe VEGA'da cari kartı ve proje kartını açar, kodları buraya yazar (serbest metin).
- **Öneri:** Aynı M1.0 müşterisinin (`m10_musteri`) önceki projesinde cari kodu varsa öneri olarak gelir.

**Muhasebe gelen kutusu** (`MUHASEBE`, `YETKILI`):
- **Satırlar:** Devri olan ve kullanıcının `PROJE` okumasıyla gördüğü projeler. Görmediği satır listelenmez.
- **Sütunlar:**
  - proje kodu, sipariş adı, müşteri, devir durumu, devir anı
  - "PO bekleniyor"
  - eksik sayısı ve listesi (açılır)
  - VEGA cari ve proje kodu (satırda düzenlenir)
  - **yaklaşan tarihler:** bugünden itibaren `yaklasan_tarih_gun` (varsayılan 30) gün içindeki ödeme satırları (koşulu `TARIH` olanlar) ve teminat bitişleri; en yakın üçü. Geçmiş tarih kırmızı ▲.
- **Sıra:** Önce `DEVREDILDI`, sonra `EKSIK_VAR`, sonra en yakın tarih.

### 8.5 Tutar değişikliği

- **Kim ve ne zaman:** `SATIS` ya da `YETKILI`; bütçe `ACIK` iken.
- **Form (bütçe panelinden):**
  - yeni güncel tutar (sözleşme para biriminde)
  - dört kalemin yeni güncel bütçesi (şimdiki değerlerle dolu gelir)
  - gerekçe (zorunlu)
  - belge (dosya kaydı, zorunlu)
- **Örnek:** Müşteri robotu kendisi verecek. Güncel tutar 56.000 → 50.000 €, `MALZEME` 32.500 → 26.500 €.
- **Yazılanlar:** `tutar_degisiklikleri` (eski ve yeni tutar, eski ve yeni bütçe JSON), `projeler.guncel_tutar` ve `butce_satirlari.guncel`. Tek işlem. Sözleşme tutarı ve başlangıç değişmez.
- **Bildirim:** `TUTAR_DEGISTI` bırakılır (`ROL MUHASEBE`, `BILGI`). Metin: `"<kod> <ad> · Güncel tutar ve bütçe değişti (değişiklik #<n>)"`. Tutar ve gerekçe metne yazılmaz.
  - Aynı projede tek bildirim durur (tekillik); sonraki değişiklik metni günceller.
  - Bütçe kapanınca ya da proje aktif değilken kaldırılır.
- **Bütçe `KAPALI` ise** 409 `BUTCE_KAPALI`.

### 8.6 Bütçe ölçümü, bütçe şeridi ve paneli

**Ölçüm kullanıcının gözüyle yapılır:** Proje sayfası, bütçeler listesi ya da `M11A.BUTCE_YUZDELERI` her açıldığında.

**Okumalar** (proje başına):
- `PROJE_DURUM {hedef: proje}`: `harcanan_emek` ve `etaplar[kimlik].harcanan_emek` (saat)
- `ETAPLAR {proje}`: etabın birimi
- `NESNELER {proje}`: parçaların aşaması

Para okunmaz. Servis gözü kullanılmaz; para okumaları servis gözüyle yapılmaz, `PROJE_DURUM` de servis okumaları arasında değildir.

**Saf fonksiyon** `olcum(butce, etaplar, proje_durum, ucretler, kurlar, parcalar, esik)`:
1. **Etabın saati:** `etaplar[k].harcanan_emek`. Birim `ETAPLAR`'dan gelir.
   - **Ücret:** projenin donmuş ücreti; yoksa `saat_ucretleri` (yedek); o da yoksa saat "ücreti bilinmeyen" sayılır.
   - **Etapsız saat:** `harcanan_emek` − etapların toplamı (en az 0). Birimi yoktur, ücreti bilinmeyendir.
2. **Tahmini gerçekleşen işçilik:** Σ saat × ücret, Ek D.2'nin kur ve yuvarlama kuralıyla proje para birimine çevrilir. Kuru eksik birim de bilinmeyen sayılır.
3. **Kapsam:** Güncel `ISCILIK` bütçesi > 0 ise `["ISCILIK"]`, değilse `[]`. Malzeme ve fason M3 gelince kapsama girer. Genel gider S-8 cevaplanınca girer.
4. **Dolum** = 100 × kapsamdaki gerçekleşen ÷ kapsamdaki güncel bütçe, bir ondalık. Kapsam boşsa `null`.
5. **İlerleme** = 100 × (`MONTAJA_HAZIR` + `MONTAJDA` aşamasındaki `PARCA`) ÷ toplam `PARCA`, bir ondalık. Parça yoksa `null`. Bu, kullanıcının Mustafa'ya önerdiği tanımdır. Çekirdek hesaplayınca oradan okunur (M11A-03). Saat ağırlıklı hesap sonraya kalır.
6. **Sapma** = dolum − ilerleme (ikisi de varsa).
7. **Renk:**
   - `GRI` ○ "Hesaplanamaz": sapma yok.
   - `KIRMIZI` ▲ "Dolum ilerlemenin <s> puan önünde": sapma > eşik (`sapma_esigi_puan`, varsayılan 15).
   - Değilse `YESIL` ● "Yolunda".
   - **Örnek:** %60 harcanmış bütçe, iş %80 bittiyse iyidir; %30 bittiyse kötüdür.
8. **Ücreti bilinmeyen saat** ayrıca döner. Ekranda: "Ücreti bilinmeyen 3,5 saat hesaba girmedi."

**Örnek** (denendi):
- K041'in tasarım görevi tamamlanınca `PROJE_DURUM` `MEK_TASARIM` etabına 12,8 saat verdi.
- 12,8 sa × 1.760 TL = 22.528,00 TL = 640,00 €. Bütçe `ISCILIK` 10.000 € → dolum 6,4.
- 4 parçadan 1'i `MONTAJA_HAZIR` → ilerleme 25,0 → sapma −18,6 → `YESIL`.

**Saklama:**
- `butce_olcumleri`'ne yalnızca yüzdeler, kapsam, eşik, uyarı ve bilinmeyen saat yazılır.
- Yeni satır yalnızca değerler son ölçümden farklıysa ya da son ölçüm bir saatten eskiyse yazılır. Tutar ve saat saklanmaz.

**Uyarı** (her ölçümden sonra, `alan/bildirim.py`):
- **Bırakma:** Renk `KIRMIZI` ise `BUTCE_SAPMASI` bırakılır ya da güncellenir (metin değiştiyse):
  - **kayıt:** `{tur: PROJE, kimlik, modul_kaydi: "bütçe"}`
  - **alıcılar:** `[{tur: KISI, kimlik: <satış yöneticisi>}, {tur: ROL, kimlik: YETKILI}]`
  - **metin:** `"<kod> <ad> · İşçilik dolumu %62,0, ilerleme %40,0 (22,0 puan; eşik 15)"`. Tutar yazılmaz.
  - **önem:** `UYARI`
- **Kaldırma:** Renk `KIRMIZI` değilse ve açık bildirim varsa kaldırılır.
- `acik_bildirimler` güncellenir.

**Bütçe şeridi** (proje sayfasının üstü; projeyi gören herkes):
- dolum ve ilerleme yan yana, iki yatay çubuk
- renk ve simge, sapma
- kapsam: "Dolum: yalnızca işçilik (malzeme ve fason M3 bağlanınca)"
- ölçüm anı; "PO bekleniyor"
- Okuma güncel değilse "hesaplanıyor".

**Bütçe paneli** (şeridin altında açılır; yalnızca `SATIS`, `MUHASEBE`, `YETKILI`):
- **Dört kalem:** başlangıç, güncel ve tahmini gerçekleşen çubukları. Gerçekleşeni olmayan kalemde "bilgi yok (M3)" ya da "formül yok (S-8)".
- **Tutarlar:** sözleşme tutarı ile güncel tutar.
- **Tutar değişiklikleri:** kim, ne zaman, eski → yeni, gerekçe, belge.
- **İşçilik ayrıntısı:** birim, saat, ücret, tutar; ücreti bilinmeyen saat.
- **İlerleme ayrıntısı:** hazır ve toplam parça.
- **Etiket:** Bütün gerçekleşen rakamlar "tahmini gerçekleşen" etiketiyle durur (risk önlemi: muhasebenin rakamıyla karışmasın).

**Bütçeler listesi** (`SATIS`, `MUHASEBE`, `YETKILI`):
- Kullanıcının gördüğü bütün `ACIK` M1.1A projeleri, şerit değerleriyle: kod, ad, müşteri, dolum, ilerleme, sapma, renk, bütçe durumu.
- **Sıra:** Kırmızılar önce, sapması büyük olan önce.
- Listeyi açmak her proje için ölçüm yapar (proje başına üç okuma).

### 8.7 Bildirimler ve kural işi

- **Çalıştırmak:** `python -m m11a.komutlar kurallari-calistir`. Ayrıca arka yüz içinde `M11A_KURAL_ARALIGI_DK` dakikada bir. Tekrar güvenlidir.
- **Servis gözü:** Yalnızca `PROJE` (aktif mi). Para ve saat okunmaz.
- **Her `ACIK` M1.1A projesi için:**
  1. Proje aktif değilse açık bildirimlerin hepsi kaldırılır.
  2. Bütçe `KAPALI` ise `BUTCE_SAPMASI` ve `TUTAR_DEGISTI` kaldırılır.
  3. Devir `TAMAM` ise `TICARI_DEVIR` kaldırılır.
  4. Devir `TAMAM` değilse ve `bildirim_birakildi` yanlış ya da `son_suzulenler` boş değilse `TICARI_DEVIR` yeniden bırakılır; alıcılar ve süzülenler güncellenir. Erişim sonradan verilen muhasebeci bildirimi böyle alır.
  5. `bildirim_birakildi` yanlış olan son tutar değişikliği için `TUTAR_DEGISTI` bırakılır.
- **`BUTCE_SAPMASI`** kural işinde yeniden hesaplanmaz; ölçüm kullanıcının gözüyledir. Kural işi yalnızca kaldırır.
- **Modül kapatılırken:** `python -m m11a.komutlar bildirimleri-kaldir` açık bildirimlerin hepsini kaldırır.
- **Üründe:** Servis okuması gerçek bulutta MVP'den sonra gelir. O zamana kadar kural işinin 1. adımı yalnızca simülatörde çalışır. Öteki adımlar modülün kendi tablosuna bakar, üründe de çalışır.

### 8.8 Kapanış ve kapanış sonrası düzeltme

- **"Bütçeyi kapat"** (`MUHASEBE`, `YETKILI`). Kesin kabul tarihi zorunludur; varsayılan, çekirdeğin `PROJE.kesin_kabul_tarihi`'si. Bütçe kesin kabulde (M7) kapanır; Faz 1'de M7 yok, tarih elle onaylanır.
- **Yapılanlar:**
  1. Kullanıcının gözüyle son ölçüm yapılır.
  2. `kapanis_farklari` yazılır. Her kalem için:
     - bütçe = güncel
     - gerçekleşen = tahmini gerçekleşen ya da `null`
     - fark = bütçe − gerçekleşen ya da `null`
     - kaynak (`SAAT_X_UCRET`, `BILGI_YOK_M3`, `FORMUL_YOK`)
  3. Bütçe `KAPALI` olur, kapanış anı ve kapatan yazılır.
  4. `BUTCE_SAPMASI` ve `TUTAR_DEGISTI` kaldırılır.
- **Sonrası:**
  - Tutar değişikliği yapılmaz.
  - Kilitten sonra gelen fatura gerekçeli bir **kapanış sonrası düzeltme** satırıdır: kalem, tutar (artı ya da eksi), gerekçe, belge. Yalnızca `KAPALI` bütçede.
  - Düzeltmeler `M11A.PROJE_BUTCESI`'nde ayrı listelenir; farkı yeniden yazmaz.

### 8.9 Ayarlar (`YETKILI`)

- `proje_kodu_deseni`, `proje_kodu_sira_kapsami`, `siparis_adi_deseni`. Kalıp değişkenleri: `YY`, `YYYY`, `AA`, `SIRA3`, `YILLIK_SIRA3`, `PROJE_KODU`, `MUSTERI`, `PROJE_ADI`, `PO`. Kaydederken bilinmeyen değişken 422.
- `sapma_esigi_puan` (varsayılan 15), `yaklasan_tarih_gun` (30).
- Yedek saat ücretleri (birim, ücret, para birimi). Birimler `BIRIMLER`'den.

### 8.10 Sağlanan okumalar

- **Dört okuma:** `M11A.BASLANGIC_PLANI`, `M11A.TEKLIF_GIRDILERI`, `M11A.BUTCE_YUZDELERI`, `M11A.PROJE_BUTCESI`. Biçimleri ve görme kuralları Ek D.7'de.
- **Uç:** `GET /api/saglanan/{ad}?proje=`, M1.1B'ninkiyle aynı.
- **Projeyi gören herkese açık olanlar:** Müşteri PDF'i `GET /api/projeler/{p}/teklif-pdf` ile, `BASLANGIC_PLANI` ve `TEKLIF_GIRDILERI`.

### 8.11 M1.1B'ye geçiş

- **Dönüştürmenin sonuç sayfası:**
  - "Proje ekibine devir (M1.1B): M1.1B'de 'Devri başlat'a `2611001` yazın."
  - `VITE_M11B_ADRES` bağlantısı.
- **Neden elle:** M1.1B yeni projeyi kendiliğinden göremez (M11B-04).
- **M1.1B'nin hazır bulduğu proje kaydı:** Proje çekirdekte sorumlusu ve tarihleriyle açıktır. M1.1B'nin ön doldurması (P0 = sipariş tarihi, P1 = kesin kabul ya da teslim) hemen çalışır. Denendi: K050 aynı projeye `ETAP.TANIMLADIM` ve `PLAN.ONAYLADIM` gönderebildi.
- **Sonraki iş (M1.1B'de):** M1.1B `M11A.BASLANGIC_PLANI`'nı isteğe bağlı bağımlılık olarak okuyup ön doldurmayı teklif takviminden yapar. `etap_kodu` M1.1B'nin şablon koduyla aynıdır (Ek D.2).

---

## 9. API

- **Taban:** `/api`, JSON.
- **Kimlik:** Her istekte kullanıcının erişim anahtarı (`Authorization: Bearer`).
- **Projeye ait uçlar** önce `PROJE` okur (6).

| Yöntem | Yol | Ne |
|---|---|---|
| GET | `/ben` | Kişi, roller, M1.1A'daki izinleri |
| GET | `/donustur/onizleme?surum=` | 8.1 önizleme |
| POST | `/donustur` | 8.1 dönüştürme |
| POST | `/donustur/{proje}/yeniden-dene` | `ACILIYOR` projeyi tamamla |
| GET | `/projeler/{p}` | Proje kartı: özet, sipariş adı, PO işareti, devir durumu, bütçe şeridi (ölçümle), kullanıcının izinleri |
| PUT | `/projeler/{p}/siparis` | PO no ve dosyası, sözleşme dosyası |
| GET, PUT | `/projeler/{p}/ticari` | Ticari devir formu, eksikler (`surum` ile) |
| POST | `/projeler/{p}/devir` | Muhasebeye devret |
| POST | `/projeler/{p}/devir/aldim` | Devri aldım |
| POST | `/projeler/{p}/devir/tamamla` | Devri tamamla |
| POST, PUT | `/projeler/{p}/eksikler`, `/projeler/{p}/eksikler/{e}` | Elle eksik; durum değişikliği |
| PUT | `/projeler/{p}/vega` | `{vega_cari_kodu, vega_proje_kodu}` |
| GET | `/projeler/{p}/butce` | Şerit; tutarları görene panel (8.6) |
| POST | `/projeler/{p}/tutar-degisikligi` | 8.5 |
| POST | `/projeler/{p}/kapanis` | 8.8 |
| POST | `/projeler/{p}/kapanis-sonrasi` | Kapanış sonrası düzeltme |
| GET | `/projeler/{p}/baslangic-plani` | Tarihlenmiş takvim |
| GET | `/projeler/{p}/teklif-girdileri` | Gereksinim, kapsam, dosyalar |
| GET | `/projeler/{p}/teklif-pdf` | Müşteri PDF'i (`application/pdf`) |
| POST | `/projeler/{p}/dosyalar` | Dosya kaydı |
| GET | `/gelen-kutusu` | Muhasebe gelen kutusu |
| GET | `/butceler` | Bütçeler listesi |
| GET, PUT | `/ayarlar` | 8.9 |
| GET | `/birimler`, `/kisiler` | Seçim listeleri |
| GET | `/saglanan/{ad}` | Ek D.7 |
| POST | `/gelistirme/giris` | Yalnızca `M11A_GELISTIRME=1` |

Okuma güncel değilse cevaba `"hesaplaniyor": true` eklenir.

---

## 10. Hata eşleme

Gövde `{"kod", "mesaj", ...}` (M1.1B ile aynı).

| Durum | HTTP | Kod | Mesaj |
|---|---|---|---|
| `PROJE` okumasında `YETKI` | 403 | `YETKI` | "Bu projeyi göremiyorsunuz." |
| Modülün rol kuralı | 403 | `YETKI` | "Bu işi muhasebe ya da yetkili yapar." vb. |
| `PROJE.ACTIM` `REDDEDILDI / YETKI` | 403 | `YETKI` | "Çekirdekte proje açma yetkiniz yok." |
| `PROJE.ACTIM` `REDDEDILDI / DURUM` | 409 | `KOD_KULLANILIYOR` ya da `ANA_PROJE` | 8.1 |
| Kapı (sürüm gönderilmemiş ya da kazanılmamış) | 409 | `KAPI` | "Yalnızca gönderilmiş ve kazanılmış teklif siparişe dönüştürülür." |
| Zaten dönüştürülmüş | 409 | `ZATEN_DONUSTU` | Proje kodu ile |
| M1.0'a ulaşılamıyor | 503 | `SAGLAYICI_YOK` | "Teklif modülüne (M1.0) ulaşılamıyor." |
| M1.0 403 | 403 | `YETKI` | "Bu teklifi görme yetkiniz yok." |
| Bütçe kapalı | 409 | `BUTCE_KAPALI` | |
| Devri tamamlama koşulu | 409 | `DURUM` | "Açık eksik var" ya da "VEGA kodları boş" |
| Doğrulama | 422 | `DOGRULAMA` | `hatalar: [{alan, sira, mesaj}]` |
| Aynı anda düzenleme | 409 | `DEGISTI` | `guncel` ile |
| `CekirdekHatasi('BAGLANTI')` | 503 | `BAGLANTI` | "Çekirdeğe ulaşılamıyor…" |
| `BICIM`, `KUNYE`, `URUN` | 400 / 500 / 502 | `BEKLENMEYEN` / `URUN` | Günlüğe ayrıntısıyla |

**Çekirdek kabul etti, modülün kaydı yazılamadı:** `PROJE.ACTIM` başarılı, `ACIK` güncellemesi yazılamadıysa satır `ACILIYOR` kalır. "Yeniden dene" `PROJE` okuyup tamamlar (8.1).

---

## 11. Ekranlar

Bu liste `TESLIM.md` › 4'e de yazılır. Görünüş Ek D.12.

| Ekran | Ne gösterir | Kim görür | Okumalar | Olaylar |
|---|---|---|---|---|
| Siparişe dönüştür | 8.1: önizleme, kod, sipariş adı, tarihler, sorumlu, PO ve sözleşme, bütçe ve takvim; sonuç ve M1.1B geçişi. M1.0'ın sürüm sayfasından açılan küçük bir pencere gibi tasarlanır ("tek tık") | `SATIS`, `YETKILI` | `M10.KAZANAN_SURUM`, `PROJE`, `KISILER` | `PROJE.ACTIM` |
| Proje kartı | Üstte bütçe şeridi; sekmeler: Özet (sipariş, PO, VEGA, devir durumu), Ticari, Bütçe, Başlangıç planı, Teklif girdileri (PDF) | Projeyi gören; Ticari ve Bütçe paneli tutarları görene | `PROJE`, `PROJE_DURUM`, `ETAPLAR`, `NESNELER`, `KISILER` | — |
| Muhasebe gelen kutusu | 8.4 | `MUHASEBE`, `YETKILI` | `PROJE` | — |
| Bütçeler listesi | 8.6 | `SATIS`, `MUHASEBE`, `YETKILI` | `PROJE`, `PROJE_DURUM`, `ETAPLAR`, `NESNELER` | — |
| Tutar değişikliği formu | 8.5, bütçe panelinden | `SATIS`, `YETKILI` | `PROJE` | — |
| Ayarlar | 8.9 | `YETKILI` | `BIRIMLER` | — |
| Geliştirme girişi | Kişi seçimi | Yalnızca geliştirmede | — | — |

**Derin bağlantı:** `PROJE` bağlamında `/proje/{kimlik}` → proje kartı ("Ticari bilgiler ve bütçe (M1.1A)").

---

## 12. Künye

Ek A, `kunye.json` olarak modülün köküne konur.
- **Denetim:** 0 hata, 0 uyarı.
- **Kayıt denetimi:** M1.0 ve M1.1B künyeleriyle birlikte (`kunye_denetle.py . <m1.0> <m1.1b>`) 0 hata. `M10.KAZANAN_SURUM`'u M1.0 sağlar (R07).

---

## 13. Çekirdeğe (ve M3'e) istekler

Her biri `istekler/M11A-NN_kisa_ad.md` olarak, `irp_sozlesme/sablonlar/istek.md` biçiminde.

| Kod | Önem | Ne | Kanıt | Öneri | Beklerken |
|---|---|---|---|---|---|
| M11A-01 | KRITIK | Muhasebe ve projeyi açan satış yöneticisi projeyi göremiyor (UYELER). Projeyi açan ekibe girmiyor; rol bazlı görünürlük yok; satış yöneticisi muhasebeye görev atayamıyor | K060 `PROJE` → `YETKI: Gorunurluk`; `TICARI_DEVIR` `suzulenler: K060 PROJEYI_GOREMEZ`. K050 sorumluyu K004 yapınca kendi açtığı projeyi okuyamıyor. K050 → K060 `GOREV.ATADIM` → `YETKI`. Yalnızca `PROJE.ERISIM_VERDIM` açıyor (hepsi denendi) | (a) Projeyi açan proje ekibine girsin. (b) Ayar: bütün projeleri gören roller (ör. `MUHASEBE`, `SATIS`); para maskesi çekirdeğin kuralıyla kalır | Yetkili çekirdeğin ekranından erişim verir; modül süzüleni gösterir ve bildirimi yeniden bırakır (6, 8.7) |
| M11A-02 | ONEMLI | Modüller arası okumaların yönlendirmesi yok (M10-02 ile aynı) | `oku('M10.KAZANAN_SURUM')` → `BICIM: TANIMSIZ_VERI` | Çekirdek `<KOD>.<AD>`'ı sağlayana kullanıcının anahtarıyla yönlendirsin | `saglayicilar.py` üzerinden HTTP (Ek D.4) |
| M11A-03 | ONEMLI | Parça ilerlemesi çekirdekte yok | `PROJE_DURUM.yuzde` görev saatinden; parça aşaması oranı yok | `PROJE_DURUM`'a `parca_ilerlemesi: {hazir, toplam, yuzde}` (montaja hazır + montajda ÷ toplam); saat ağırlıklısı sonra | Modül `NESNELER`'den sayar (8.6) |
| M11A-04 | ONEMLI | Proje ve birim bazında saat okuması simülatörde yok | `PROJE_ISCILIGI`, `PROJE_MALIYETI`, `TAHMIN_GERCEK` → `TANIMSIZ_VERI` (denendi) | T12'nin okumaları simülatöre | `PROJE_DURUM` etap saatleri + `ETAPLAR` birimi; etapsız saat "bilinmeyen" |
| M11A-05 | ONEMLI | **M3'e:** Proje bazında satın alma ve fason sipariş tutarları | M3'ün sağladığı `M3.SIPARIS_DURUMU` fiyat taşımıyor | `M3.PROJE_ALIMLARI {proje}` → `{kalemler: [{butce_kalemi: MALZEME \| FASON, tutar, para_birimi}], an}`; görme `ROL`, para | Malzeme ve fason "bilgi yok (M3)"; kapsam dışında |
| M11A-06 | DUSUK | M1.0 kazanan teklifinin hangi projeye dönüştüğünü bilemiyor; kapanış farkı öğrenmeye dönemiyor (döngü) | M10 → M11A bağımlılığı R08; `PROJE.ACTIM`'da kaynak alanı yok (fazladan alan saklanıyor ama sözleşmede değil; kullanılmadı) | `PROJE.ACTIM`'a `kaynak: {modul, kayit}` alanı ve `PROJE`/`PROJELER`'de dönmesi; kapanış sonucu için çekirdek okuması | M1.0'da bağlantı yok; fark `M11A.PROJE_BUTCESI`'nde |
| M11A-07 | ONEMLI | Dosya depolama kapısı yok (M11B-05, M10-05 ile aynı) | — | Yükleme kapısı | Dosya kaydı |
| M11A-08 | DUSUK | Sahte bulut tek künye kuruyor; ortak geliştirme ortamında yalnızca bir modülün servis anahtarı çalışıyor | Ortak zeminde M1.1B'nin `bildirim_birak`'ı `YETKI: Servis kimliği` (denendi) | `sunucu.py --kunye` birden çok künye alsın; yetkili olayı için bir sahte uç | Ek D.11 |

---

## 14. Sınama

### 14.1 Ortam

```
python3 irp_sozlesme/arac/paket_denetle.py
python3 -m unittest discover -s irp_sozlesme/testler
python3 irp_sozlesme/arac/kunye_denetle.py .
python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json
pytest
```

### 14.2 Birim testleri (saf fonksiyonlar)

- **Kod:** Kalıp ve kapsam (`YIL`, `AY`). 02.11.2026 ilk sipariş `2611001`. Elle kodun deseni. Sipariş adı PO'lu ve PO'suz.
- **Tarih:** Ek D.5 ile 8.1'deki tablo; teslim 16.05.2027, kesin kabul 23.05.2027. `KESIN_KABUL` yokken.
- **Bütçe dönüşümü:** Ek D.5 → `MALZEME` 32.500,00, `ISCILIK` 10.000,00, `FASON` 1.000,00, `GENEL_GIDER` 0,00. Ücretler `MEK_TASARIM` 1.760 TL, `IMALAT` 1.408 TL.
- **Ölçüm:**
  - 12,8 sa `MEK_TASARIM` → 640,00 €, dolum 6,4
  - 1/4 parça hazır → ilerleme 25,0, sapma −18,6, `YESIL`
  - `ISCILIK` bütçesi 2.000 ve 0/4 parça → dolum 32,0, sapma 32,0, `KIRMIZI`
  - parça yok → `GRI`
  - ücreti ya da kuru bilinmeyen birim
  - etapsız saat
  - `ISCILIK` bütçesi 0 → kapsam boş
  - eşik sınırı (tam 15,0 `YESIL`)
- **Eksik:** Her alan kodunun koşulu; devirden sonra dolan ve boşalan alan.
- **Devir durumu:** Geçişler; "tamamla" koşulları.

### 14.3 Sözleşme testleri (simülatöre karşı)

- **Her test** kendi çekirdeğini açar (`Cekirdek.ac('kunye.json', sayac=TabloSayac(...))`). D.10'daki zemini `satis_rolu_kur=True` ile kurar: M1.0 kurulu olmadığından `SATIS` rolü ve `PROJE.ACTIM` yetkisi elle yazılır. Bu yazım üründe M1.0'ın künyesinden gelir.
- **M1.0'ın yerine** `SahteM10Saglayici` durur: `testler/sabitler/M10.KAZANAN_SURUM.json`'u verir. PDF'i küçük bir gerçek PDF'le doldurur. Gerekirse kaynağı `EK_IS` ya da kimliği değişmiş kopyaları verir.
- **Senaryo:** Sonunda `senaryo_yaz`; `.beklenen.json`'u `senaryo_dogrula` üretir.
- **Başka modüllerin ve çekirdek ekranının işleri** sınamada `surucu.yetkili_olay` ile yazılır ve senaryoya girer: etap, görev, parça, erişim, proje kapatma.
  - Görev kabulü ve tamamlanması `neyin_ustunde`'de görevin sürümünü taşır; yoksa `BICIM: Gorev hedefi gerekli` alır (denendi).

| Senaryo | Akış | Beklenen retler |
|---|---|---|
| `M11A01_siparise_donustur` | K050 sürüm 57'yi 02.11.2026'da dönüştürür, PO `PO1246789` ile. `PROJE.ACTIM` kabul edilir: `2611001`, sorumlu K050, teslim 16.05.2027, kesin kabul 23.05.2027. K050 `PROJE`'yi okur. `M11A.BASLANGIC_PLANI` 8.1'deki tabloyu verir. İkinci dönüştürme 409 `ZATEN_DONUSTU` alır, çekirdeğe olay gitmez | — |
| `M11A02_kod_ve_yetki` | K050 kodu elle `2614` verir: çekirdek `DURUM` der, modül 409 `KOD_KULLANILIYOR` döner ve satırları siler. K004'ün (SATIS yok) dönüştürmesi modülde 403 alır. K004'ün doğrudan `PROJE.ACTIM`'ı çekirdekten `YETKI` alır (çekirdeğin kuralını gösterir) | `DURUM`, `YETKI` |
| `M11A03_muhasebeye_devir` | K050 dönüştürür, ticari formun bir kısmını doldurur, devreder. `TICARI_DEVIR`'de K060 `PROJEYI_GOREMEZ` ile süzülür; ekranda uyarı çıkar. K060'ın gelen kutusu boştur; `PROJE` okuması `YETKI`. Yetkili `PROJE.ERISIM_VERDIM {proje: '2611001', kisi: 'K060'}` yazar. Kural işi bildirimi yeniden bırakır, K060 alıcıdır. K060 "devri aldım" der (`EKSIK_VAR`), eksikleri doldurur, VEGA kodlarını yazar, tamamlar (`TAMAM`). Bildirim kaldırılır | 1 okuma hatası (`YETKI`) |
| `M11A04_butce_olcumu` | Dönüştürmeden sonra yetkili `ETAP.TANIMLADIM {proje: '2611001', birim: 'MEK_TASARIM', sorumlu: 'K012', …}` yazar. K012 K041'e görev atar; K041 kabul eder, 05.11.2026 15:00'te tamamlar. Dört `PARCA` açılır, biri `MONTAJA_HAZIR`'a geçirilir. K050'nin ölçümü dolum 6,4 (saat × 1.760 TL ÷ 35,2), ilerleme 25,0, `YESIL` verir. Saat değeri `PROJE_DURUM`'dan geldiği gibi doğrulanır; denemede 12,8 | — |
| `M11A05_bildirim_sapma` | `M11A04`'ün zemininde dört parça da `SIPARIS_VERILMELI`. K050 `ISCILIK` güncelini 2.000'e indirir (tutar değişikliği): `TUTAR_DEGISTI` bırakılır. Ölçüm 32,0 / 0,0 → `BUTCE_SAPMASI` K050 ve K001'e gider. Bütçe 10.000'e döner → ölçüm `YESIL` → bildirim kaldırılır. Yeniden 2.000 → yeniden bırakılır. Yetkili `PROJE.KAPATTIM` yazar; kural işi bütün açık bildirimleri kaldırır | — |
| `M11A06_gorunurluk` | K017 `PROJE`'yi okuyamaz; modül 403 döner. K012 (etap sorumlusu olarak projeyi görür, denendi) şeridi ve yüzdeleri görür. Paneli, ticari formu ve `M11A.PROJE_BUTCESI`'ni göremez (modülde 403, çekirdeğe gitmez) | 1 okuma hatası (`YETKI`) |
| `M11A07_tutar_ve_kapanis` | K050 güncel tutarı 56.000 → 50.000, `MALZEME`'yi 32.500 → 26.500 yapar (gerekçe "Robotu müşteri verecek", belge). Sözleşme tutarı ve başlangıç aynı kalır. Erişimi verilmiş K060 bütçeyi 23.05.2027 kesin kabulle kapatır: `kapanis_farklari` yazılır, bildirimler kaldırılır. Kapanıştan sonra tutar değişikliği 409 alır; K060'ın `MALZEME` +1.200,00 düzeltmesi kaydedilir | — |
| `M11A08_ek_is` | `2611001` açıldıktan sonra kaynağı `EK_IS`, bağlı projesi `2611001` olan sürüm 58 dönüştürülür: `ana_proje` ile `2611002` açılır. Bağlı projesi `2611002` olan sürüm 59'u dönüştürmek çekirdekte `DURUM` alır (ana projenin kendi ana projesi var), modül 409 `ANA_PROJE` döner | `DURUM` |

`TESLIM.md` › 2'ye senaryo sayısı ve beklenen retler yazılır.

### 14.4 Veritabanı, sağlayıcı ve API testleri

- **Göçler:** Boş şemada sırayla.
- **Değişmezler:**
  - sözleşme tutarı ve donmuş kopya (tetikleyici)
  - başlangıç bütçesi (tetikleyici)
  - tek dönüştürme
  - `TARIH` koşulunda tarih
  - kapalı bütçede kapanış alanları
- **Sağlayıcı istemcisi:** `httpx.MockTransport` ile Ek D.4'teki her cevap; zaman aşımı ve boş adres → `SAGLAYICI_YOK`. İstemcinin kullanıcının anahtarını değiştirmeden ilettiği de sınanır.
- **API:**
  - Bölüm 6'nın tablosu: her iş için izinli ve izinsiz bir kişi.
  - Tutar görmeyenin cevabında tutar alanının **hiç olmaması** (yalnızca boş değil).
  - Hata eşleme.
  - `ACILIYOR` projenin listelere girmemesi.
- **Test veritabanı:** `M11A_TEST_VERITABANI`, her test temiz.

### 14.5 Ön yüz

- **vitest:** Tutar, yüzde ve tarih biçimleyicileri; renk ve simge eşlemesi.
- **Elle duman testi:** `gelistirme/BENIOKU.md`'de, her ekran için bir paragraf.
  - Biri **ortak ortamda** (Ek D.11): M1.0'da teklif kur → onayla → gönder → "Siparişe dönüştür" → M1.1A'da aç → M1.1B'de devri başlat.

---

## 15. Geliştirme ortamı

1. **Python:** `uv venv --python 3.15`, `uv pip install -e ".[dev]"`.
2. **Veritabanı:** `docker compose -f gelistirme/docker-compose.yml up -d` (PostgreSQL 16, `localhost:54331`) ya da Homebrew `postgresql@17`.
   - `python -m m11a.komutlar gelistirme-vt-sifirla` şunları sırayla koşar: `gelistirme/sema_ac.sql`, `veritabani/*.sql`, `gelistirme/ornek_ayarlar.sql`.
3. **Çekirdek:**
   - **Testlerde:** Simülatör sürücüsü.
   - **Uygulamayı yalnız çalıştırırken:** Ortak zemin kullanılır, çünkü örnek firmada satış ve muhasebe yoktur.
     ```
     python gelistirme/ortak_zemin.py <M1.0 klasörü>/kunye.json <M1.1B klasörü>/kunye.json gelistirme/a_ekibi_zemini.json
     python irp_sozlesme/simulator/sunucu.py --kunye kunye.json --zemin gelistirme/a_ekibi_zemini.json --port 8790
     ```
     Sunucunun yazdığı `IRP_*` değerleri arka yüzün ortamına verilir. Sahte bulut yeniden başlarsa `gelistirme-vt-sifirla` de koşulur.
   - **Saat:** `POST /sahte/saat {"an": "2026-11-02T09:00:00+03:00"}`.
4. **M1.0:** Kendi klasöründe `uvicorn m10.api.uygulama:app --port 8010` aynı `IRP_TABAN`'la çalışır. `M11A_SAGLAYICI_M10=http://localhost:8010/api`. M1.0 çalışmıyorsa dönüştürme `SAGLAYICI_YOK` der, gerisi çalışır.
5. **Arka yüz:** `uvicorn m11a.api.uygulama:app --reload --port 8011`.
6. **Ön yüz:** `cd on_yuz && npm install && npm run dev -- --port 5181`. `/api` → `http://localhost:8011`.
7. **Geliştirme girişi:** K050 (satış), K060 (muhasebe), K001 (yetkili). Anahtar `sessionStorage`'da `m11a_anahtar`.
8. **Olay sayacı:** `TabloSayac.sonraki` `SELECT mod_m11a.olay_sirasi(%s, %s)`'i kendi kısa işleminde çağırır.

---

## 16. Uygulama sırası

| Adım | İş | Sonunda |
|---|---|---|
| 1 | Ortam, göçler (Ek B), künye (Ek A), `CLAUDE.md` | `kunye_denetle` 0 hata |
| 2 | `baglanti.py`, kişi ve roller, hata eşleme, `/ben`, geliştirme girişi | — |
| 3 | `saglayicilar.py` (HTTP ve sahte), sabit `M10.KAZANAN_SURUM.json` | 14.4 sağlayıcı testleri |
| 4 | Saf fonksiyonlar: kod, tarih, bütçe dönüşümü, ölçüm, eksik | 14.2 |
| 5 | Siparişe dönüştürme (önizleme, dönüştürme, yeniden dene, ek iş) | `M11A01`, `M11A02`, `M11A08` |
| 6 | PO ve sözleşme, ticari form, eksikler, devir, gelen kutusu, VEGA | `M11A03` |
| 7 | Bütçe ölçümü, şerit, panel, bütçeler listesi | `M11A04`, `M11A06` |
| 8 | Tutar değişikliği, bildirimler, kural işi | `M11A05` |
| 9 | Kapanış ve kapanış sonrası düzeltme | `M11A07` |
| 10 | Ayarlar, sağlanan okumalar, müşteri PDF'i | — |
| 11 | Ön yüz ekranları; `gelistirme/ortak_zemin.py` | Elle duman testi, ortak ortam dahil |
| 12 | İstek dosyaları, `TESLIM.md`, teslim kontrol listesi | — |

**Bitince modülün sahibine söyle** (`BASLA.md` › Bitirince):
- künye denetimi: hata ve uyarı sayısı
- paket denetimi
- senaryo sayısı ve retler
- istek sayısı

---

## 17. Uygulayıcıya bırakılanlar

- Ekranların yerleşimi (Ek D.12'nin değişkenleriyle); şerit ve çubukların çizimi.
- Ölçüm sonuçlarını istek içinde önbelleğe almak (aynı istekte iki kez ölçmemek).
- Klasörlerin içindeki kod düzeni; günlük biçimi; hata mesajlarının tam cümleleri.

---

## 18. Açık sorular

Bunlar yazılımı değiştirmez; cevapları ayara ya da veriye girer.

| Soru | Nereye girer |
|---|---|
| S-1: Proje numarası ne zaman veriliyor? | `proje_kodu_deseni`, `proje_kodu_sira_kapsami`; teklifte veriliyorsa dönüştürmede elle kod |
| S-4: VEGA kartlarında IRP proje kodu tutulabilir mi? | Faz 1 elle; otomatik eşleşme sonraki faz |
| S-6: Muhasebe bütçeyi bugün nasıl izliyor? | Bütçe panelinin içeriği |
| S-8: Genel gider payı nasıl yükleniyor? | Genel gider gerçekleşeninin formülü; o zamana kadar "formül yok" |
| S-5: Ödeme ve teminat takibi bugün nerede? | Tarih uyarılarının bildirime dönüşmesi |
| S-2: Satış ile planlama arasında iş bölümü | Dönüştürmedeki varsayılan sorumlu |
| Mustafa: modül kodu ve harfi; ekranların yolu (S1); istekler M11A-01…08 | Künye; ön yüz |

---

## Ek A · `kunye.json`

```json
{
 "kunye_surumu": 1,
 "kod": "M11A",
 "ad": "Sipariş alma ve muhasebeye devir",
 "surum": "0.1.0",
 "cekirdek": ">=10.2",
 "sahip": "A ekibi",
 "aciklama": "Gönderilmiş ve kazanılmış teklif sürümünü tek tıkla siparişe dönüştürür: proje kodunu verir, projeyi çekirdekte açar, teklifin maliyet kırılımını başlangıç bütçesi, takvimini başlangıç planı olarak dondurur. Ticari devir formu, muhasebe gelen kutusu, VEGA kart kodları, tutar değişikliği, bütçe şeridi (dolum ile ilerleme yan yana) ve kesin kabulde bütçe kapanışı.",
 "servis_kimligi": "SRV-M11A",
 "arka_yuz": true,
 "olay_yolu": "ARKA_YUZ",
 "cihaz_harfi": "Q",
 "kapilar": {
  "okumalar": [
   "PROJE",
   "KISILER",
   "BIRIMLER",
   "ETAPLAR",
   "PROJE_DURUM",
   "NESNELER",
   "M10.KAZANAN_SURUM"
  ],
  "servis_okumalari": [
   "PROJE"
  ],
  "olaylar": [
   "PROJE.ACTIM"
  ],
  "plan": false,
  "belge_surumu": false,
  "bildirimler": [
   {
    "kural": "TICARI_DEVIR",
    "ad": "Ticari devir muhasebeye geldi",
    "onem": "BILGI",
    "kayit_turleri": [
     "PROJE"
    ],
    "alici_turleri": [
     "ROL"
    ],
    "roller": [
     "MUHASEBE"
    ]
   },
   {
    "kural": "TUTAR_DEGISTI",
    "ad": "Sözleşmenin güncel tutarı ya da güncel bütçe değişti",
    "onem": "BILGI",
    "kayit_turleri": [
     "PROJE"
    ],
    "alici_turleri": [
     "ROL"
    ],
    "roller": [
     "MUHASEBE"
    ]
   },
   {
    "kural": "BUTCE_SAPMASI",
    "ad": "Bütçe dolumu ilerlemeyi eşikten fazla geçti",
    "onem": "UYARI",
    "kayit_turleri": [
     "PROJE"
    ],
    "alici_turleri": [
     "KISI",
     "ROL"
    ],
    "roller": [
     "YETKILI"
    ]
   }
  ],
  "abonelikler": []
 },
 "nesne_turleri": [],
 "tur_uzantilari": [],
 "roller": [
  {
   "kod": "MUHASEBE",
   "ad": "Muhasebe ve finans"
  }
 ],
 "kod_listeleri": [],
 "yetki_onerileri": [],
 "veritabani": {
  "sema": "mod_m11a",
  "gocler": "veritabani/"
 },
 "on_yuz": {
  "tur": "AYRI_UYGULAMA",
  "derin_baglantilar": [
   {
    "ad": "Ticari bilgiler ve bütçe (M1.1A)",
    "baglam": "PROJE",
    "yol": "/proje/{kimlik}"
   }
  ]
 },
 "saglananlar": [
  {
   "ad": "M11A.BASLANGIC_PLANI",
   "parametreler": [
    "proje"
   ],
   "gorme": "KAYDI_GOREN",
   "kisisel": false,
   "para": false,
   "aciklama": "Kazanan teklifin donmuş takvimi, sipariş tarihine göre tarihlenmiş: etap kodu (M1.1B şablonuyla ortak), ad, sıra, paralel grup, başlangıç, bitiş. M1.1B'nin başlangıç planı için"
  },
  {
   "ad": "M11A.BUTCE_YUZDELERI",
   "parametreler": [
    "proje"
   ],
   "gorme": "KAYDI_GOREN",
   "kisisel": false,
   "para": false,
   "aciklama": "Bütçe şeridi, yalnızca yüzdeler: dolum, ilerleme, sapma puanı, renk, hangi kalemlerin hesaba girdiği; tutar yok"
  },
  {
   "ad": "M11A.TEKLIF_GIRDILERI",
   "parametreler": [
    "proje"
   ],
   "gorme": "KAYDI_GOREN",
   "kisisel": false,
   "para": false,
   "aciklama": "Kazanan teklifin gereksinim listesi, kapsamı (dahil, hariç), talep dosyalarının kayıtları ve müşteri PDF'inin kaydı. M1.1B klasör arşivi ve M2 tasarım girdisi için; maliyet ve kâr yok"
  },
  {
   "ad": "M11A.PROJE_BUTCESI",
   "parametreler": [
    "proje"
   ],
   "gorme": "ROL",
   "kisisel": false,
   "para": true,
   "aciklama": "Sözleşme tutarı, güncel tutar, dört kalemde başlangıç ve güncel bütçe, tahmini gerçekleşen, değişiklik kayıtları, kapanış farkı. Yalnızca SATIS, MUHASEBE, YETKILI. M8 için"
  }
 ],
 "bagimliliklar": [
  {
   "modul": "M10",
   "zorunlu": false,
   "okumalar": [
    "M10.KAZANAN_SURUM"
   ]
  }
 ],
 "kisisel_veri": [
  {
   "alan": "projeler.donmus_teklif.musteri.kisiler: ad, unvan, telefon, e-posta",
   "neden": "Kazanan teklifin donmuş kopyasındaki müşteri iletişim kişileri; muhasebenin eksik ticari bilgiyi müşteriden istemesi için (KVKK m.5/2-c)"
  }
 ],
 "para": true,
 "sinirlar": {
  "bildirim_dakika": 30,
  "okuma_dakika": 600,
  "servis_okuma_dakika": 60
 },
 "istekler": [
  {
   "kod": "M11A-01",
   "baslik": "Muhasebe ve projeyi açan satış yöneticisi projeyi göremiyor (UYELER): açan ekibe girmiyor, rol bazlı proje görünürlüğü yok",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-02",
   "baslik": "Modüller arası okumaların yönlendirmesi yok: oku('M10.KAZANAN_SURUM') simülatörde TANIMSIZ_VERI",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-03",
   "baslik": "Parça ilerlemesi (montaja hazır + montajda / toplam parça) çekirdekte hesaplansın",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-04",
   "baslik": "Proje ve birim bazında saat okuması simülatörde yok (PROJE_ISCILIGI, PROJE_MALIYETI); şimdilik PROJE_DURUM etap saatleri",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-05",
   "baslik": "M3'e: proje bazında satın alma ve fason sipariş tutarları (M3.PROJE_ALIMLARI)",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-06",
   "baslik": "PROJE.ACTIM'da kaynak kayıt alanı yok: M1.0 kazanan teklifinin hangi projeye dönüştüğünü bilemiyor (geri bağlantı döngüye takılıyor)",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-07",
   "baslik": "Dosya depolama kapısı yok (PO, sözleşme, teminat mektubu yalnızca kayıt)",
   "durum": "ACIK"
  },
  {
   "kod": "M11A-08",
   "baslik": "Sahte bulut tek künye kuruyor: ortak geliştirme ortamında yalnızca bir modülün servis anahtarı çalışıyor",
   "durum": "ACIK"
  }
 ]
}
```

## Ek B · Göçler

### `veritabani/001_m11a.sql`

```sql
-- M1.1A Sipariş alma ve muhasebeye devir · modülün tabloları (şema mod_m11a)
-- Çekirdeğin kimlikleri (proje, kişi, birim, olay) metin olarak, değer olarak tutulur; çekirdeğe yabancı anahtar yoktur (G08).
-- M1.0'ın kimlikleri (teklif sürümü, müşteri) de değer olarak tutulur; başka modülün şeması okunmaz (G02).

-- Olay kimliğinin sırası (04_veritabani.md › 3)
CREATE TABLE mod_m11a.olay_sayaci (
  kisi text NOT NULL,
  gun text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (kisi, gun)
);

CREATE FUNCTION mod_m11a.olay_sirasi(p_kisi text, p_gun text) RETURNS integer
LANGUAGE sql SET search_path = mod_m11a, pg_temp AS $$
  INSERT INTO mod_m11a.olay_sayaci AS s (kisi, gun, son) VALUES (p_kisi, p_gun, 1)
  ON CONFLICT (kisi, gun) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

-- Proje kodu ve yıllık sipariş sırası
CREATE TABLE mod_m11a.sayaclar (
  ad text NOT NULL,
  donem text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (ad, donem)
);

CREATE FUNCTION mod_m11a.sayac_ilerlet(p_ad text, p_donem text) RETURNS integer
LANGUAGE sql SET search_path = mod_m11a, pg_temp AS $$
  INSERT INTO mod_m11a.sayaclar AS s (ad, donem, son) VALUES (p_ad, p_donem, 1)
  ON CONFLICT (ad, donem) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

CREATE TABLE mod_m11a.ayarlar (
  anahtar text PRIMARY KEY,
  deger jsonb NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Teklifte işçiliği olmayan birim için yedek saat ücreti (karar 104: varsayım)
CREATE TABLE mod_m11a.saat_ucretleri (
  birim text PRIMARY KEY,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Dosyanın kaydı modülde, dosyanın kendisi şirket sunucusunda
CREATE TABLE mod_m11a.dosya_kayitlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL,
  tur text NOT NULL CHECK (tur IN ('PO', 'SOZLESME', 'TEMINAT', 'TUTAR_DEGISIKLIGI', 'FATURA', 'DIGER')),
  ad text NOT NULL,
  konum text NOT NULL CHECK (btrim(konum) <> ''),
  aciklama text,
  parmak_izi text CHECK (parmak_izi ~ '^[0-9a-f]{64}$'),
  ekleyen text NOT NULL,
  ekleme_ani timestamptz NOT NULL
);

-- Projenin M1.1A kaydı: teklifin donmuş kopyası, sipariş, ticari özet
CREATE TABLE mod_m11a.projeler (
  proje text PRIMARY KEY,
  durum text NOT NULL CHECK (durum IN ('ACILIYOR', 'ACIK')),
  teklif_surumu bigint NOT NULL UNIQUE,
  teklif_etiketi text NOT NULL,
  talep_no text NOT NULL,
  m10_musteri bigint,
  musteri_adi text NOT NULL,
  proje_adi text NOT NULL,
  kaynak text NOT NULL CHECK (kaynak IN ('YENI_IS', 'EK_IS', 'SERVIS')),
  ana_proje text,
  sorumlu text NOT NULL,
  satis_yoneticisi text NOT NULL,
  siparis_tarihi date NOT NULL,
  teslim_tarihi date NOT NULL,
  kesin_kabul_tarihi date,
  yil integer NOT NULL,
  yillik_sira integer NOT NULL,
  po_no text,
  po_dosyasi bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  sozlesme_dosyasi bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  vega_cari_kodu text,
  vega_proje_kodu text,
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  sozlesme_tutari numeric(14,2) NOT NULL CHECK (sozlesme_tutari >= 0),
  guncel_tutar numeric(14,2) NOT NULL CHECK (guncel_tutar >= 0),
  kurlar jsonb NOT NULL DEFAULT '[]'::jsonb,
  teslim_suresi_hafta integer,
  donmus_teklif jsonb NOT NULL,
  pdf bytea NOT NULL,
  pdf_ad text NOT NULL,
  pdf_parmak_izi text NOT NULL CHECK (pdf_parmak_izi ~ '^[0-9a-f]{64}$'),
  acan text NOT NULL,
  acilis_ani timestamptz NOT NULL,
  acilis_olayi text,
  butce_durumu text NOT NULL DEFAULT 'ACIK' CHECK (butce_durumu IN ('ACIK', 'KAPALI')),
  kapanis_kesin_kabul date,
  kapanis_ani timestamptz,
  kapatan text,
  surum integer NOT NULL DEFAULT 1,
  UNIQUE (yil, yillik_sira),
  CHECK (kaynak = 'YENI_IS' OR ana_proje IS NOT NULL),
  CHECK (butce_durumu = 'ACIK' OR (kapanis_ani IS NOT NULL AND kapanis_kesin_kabul IS NOT NULL AND kapatan IS NOT NULL))
);

ALTER TABLE mod_m11a.dosya_kayitlari
  ADD CONSTRAINT dosya_kayitlari_proje_fk FOREIGN KEY (proje) REFERENCES mod_m11a.projeler (proje);

-- Sözleşme tutarı, teklifin donmuş kopyası ve PDF değişmez
CREATE FUNCTION mod_m11a.donmus_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m11a, pg_temp AS $$
BEGIN
  IF NEW.sozlesme_tutari IS DISTINCT FROM OLD.sozlesme_tutari
     OR NEW.para_birimi IS DISTINCT FROM OLD.para_birimi
     OR NEW.teklif_surumu IS DISTINCT FROM OLD.teklif_surumu
     OR NEW.donmus_teklif IS DISTINCT FROM OLD.donmus_teklif
     OR NEW.kurlar IS DISTINCT FROM OLD.kurlar
     OR NEW.pdf_parmak_izi IS DISTINCT FROM OLD.pdf_parmak_izi THEN
    RAISE EXCEPTION 'Sözleşme tutarı ve teklifin donmuş kopyası değiştirilemez (proje %)', OLD.proje;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER projeler_donmus_degismez BEFORE UPDATE ON mod_m11a.projeler
  FOR EACH ROW EXECUTE FUNCTION mod_m11a.donmus_degismez();

-- Bütçe: dört kalem; başlangıç donmuş, güncel yalnızca tutar değişikliği formuyla
CREATE TABLE mod_m11a.butce_satirlari (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  baslangic numeric(14,2) NOT NULL CHECK (baslangic >= 0),
  guncel numeric(14,2) NOT NULL CHECK (guncel >= 0),
  PRIMARY KEY (proje, kalem)
);

CREATE FUNCTION mod_m11a.baslangic_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m11a, pg_temp AS $$
BEGIN
  IF NEW.baslangic IS DISTINCT FROM OLD.baslangic THEN
    RAISE EXCEPTION 'Başlangıç bütçesi değiştirilemez (proje %, kalem %)', OLD.proje, OLD.kalem;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER butce_satirlari_baslangic_degismez BEFORE UPDATE ON mod_m11a.butce_satirlari
  FOR EACH ROW EXECUTE FUNCTION mod_m11a.baslangic_degismez();

-- Tekliften donmuş birim saat ücretleri (tahmini gerçekleşen işçilik için)
CREATE TABLE mod_m11a.proje_saat_ucretleri (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  birim text NOT NULL,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  PRIMARY KEY (proje, birim)
);

-- Tekliften donmuş takvim, sipariş tarihine göre tarihlenmiş (M11A.BASLANGIC_PLANI)
CREATE TABLE mod_m11a.baslangic_plani (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  sira integer NOT NULL,
  etap_kodu text,
  ad text NOT NULL,
  paralel_grup text,
  baslangic_hafta integer NOT NULL CHECK (baslangic_hafta >= 0),
  sure_hafta integer NOT NULL CHECK (sure_hafta >= 1),
  baslangic date NOT NULL,
  bitis date NOT NULL,
  PRIMARY KEY (proje, sira),
  CHECK (baslangic <= bitis)
);

-- Ticari devir formu
CREATE TABLE mod_m11a.ticari_kosullar (
  proje text PRIMARY KEY REFERENCES mod_m11a.projeler (proje),
  faturalama_bicimi text CHECK (faturalama_bicimi IN ('PESIN', 'KADEMELI', 'SEVKTE', 'ON_KABULDE', 'KESIN_KABULDE', 'HAKEDIS')),
  faturalama_notu text,
  teslim_sekli text,
  ihracat boolean,
  tesvik text CHECK (tesvik IN ('VAR', 'YOK')),
  tesvik_belge_no text,
  teminat_gerekli text CHECK (teminat_gerekli IN ('VAR', 'YOK')),
  notlar text,
  guncelleyen text,
  guncelleme_ani timestamptz,
  surum integer NOT NULL DEFAULT 1
);

CREATE TABLE mod_m11a.odeme_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  sira integer NOT NULL,
  kosul text NOT NULL CHECK (kosul IN ('SIPARIS', 'SEVK', 'ON_KABUL', 'KESIN_KABUL', 'TARIH', 'DIGER')),
  tarih date,
  tutar numeric(14,2) NOT NULL CHECK (tutar >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  aciklama text,
  UNIQUE (proje, sira) DEFERRABLE INITIALLY DEFERRED,
  CHECK (kosul <> 'TARIH' OR tarih IS NOT NULL)
);

CREATE TABLE mod_m11a.teminatlar (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  tur text NOT NULL CHECK (tur IN ('AVANS', 'KESIN', 'DIGER')),
  tutar numeric(14,2) NOT NULL CHECK (tutar >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  banka text,
  bitis_tarihi date,
  dosya bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  aciklama text
);

-- Muhasebeye devir ve eksik bilgi
CREATE TABLE mod_m11a.devirler (
  proje text PRIMARY KEY REFERENCES mod_m11a.projeler (proje),
  durum text NOT NULL DEFAULT 'DEVREDILDI' CHECK (durum IN ('DEVREDILDI', 'MUHASEBE_GORDU', 'EKSIK_VAR', 'TAMAM')),
  devreden text NOT NULL,
  devir_ani timestamptz NOT NULL,
  goren text,
  gorme_ani timestamptz,
  tamamlayan text,
  tamamlanma_ani timestamptz,
  bildirim_birakildi boolean NOT NULL DEFAULT false,
  son_alicilar jsonb NOT NULL DEFAULT '[]'::jsonb,
  son_suzulenler jsonb NOT NULL DEFAULT '[]'::jsonb,
  CHECK (durum = 'DEVREDILDI' OR gorme_ani IS NOT NULL),
  CHECK (durum <> 'TAMAM' OR tamamlanma_ani IS NOT NULL)
);

CREATE TABLE mod_m11a.eksik_bilgiler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  alan text,
  ne text NOT NULL CHECK (btrim(ne) <> ''),
  kimden text CHECK (kimden IN ('MUSTERI', 'SATIS', 'DIGER')),
  durum text NOT NULL DEFAULT 'EKSIK' CHECK (durum IN ('EKSIK', 'ISTENDI', 'ALINDI')),
  aciklama text,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz,
  CHECK (durum <> 'ISTENDI' OR kimden IS NOT NULL)
);

CREATE UNIQUE INDEX eksik_bilgiler_alan ON mod_m11a.eksik_bilgiler (proje, alan) WHERE alan IS NOT NULL;

-- Kapsam ya da fiyat değişikliği: güncel tutar ve güncel bütçe
CREATE TABLE mod_m11a.tutar_degisiklikleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  eski_tutar numeric(14,2) NOT NULL,
  yeni_tutar numeric(14,2) NOT NULL CHECK (yeni_tutar >= 0),
  butce_eski jsonb NOT NULL,
  butce_yeni jsonb NOT NULL,
  gerekce text NOT NULL CHECK (btrim(gerekce) <> ''),
  belge bigint NOT NULL REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL,
  bildirim_birakildi boolean NOT NULL DEFAULT false
);

-- Bütçe ölçümü: yalnızca yüzdeler (tutar tutulmaz)
CREATE TABLE mod_m11a.butce_olcumleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  an timestamptz NOT NULL,
  olcen text NOT NULL,
  dolum_yuzde numeric(6,1),
  ilerleme_yuzde numeric(6,1),
  sapma_puan numeric(6,1),
  kapsam text[] NOT NULL DEFAULT '{}',
  esik_puan numeric(5,1) NOT NULL,
  uyari boolean NOT NULL,
  bilinmeyen_saat numeric(10,1) NOT NULL DEFAULT 0
);

CREATE INDEX butce_olcumleri_proje ON mod_m11a.butce_olcumleri (proje, an DESC);

-- Çekirdekte açık duran bildirimlerimiz (kaldırmak için)
CREATE TABLE mod_m11a.acik_bildirimler (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kural text NOT NULL CHECK (kural IN ('TICARI_DEVIR', 'TUTAR_DEGISTI', 'BUTCE_SAPMASI')),
  modul_kaydi text NOT NULL,
  metin text NOT NULL,
  an timestamptz NOT NULL,
  PRIMARY KEY (proje, kural)
);

-- Kesin kabulde kapanış: kalem bazında fark (donmuş)
CREATE TABLE mod_m11a.kapanis_farklari (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  butce numeric(14,2) NOT NULL,
  gerceklesen numeric(14,2),
  fark numeric(14,2),
  kaynak text NOT NULL,
  PRIMARY KEY (proje, kalem)
);

-- Kapanış sonrası düzeltme: kilitten sonra gelen fatura
CREATE TABLE mod_m11a.kapanis_sonrasi_duzeltmeler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  tutar numeric(14,2) NOT NULL,
  gerekce text NOT NULL CHECK (btrim(gerekce) <> ''),
  belge bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL
);

CREATE INDEX dosya_kayitlari_proje ON mod_m11a.dosya_kayitlari (proje, tur);
CREATE INDEX odeme_satirlari_tarih ON mod_m11a.odeme_satirlari (tarih);
CREATE INDEX teminatlar_bitis ON mod_m11a.teminatlar (bitis_tarihi);
CREATE INDEX projeler_musteri ON mod_m11a.projeler (m10_musteri);
```

### `veritabani/002_varsayilanlar.sql`

```sql
-- Varsayılan ayarlar. YETKILI ayarlar ekranından değiştirir.
INSERT INTO mod_m11a.ayarlar (anahtar, deger) VALUES
  ('proje_kodu_deseni',        '"{YY}{AA}{SIRA3}"'),
  ('proje_kodu_sira_kapsami',  '"YIL"'),
  ('siparis_adi_deseni',       '"{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}"'),
  ('sapma_esigi_puan',         '15'),
  ('yaklasan_tarih_gun',       '30');
```

## Ek C · Geliştirme dosyaları

### `gelistirme/ornek_ayarlar.sql`

Yalnızca geliştirme. Teklifte işçiliği olmayan birimler için yedek saat ücretleri.

```sql
-- Yalnızca geliştirme: teklifte işçiliği olmayan birimler için yedek saat ücretleri (örnek firmanın birimleri).
INSERT INTO mod_m11a.saat_ucretleri (birim, ucret, para_birimi) VALUES
  ('PLANLAMA',    1500.00, 'TRY'),
  ('MEK_TASARIM', 1760.00, 'TRY'),
  ('IMALAT',      1408.00, 'TRY');
```

### `gelistirme/ortak_zemin.py`

Ek D.11'deki ortak geliştirme ortamının zemini. Denendi: çıkan zeminle sahte bulut M1.1A'yı kurdu; üç modül aynı projede konuştu.

```python
"""Yalnızca geliştirme: M1.0, M1.1A ve M1.1B'yi aynı sahte bulutta denemek için zemin (SPEC › Ek D.11).

    python gelistirme/ortak_zemin.py <M1.0>/kunye.json <M1.1B>/kunye.json gelistirme/a_ekibi_zemini.json
    python irp_sozlesme/simulator/sunucu.py --kunye kunye.json --zemin gelistirme/a_ekibi_zemini.json --port 8790

Örnek firma + M1.0'ın kurulumu (SATIS rolü, PROJE.ACTIM yetkisi) + M1.1B'nin kurulumu + satış ve muhasebe birimleri,
K050 (satış yöneticisi) ve K060 (muhasebe). M1.1A'yı sahte bulut bu zeminin üstüne kendisi kurar.
"""
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(KOK), str(KOK / 'irp_sozlesme' / 'arac')]

from irp_sozlesme.baglanti.surucu_simulator import SimulatorSurucu  # noqa: E402
from kunye_denetle import kurulum_olaylari  # noqa: E402


def zemin_uret(m10_kunye, m11b_kunye, cikti):
    s = SimulatorSurucu(json.loads(Path(m10_kunye).read_text('utf-8')))

    def y(eylem, girdiler):
        cevap = s.yetkili_olay(eylem, girdiler)
        if cevap.get('sonuc') != 'BASARILI':
            raise SystemExit(f'{eylem} reddedildi: {cevap}')

    for o in kurulum_olaylari(json.loads(Path(m11b_kunye).read_text('utf-8'))):
        y(o['eylem_kodu'], o['girdiler'])
    y('KOD.TANIMLADIM', {'liste': 'ROL', 'kod': 'MUHASEBE', 'ad': 'Muhasebe ve finans', 'aktif': True})
    y('BIRIM.TANIMLADIM', {'kod': 'SATIS', 'ad': 'Satış', 'tur': 'MASA_BASI', 'basi': None, 'ust_birim': 'YONETIM'})
    y('BIRIM.TANIMLADIM', {'kod': 'MUHASEBE', 'ad': 'Muhasebe ve Finans', 'tur': 'MASA_BASI', 'basi': None,
                           'ust_birim': 'YONETIM'})
    y('KISI.EKLEDIM', {'kod': 'K050', 'ad': 'Satış Yöneticisi', 'birim': 'SATIS', 'yaka': 'BEYAZ',
                       'roller': ['YONETICI'], 'giris_tarihi': '2026-01-01'})
    y('KISI.EKLEDIM', {'kod': 'K060', 'ad': 'Muhasebe Uzmanı', 'birim': 'MUHASEBE', 'yaka': 'BEYAZ',
                       'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-01-01'})
    y('KISI.DEGISTIRDIM', {'kisi': 'K050', 'degisenler': {'roller': ['YONETICI', 'SATIS']}, 'gecerli_baslangic': s.simdi()})
    y('KISI.DEGISTIRDIM', {'kisi': 'K060', 'degisenler': {'roller': ['BEYAZ_YAKA', 'MUHASEBE']},
                           'gecerli_baslangic': s.simdi()})
    Path(cikti).write_text(json.dumps(s.senaryo('A_EKIBI_ZEMINI'), ensure_ascii=False), 'utf-8')
    return cikti


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    print(zemin_uret(*sys.argv[1:]))
```

## Ek D · A ekibi modülleri arası sözleşme (M1.0 · M1.1A · M1.1B)

*Bu ek M1.0 ve M1.1A spec'lerinde birebir aynıdır. M1.1B yazıldı (`~/Downloads/m11b`); onun sağladıkları buraya yalnızca başvuru için yazıldı. Bir tarafta değişen alan öbür tarafta da değişir; ikisi ayrı ayrı değiştirilmez.*

### D.1 Kimlikler

| Modül | Kod (geçici) | Cihaz harfi | Servis | Şema | Arka yüz | Ön yüz (vite) | PostgreSQL (docker) |
|---|---|---|---|---|---|---|---|
| M1.0 Teklif hazırlama | `M10` | — (olay yazmaz) | `SRV-M10` | `mod_m10` | 8010 | 5180 | 54330 |
| M1.1A Sipariş ve muhasebeye devir | `M11A` | `Q` | `SRV-M11A` | `mod_m11a` | 8011 | 5181 | 54331 |
| M1.1B Proje ekibine devir | `M11B` | `R` | `SRV-M11B` | `mod_m11b` | 8000 | 5173 | 54329 |

- Kodlar ve harfler geçicidir; kesinini Mustafa verir. "M1.0" künyede geçersizdir (nokta).
- Üç şema üründe aynı Supabase projesindedir. Geliştirmede her modülün kendi PostgreSQL'i olabilir ya da üçü tek bir PostgreSQL'i paylaşır; şemalar çakışmaz.
- Olay kimliği harfle ayrıldığı için iki modülün aynı kişi ve günde verdiği sıra çakışmaz (`K050-2611020001-Q` ve `K050-2611020001-R`, denendi).

### D.2 Ortak sözlük

| Kavram | Değerler | Sahibi |
|---|---|---|
| Bütçe kalemi | `MALZEME`, `ISCILIK`, `FASON`, `GENEL_GIDER` | M1.0'ın maliyet unsuru tek bir kaleme bağlıdır; M1.1A bütçeyi bu dört kalemde tutar |
| Etap kodu | `ACILIS`, `MEK_TASARIM`, `OTO_TASARIM`, `SATIN_ALMA`, `IMALAT`, `MEK_MONTAJ`, `ELK_YAZILIM`, `TEST_FAT`, `SEVK_KURULUM`, `KESIN_KABUL` | M1.1B'nin `etap_sablonu`'su. M1.0'ın `takvim_sablonu`'su aynı kodu, adı, sırayı, paralel grubu ve oranı taşır. Şablonsuz satırda kod boştur |
| Birim (departman) | Çekirdeğin `BIRIMLER` kodları | Çekirdek. Teklifin işçiliği, bütçenin saat ücreti, etabın birimi aynı listedendir |
| Kişi, proje | Çekirdeğin kodları (`K050`, `2611001`) | Çekirdek |
| Para birimi | ISO 4217, üç büyük harf (`TRY`, `EUR`, `USD`) | Modül |
| Kur | `kur_try`: 1 birim kaç TL; yanında `kur_tarihi` | Teklifte girilir, siparişte donar |

**Biçimler:**
- Tutar her zaman ondalık **metin**dir, iki hane: `"56000.00"`. JSON'da sayı (float) olarak gönderilmez.
- Saat bir haneli ondalık metindir: `"120.0"`. Yüzde bir haneli sayıdır: `62.5`; hesaplanamıyorsa `null`.
- Tarih `yyyy-aa-gg`; an ISO 8601, `+03:00`, çekirdeğin saatiyle.
- Hafta tam sayıdır. Hafta 0 sipariş haftasıdır. Tarihe çevirme: başlangıç = sipariş tarihi + 7 × `baslangic_hafta`; bitiş (dahil) = sipariş tarihi + 7 × (`baslangic_hafta` + `sure_hafta`) − 1 gün.
- Yuvarlama yarım yukarıdır (`ROUND_HALF_UP`), her satırın tutarında ayrı ayrı; toplam yuvarlanmış satırların toplamıdır.

### D.3 Bağımlılık yönü

```
M1.0 ──KAZANAN_SURUM──▶ M1.1A ──BASLANGIC_PLANI, TEKLIF_GIRDILERI, BUTCE_YUZDELERI──▶ M1.1B (sonra)
  (kök: hiçbir modüle bağlı değil)    └──PROJE_BUTCESI──▶ M8 (sonra)     M2 (sonra) ◀── TEKLIF_GIRDILERI, M11B.TASARIM_KAPISI
```

- **M1.0 köktür.** Hiçbir modülden okumaz. Döngü yasaktır (R08): M1.1A M1.0'a bağlı olduğu için M1.0 M1.1A'dan, M8'den ya da M3'ten okursa döngü olur.
- Geri besleme (kapanış farkı → öğrenme katmanı, M3'ün gerçek temin süreleri → katalog ortalaması) bu yüzden çekirdek üzerinden gelmelidir. İstekler: M10-03, M11A-06.
- Bağımlılık her zaman isteğe bağlıdır: sağlayan kapalıyken tüketen çalışır, o bilgi için "bilgi yok" der.

### D.4 Taşıma: sağlanan okumanın çağrılması

Çekirdek modüller arası okumayı henüz yönlendirmiyor: `oturum.oku('M10.KAZANAN_SURUM', …)` simülatörde `BICIM: TANIMSIZ_VERI` döner (denendi; istekler M10-02, M11A-02). Faz 1'de sağlayan modül okumayı **kendi arka yüzünde** sunar, M1.1B'nin `/api/saglanan/{ad}` ucuyla aynı biçimde:

```
GET <sağlayanın tabanı>/api/saglanan/<AD>?<parametre>=<değer>
Authorization: Bearer <kullanıcının erişim anahtarı>
```

- **Kullanıcının gözü:** Tüketen, isteği yapan kullanıcının anahtarını olduğu gibi iletir. Sağlayan `cekirdek.oturum(anahtar)` ile açar, kişiyi `KISILER`'den tanır ve kendi görme kuralını uygular. Proje taşıyan okumada önce `PROJE`'yi kullanıcının gözüyle okur. Servis anahtarı ya da modülün kendi kimliği kullanılmaz.
- **Tüketenin tek kapısı:** Tüketen bu çağrıyı tek bir sınıftan yapar (`saglayicilar.py`). Çekirdek yönlendirmeyi verince yalnızca o sınıf değişir.
- **Adres:** Tüketenin ortam değişkeninden (`M11A_SAGLAYICI_M10=http://localhost:8010/api`). Boşsa sağlayan "kapalı" sayılır.
- **Zaman aşımı:** 5 sn; bir kez yeniden denenir.
- **Cevap:** 200 ve okumanın gövdesi. Çekirdek okumalarından biri güncel değilse gövdeye `"hesaplaniyor": true` eklenir.

| Sağlayanın cevabı | Gövde | Tüketen ne yapar |
|---|---|---|
| 200 | Okuma | Kullanır |
| 401 | — | Oturum düşmüş: kullanıcı yeniden girer |
| 403 | `{"kod": "YETKI", "mesaj": …}` | "Bu bilgiyi görme yetkiniz yok" |
| 404 | `{"kod": "BULUNAMADI" \| "TANIMSIZ_VERI", …}` | Kayıt yok ya da okuma yok |
| 409 | `{"kod": "KAPI", "mesaj": …}` | Kapı: ör. sürüm gönderilmemiş, talep kazanılmamış |
| 422 | `{"kod": "DOGRULAMA", …}` | Parametre eksik: tüketenin hatası |
| 5xx, bağlantı hatası, zaman aşımı, adres boş | — | `SAGLAYICI_YOK`: "M1.0'a ulaşılamıyor; bu bilgi şu an yok". Tüketenin geri kalanı çalışır |

### D.5 `M10.KAZANAN_SURUM` (M1.0 sağlar, M1.1A tüketir)

- **Parametre:** `surum` = M1.0'ın teklif sürümü kimliği (tam sayı).
- **Görme:** Kullanıcı M1.0'a erişebilen biri olmalı: `SATIS` ya da `YETKILI` rolü, ya da birimi M1.0'ın `yonetim_birimleri` ayarında. Değilse 403.
- **Kapı:** Sürüm `GONDERILDI`, talep `KAZANILDI` ve talebin `kazanan_surum`'u bu sürüm olmalı. Değilse 409 `KAPI`, `neden`: `GONDERILMEDI` ya da `KAZANILMADI`.
- **Tutarlar donmuştur:** Sürüm gönderildikten sonra değişmediği için cevap her çağrıda aynıdır. `toplamlar` sürümün onayda dondurulan özetinden (`donmus_ozet`) gelir, yeniden hesaplanmaz.
- **Dışarıda kalanlar:** Müşterinin strateji notu ve işlem geçmişi gönderilmez.

Örnek (bu iki spec'teki sınamaların ortak örneği; M1.1A'nın testlerinde `testler/sabitler/M10.KAZANAN_SURUM.json` olarak durur, `pdf.icerik_base64` testte küçük bir PDF'le doldurulur ve `parmak_izi` onun SHA-256'sıdır):

```json
{
 "surum": 57,
 "etiket": "T-2026-0012/V2",
 "talep": 12,
 "talep_no": "T-2026-0012",
 "durum": "GONDERILDI",
 "talep_durumu": "KAZANILDI",
 "kaynak": "YENI_IS",
 "bagli_proje": null,
 "tur": "KURUMSAL_SARTNAME",
 "konu": "710 Projesi Burç Çakma Ekipmanı",
 "makine_turu": "ROBOTIK_HUCRE",
 "musteri": {
  "kimlik": 3,
  "ad": "Autoliv",
  "adres": "Bursa",
  "ulke": "TR",
  "vergi_dairesi": null,
  "vergi_no": null,
  "kisiler": [{"ad": "Ayşe Demir", "unvan": "Satın alma", "telefon": null, "eposta": "ayse@example.com"}]
 },
 "para_birimi": "EUR",
 "kurlar": [{"para_birimi": "EUR", "kur_try": "35.200000", "kur_tarihi": "2026-10-20"}],
 "fiyat": "56000.00",
 "kar_orani": "28.74",
 "fiyat_girisi": "FIYAT",
 "toplamlar": {
  "maliyet": "43500.00",
  "kalemler": {"MALZEME": "32500.00", "ISCILIK": "10000.00", "FASON": "1000.00", "GENEL_GIDER": "0.00"},
  "marj_yuzde": "22.32"
 },
 "kalemler": [
  {"sira": 1, "unsur": "ROBOT", "unsur_adi": "Robot", "butce_kalemi": "MALZEME", "katalog_kodu": "ROB-6E-20", "aciklama": "Robot, 6 eksen, 20 kg",
   "adet": "1.000", "olcu_birimi": "adet", "birim_fiyat": "28000.00", "para_birimi": "EUR", "tutar": "28000.00", "tutar_teklif": "28000.00",
   "kaynak_etiketi": "TEDARIKCI_TEKLIFI", "temin_hafta": 10, "kritik": true},
  {"sira": 2, "unsur": "PLC", "unsur_adi": "PLC ve HMI", "butce_kalemi": "MALZEME", "katalog_kodu": null, "aciklama": "PLC ve HMI seti",
   "adet": "1.000", "olcu_birimi": "adet", "birim_fiyat": "4500.00", "para_birimi": "EUR", "tutar": "4500.00", "tutar_teklif": "4500.00",
   "kaynak_etiketi": "GECMIS_PROJE", "temin_hafta": 6, "kritik": false},
  {"sira": 3, "unsur": "ISIL_ISLEM", "unsur_adi": "Isıl işlem", "butce_kalemi": "FASON", "katalog_kodu": null, "aciklama": "Fikstür ısıl işlem",
   "adet": "1.000", "olcu_birimi": "adet", "birim_fiyat": "35200.00", "para_birimi": "TRY", "tutar": "35200.00", "tutar_teklif": "1000.00",
   "kaynak_etiketi": "TAHMIN", "temin_hafta": 2, "kritik": false}
 ],
 "iscilik": [
  {"birim": "MEK_TASARIM", "saat": "120.0", "saat_ucreti": "1760.00", "para_birimi": "TRY", "tutar": "211200.00", "tutar_teklif": "6000.00"},
  {"birim": "IMALAT", "saat": "100.0", "saat_ucreti": "1408.00", "para_birimi": "TRY", "tutar": "140800.00", "tutar_teklif": "4000.00"}
 ],
 "takvim": [
  {"sira": 1, "etap_kodu": "ACILIS", "ad": "Proje açılışı ve planlama", "paralel_grup": null, "baslangic_hafta": 0, "sure_hafta": 1},
  {"sira": 2, "etap_kodu": "MEK_TASARIM", "ad": "Mekanik tasarım (3D/2D)", "paralel_grup": "TASARIM", "baslangic_hafta": 1, "sure_hafta": 5},
  {"sira": 3, "etap_kodu": "OTO_TASARIM", "ad": "Otomasyon tasarımı (elektrik, PLC/HMI mimarisi)", "paralel_grup": "TASARIM", "baslangic_hafta": 1, "sure_hafta": 7},
  {"sira": 4, "etap_kodu": "SATIN_ALMA", "ad": "Satın alma ve malzeme temini", "paralel_grup": "TEDARIK", "baslangic_hafta": 4, "sure_hafta": 8},
  {"sira": 5, "etap_kodu": "IMALAT", "ad": "İmalat", "paralel_grup": "TEDARIK", "baslangic_hafta": 7, "sure_hafta": 7},
  {"sira": 6, "etap_kodu": "MEK_MONTAJ", "ad": "Mekanik, hidrolik ve pnömatik montaj", "paralel_grup": "MONTAJ", "baslangic_hafta": 13, "sure_hafta": 5},
  {"sira": 7, "etap_kodu": "ELK_YAZILIM", "ad": "Elektrik montajı ve yazılım", "paralel_grup": "MONTAJ", "baslangic_hafta": 14, "sure_hafta": 6},
  {"sira": 8, "etap_kodu": "TEST_FAT", "ad": "Testler, ön deneme ve ön kabul (FAT)", "paralel_grup": null, "baslangic_hafta": 19, "sure_hafta": 3},
  {"sira": 9, "etap_kodu": "SEVK_KURULUM", "ad": "Sevkiyat, saha kurulumu ve devreye alma", "paralel_grup": null, "baslangic_hafta": 22, "sure_hafta": 3},
  {"sira": 10, "etap_kodu": "KESIN_KABUL", "ad": "Kesin kabul", "paralel_grup": null, "baslangic_hafta": 25, "sure_hafta": 1}
 ],
 "takvim_teslim_hafta": 25,
 "en_erken_teslim_hafta": 27,
 "teslim_suresi_hafta": 28,
 "gereksinimler": [{"sira": 1, "metin": "Çevrim süresi 45 sn altında", "belirsiz": false, "cevap": null}],
 "kapsam": {"dahil": ["Mekanik ve otomasyon tasarımı", "Robot ve fikstür", "FAT"], "haric": ["Saha elektrik altyapısı"]},
 "dosyalar": [{"tur": "SARTNAME", "ad": "Autoliv_710_sartname.pdf", "konum": "\\\\sunucu\\satis\\T-2026-0012\\sartname.pdf", "parmak_izi": null}],
 "hazirlayan": "K050",
 "onaylayan": "K001",
 "onay_ani": "2026-10-21T10:00:00+03:00",
 "gonderim_ani": "2026-10-21T14:00:00+03:00",
 "pdf": {"ad": "T-2026-0012-V2.pdf", "parmak_izi": "<icerigin SHA-256'sı, 64 hex>", "icerik_base64": "<PDF>"}
}
```

**Örneğin hesabı** (iki modülün birim testleri bunu doğrular):
- Isıl işlem: 35.200,00 TL ÷ 35,20 = 1.000,00 €. İşçilik: 120 sa × 1.760 TL = 211.200 TL = 6.000,00 €; 100 sa × 1.408 TL = 140.800 TL = 4.000,00 €.
- Maliyet 43.500,00 €. Fiyat 56.000,00 € girildi: kâr oranı (maliyetin üstüne) %28,74; fiyatın yüzdesi olarak marj %22,32.
- Takvim 26 haftalık şablon oranlarıyla kuruldu; teslim noktası (kesin kabul dışındaki en geç bitiş) 25. hafta.
- Robotun temini 10 hafta: satın alma 4. haftada başlar, robot 14. haftada gelir, satın alma 12. haftada biter. Kayma 2 hafta; en erken teslim 27. hafta. Teklifte 28 hafta yazıldı.

### D.6 `M10.KATALOG_TEMIN_SURELERI` (M1.0 sağlar; M2, M3, M4 sonra tüketir)

- Parametre yok. Görme: oturumu olan herkes (`KAYDI_GOREN`). Fiyat yok.
- Cevap: `{"kalemler": [{"kod", "ad", "unsur", "butce_kalemi", "tipik_temin_hafta", "ortalama_temin_hafta": null, "kritik"}]}`. Yalnızca aktif kalemler.
- `ortalama_temin_hafta` Faz 1'de her zaman `null`'dır (M3 bağı yok, M10-03).

### D.7 M1.1A'nın sağladıkları

Dördü de `proje` parametresi alır. Her biri önce `PROJE`'yi kullanıcının gözüyle okur; `YETKI` gelirse 403. Projenin M1.1A kaydı yoksa 404 `BULUNAMADI`. Kayıt `ACILIYOR` durumundaysa 409 `KAPI`.

**`M11A.BASLANGIC_PLANI`** (KAYDI_GOREN). M1.1B başlangıç planını bundan ön doldurur (sonra):

```json
{"proje": "2611001", "kaynak": "T-2026-0012/V2", "siparis_tarihi": "2026-11-02", "teslim_tarihi": "2027-05-16",
 "kesin_kabul_tarihi": "2027-05-23", "teslim_suresi_hafta": 28,
 "etaplar": [{"sira": 2, "etap_kodu": "MEK_TASARIM", "ad": "Mekanik tasarım (3D/2D)", "paralel_grup": "TASARIM",
              "baslangic_hafta": 1, "sure_hafta": 5, "baslangic": "2026-11-09", "bitis": "2026-12-13"}]}
```

Tarihler D.2'deki kuralla hesaplanır, siparişte donar. Örneğin bütün satırları M1.1A spec'inin 8.1'inde.

**`M11A.TEKLIF_GIRDILERI`** (KAYDI_GOREN). M1.1B'nin klasör arşivi ve M2'nin tasarım girdisi için. Maliyet, kâr ve fiyat yoktur:

```json
{"proje": "2611001", "kaynak": "T-2026-0012/V2", "konu": "710 Projesi Burç Çakma Ekipmanı",
 "gereksinimler": [{"sira": 1, "metin": "Çevrim süresi 45 sn altında", "belirsiz": false, "cevap": null}],
 "kapsam": {"dahil": ["…"], "haric": ["…"]},
 "dosyalar": [{"tur": "SARTNAME", "ad": "…", "konum": "…", "parmak_izi": null}],
 "musteri_pdf": {"ad": "T-2026-0012-V2.pdf", "parmak_izi": "…", "yol": "/api/projeler/2611001/teklif-pdf"}}
```

Müşteriye giden PDF'i projeyi gören herkes açabilir (M1.0 › 4. Kurallar, madde 4); `yol` M1.1A'nın arka yüzündedir.

**`M11A.BUTCE_YUZDELERI`** (KAYDI_GOREN). Tutar yoktur; ekip liderleri yalnızca yüzdeleri görür:

```json
{"proje": "2611001", "dolum_yuzde": 6.4, "ilerleme_yuzde": 0.0, "sapma_puan": 6.4, "esik_puan": 15.0,
 "renk": "YESIL", "kapsam": ["ISCILIK"], "olcum_ani": "2026-11-05T15:00:01+03:00", "butce_durumu": "ACIK", "po_bekleniyor": false}
```

- `renk`: `YESIL` (sapma ≤ eşik), `KIRMIZI` (sapma > eşik), `GRI` (dolum ya da ilerleme hesaplanamıyor).
- `kapsam`: dolumun hesabına giren kalemler. Faz 1'de yalnızca `ISCILIK`.
- Her çağrı ölçümü kullanıcının gözüyle yeniden yapar (M1.1A › 8.6).

**`M11A.PROJE_BUTCESI`** (ROL: `SATIS`, `MUHASEBE`, `YETKILI`; para). M8 için:

```json
{"proje": "2611001", "para_birimi": "EUR", "sozlesme_tutari": "56000.00", "guncel_tutar": "50000.00",
 "kalemler": [{"kalem": "ISCILIK", "baslangic": "10000.00", "guncel": "10000.00", "tahmini_gerceklesen": "640.00", "kaynak": "SAAT_X_UCRET"},
              {"kalem": "MALZEME", "baslangic": "32500.00", "guncel": "26500.00", "tahmini_gerceklesen": null, "kaynak": "BILGI_YOK_M3"}],
 "degisiklikler": [{"an": "…", "kim": "K050", "eski_tutar": "56000.00", "yeni_tutar": "50000.00", "gerekce": "Robotu müşteri verecek"}],
 "butce_durumu": "ACIK", "kapanis": null}
```

`kaynak`: `SAAT_X_UCRET`, `BILGI_YOK_M3`, `FORMUL_YOK` (genel gider, S-8). Kapanışta `kapanis`: `{"kesin_kabul_tarihi", "an", "farklar": [{"kalem", "butce", "gerceklesen", "fark"}], "duzeltmeler": [...]}`.

### D.8 M1.1B'nin sağladıkları (yazıldı; başvuru için)

- `M11B.TASARIM_KAPISI {proje}` → `{proje, durum: ACIK | KAPALI, neden: GIRDI_VAR | GECIS | null}`
- `M11B.PROJE_SATIRI {proje}` → projeler listesinin satırı (etap renkleri, açılış listesi x/6, geciken etap sayısı)
- Uç: `GET http://localhost:8000/api/saglanan/{ad}?proje=`.

### D.9 Proje kaydı: M1.1A yazar, M1.1B okur

M1.1A siparişe dönüştürürken kullanıcının gözüyle `PROJE.ACTIM` gönderir. M1.1B'nin ön doldurması bu alanlara dayanır (P0 = `baslangic_tarihi`, P1 = `kesin_kabul_tarihi` ya da `teslim_tarihi`):

| Alan | Değer |
|---|---|
| `kimlik`, `kod` | Proje kodu (ör. `2611001`); ikisi aynı. Kod sonradan değişmez |
| `ad` | Projenin kısa adı (teklifin konusu, kullanıcı düzeltebilir). Uzun sipariş adı çekirdeğe yazılmaz |
| `musteri` | Müşterinin adı (teklifteki `musteri.ad`) |
| `sorumlu` | Proje sorumlusu; varsayılan dönüştüren satış yöneticisi |
| `baslangic_tarihi` | Sipariş tarihi |
| `teslim_tarihi` | Sipariş tarihi + 7 × `teslim_suresi_hafta` − 1 (değiştirilebilir) |
| `kesin_kabul_tarihi` | Takvimde `KESIN_KABUL` varsa onun bitişi + kayma (M1.1A › 8.1); yoksa gönderilmez |
| `ana_proje` | Yalnızca ek iş ve serviste: talebin bağlı projesi. Bir basamak; ana projenin kendi ana projesi olamaz |

Bilinen davranış (denendi): Çekirdek aynı kodu ikinci kez `REDDEDILDI / DURUM` ile reddeder. Projeyi açan, sorumlu olmadıkça projeyi göremez; muhasebe de göremez (M11A-01).

### D.10 Ortak sınama zemini

Simülatörün örnek firmasında satış ve muhasebe yoktur. M1.0 ve M1.1A'nın sözleşme testleri aynı kişileri, aynı sırayla, `surucu.yetkili_olay` ile kurar (senaryoya yazılır; yalnızca sınamada):

```python
def _basarili(cevap, eylem):
    if cevap.get('sonuc') != 'BASARILI':
        raise AssertionError(f'Zemin olayı reddedildi: {eylem} {cevap}')
    return cevap


def a_ekibi_zemini(c, *, satis_rolu_kur=False):
    """M1.0 ve M1.1A testlerinin ortak zemini. M1.0'ın künyesi SATIS rolünü ve PROJE.ACTIM yetkisini kendisi
    kurar; M1.1A'nın testinde M1.0 kurulu olmadığı için satis_rolu_kur=True ile elle kurulur."""
    s = c.surucu
    s.saat('2026-11-02T09:00:00+03:00')
    y = lambda e, g: _basarili(s.yetkili_olay(e, g), e)
    if satis_rolu_kur:
        y('KOD.TANIMLADIM', {'liste': 'ROL', 'kod': 'SATIS', 'ad': 'Satış yöneticisi', 'aktif': True})
        y('YETKI.TANIMLADIM', {'eylem_kodu': 'PROJE.ACTIM', 'kimler': ['SATIS'], 'kapsam': 'FIRMA'})
    y('BIRIM.TANIMLADIM', {'kod': 'SATIS', 'ad': 'Satış', 'tur': 'MASA_BASI', 'basi': None, 'ust_birim': 'YONETIM'})
    y('BIRIM.TANIMLADIM', {'kod': 'MUHASEBE', 'ad': 'Muhasebe ve Finans', 'tur': 'MASA_BASI', 'basi': None, 'ust_birim': 'YONETIM'})
    y('KISI.EKLEDIM', {'kod': 'K050', 'ad': 'Satış Yöneticisi', 'birim': 'SATIS', 'yaka': 'BEYAZ',
                       'roller': ['YONETICI'], 'giris_tarihi': '2026-01-01'})
    y('KISI.EKLEDIM', {'kod': 'K060', 'ad': 'Muhasebe Uzmanı', 'birim': 'MUHASEBE', 'yaka': 'BEYAZ',
                       'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-01-01'})
    y('KISI.DEGISTIRDIM', {'kisi': 'K050', 'degisenler': {'roller': ['YONETICI', 'SATIS']}, 'gecerli_baslangic': c.simdi()})
    # MUHASEBE rolü yalnızca M1.1A kuruluysa vardır:
    if 'MUHASEBE' in {r['kod'] for r in c.kunye.get('roller', [])}:
        y('KISI.DEGISTIRDIM', {'kisi': 'K060', 'degisenler': {'roller': ['BEYAZ_YAKA', 'MUHASEBE']},
                               'gecerli_baslangic': c.simdi()})
```

- `BIRIM.TANIMLADIM`'da `tur` yalnızca `ATOLYE` ya da `MASA_BASI` olabilir; başka değer `DURUM: Bulut kapisi kapali` alır (denendi).
- `KISI.EKLEDIM` yalnızca çekirdeğin beş rolünü kabul eder; modülün rolü `KISI.DEGISTIRDIM` ile sonradan verilir (denendi).
- Örnek firmanın kişileri: K001 Genel Müdür (`YETKILI`), K004 Planlama Müdürü (`YONETICI`), K012 Tasarım Müdürü (`YONETICI`), K041 Tasarım Mühendisi, K017 atölye çalışanı.

### D.11 Ortak geliştirme ortamı (isteğe bağlı)

Üç modülü aynı sahte çekirdekte birlikte denemek içindir; modüllerin kendi testleri buna dayanmaz.

- **Sorun:** Sahte bulut tek künye kurar. Örnek firmada satış ve muhasebe yoktur. Sahte bulutta yetkili olayı yazacak bir uç yoktur.
- **Çözüm (denendi):** M1.1A'nın `gelistirme/ortak_zemin.py` betiği bir zemin dosyası üretir:
  1. `SimulatorSurucu(M1.0'ın künyesi)` açar; böylece M1.0 kurulur (SATIS rolü, PROJE.ACTIM yetkisi).
  2. M1.1B'nin künyesinden `kunye_denetle.kurulum_olaylari(...)` ile kurulum olaylarını yazar.
  3. `MUHASEBE` rolünü (`KOD.TANIMLADIM`) ve D.10'daki birimleri ve kişileri yazar; K060'a `MUHASEBE`'yi verir.
  4. `surucu.senaryo('A_EKIBI_ZEMINI')`'ni `gelistirme/a_ekibi_zemini.json`'a yazar. Bu dosya örnek firma girdisiyle aynı biçimdedir.
- **Çalıştırmak:** `python irp_sozlesme/simulator/sunucu.py --kunye kunye.json --zemin gelistirme/a_ekibi_zemini.json --port 8790` (M1.1A'nın klasöründen). M1.1A zeminin üstüne kurulur; `MUHASEBE`'nin yeniden tanımı reddedilmez (denendi).
- **Üç arka yüz** aynı `IRP_TABAN=http://localhost:8790`'a bağlanır. Her modül kendi servis anahtarını kendisi üretemez; sahte bulutun yazdığı `IRP_SERVIS` yalnızca M1.1A'nındır.
- **Bilinen sınır:** Bu ortamda M1.1B'nin bildirimi `YETKI: Servis kimliği` alır (denendi). M1.1B bunu zaten tolere eder: plan geri alınmaz, kural işi telafi eder. İstek M11A-08.
- **Denendi:** M1.0 kişileri ve birimleri okudu; M1.1A `2611001`'i açtı ve bildirim bıraktı; M1.1B aynı projeye etap yazıp `PLAN.ONAYLADIM` gönderdi.
- **Oturum:** Modüllerin ön yüzleri ayrı adreslerde çalıştığı için geliştirme girişi her modülde ayrı yapılır. Üründe tek giriş çekirdeğindir.

### D.12 Ortak görünüş

Kullanıcı tek sistem görür (`07_on_yuz.md` › 1). M1.1B'nin görsel dili esastır: teknik resim kâğıdı zemin, lacivert mürekkep, Barlow ailesi. M1.0 ve M1.1A `on_yuz/src/stil.css`'in başına bu değişkenleri aynen koyar ve bileşenleri bunlarla yazar:

```css
:root {
  --kagit: #eef1f4;  --yuzey: #ffffff;  --murekkep: #1b2a3a;  --ikincil: #55667a;
  --cizgi: #c3ccd6;  --celik: #7a8c9e;  --izgara: #dde3ea;
  --eylem: #1f5fae;  --eylem-koyu: #174a88;
  --yesil: #2e7d4f;  --kirmizi: #b8322a;  --sari: #b57a0c;  --gri: #8a94a0;
  --uyari-zemin: #fff5e0;  --hata-zemin: #fdecea;
  --yazi: 'Barlow', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --baslik: 'Barlow Condensed', 'Barlow', system-ui, sans-serif;
  color-scheme: light;
}
body { background: var(--kagit); color: var(--murekkep); font: 16px/1.5 var(--yazi); }
h1, h2, h3 { font-family: var(--baslik); font-weight: 600; }
.ust { background: var(--murekkep); color: #fff; }            /* üst çubuk */
button { border: 1px solid var(--eylem); background: var(--eylem); color: #fff; border-radius: 4px; }
button.ikinci { background: var(--yuzey); color: var(--eylem); }
.pano { background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 4px; }
.hata { background: var(--hata-zemin); border-left: 4px solid var(--kirmizi); }
.uyari { background: var(--uyari-zemin); border-left: 4px solid var(--sari); }
td.sayi, th.sayi { text-align: right; font-variant-numeric: tabular-nums; }
```

- **Yazı tipi:** Google Fonts'tan Barlow 400/500/600 ve Barlow Condensed 500/600 (M1.1B'nin `index.html`'indeki bağlantı).
- **Üst çubuk:** Lacivert; solda "Sibernetik IRP · <modülün kısa adı>", sağda kişinin adı ve kodu.
- **Dil ve biçim:** Türkçe; tarih `gg.aa.yyyy`; tutar `56.000,00 €` (binlik nokta, ondalık virgül, para biriminin simgesi ya da kodu).
- **Renk ve simge:** Renk her zaman yazı ve simgeyle birlikte gösterilir: ● yolunda, ▲ gecikti ya da eşik aşıldı, ○ hesaplanamıyor.
- **Ön yüzün API kapısı:** M1.1B'nin `api.ts`'iyle aynı kalıp; anahtar `sessionStorage`'da `m10_anahtar` ya da `m11a_anahtar` olarak durur.
