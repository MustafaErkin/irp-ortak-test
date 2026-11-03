# SPEC · M1.0 Teklif hazırlama · Faz 1

*Modül kodu (geçici): `M10` · Paket: `irp_sozlesme` 1.0 · çekirdek 10.2 · 29 Ekim 2026*

*Kaynaklar:*
- *A ekibi çıktısı `M1.0_teklif_hazirlama.md` (15 Ekim) ve kaynak akışı `yazilim_akislari/M1.0_teklif_hazirlama.md`.*
- *IRP Karar Haritası: M1.0 kartı, kapılar ve modüller arası arayüzler.*
- *M1.1A çıktısındaki "ortak katalog eki". Yazılmış M1.1B modülü (`~/Downloads/m11b`) ve onun SPEC'i.*

*Bu belgedeki çekirdek davranışları paketteki simülatörde denenerek yazıldı. M1.0, M1.1A ve M1.1B aynı sistemde çalışır; aralarındaki sözleşme Ek D'dedir ve M1.1A'nın SPEC'inde birebir aynıdır.*

---

## 0. Bu belgeyi okuyan Claude Code için

- **Yalnızca M1.0'ı yaz.** M1.1A, M1.1B ya da başka bir modülün kodunu yazma. Onlarla konuşma yalnızca Ek D'deki sözleşmeyle olur.
- **Önce sözleşmeyi oku:** Çekirdekle ilgili her işten önce `irp_sozlesme/BASLA.md`'yi ve oradaki okuma sırasını oku. `irp_sozlesme/` içindeki hiçbir dosyayı değiştirme.
- **Öncelik:** `irp_sozlesme/` kuralları bu belgeden önce gelir. Bu belge sözleşmeyle çelişirse sözleşmeye uy, çelişkiyi `istekler/` altına yaz ve modülün sahibine söyle.
- **Etrafından dolaşma:** Çekirdek bir şeyi vermiyorsa taklit etme, başka yoldan alma (BASLA › Kural 10). Bilinen eksikler bölüm 13'te; istek dosyalarını sen yazarsın.
- **Kök talimat:** Modülün köküne `CLAUDE.md` koy. İçine `irp_sozlesme/BENIOKU.md` › 2'deki dört satırı ve "Modülün tarifi `SPEC.md`'dedir" satırını yaz.
- **Ekler doğrulandı:**
  - Ek A'daki künye `kunye_denetle.py`'den 0 hata ve 1 beklenen uyarıyla geçti. M1.1A ve M1.1B künyeleriyle birlikte kayıt denetiminde de 0 hata verdi.
  - Ek B'deki göçler G01–G09 denetiminden geçti ve PostgreSQL 17'de koştu.
  - Ek D.10'daki sınama zemini bu künyeyle simülatörde koştu.
  - Bunlardan başla.

---

## 1. Ne ve neden

M1.0, müşterinin bizimle ilk temasından onaylı teklifin müşteriye gönderilmesine kadar olan işi taşır. Teklifi **satış yöneticisi** hazırlar, **CEO** (yönetim) onaylar. Sipariş gelince proje M1.1A'da açılır. M1.1A kazanan teklifin maliyetini başlangıç bütçesi, takvimini başlangıç planı olarak M1.0'dan alıp dondurur.

**Öncelikler (kullanıcının kararı):**
1. Benzer işi bulmak.
2. Doğru maliyet tahmini.
3. Gerçekçi teslim süresi.

Teklif takibi ve onay ikinci planda.

**Başarı şöyle görünür:**
- Satış yöneticisi bir talebi açar, eski bir teklifi kopyalayarak V1'i birkaç dakikada kurar.
- Her maliyet kaleminin yanında kaynağı (tedarikçi teklifi, geçmiş proje, tahmin) ve temin süresi görünür. İşçilik satırının yanında başlangıç tablosunun ve geçmiş projelerin önerisi durur.
- Takvim, uzun teslimli kalemi hesaba katarak "en erken teslim"i söyler. Teklife bundan kısa süre yazılamaz.
- Kâr oranı ve fiyat birbirinden hesaplanır. Ekranda kârın iki anlamı da görünür.
- Onaylanmamış teklif müşteriye gönderilemez.
- CEO telefonundan özeti görüp onaylar ya da gerekçeyle geri gönderir.
- Gönderilmiş sürüm değişmez. Düzeltme yeni sürümdür.
- Kazanılan sürüm tek tıkla M1.1A'nın "siparişe dönüştür" penceresine geçer.

---

## 2. Kapsam

### 2.1 Faz 1'de var

1. **Müşteriler:** firma, iletişim kişileri, adres, vergi bilgisi, strateji notu.
2. **Talep:**
   - kaynak (yeni iş, ek iş, servis; ek iş ve serviste bağlı proje)
   - tür
   - makine türü
   - geliş ve beklenen cevap tarihi
   - dosya kayıtları, gereksinim listesi, kapsam (dahil, hariç)
   - "teklif vermiyoruz" kapanışı
   - müşterinin cevabı: kazanıldı, kaybedildi ve nedeni, beklemede
3. **Teklif sürümü** (V1, V2…): boş başlatma, aynı talebin ya da eski bir talebin sürümünden kopyalama. Dört bölüm:
   - maliyet
   - işçilik
   - takvim
   - fiyat
4. **Maliyet:**
   - unsur → kalem; katalogdan çekme ya da elle girme; "Diğer" ile yeni unsur
   - kaynak etiketi, temin süresi, kritik işareti
   - her kalemde para birimi; sürüm başına kurlar
5. **İşçilik:** birim (departman) başına saat. Öneri yanında durur: başlangıç tablosu ve geçmiş proje ortalaması. Saat ücreti ayarlardan gelir.
6. **Takvim:**
   - şablondan ön doldurma (M1.1B'nin etap listesiyle ortak, Ek D.2)
   - basit Gantt
   - uzun teslimli kalemle "en erken teslim"
7. **Fiyat:** maliyet, kâr oranı, fiyat. Biri girilir, öbürü hesaplanır.
8. **Teklif PDF'i:** taslak ve onaylı. Maliyet ve kâr PDF'e girmez.
9. **Onay:**
   - onaya gönder
   - onayla / kendim düzelt / gerekçeyle geri gönder
   - düzenlemeye aç
   - telefondan onay sayfası
   - "Onayınızı bekleyen teklifler" şeridi
10. **Kapı:** Onaylanmamış teklif gönderilemez; geçiş yolu yok. Gönderim kaydı modülde tutulur; modül e-posta göndermez.
11. **Talepler listesi:**
    - basit arama (müşteri, makine türü, anahtar kelime)
    - sayaç şeridi (kazanılan, kaybedilen, kayıp nedenleri)
    - cevap tarihi yaklaşan talepte işaret
12. **Ayarlar ve geçmiş veri:**
    - maliyet unsurları ve bütçe kalemi
    - kalem kataloğu
    - makine türleri ve başlangıç tablosu
    - saat ücretleri
    - takvim şablonunun birimleri
    - firma bilgileri ve varsayılan metinler
    - geçmiş proje formu
13. **İşlem geçmişi ve bilgi havuzu:** Her değişiklik için kim, ne, ne zaman. Onaycının düzeltmeleri ayrıca işaretlenir.
14. **Sağlanan iki okuma:** `M10.KAZANAN_SURUM` (M1.1A için) ve `M10.KATALOG_TEMIN_SURELERI` (Ek D.5, D.6).
15. **Kazanılan sürümden** M1.1A'nın dönüştürme penceresine geçiş.

### 2.2 Faz 1'de yok

- **Yapay zekâ:** şartname okuma, benzer teklif bulma, metin taslağı, emsal maliyet, sapma uyarısı. Gizlilik izni (soru 7) ve veri birikimi bekleniyor.
- **Öğrenme katmanı:** Kapanan projenin gerçek saatleri ve maliyeti öneriyi kendiliğinden beslemez. Geri besleme döngüye takılıyor (Ek D.3, istek M10-03, M10-04). Faz 1'de öneri, başlangıç tablosu ve elle girilen geçmiş proje formundan gelir.
- **Ortalama temin süresi (M3'ten):** Alanı vardır, değeri her zaman "bilgi yok"tur (M10-03).
- **Atölye doluluğunun takvime katılması.**
- **Eski tekliflerin sisteme taşınması** (S-20).
- **Çekirdeğin bildirim kutusu:** Onay bekleyen teklif ve cevap tarihi hatırlatması oraya düşmez. Projesiz kayda bildirim yok (M10-01). Faz 1'de modülün ekranında iş listesi ve işaret olarak durur.
- **PDF'i e-postayla göndermek:** İletişim modülünün işi. Kullanıcı PDF'i indirir, kendisi gönderir, "gönderildi" der.
- **Kapsam, maliyet ve fiyatın ayrı ayrı onaylanması** (görsel önerisi).
- **Onaylı fiyatlama kuralı** (kim hangi marjı verebilir).
- **İşçilik saatlerinin departman liderlerine dağıtılması** (S-8a). Faz 1'de satış yöneticisi girer.
- **AR-GE'nin üç türü ve dönemsel raporlar** (askıda). AR-GE tek talep türüdür.
- **Kazanılan talebin hangi projeye dönüştüğünü göstermek:** M1.0 M1.1A'dan okuyamaz (döngü). İstek M11A-06.

### 2.3 Yapılmayacaklar

Aşağıdakilerden biri olursa testler geçse bile iş yanlıştır:
- **Teklifi çekirdeğe projesiz nesne olarak açmak.** Projesiz nesneyi mavi yaka dahil herkes görür (K-30). Teklif modülde kalır.
- **Maliyeti ya da kârı** M1.0'a erişimi olmayan birine göstermek; PDF'e ya da `M10.KATALOG_TEMIN_SURELERI`'ne koymak.
- **Gönderilmiş sürümü değiştirmek.** Düzeltme yeni sürümdür.
- **Onaylanmamış sürümü** "gönderildi" yapmak. Hiçbir rol bu kapıdan geçemez.
- **Kişi, birim ya da proje bilgisini** modülün tablosunda ikinci kez tutmak. Kişi ve birim kodu değer olarak tutulur, adı ekranda `KISILER` ve `BIRIMLER`'den okunur.
- **Çekirdeğin maaş ya da saat maliyetini** okumak ya da taklit etmek. Teklifin saat ücreti modülün kendi varsayımıdır (karar 104).
- **Başka modülden okumak** (M1.1A, M3, M8…). M1.0 köktür (Ek D.3).
- **Ayrı bir bildirim kutusu kurmak.** İş listeleri ekrandadır; çan, sayaç rozeti ve açılır bildirim yoktur.
- **Çekirdeğe `irp_sozlesme.baglanti` dışından gitmek;** çekirdeğin şemalarına SQL yazmak.

---

## 3. Kimlik

| Alan | Değer | Not |
|---|---|---|
| `kod` | `M10` | **Geçici.** "M1.0" künyede geçersiz (nokta). Kesin kodu Mustafa verir |
| `cihaz_harfi` | — | M1.0 çekirdeğe olay yazmaz; harf almaz |
| `olay_yolu` | `YOK` | |
| `arka_yuz` | `true` | Modülün kendi sunucusu var; servis gözü kullanılmaz |
| `servis_kimligi` | `SRV-M10` | |
| Şema | `mod_m10` | |
| `on_yuz.tur` | `AYRI_UYGULAMA` | Ekranların yolu (S1) kesinleşmedi; katmanlar ayrı tutulur |
| Rol | `SATIS` (Satış yöneticisi) | M1.0'ın rolü. M1.1A da kullanır, bu yüzden M1.0'a bağımlıdır |

Kod değişince künye, göçlerdeki şema adı ve ayar değişir. Python kodunda `M10` ve `mod_m10` tek bir ayar sabitinden okunur.

---

## 4. Teknoloji ve klasör düzeni

### 4.1 Yığın

M1.1B ile aynı yığın. Üç modül aynı ekip tarafından aynı biçimde bakılsın diye.

| Katman | Seçim |
|---|---|
| Dil | **Python 3.15** (makinede uv ile kurulu, 3.15.1). Sanal ortam: `uv venv --python 3.15`. `pyproject.toml`'da `requires-python = ">=3.11"` |
| Arka yüz | FastAPI, Pydantic v2, psycopg 3 (`psycopg[binary,pool]`), uvicorn (eksiz; `uvicorn[standard]`'ın ekleri 3.15 için hazır derlemeli değil). ORM yok; SQL elle ve parametreli. Para `decimal.Decimal`; float yok |
| PDF | **fpdf2** (saf Python; 2.8.9 ve pillow 3.15'te hazır derlemeyle kuruldu, Türkçe karakter denendi). Yazı tipi Barlow ve Barlow Condensed TTF (SIL OFL). `github.com/google/fonts` deposundan indirilip `m10/pdf/yazitipi/`'ne lisansıyla birlikte konur |
| Veritabanı | PostgreSQL. Üründe Supabase'te `mod_m10`. Geliştirmede yerel PostgreSQL 16 ya da 17 (Homebrew `postgresql@17` ya da Docker) |
| Ön yüz | React 18, TypeScript, Vite, react-router. UI kütüphanesi yok. Takvimin Gantt'ı düz SVG. Görünüş M1.1B ile ortak (Ek D.12) |
| Test | pytest (arka yüz), vitest (ön yüzün saf yardımcıları) |

**Katman kuralı** (`07_on_yuz.md` › 2): ekran → modülün arka yüzü → bağlantı katmanı. Ön yüz çekirdeği hiç çağırmaz.

### 4.2 Klasör düzeni

```
<modül kökü>/
  irp_sozlesme/          paket; değiştirilmez
  CLAUDE.md  SPEC.md  kunye.json (Ek A)  pyproject.toml
  veritabani/            001_m10.sql, 002_varsayilanlar.sql (Ek B)
  m10/                   arka yüz
    ayarlar.py           ortam değişkenleri; KOD, SEMA
    baglanti.py          Cekirdek.ac; uygulamada tek örnek
    vt.py                bağlantı havuzu, işlem yardımcısı
    depo/                tablolara SQL
    alan/                iş kuralları: hesap (maliyet, kur, fiyat), takvim, oneri, durum (talep ve sürüm),
                         dogrulama, arama, kopyalama, yetki, saglanan
    pdf/                 teklif PDF'i ve yazitipi/
    api/                 FastAPI yönlendiricileri, şemalar, hata eşleme
    komutlar.py          python -m m10.komutlar <komut>
  testler/               pytest; çekirdeğe karşı olanlar simülatörle
  senaryolar/  istekler/  on_yuz/
  gelistirme/            docker-compose.yml, sema_ac.sql, ornek_veriler.sql (Ek C), BENIOKU.md
  TESLIM.md
```

- `gelistirme/sema_ac.sql` yalnızca yerelde `CREATE SCHEMA mod_m10` yapar. Göçte şema açmak yasaktır (G03).
- **Saf fonksiyonlar** (`alan/hesap.py`, `alan/takvim.py`, `alan/oneri.py`, `alan/durum.py`, `alan/arama.py`) veritabanına ve çekirdeğe dokunmaz. Birim testleri bunları sınar.

### 4.3 Ortam değişkenleri

| Değişken | Ne |
|---|---|
| `IRP_CEKIRDEK`, `IRP_TABAN`, `IRP_ANON`, `IRP_SERVIS` | Bağlantı katmanının sürücüsü; kodda okunmaz |
| `M10_VERITABANI`, `M10_TEST_VERITABANI` | PostgreSQL adresleri (docker: `localhost:54330`) |
| `M10_KUNYE` | Künyenin yolu; varsayılan `kunye.json` |
| `M10_GELISTIRME` | `1` ise geliştirme girişi açılır. Üründe yok |
| `VITE_M11A_ADRES` | Ön yüzde "Siparişe dönüştür"ün gideceği M1.1A ön yüzü (geliştirmede `http://localhost:5181`). Boşsa düğme yerine açıklama görünür |

---

## 5. Sınır: ne nerede

| Kavram | Nerede | Nasıl |
|---|---|---|
| Kişi, rolü, birimi | Çekirdek | `KISILER`; istek başına bir kez okunur |
| Departman listesi | Çekirdek | `BIRIMLER`. İşçilik, başlangıç tablosu, saat ücreti ve takvim şablonu birim kodunu değer olarak tutar ("ortak katalog zorunlu") |
| Bağlı proje (ek iş, servis) | Çekirdek | Kullanıcının gözüyle `PROJE` okunur; yalnızca kodu tutulur |
| Müşteri, talep, sürüm, kalem, işçilik, takvim, fiyat, PDF | Modül | `mod_m10` (bölüm 7) |
| Maliyet unsuru ve bütçe kalemi | Modül | `maliyet_unsurlari.butce_kalemi`. Bütçe kalemleri Ek D.2'de ortak |
| Etap listesi | Modül (kopya) | `takvim_sablonu`: M1.1B'nin şablonuyla aynı kodlar. Çekirdekte ortak liste olsun diye istek M10-03 |
| Proje açılışı | M1.1A | M1.0 projeyi açmaz. `PROJE.ACTIM` yetkisini `SATIS`'e öneren M1.0'dır, çünkü rolün sahibi odur (V17) |
| Kazanan sürümün donmuş kopyası | M1.1A | M1.0 `M10.KAZANAN_SURUM`'u sağlar (Ek D.5) |

**Saat:** Modülün kayıtlarındaki anlar `cekirdek.simdi()`'den alınır (`+03:00`). Talep numarasının yılı da oradan.

---

## 6. Roller ve yetki

M1.0 çekirdeğe olay yazmaz. Bütün yetki modülün kendi kuralıdır. Kişinin rolü ve birimi `KISILER`'den okunur.

**M1.0'a erişim:** `SATIS` ya da `YETKILI` rolü, ya da birimi `yonetim_birimleri` ayarında olan kişi (varsayılan `["YONETIM"]`). Erişimi olmayanın her isteği 403 alır. İstisna `M10.KATALOG_TEMIN_SURELERI`'dir; onu oturumu olan herkes okur.

| İş | Kim |
|---|---|
| Talepleri, sürümleri, maliyeti ve kârı görmek | M1.0'a erişimi olan herkes ("maliyeti ve kârı yalnızca satış yöneticisi, CEO ve yönetim görür") |
| Müşteri, talep, `TASLAK` sürüm: açmak ve düzenlemek | `SATIS`, `YETKILI` |
| Onaya göndermek | `SATIS`, `YETKILI` |
| Onaylamak, kendim düzeltmek, geri göndermek | `YETKILI` (onaycı). S-8b cevaplanınca ayar olur (bölüm 18) |
| Düzenlemeye açmak (`ONAYLANDI` → `TASLAK`) | Sürümü hazırlayan, `YETKILI` |
| Gönderildi demek | `SATIS`, `YETKILI` |
| Müşterinin cevabını yazmak; talebi kapatmak | `SATIS`, `YETKILI` |
| `KAYBEDILDI` ya da `KAPATILDI` talebi geri açmak | `YETKILI` |
| Ayarlar ve geçmiş proje formu | `SATIS`, `YETKILI`, yönetim birimleri. `yonetim_birimleri`'ni yalnızca `YETKILI` değiştirir |

- **Hazırlayan ile onaycı aynı kişi olabilir:** CEO kendi teklifini onaylayabilir (S-8b cevaplanana kadar). Kayıtta ve onay ekranında "Hazırlayan ve onaylayan aynı kişi" yazar.
- **Rol yoksa:** Örnek firmada `SATIS` kimsede yok. Sınamada D.10'daki K050'ye verilir.

---

## 7. Kayıtlar (modülün tabloları)

SQL'in tamamı Ek B'de. Çekirdeğin kimlikleri `text` olarak, değer olarak tutulur.

| Tablo | Ne tutar |
|---|---|
| `ayarlar`, `sayaclar` + `sayac_ilerlet()` | Anahtar–değer ayarlar; talep numarasının yıllık sırası (tek işlemle artar) |
| `para_birimleri` | `TRY`, `EUR`, `USD`… |
| `maliyet_unsurlari` | Unsur, bütçe kalemi, sık/ara sıra, aktif |
| `katalog_kalemleri` | Tekrar kullanılan kalem: fiyat, para birimi, fiyatın tarihi ve kaynağı, tipik temin süresi, kritik |
| `makine_turleri`, `baslangic_tablosu` | Makine türü × birim → tipik saat ve süre (8a); türün tipik toplam süresi |
| `saat_ucretleri` | Birim başına teklif saat ücreti (varsayım) |
| `takvim_sablonu` | On etap: kod, ad, sıra, paralel grup, oranlar (M1.1B ile aynı) ve firmanın birim eşlemesi |
| `gecmis_projeler`, `gecmis_proje_saatleri` | Kapanmış projelerin birim bazında gerçek saatleri, elle (8b) |
| `musteriler`, `musteri_kisileri` | Müşteri ve iletişim kişileri (kişisel veri, beyanlı) |
| `talepler` | Talep: numara, müşteri, kaynak, bağlı proje, tür, makine türü, konu, tarihler, durum, kazanan sürüm, kayıp nedeni, kapatma gerekçesi, arama metni |
| `talep_dosyalari` | Dosyanın kaydı: tür, ad, konum, parmak izi. Dosyanın kendisi şirket sunucusunda |
| `gereksinimler`, `kapsam_satirlari` | Gereksinim listesi (belirsiz, soru, cevap); kapsam dahil ve hariç |
| `teklif_surumleri` | Sürüm: durum, para birimi, kâr, fiyat, süreler, metinler, hazırlayan, onaylayan, gönderim, PDF, donmuş özet |
| `surum_kurlari` | Sürümün kurları: 1 birim kaç TL, kur tarihi |
| `maliyet_kalemleri`, `iscilik_satirlari`, `takvim_satirlari` | Sürümün dört bölümünden üçü; fiyat sürümün kendisinde |
| `onay_kayitlari` | Onaya gönderme, onay, düzeltme isteği, onaycı düzeltmesi, düzenlemeye açma (bilgi havuzu) |
| `islem_gecmisi` | Her değişiklik: kim, ne, ne zaman, ayrıntı (alan, eski, yeni) |

**Değişmezler:**
- Bir talepte en çok bir gönderilmemiş sürüm olur (kısmi tekil dizin).
- Gönderilmiş sürüm satırı değişmez (tetikleyici). Çocuk satırları (kalem, işçilik, takvim, kur) yalnızca sürüm `TASLAK` ya da `ONAY_BEKLIYOR` iken değişir (modülün kuralı, testle).
- `ONAYLANDI` ve `GONDERILDI` sürümde onaylayan, onay anı, PDF ve donmuş özet doludur.
- `KAZANILDI` talepte kazanan sürüm, `KAYBEDILDI`'de neden, `KAPATILDI`'da gerekçe zorunludur.
- Sürüm silinmez.

**Kişisel veri ve para:**
- Müşteri iletişim kişileri kişisel veridir ve künyede beyanlıdır.
- Modül çalışanların yalnızca kodlarını tutar.
- Modül para tutar (`para: true`). Çekirdekten para okumaz.

---

## 8. Akışlar

### 8.1 Müşteri

- **Alanlar:**
  - ad (zorunlu), kısa ad, adres, ülke, vergi dairesi, vergi no
  - iletişim kişileri: ad, unvan, telefon, e-posta
  - strateji notu
- **Strateji notu:** CEO'nun yönlendirmesi için serbest metin (ör. "bu firmaya iyi fiyat ver"). Sistem buna göre hesap yapmaz. Yalnızca M1.0 ekranlarında görünür; `M10.KAZANAN_SURUM`'a ve PDF'e girmez.
- **Silinmez;** pasifleştirilir.
- **Aynı ada sahip müşteri:** Yeni müşteri kaydedilirken normalize adı aynı olan varsa uyarı gelir ("Bu adla bir müşteri var"); kullanıcı yine de kaydedebilir.

### 8.2 Talep

- **Açmak:**
  - müşteri
  - kaynak: `YENI_IS`, `EK_IS`, `SERVIS`
  - tür: `KURUMSAL_SARTNAME`, `SAHA_NOTU`, `ARGE`
  - makine türü
  - konu
  - açıklama
  - geliş tarihi (varsayılan bugün)
  - beklenen cevap tarihi
- **Talep numarası:** Sistem verir: `T-{YYYY}-{SIRA4}` (`talep_no_deseni`), ör. `T-2026-0012`. Sıra yıl başına `sayac_ilerlet('TALEP', '2026')` ile tek işlemde artar. Numara değişmez.
- **Ek iş ve servis:** Bağlı proje zorunludur.
  - Kullanıcı proje kodunu yazar. `PROJELER` simülatörde yok, liste gösterilemez (M10-06).
  - Modül kodu kullanıcının gözüyle `PROJE` ile okur. Okuyabilirse proje kodunu ve adını gösterir, kodu saklar.
  - `YETKI` gelirse 403: "Bu projeyi göremiyorsunuz; bağlamak için projede erişiminiz olmalı." Satış yöneticisi çoğu projeyi göremez (UYELER, denendi); istek M10-06 ve M11A-01.
- **Dosyalar:**
  - tür: şartname, fotoğraf, video, saha notu, tedarikçi teklifi, çizim, diğer
  - ad, konum (sunucudaki yol ya da bağlantı; zorunlu), açıklama
  - parmak izi (isteğe bağlı; ön yüz SubtleCrypto ile SHA-256 hesaplar, dosya yüklenmez)
  - Dosya kaydı silinmez. M1.1B ile aynı ilke; istek M10-05.
- **Gereksinim listesi:**
  - sıralı satırlar: metin, "belirsiz" işareti, müşteriye sorulan soru, cevap
  - Belirsiz ve cevapsız satır sayısı talep kartında görünür.
- **Kapsam:** dahil ve hariç, sıralı satırlar.
- **"Teklif vermiyoruz":** Gerekçe zorunlu. Talep `KAPATILDI` olur. Yalnızca `ACIK` ya da `BEKLEMEDE` talepte.
- **Arama metni:** Talep, gereksinim, kapsam ya da en son sürümün kalemleri kaydedildiğinde `arama` sütunu yeniden kurulur (8.13).

### 8.3 Sürüm

- **Yeni sürüm:** Talep `ACIK`, `TEKLIF_VERILDI` ya da `BEKLEMEDE` iken, talepte gönderilmemiş sürüm yokken açılır. Numara talebin en büyük numarası + 1.
- **Başlangıç seçenekleri:**
  - **Boş:**
    - Para birimi `varsayilan_para_birimi`, geçerlilik `varsayilan_gecerlilik_gun`.
    - Metinler `varsayilan_metinler`'den gelir.
    - Kurlar `son_kurlar`'dan gelir.
  - **Bu talebin bir sürümünden:** Kalemler, işçilik, takvim, metinler, para birimi, kurlar, kâr ve fiyat girişi kopyalanır. Saat ücretleri **o anki** ayardan yeniden okunur.
  - **Eski bir talebin sürümünden** ("benzer işi bulmak"):
    - Seçim talepler listesinin aramasıyla yapılır.
    - Sürümün kalemleri, işçilik, takvim ve metinleri gelir.
    - Bu talebin gereksinim ve kapsamı boşsa eski talebinkiler de kopyalanır.
    - **Eski müşterinin bilgileri gelmez:** Müşteri talebe aittir ve kopyalanmaz.
    - Eski fiyat uyarısı yoktur (kullanıcının kararı).
- **İşlem geçmişi:** Kopyalamanın kaynağı yazılır (`kaynak_surum`).
- **Kaydetmek:** Sürüm formu tek bütün olarak kaydedilir: genel alanlar + kalemler + işçilik + takvim + kurlar.
  - Çocuk satırlar tek işlemde değiştirilir.
  - Değişen alanlar işlem geçmişine `{alan, eski, yeni}` olarak yazılır.
- **Aynı anda düzenleme:** İstek sürümün `surum` sayacını taşır. Uyuşmazsa 409 `DEGISTI` döner ve güncel hal gösterilir. Kaydedince sayaç bir artar. Talepte de aynı kural geçerli.

### 8.4 Maliyet

- **Unsur seçimi:**
  - Liste ikiye ayrılır: sık kullanılanlar ve ötekiler.
  - Pasif unsur görünmez.
  - "Diğer…" küçük bir form açar: ad ve bütçe kalemi zorunlu. Kod addan üretilir (Türkçe harfler ASCII'ye, büyük harf, boşluk `_`; çakışırsa `_2`). Yeni unsur kataloğa eklenir ve sonraki teklifte hazır gelir.
- **Kalem:**
  - unsur, açıklama, adet, ölçü birimi, birim fiyat, para birimi
  - kaynak etiketi: `TEDARIKCI_TEKLIFI`, `GECMIS_PROJE`, `TAHMIN`; kaynak notu ve tarihi; isteğe bağlı kaynak dosyası (talebin dosya kaydı)
  - temin süresi (hafta), kritik
- **Katalogdan çekmek:** Katalog kalemi seçilince ad, unsur, birim fiyat, para birimi, temin süresi ve kritik işareti dolar. Kaynak notu "Katalog: <fiyat kaynağı>, <fiyat tarihi>" olur. Kullanıcı hepsini değiştirebilir.
- **"Kataloğa da kaydet":** Elle girilen kalemi yeni katalog kalemi yapar (kod zorunlu, tekil).
- **Temin süresi:** Kalemin yanında iki değer durur:
  - elle girilen (kalemin kendi değeri; katalogdan geldiyse katalogdaki de ipucu olarak)
  - ortalama: Faz 1'de her zaman "— (M3 bağlanınca)" (M10-03)
- **Eksik fiyat:** Fiyatı olmayan kalem kaydedilebilir. Tutarı "VERİ EKSİK" görünür, sıfır sayılmaz. Onaya gönderilemez (8.10).

### 8.5 İşçilik

- **Satır:** Birim (çekirdeğin `BIRIMLER`'i), saat, açıklama. Saat ücreti ve para birimi satır eklenirken `saat_ucretleri`'nden gelir ve satırda donar. Birimin ücreti tanımlı değilse satırda "ücret tanımlı değil" yazar, satır onaya gidemez.
- **Öneri** (saf fonksiyon `iscilik_onerisi(makine_turu, birim)` → `{tablo, gecmis_ortalama, gecmis_sayi}`):
  - **Tablo:** `baslangic_tablosu.tipik_saat`.
  - **Geçmiş:** Aynı makine türündeki geçmiş projelerde o birimin gerçek saatlerinin ortalaması ve proje sayısı. Bir haneye yuvarlanır.
  - **Ekranda:** "Tablo 120 sa · Geçmiş 140 sa (3 proje)". Biri yoksa yazılmaz.
- **"Önerileri doldur":** Makine türünün başlangıç tablosundaki her birim için satır yoksa açar. Saati boşsa tablo değeriyle, tablo yoksa geçmiş ortalamasıyla doldurur. Dolu saate dokunmaz.
- **Tutar:** saat × saat ücreti (satırın para biriminde); teklif para birimine 8.7'deki gibi çevrilir. Bütçe kalemi her zaman `ISCILIK`'tir.

### 8.6 Takvim ve en erken teslim

- **Satır:**
  - etap kodu (şablondan; şablonsuz satırda boş), ad, sıra, paralel grup
  - başlangıç haftası (0 = sipariş haftası), süre (hafta, ≥ 1)
  - Hafta tam sayıdır (Ek D.2).
- **"Şablondan doldur":** Toplam süre N (hafta) sorulur; varsayılan makine türünün `tipik_toplam_hafta`'sı. Şablonun aktif her satırı için:
  - başlangıç = yarım yukarı(`bas_orani` × N)
  - bitiş = yarım yukarı(`bit_orani` × N)
  - süre = en az 1, bitiş − başlangıç
  - Var olan satırlar sorulup değiştirilir.
- **İpucu:** Her satırın yanında, şablonun birim eşlemesine göre başlangıç tablosundaki `tipik_sure_hafta` durur ("Tablo: 5 hf").
- **Hesap** (saf fonksiyon `takvim_hesabi(satirlar, kalemler)`):
  - **Takvim teslimi:** `KESIN_KABUL` dışındaki satırların en geç bitişi (başlangıç + süre).
  - **Kayma:** `SATIN_ALMA` satırı varsa: en(0, `SATIN_ALMA`.başlangıç + en uzun temin − `SATIN_ALMA`.bitiş). En uzun temin, temin süresi girilmiş kalemlerin en büyüğüdür. Satır yoksa başlangıç 0 sayılır ve kayma en(0, en uzun temin − takvim teslimi) olur.
  - **En erken teslim** = takvim teslimi + kayma.
  - **Açıklama:** Kayma > 0 ise: "En uzun temin süreli kalem (<açıklama>, <n> hafta) satın almanın bitişini <k> hafta geçiyor; en erken teslim <k> hafta kayar."
  - **Örnek:** Ek D.5'te takvim teslimi 25, robot 10 hafta, kayma 2, en erken teslim 27.
- **Teslim süresi:** Sürümün `teslim_suresi_hafta`'sı varsayılan olarak en erken teslimdir; kullanıcı daha uzun yazabilir. Daha kısası onaya gönderilemez ("gerçekçi teslim süresi").
- **Basit Gantt:** Haftalık ızgara, satır başına çubuk, paralel gruplar köşeli ayraçla.
  - Takvim teslimi ve en erken teslim dikey çizgilerle gösterilir.
  - Kayma varsa `SATIN_ALMA` çubuğunun ucunda kırmızı ▲ ve açıklama durur.
  - Düz SVG; M1.1B'nin Gantt'ının görsel dilini izler.
- **Atölye doluluğu** hesaba katılmaz.

### 8.7 Para birimi ve kur

- **Sürümün para birimi:** Teklifin fiyatı bu birimdedir. Kalemler ve işçilik kendi para birimlerinde girilir.
- **Kurlar:** Sürüm başına, her yabancı para birimi için 1 birim kaç TL (`kur_try`) ve kur tarihi. TL'nin kuru 1'dir. Kurlar elle girilir; dış servis yok.
- **Çeviri:**
  - `tutar_teklif` = tutar × kur(kalemin birimi) ÷ kur(teklifin birimi)
  - iki ondalığa yarım yukarı
  - Her satır ayrı yuvarlanır, toplam yuvarlanmış satırların toplamıdır.
- **Eksik kur:** Kullanılan bir para biriminin kuru yoksa o satırların tutarı "VERİ EKSİK" olur. Sürüm onaya gidemez.
- **`son_kurlar`:** Sürüm kaydedilince kurları bu ayara yazılır; yeni boş sürüm oradan başlar.

### 8.8 Fiyat ve kâr

- **Maliyet:** Kalemlerin ve işçiliğin teklif para birimindeki toplamı. Kırılım bütçe kalemine göre yapılır: `MALZEME`, `ISCILIK`, `FASON`, `GENEL_GIDER`. İşçilik satırları `ISCILIK`'tir, kalemler unsurlarının bütçe kalemine gider.
- **Biri girilir, öbürü hesaplanır** (`fiyat_girisi`):
  - Kâr oranı girilirse: fiyat = maliyet × (1 + kâr ÷ 100), iki ondalığa yuvarlanır.
  - Fiyat girilirse: kâr = (fiyat ÷ maliyet − 1) × 100, iki ondalığa yuvarlanır. Maliyet 0 ya da eksikse kâr hesaplanamaz.
  - Maliyet değişince girilmiş olan sabit kalır, öbürü yeniden hesaplanır.
- **Ekranda iki anlam yan yana** (S-5a):
  - "Kâr oranı (maliyetin üstüne): %28,74 · Fiyatın yüzdesi olarak (marj): %22,32".
  - Kâr girilmişse ayrıca: "Kâr %20 fiyatın yüzdesi olsaydı fiyat 54.375,00 € olurdu (hesap maliyetin üstüne yapılır: 52.200,00 €)."
- **Görünürlük:** Maliyet, kâr ve marj yalnızca M1.0 ekranlarındadır. PDF'e girmez.

### 8.9 Teklif PDF'i

- **Kütüphane:** fpdf2. A4, kenar 18 mm, Barlow 10 pt, başlıklar Barlow Condensed.
- **İçerik:**
  1. Üst bilgi: firma unvanı, adresi, iletişimi (`firma` ayarı).
  2. "TEKLİF", teklif no `T-2026-0012 · V2`, tarih (onay günü; taslakta bugün), geçerlilik sonu (tarih + geçerlilik günü).
  3. Müşteri: ad, adres, ilgili kişi (ilk aktif iletişim kişisi).
  4. Konu.
  5. Teknik çözüm (sürümün metni).
  6. Kapsam: dahil ve hariç listeleri.
  7. Teslim süresi: "Siparişten itibaren 28 hafta".
  8. Fiyat: `56.000,00 €` ve para birimi.
  9. Ödeme koşulları, teslim koşulları, notlar.
  10. Alt bilgi: sayfa x/y, "Bu teklif gg.aa.yyyy tarihine kadar geçerlidir."
- **Girmeyenler:** Maliyet, kalem fiyatları, işçilik ve kâr PDF'e girmez. Kalem listesi de girmez.
- **Taslak PDF:** `TASLAK` ve `ONAY_BEKLIYOR` sürümde istenince üretilir, saklanmaz. Her sayfada çapraz soluk "TASLAK — ONAYLANMADI" yazar.
- **Onaylı PDF:** Onay anında üretilir, sürüme yazılır (`pdf`, `pdf_parmak_izi` = SHA-256). Gönderilen ve M1.1A'ya giden budur.
- **Dosya adı:** `T-2026-0012-V2.pdf`.
- **Sayı biçimi:** Binlik nokta, ondalık virgül; para birimi simgesi sonda (`56.000,00 €`, `35.200,00 ₺`).

### 8.10 Onay

**Durumlar ve geçişler** (saf fonksiyon `alan/durum.py`, tablo testle sınanır):

| Durum | Eylem | Kim | Sonuç |
|---|---|---|---|
| `TASLAK` | Onaya gönder | `SATIS`, `YETKILI` | Doğrulama geçerse `ONAY_BEKLIYOR`. `onay_kayitlari`: `ONAYA_GONDERILDI` |
| `ONAY_BEKLIYOR` | Onayla | `YETKILI` | Onaylı PDF ve donmuş özet yazılır → `ONAYLANDI`. Kayıt: `ONAYLANDI` |
| `ONAY_BEKLIYOR` | Kendim düzelt | `YETKILI` | Onaycı formu düzenler (bilgisayarda). İlk kayıtta `ONAYCI_DUZELTTI` yazılır; değişiklikler işlem geçmişinde `onayci_duzeltmesi` işaretlidir. Ardından Onayla |
| `ONAY_BEKLIYOR` | Gerekçeyle geri gönder | `YETKILI` | Gerekçe zorunlu → `TASLAK`. Kayıt: `DUZELTME_ISTENDI`. Aynı sürüm düzeltilir |
| `ONAYLANDI` | Düzenlemeye aç | Hazırlayan, `YETKILI` | Gerekçe zorunlu → `TASLAK`. PDF, donmuş özet, onaylayan silinir. Kayıt: `DUZENLEMEYE_ACILDI` |
| `ONAYLANDI` | Gönderildi | `SATIS`, `YETKILI` | 8.11 → `GONDERILDI` |

**"Onaya gönder"in doğrulaması** (422; her hata `{alan, sira, mesaj}`):
- En az bir maliyet kalemi ya da işçilik satırı var.
- Her kalemde birim fiyat ve para birimi var. Her işçilik satırında saat ücreti var.
- Kullanılan her yabancı para biriminin kuru var.
- Fiyat ve kâr hesaplanmış, fiyat > 0.
- Takvimde en az bir satır var.
- Teslim süresi ≥ en erken teslim.
- Geçerlilik günü var.
- **Uyarı (durdurmaz):** Kapsam boş; belirsiz ve cevapsız gereksinim var. Ekran ikisini de gösterir.

**Donmuş özet (`donmus_ozet`), onay anında:**
- `toplamlar`: maliyet, kalemlere göre kırılım, marj
- `takvim_teslim_hafta`, `en_erken_teslim_hafta`
- müşteri: strateji notu hariç, iletişim kişileriyle
- gereksinimler, kapsam, talebin dosya kayıtları

Talep düzeyindeki bu bilgiler sonradan değişse de gönderilen sürüm onay anındaki haliyle kalır.

**Telefondan onay** (`/onay/{surum}`, dar ekran için):
- Özet: müşteri, konu, toplam maliyet, fiyat, kâr oranı ve marj, teslim süresi ve en erken teslim, taslak PDF bağlantısı.
- Düğmeler: "Onayla" ve "Gerekçeyle geri gönder".
- "Kendim düzelt" yalnızca bilgisayar ekranındaki sürüm sayfasındadır. Telefonda "Düzeltmek için bilgisayardan açın" yazar.

**"Onayınızı bekleyen teklifler":**
- `YETKILI`'nin her M1.0 sayfasının üstünde ince bir şerit durur: "Onayınızı bekleyen 2 teklif", tıklanınca liste açılır.
- Bu bir iş listesidir, bildirim kutusu değildir. Çekirdeğin bildirim kutusuna düşmesi istek M10-01'dedir.

### 8.11 Gönderim (kapı)

- **Kapı:** Yalnızca `ONAYLANDI` sürüm "gönderildi" yapılabilir. Başka durumda 409 `KAPI`: "Onaylanmamış teklif müşteriye gönderilemez." Geçiş yolu yok.
- **Kayıt:** gönderim şekli (`E_POSTA`, `ELDEN`, `PORTAL`, `DIGER`), not, gönderen, an.
- **Talep durumu:** `ACIK` ya da `BEKLEMEDE` ise `TEKLIF_VERILDI` olur.
- **Modül göndermez:** E-posta göndermez. Sürüm sayfasında onaylı PDF'in indirme bağlantısı durur.
- **Gönderilen sürüm donar:** Düzeltme için "Yeni sürüm" (8.3).

### 8.12 Müşterinin cevabı ve siparişe dönüştürme

**Talebin durumu** (müşterinin cevabı sürüme değil talebe yazılır):

| Durumdan | Eylem | Sonuç |
|---|---|---|
| `ACIK` | Bir sürüm gönderildi | `TEKLIF_VERILDI` |
| `ACIK`, `BEKLEMEDE` | Teklif vermiyoruz (gerekçe) | `KAPATILDI` |
| `TEKLIF_VERILDI`, `BEKLEMEDE` | Kazanıldı (kazanan sürüm: gönderilmiş bir sürüm) | `KAZANILDI` |
| `TEKLIF_VERILDI`, `BEKLEMEDE` | Kaybedildi (neden: `FIYAT`, `TEKNIK_COZUM`, `TESLIM_SURESI`; açıklama) | `KAYBEDILDI` |
| `TEKLIF_VERILDI` | Beklemede | `BEKLEMEDE` |
| `BEKLEMEDE` | Cevap bekleniyor | `TEKLIF_VERILDI` |
| `KAYBEDILDI`, `KAPATILDI` | Geri aç (`YETKILI`, gerekçe) | Gönderilmiş sürüm varsa `TEKLIF_VERILDI`, yoksa `ACIK` |

- **Revize istendi:** Durum değişmez. Yeni sürüm açılır; işlem geçmişine "Müşteri revize istedi" notu yazılır.
- **`KAZANILDI` geri alınmaz:** M1.1A siparişe dönüştürmüş olabilir ve M1.0 bunu bilemez.
- **Sonuç kaydı:** `sonuc_ani` ve `sonucu_yazan` doldurulur.

**Siparişe dönüştür:**
- **Düğme:** Gönderilmiş sürümün sayfasında, talep `TEKLIF_VERILDI`, `BEKLEMEDE` ya da bu sürümle `KAZANILDI` iken görünür: "Kazanıldı · Siparişe dönüştür".
- **Basınca:**
  1. Talep `KAZANILDI` değilse onay sorulur ve talep bu sürümle `KAZANILDI` yapılır.
  2. Yeni sekmede `${VITE_M11A_ADRES}/donustur?surum=<sürüm kimliği>` açılır.
- **Gerisi M1.1A'nın işidir:**
  - M1.1A `M10.KAZANAN_SURUM`'u kullanıcının anahtarıyla çağırır, PO ve sözleşmeyi alır, projeyi açar.
  - Pencere zaten dönüştürülmüş sürümde projeyi gösterir.
- **Adres boşsa:** Düğme yerine "M1.1A'nın adresi tanımlı değil" yazar. Talep yine kazanıldı yapılabilir.

### 8.13 Talepler listesi, arama, sayaç şeridi

- **Tablo:**
  - talep no, müşteri, konu, makine türü, kaynak, tür
  - durum
  - cevap tarihi
  - son sürüm (no ve durumu)
  - fiyat (son sürümün)
- **Varsayılan sıra:** Açık olanlar önce, cevap tarihi yakın olan önce.
- **Cevap tarihi işareti:** Durumu `ACIK` ya da `BEKLEMEDE` olan, henüz gönderilmiş sürümü olmayan ve cevap tarihine `cevap_uyari_gun` (varsayılan 3) ya da daha az gün kalmış ya da tarihi geçmiş talepte ▲ ve "Cevap tarihi yaklaşıyor / geçti" yazar. Çekirdeğin hatırlatması istek M10-01'dedir.
- **Arama** (saf fonksiyon `normal(metin)`):
  - Türkçe küçük harf (`İ`→`i`, `I`→`ı`, sonra küçült), ardından ASCII'ye katlama (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u), noktalama boşluğa, boşluklar teke.
  - `talepler.arama`: talep no, müşteri adı ve kısa adı, konu, açıklama, makine türünün adı, gereksinimler, kapsam ve en son sürümün kalem açıklamalarının normal hali.
  - Sorgunun her kelimesi `arama`'da geçmelidir (VE). Örnek: "çakma autoliv" "Autoliv — Burç Çakma"yı bulur.
- **Süzgeçler:** müşteri, makine türü, durum, yıl.
- **Sayaç şeridi** (seçili yıl; varsayılan çekirdeğin saatine göre bu yıl, `sonuc_ani` yılı):
  - kazanılan
  - kaybedilen
  - kazanma oranı = kazanılan ÷ (kazanılan + kaybedilen)
  - kayıp nedenleri: fiyat / teknik çözüm / teslim süresi sayıları
  - açık talep sayısı

### 8.14 Ayarlar ve geçmiş proje formu

Tek ekran, iki sekme (kullanıcının kararı).

- **Ayarlar sekmesi:**
  - **Maliyet unsurları:** ad, bütçe kalemi, sık, aktif, sıra. Kullanılmış unsurun bütçe kalemi değişirse uyarı gelir: "Gönderilmiş sürümler eski kalemle kaldı."
  - **Kalem kataloğu:** kod, ad, unsur, ölçü birimi, fiyat, para birimi, fiyat tarihi ve kaynağı, tipik temin, kritik, aktif.
  - **Makine türleri ve başlangıç tablosu:** Makine türü × birim ızgarası: tipik saat ve süre. Birimler `BIRIMLER`'den gelir. Yönetim doldurur; "ilk gün doldurulur" (risk önlemi).
  - **Saat ücretleri:** Birim başına ücret ve para birimi. Değişiklik yalnızca yeni işçilik satırlarını etkiler.
  - **Takvim şablonu:** Satırların birimi ve aktifliği. Kod, ad, sıra, oran değişmez; M1.1B ile ortak (Ek D.2).
  - **Firma bilgileri ve varsayılan metinler:** Ödeme koşulları, teslim koşulları, notlar, geçerlilik günü, varsayılan para birimi.
  - **Para birimleri:** Aktiflik.
  - **Yönetim birimleri:** Yalnızca `YETKILI`.
- **Geçmiş proje formu sekmesi:**
  - Kapanmış proje: proje kodu (serbest metin; çekirdekte olmayabilir), ad, makine türü, kapanış tarihi, açıklama.
  - Birim × gerçek saat.
  - Liste ve düzenleme. İşçilik önerisinin "geçmiş" ayağı buradan gelir.

### 8.15 İşlem geçmişi ve bilgi havuzu

- **Ne yazılır:** Talebe ve sürüme yapılan her değişiklik `islem_gecmisi`'ne yazılır: kim, ne (`TALEP_ACILDI`, `SURUM_KAYDEDILDI`, `DURUM_DEGISTI`, `DOSYA_EKLENDI`…), ne zaman, ayrıntı.
- **Talep kartının "Geçmiş" sekmesi** bunları sırayla gösterir.
- **Onaycının düzeltmeleri** (`onayci_duzeltmesi`) ve geri gönderme gerekçeleri "bilgi havuzu"dur. Faz 1'de ayrı bir süzgeçle listelenir ("Onaycı düzeltmeleri"). Yapay zekâ sonraki fazda bunlardan öğrenir.

### 8.16 Sağlanan okumalar

- **`M10.KAZANAN_SURUM {surum}` ve `M10.KATALOG_TEMIN_SURELERI`:** Biçimleri, görme kuralları ve hataları Ek D.4–D.6'da.
- **Uç:** `GET /api/saglanan/{ad}`. Parametreler sorgu dizgisinde.
- **Kimlik:** Çağıran, kullanıcının anahtarıyla gelir. Modül `cekirdek.oturum(anahtar)` ile açar, `KISILER`'den kişiyi tanır.
- **`KAZANAN_SURUM` nasıl kurulur:**
  - Sürümün satırından, çocuk satırlarından ve `donmus_ozet`'ten kurulur.
  - `toplamlar` donmuş özetten gelir.
  - PDF base64 olarak eklenir.
- **Sözleşme testi:** Ek D.5'teki örneği uçtan uca kurar (bölüm 14.3) ve cevabı örnekle karşılaştırır (kimlikler, anlar ve PDF dışında).

---

## 9. API

- **Taban:** `/api`, JSON.
- **Kimlik:** Her istekte `Authorization: Bearer <kullanıcının erişim anahtarı>`. Arka yüz `cekirdek.oturum(anahtar)` ile çalışır; modül şifre görmez.
- **Erişim:** Bölüm 6'daki kural her uçta uygulanır.

| Yöntem | Yol | Ne |
|---|---|---|
| GET | `/ben` | Kişi: kimlik, ad, birim, roller, M1.0'a erişim, onaycı mı, onay bekleyen sayısı |
| GET, POST | `/musteriler` | Liste (arama) ve yeni |
| GET, PUT | `/musteriler/{m}` | Ayrıntı ve güncelleme (kişiler dahil) |
| GET | `/talepler` | Liste: `?q=&musteri=&makine_turu=&durum=&yil=` (8.13) |
| GET | `/talepler/sayac?yil=` | Sayaç şeridi |
| POST | `/talepler` | Yeni talep (8.2) |
| GET, PUT | `/talepler/{t}` | Talep kartı: alanlar, gereksinimler, kapsam, dosyalar, sürümler; güncelleme (`surum` ile) |
| POST | `/talepler/{t}/dosyalar` | Dosya kaydı ekle |
| POST | `/talepler/{t}/kapat` | Teklif vermiyoruz `{gerekce}` |
| POST | `/talepler/{t}/sonuc` | `{sonuc: KAZANILDI \| KAYBEDILDI \| BEKLEMEDE \| BEKLENIYOR, kazanan_surum?, kayip_nedeni?, aciklama?}` |
| POST | `/talepler/{t}/geri-ac` | `YETKILI`, `{gerekce}` |
| GET | `/talepler/{t}/gecmis` | İşlem geçmişi |
| POST | `/talepler/{t}/surumler` | Yeni sürüm `{kaynak: BOS \| SURUM, kaynak_surum?}` |
| GET, PUT | `/surumler/{s}` | Sürüm formu: genel + kalemler + işçilik + takvim + kurlar + hesaplar (maliyet, kırılım, kâr, marj, takvim teslimi, kayma, en erken teslim, doğrulama uyarıları); kaydet (`surum` ile) |
| GET | `/surumler/{s}/oneriler` | İşçilik önerileri (8.5) |
| POST | `/surumler/{s}/takvim/sablondan` | `{toplam_hafta}` |
| GET | `/surumler/{s}/pdf` | Taslakta üretilir; onaylı ve gönderilmişte saklanan döner (`application/pdf`) |
| POST | `/surumler/{s}/onaya-gonder` | 8.10 |
| POST | `/surumler/{s}/onayla` | `YETKILI` |
| POST | `/surumler/{s}/geri-gonder` | `YETKILI`, `{gerekce}` |
| POST | `/surumler/{s}/duzenlemeye-ac` | `{gerekce}` |
| POST | `/surumler/{s}/gonderildi` | `{gonderim_sekli, not}` (8.11) |
| GET | `/onay-bekleyenler` | `YETKILI` için iş listesi |
| GET | `/projeler/{p}` | Bağlı proje doğrulaması: kullanıcının gözüyle `PROJE` → kod, ad |
| GET | `/katalog?q=` | Kalem kataloğu araması (teklif formu için) |
| POST | `/unsurlar` | "Diğer…" ile yeni unsur |
| GET, PUT | `/ayarlar/...` | `unsurlar`, `katalog`, `makine-turleri`, `baslangic-tablosu`, `saat-ucretleri`, `takvim-sablonu`, `genel` |
| GET, POST, PUT | `/gecmis-projeler` | Geçmiş proje formu |
| GET | `/birimler`, `/kisiler` | Seçim listeleri (`BIRIMLER`, `KISILER`) |
| GET | `/saglanan/{ad}` | Sağlanan okumalar (Ek D.4) |
| POST | `/gelistirme/giris` | Yalnızca `M10_GELISTIRME=1`: `{kisi}` → `{anahtar}` |

Okuma güncel değilse (`guncel` yanlış) cevaba `"hesaplaniyor": true` eklenir.

---

## 10. Hata eşleme

Hata gövdesi M1.1B ile aynıdır: `{"kod", "mesaj", ...}`.

| Durum | HTTP | Kod | Mesaj |
|---|---|---|---|
| `CekirdekHatasi('YETKI')` (okuma) | 403 | `YETKI` | "Bu bilgiyi görme yetkiniz yok." Bağlı projede 8.2'deki cümle |
| M1.0'a erişim yok, modülün rol kuralı | 403 | `YETKI` | "Bu işi satış yöneticisi ya da yetkili yapar." vb. |
| Doğrulama | 422 | `DOGRULAMA` | `hatalar: [{alan, sira, mesaj}]` |
| Durum geçişi geçersiz | 409 | `DURUM` | "Bu sürüm bu durumda değiştirilemez." |
| Onaysız gönderim | 409 | `KAPI` | "Onaylanmamış teklif müşteriye gönderilemez." |
| Aynı anda düzenleme | 409 | `DEGISTI` | "Kayıt siz bakarken değişti." `guncel` ile |
| Bulunamadı | 404 | `BULUNAMADI` | |
| `CekirdekHatasi('BICIM' \| 'KUNYE')` | 400 / 500 | `BEKLENMEYEN` | "Beklenmeyen bir hata oldu." Modülün hatasıdır; günlüğe ayrıntısıyla |
| `CekirdekHatasi('BAGLANTI')` | 503 | `BAGLANTI` | "Çekirdeğe ulaşılamıyor, biraz sonra yeniden deneyin." |
| `CekirdekHatasi('URUN')` | 502 | `URUN` | "Çekirdekte beklenmeyen hata." |

---

## 11. Ekranlar

Bu liste `TESLIM.md` › 4'e de yazılır. Dil Türkçe, tarih `gg.aa.yyyy`, tutar `56.000,00 €`. Görünüş Ek D.12. Az ekran, basitlik ilkesi (kullanıcının kararı).

| Ekran | Ne gösterir | Kim görür | Okumalar | Olaylar |
|---|---|---|---|---|
| Talepler listesi | 8.13: tablo, arama, süzgeçler, sayaç şeridi, ▲ cevap tarihi; `YETKILI`'ye onay bekleyenler şeridi | M1.0'a erişimi olan | `KISILER` | — |
| Talep kartı | Müşteri, kaynak ve bağlı proje, tarihler, durum; dosyalar, gereksinimler, kapsam; sürümler ve durumları; teklif vermiyoruz; müşterinin cevabı; geçmiş | M1.0'a erişimi olan | `KISILER`, `PROJE` | — |
| Teklif sürümü | Dört bölüm: Maliyet, İşçilik, Takvim (Gantt), Fiyat; altta "PDF oluştur" ve "Onaya gönder"; onaycıya üstte üç düğme; gönderilmişte "Siparişe dönüştür" | M1.0'a erişimi olan; düzenleme 6'ya göre | `KISILER`, `BIRIMLER` | — |
| Telefondan onay | 8.10 özet ve iki düğme | `YETKILI` | `KISILER` | — |
| Müşteriler | Liste ve kart | M1.0'a erişimi olan | — | — |
| Ayarlar ve geçmiş veri | İki sekme (8.14) | `SATIS`, `YETKILI`, yönetim | `BIRIMLER` | — |
| Geliştirme girişi | Örnek firmanın kişilerinden seçim | Yalnızca geliştirmede | — | — |

- **Derin bağlantı yok:** M1.0'ın çekirdekte bağlamı yoktur, teklif projesizdir.
- **Teklif sürümü ekranı modülün ağır ekranıdır:** Dört bölüm sekmelerle değil alt alta, sabit bir özet şeridiyle durur: maliyet, fiyat, kâr, en erken teslim, durum.

---

## 12. Künye

Ek A, `kunye.json` olarak modülün köküne konur. Denetim sonucu: **0 hata, 1 uyarı.**
- **Uyarı:** V17, `PROJE.ACTIM` modülün olaylarında yok. Beklenen: yetkiyi rolün sahibi önerir; olayı M1.1A yazar (bölüm 5).
- **Kayıt denetimi:** M1.1A ve M1.1B künyeleriyle birlikte 0 hata (`kunye_denetle.py . <m1.1a> <m1.1b>`).

---

## 13. Çekirdeğe istekler

Her biri `istekler/M10-NN_kisa_ad.md` olarak `irp_sozlesme/sablonlar/istek.md` biçiminde yazılır. Künyedeki `istekler` listesinde de durur.

| Kod | Önem | Ne | Kanıt | Öneri | Beklerken |
|---|---|---|---|---|---|
| M10-01 | ONEMLI | Projesiz modül kaydına bildirim yok. Onay bekleyen teklif CEO'nun, cevap tarihi yaklaşan talep satış yöneticisinin bildirim kutusuna düşemiyor | `cekirdek_katalogu.json` › `bildirim.kayit_turleri` = `GOREV`, `IS`, `NESNE`, `PROJE`. Teklif projesizdir ve çekirdeğe açılmamalıdır (K-30) | Yalnızca `KISI` alıcılı, kaydı modül kaydı olan bir bildirim türü (`kayit: {tur: MODUL, modul_kaydi}`); metin kaydın bilgisinden başkasını taşımaz | Ekranda iş listesi ve ▲ işareti (8.10, 8.13) |
| M10-02 | ONEMLI | Modüller arası okumaların yönlendirmesi yok | `oturum.oku('M10.KAZANAN_SURUM', …)` → `BICIM: TANIMSIZ_VERI` (denendi). Sözleşmede uç yok | Çekirdek `oku('<KOD>.<AD>')`'ı sağlayan modüle kullanıcının anahtarıyla yönlendirsin | `GET /api/saglanan/{ad}` (Ek D.4) |
| M10-03 | ONEMLI | Ortak katalog çekirdekte değil: maliyet unsuru ve bütçe kalemi, etap şablonu kodları. M3'ün gerçek temin süreleri ve M1.1A'nın kapanış farkı M1.0'a dönemiyor: M1.1A M1.0'a bağlı olduğu için geri okuma döngü olur (R08) | Kod listeleri sabit (V16). M10 → M11A ya da M10 → M3 → M10 bağımlılığı R08 hatası | Çekirdekte (a) ortak kod listeleri `MALIYET_UNSURU`, `ETAP_SABLONU`; (b) kapanan projenin kalem bazında sonucu ve katalog kalemi bazında gerçek temin süresi için okumalar | Etap kodları M1.1B ile elle aynı tutulur; ortalama temin "bilgi yok"; öğrenme yok |
| M10-04 | DUSUK | Kapanan projenin departman bazında gerçek saatleri okunamıyor. Her saat kaydı bir departman taşımalı (kullanıcının notu) | `PROJE_ISCILIGI` simülatörde `TANIMSIZ_VERI` (denendi) | `PROJE_ISCILIGI {hedef: proje, kirilim: BIRIM}` | Geçmiş proje formu elle |
| M10-05 | ONEMLI | Dosya depolama kapısı yok (M11B-05 ile aynı) | Sözleşmede yükleme ucu yok | Dosya kimliği üreten yükleme kapısı | Dosya kaydı: konum ve parmak izi |
| M10-06 | ONEMLI | Ek iş ve servis talebinde bağlı proje seçilemiyor | `PROJELER` → `TANIMSIZ_VERI`; satış yöneticisi K050 2614'ü okuyamıyor (`YETKI: Gorunurluk`), `PROJE.ERISIM_VERDIM`'den sonra okuyabiliyor (denendi) | `PROJELER` simülatöre; `SATIS` rolüne proje adlarını görme (ayrıntısız) | Kod elle yazılır; göremiyorsa bağlanamaz |

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

- **Hesap** (Ek D.5'in sayıları):
  - satır tutarları ve çeviri (35.200 TL → 1.000,00 €)
  - kırılım (`MALZEME` 32.500,00, `ISCILIK` 10.000,00, `FASON` 1.000,00, `GENEL_GIDER` 0,00)
  - maliyet 43.500,00
  - fiyat girişinden kâr %28,74 ve marj %22,32
  - kâr %20 girişinden fiyat 52.200,00 ve "fiyatın yüzdesi" 54.375,00
  - eksik fiyat ve eksik kurda `VERI_EKSIK`
  - yuvarlama yarım yukarı
- **Takvim:**
  - N = 26 ile şablondan on satır, Ek D.5'teki başlangıç ve süreler (`IMALAT` başlangıcı 6,5 → 7)
  - takvim teslimi 25, kayma 2, en erken 27
  - `SATIN_ALMA` yokken kayma
  - temin süresi olmayan kalem
- **Öneri:** Tablo ve geçmiş ortalaması; biri yokken.
- **Durum:** Sürüm ve talep geçiş tabloları; her geçersiz geçiş reddedilir.
- **Doğrulama:** "Onaya gönder"in her kuralı ayrı ayrı.
- **Arama:** `normal()`; "ÇAKMA", "cakma", "Çakma" aynı; "IŞIK" → "isik"; VE araması.
- **Kod üretme:** "Diğer" unsur kodu, çakışmada `_2`.

### 14.3 Sözleşme testleri (simülatöre karşı)

- **Her test** kendi çekirdeğini açar (`Cekirdek.ac('kunye.json')`) ve D.10'daki zemini kurar (`satis_rolu_kur=False`: M1.0'ın künyesi `SATIS`'i ve `PROJE.ACTIM` yetkisini kendisi kurar).
- **Senaryo:** Sonunda `cekirdek.surucu.senaryo_yaz('senaryolar/<ad>.girdi.json')`; `senaryo_dogrula` ile `.beklenen.json`.
- **Okumalar:** M1.0 çekirdeğe yalnızca okur; senaryolar okumaları ve zemin olaylarını kaydeder.

| Senaryo | Akış | Beklenen |
|---|---|---|
| `M1001_teklif_dongusu` | K050 müşteri ve talep açar, V2'yi Ek D.5'teki gibi kurar: işçilik birimleri `BIRIMLER`'den, saat ücretleri Ek C'den. Onaya gönderir. K050'nin onay denemesi modülde 403 alır. K001 onaylar, K050 "gönderildi" der, talebi bu sürümle `KAZANILDI` yapar. `GET /api/saglanan/M10.KAZANAN_SURUM?surum=…` K050'nin anahtarıyla Ek D.5'e eşittir (kimlik, an ve PDF dışında). K041'in anahtarıyla 403, `TASLAK` bir sürümde 409 `KAPI` | Ret yok |
| `M1002_bagli_proje` | K050 kaynağı `EK_IS`, bağlı projesi `2614` olan talep açmak ister. `PROJE` okuması `YETKI` alır, modül 403 döner, talep açılmaz. Yetkili `PROJE.ERISIM_VERDIM {proje: '2614', kisi: 'K050', gerekce: 'ek iş'}` yazar (sınamada `yetkili_olay`). K050 yeniden dener; proje okunur, talep açılır | 1 okuma hatası (`YETKI`) |

`TESLIM.md` › 2'ye senaryo sayısı ve beklenen ret yazılır.

### 14.4 Veritabanı ve API testleri

- **Göçler:** Boş şemada sırayla koşar; ardından `gelistirme/ornek_veriler.sql`.
- **Kısıtlar:**
  - tek açık sürüm
  - gönderilen sürümün değişmezliği (tetikleyici)
  - `KAZANILDI`'da kazanan sürüm
  - kur ve fiyatın birlikte boş ya da dolu olması
- **API:** FastAPI `TestClient`, simülatör ve test veritabanıyla.
  - Bölüm 6'nın yetki tablosu: her satır için izinli ve izinsiz bir kişi.
  - Hata eşleme.
  - 409 `DEGISTI`.
  - Gönderilmiş sürümün çocuk satırlarına yazma 409.
  - Kopyalamada müşterinin gelmemesi.
- **PDF:**
  - Üretilen PDF `%PDF` ile başlar.
  - Metninde (fpdf2'nin çıktısı açılarak ya da `pypdf` ile) fiyat ve kapsam geçer; maliyet, kâr ve kalem fiyatları geçmez.
  - Taslakta "TASLAK" yazar.
  - Onaylı PDF'in parmak izi saklananla aynıdır.
- **Test veritabanı:** `M10_TEST_VERITABANI`. Her test şemayı temiz bulur.

### 14.5 Ön yüz

- **vitest:** Tutar ve tarih biçimleyicileri (`56.000,00 €`), takvim çizim yardımcıları.
- **Elle duman testi:** `gelistirme/BENIOKU.md`'de, her ekran için bir paragraf.

---

## 15. Geliştirme ortamı

1. **Python:** `uv venv --python 3.15`, `uv pip install -e ".[dev]"`. Paketin komutları sanal ortam etkinken koşulur (makinenin `python3`'ü başka sürüm olabilir).
2. **Veritabanı:** `docker compose -f gelistirme/docker-compose.yml up -d` (PostgreSQL 16, `localhost:54330`) ya da Homebrew `postgresql@17`.
   - `python -m m10.komutlar gelistirme-vt-sifirla` şemayı silip açar ve sırayla koşar: `gelistirme/sema_ac.sql`, `veritabani/*.sql`, `gelistirme/ornek_veriler.sql`.
3. **Çekirdek:**
   - Testlerde simülatör sürücüsü.
   - Uygulamayı yalnız çalıştırırken sahte bulut: `python irp_sozlesme/simulator/sunucu.py --kunye kunye.json --port 8787`. Örnek firmada `SATIS` rolünü taşıyan kimse yoktur; satış yöneticisi gibi denemek için K001 (`YETKILI`) ile girilir.
   - **Üç modülü birlikte denemek için** M1.1A'nın klasöründeki ortak sahte bulut (Ek D.11): `IRP_TABAN=http://localhost:8790`. Orada K050 ve K060 vardır.
4. **Arka yüz:** `uvicorn m10.api.uygulama:app --reload --port 8010`.
5. **Ön yüz:** `cd on_yuz && npm install && npm run dev -- --port 5180`. Vite `/api`'yi `http://localhost:8010`'a yönlendirir; `VITE_M11A_ADRES=http://localhost:5181`.
6. **Geliştirme girişi:** `/api/gelistirme/giris`; anahtar `sessionStorage`'da `m10_anahtar`.

---

## 16. Uygulama sırası

| Adım | İş | Sonunda |
|---|---|---|
| 1 | Ortam, `pyproject.toml`, göçler (Ek B), künye (Ek A), `CLAUDE.md`, yazı tipleri | `kunye_denetle` 0 hata; paket testleri geçer |
| 2 | `baglanti.py`, kişi ve erişim (bölüm 6), hata eşleme, `/ben`, geliştirme girişi | — |
| 3 | Saf fonksiyonlar: hesap, kur, fiyat, takvim, öneri, durum, arama | 14.2'nin hepsi |
| 4 | Ayarlar ve geçmiş proje formu; müşteriler | — |
| 5 | Talep: açma, numara, dosyalar, gereksinim, kapsam, bağlı proje, kapatma | `M1002` |
| 6 | Sürüm: yeni, kopyalama, kaydetme, dört bölüm, eşzamanlılık | — |
| 7 | PDF | 14.4 PDF testleri |
| 8 | Onay, gönderim, müşterinin cevabı, işlem geçmişi | — |
| 9 | Talepler listesi, arama, sayaç şeridi, onay bekleyenler | — |
| 10 | Sağlanan okumalar | `M1001` |
| 11 | Ön yüz ekranları (adımlarla birlikte de yazılabilir) | Elle duman testi |
| 12 | İstek dosyaları, `TESLIM.md` (`sablonlar/TESLIM.md`'den), teslim kontrol listesi (`06_teslim.md` › 1) | — |

**Bitince modülün sahibine söyle** (`BASLA.md` › Bitirince):
- künye denetimi: hata ve uyarı sayısı
- paket denetimi
- senaryo sayısı ve retler
- istek sayısı

---

## 17. Uygulayıcıya bırakılanlar

- Ekranların yerleşimi ve görünüşü (Ek D.12'nin değişkenleriyle). Gantt'ın ölçeği.
- PDF'in tipografik ayrıntısı (bölüm 8.9'daki içerik ve sıra kalır).
- Klasörlerin içindeki kod düzeni; günlük biçimi.
- Hata mesajlarının tam cümleleri. Anlamı bölüm 10'daki gibi kalır.
- "Diğer" unsur kodunun üretimindeki ayrıntılar (tekilliği koruyarak).

---

## 18. Açık sorular

Bunlar yazılımı değiştirmez; cevapları ayara ya da veriye girer.

| Soru | Nereye girer |
|---|---|
| Soru 1: Kazanılmış 2, kaybedilmiş 1 teklifin gerçek dosyaları | PDF'in içeriği ve sırası, maliyet kırılımının unsurları |
| S-8a: İşçiliği kim tahmin ediyor? | Faz 1'de satış yöneticisi girer; dağıtım sonraki faz |
| S-8b: Teklifi kim onaylıyor? CEO kendi teklifini? | Faz 1: `YETKILI` onaylar, kendi teklifini de. Cevaba göre ayar: onaycı rolü, hazırlayan ≠ onaylayan |
| S-4a: Geçmişte departman bazında saat kaydı var mı? | Geçmiş proje formunun ilk gün doldurulması |
| S-20: Eski teklifler taşınsın mı? | Taşıma komutu (sonraki faz) |
| S-5a: Kâr maliyetin üstüne mi, fiyatın yüzdesi mi? | Faz 1 maliyetin üstüne; iki anlam ekranda. Cevaba göre `kar_hesabi` ayarı |
| S-19: Şartnameler yapay zekâ servisine gönderilebilir mi? | Sonraki faz |
| Mustafa: modül kodu; ekranların yolu (S1); istekler M10-01…06 | Künye; ön yüz |

---

## Ek A · `kunye.json`

```json
{
 "kunye_surumu": 1,
 "kod": "M10",
 "ad": "Teklif hazırlama",
 "surum": "0.1.0",
 "cekirdek": ">=10.2",
 "sahip": "A ekibi",
 "aciklama": "Müşteri talebinden onaylı teklifin müşteriye gönderilmesine kadar: talep ve sürümleri (V1, V2…), maliyet kalemleri, departman işçiliği, basit takvim ve en erken teslim, fiyat, teklif PDF'i, onay kapısı, müşteriler, ayarlar ve geçmiş proje formu. Teklif çekirdeğe açılmaz, modülde kalır (K-30); sipariş gelince proje M1.1A'da açılır.",
 "servis_kimligi": "SRV-M10",
 "arka_yuz": true,
 "olay_yolu": "YOK",
 "kapilar": {
  "okumalar": [
   "KISILER",
   "BIRIMLER",
   "PROJE"
  ],
  "servis_okumalari": [],
  "olaylar": [],
  "plan": false,
  "belge_surumu": false,
  "bildirimler": [],
  "abonelikler": []
 },
 "nesne_turleri": [],
 "tur_uzantilari": [],
 "roller": [
  {
   "kod": "SATIS",
   "ad": "Satış yöneticisi"
  }
 ],
 "kod_listeleri": [],
 "yetki_onerileri": [
  {
   "eylem_kodu": "PROJE.ACTIM",
   "kimler": [
    "SATIS"
   ],
   "kapsam": "FIRMA"
  }
 ],
 "veritabani": {
  "sema": "mod_m10",
  "gocler": "veritabani/"
 },
 "on_yuz": {
  "tur": "AYRI_UYGULAMA",
  "derin_baglantilar": []
 },
 "saglananlar": [
  {
   "ad": "M10.KAZANAN_SURUM",
   "parametreler": [
    "surum"
   ],
   "gorme": "ROL",
   "kisisel": true,
   "para": true,
   "aciklama": "Kazanan ve müşteriye gönderilmiş teklif sürümünün donmuş içeriği: müşteri, fiyat, para birimi ve kurlar, maliyet kırılımı (bütçe kalemiyle), işçilik, takvim, gereksinimler, kapsam, dosya kayıtları, müşteri PDF'i. Yalnızca SATIS, YETKILI ve yönetim birimleri"
  },
  {
   "ad": "M10.KATALOG_TEMIN_SURELERI",
   "parametreler": [],
   "gorme": "KAYDI_GOREN",
   "kisisel": false,
   "para": false,
   "aciklama": "Katalog kalemlerinin elle girilen tipik temin süresi ve kritik işareti; fiyat yok"
  }
 ],
 "bagimliliklar": [],
 "kisisel_veri": [
  {
   "alan": "musteri_kisileri: ad, unvan, telefon, e-posta",
   "neden": "Müşteri firmanın teklif yazışmasındaki iletişim kişileri; teklifin hazırlanması ve sözleşmenin kurulması için (KVKK m.5/2-c)"
  }
 ],
 "para": true,
 "sinirlar": {
  "okuma_dakika": 600
 },
 "istekler": [
  {
   "kod": "M10-01",
   "baslik": "Projesiz modül kaydına bildirim yok: onay bekleyen teklif ve cevap tarihi hatırlatması çekirdeğin bildirim kutusuna düşemiyor",
   "durum": "ACIK"
  },
  {
   "kod": "M10-02",
   "baslik": "Modüller arası okumaların yönlendirmesi yok: oku('M10.KAZANAN_SURUM') simülatörde TANIMSIZ_VERI",
   "durum": "ACIK"
  },
  {
   "kod": "M10-03",
   "baslik": "Ortak katalog çekirdekte değil (maliyet unsuru ve bütçe kalemi, etap şablonu); M3'ten ortalama temin süresi ve kapanış farkı geri beslemesi bağımlılık döngüsüne (R08) takılıyor",
   "durum": "ACIK"
  },
  {
   "kod": "M10-04",
   "baslik": "Kapanan projenin departman bazında gerçek saatleri okunamıyor (PROJE_ISCILIGI simülatörde yok); öğrenme katmanı için",
   "durum": "ACIK"
  },
  {
   "kod": "M10-05",
   "baslik": "Dosya depolama kapısı yok (yükleme, dosya kimliği, parmak izi); talep dosyaları yalnızca kayıt",
   "durum": "ACIK"
  },
  {
   "kod": "M10-06",
   "baslik": "Ek iş ve servis talebinde bağlı proje seçilemiyor: PROJELER simülatörde yok, satış yöneticisi projeyi göremiyor (UYELER)",
   "durum": "ACIK"
  }
 ]
}
```

## Ek B · Göçler

### `veritabani/001_m10.sql`

```sql
-- M1.0 Teklif hazırlama · modülün tabloları (şema mod_m10)
-- Çekirdeğin kimlikleri (kişi, birim, proje) metin olarak, değer olarak tutulur; çekirdeğe yabancı anahtar yoktur (G08).
-- Şemayı kurulum açar; bu dosya yalnızca içini doldurur (G03).

-- Ayarlar ve sayaçlar
CREATE TABLE mod_m10.ayarlar (
  anahtar text PRIMARY KEY,
  deger jsonb NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz
);

CREATE TABLE mod_m10.sayaclar (
  ad text NOT NULL,
  donem text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (ad, donem)
);

CREATE FUNCTION mod_m10.sayac_ilerlet(p_ad text, p_donem text) RETURNS integer
LANGUAGE sql SET search_path = mod_m10, pg_temp AS $$
  INSERT INTO mod_m10.sayaclar AS s (ad, donem, son) VALUES (p_ad, p_donem, 1)
  ON CONFLICT (ad, donem) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

-- Kataloglar (ayarlar ekranı)
CREATE TABLE mod_m10.para_birimleri (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z]{3}$'),
  ad text NOT NULL,
  sembol text,
  aktif boolean NOT NULL DEFAULT true
);

CREATE TABLE mod_m10.maliyet_unsurlari (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z][A-Z0-9_]{1,39}$'),
  ad text NOT NULL,
  butce_kalemi text NOT NULL CHECK (butce_kalemi IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  sik boolean NOT NULL DEFAULT false,
  aktif boolean NOT NULL DEFAULT true,
  sira integer NOT NULL DEFAULT 100,
  ekleyen text,
  ekleme_ani timestamptz
);

CREATE TABLE mod_m10.katalog_kalemleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kod text NOT NULL UNIQUE CHECK (btrim(kod) <> ''),
  ad text NOT NULL,
  unsur text NOT NULL REFERENCES mod_m10.maliyet_unsurlari (kod),
  olcu_birimi text NOT NULL DEFAULT 'adet',
  birim_fiyat numeric(14,2) CHECK (birim_fiyat >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  fiyat_tarihi date,
  fiyat_kaynagi text,
  tipik_temin_hafta integer CHECK (tipik_temin_hafta >= 0),
  kritik boolean NOT NULL DEFAULT false,
  aktif boolean NOT NULL DEFAULT true,
  CHECK ((birim_fiyat IS NULL) = (para_birimi IS NULL))
);

CREATE TABLE mod_m10.makine_turleri (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z][A-Z0-9_]{1,39}$'),
  ad text NOT NULL,
  tipik_toplam_hafta integer CHECK (tipik_toplam_hafta > 0),
  aktif boolean NOT NULL DEFAULT true
);

-- Başlangıç tablosu: makine türü × birim → tipik saat ve süre (8a)
CREATE TABLE mod_m10.baslangic_tablosu (
  makine_turu text NOT NULL REFERENCES mod_m10.makine_turleri (kod),
  birim text NOT NULL,
  tipik_saat numeric(8,1) NOT NULL CHECK (tipik_saat >= 0),
  tipik_sure_hafta integer CHECK (tipik_sure_hafta >= 0),
  PRIMARY KEY (makine_turu, birim)
);

-- Teklif için standart saat ücreti (karar 104: varsayım, maaşın kopyası değil)
CREATE TABLE mod_m10.saat_ucretleri (
  birim text PRIMARY KEY,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Takvim şablonu: M1.1B'nin etap şablonuyla aynı kodlar (ortak etap listesi)
CREATE TABLE mod_m10.takvim_sablonu (
  kod text PRIMARY KEY,
  ad text NOT NULL,
  sira integer NOT NULL UNIQUE,
  paralel_grup text,
  birim text,
  bas_orani numeric(4,3) NOT NULL CHECK (bas_orani BETWEEN 0 AND 1),
  bit_orani numeric(4,3) NOT NULL CHECK (bit_orani BETWEEN 0 AND 1),
  aktif boolean NOT NULL DEFAULT true,
  CHECK (bas_orani <= bit_orani)
);

-- Geçmiş proje formu (8b): kapanmış projelerin birim bazında gerçek saatleri, elle
CREATE TABLE mod_m10.gecmis_projeler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje_kodu text NOT NULL UNIQUE,
  ad text NOT NULL,
  makine_turu text NOT NULL REFERENCES mod_m10.makine_turleri (kod),
  kapanis_tarihi date,
  aciklama text,
  giren text NOT NULL,
  giris_ani timestamptz NOT NULL
);

CREATE TABLE mod_m10.gecmis_proje_saatleri (
  gecmis_proje bigint NOT NULL REFERENCES mod_m10.gecmis_projeler (kimlik) ON DELETE CASCADE,
  birim text NOT NULL,
  gercek_saat numeric(8,1) NOT NULL CHECK (gercek_saat >= 0),
  PRIMARY KEY (gecmis_proje, birim)
);

-- Müşteri
CREATE TABLE mod_m10.musteriler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ad text NOT NULL CHECK (btrim(ad) <> ''),
  kisa_ad text,
  adres text,
  ulke text NOT NULL DEFAULT 'TR',
  vergi_dairesi text,
  vergi_no text,
  strateji_notu text,
  aktif boolean NOT NULL DEFAULT true,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  arama text NOT NULL DEFAULT ''
);

CREATE TABLE mod_m10.musteri_kisileri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  musteri bigint NOT NULL REFERENCES mod_m10.musteriler (kimlik),
  ad text NOT NULL,
  unvan text,
  telefon text,
  eposta text,
  aktif boolean NOT NULL DEFAULT true
);

-- Talep: tek kayıt, altında sürümler
CREATE TABLE mod_m10.talepler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep_no text NOT NULL UNIQUE,
  musteri bigint NOT NULL REFERENCES mod_m10.musteriler (kimlik),
  kaynak text NOT NULL CHECK (kaynak IN ('YENI_IS', 'EK_IS', 'SERVIS')),
  bagli_proje text,
  tur text NOT NULL CHECK (tur IN ('KURUMSAL_SARTNAME', 'SAHA_NOTU', 'ARGE')),
  makine_turu text REFERENCES mod_m10.makine_turleri (kod),
  konu text NOT NULL CHECK (btrim(konu) <> ''),
  aciklama text,
  gelis_tarihi date NOT NULL,
  cevap_tarihi date,
  durum text NOT NULL DEFAULT 'ACIK'
    CHECK (durum IN ('ACIK', 'TEKLIF_VERILDI', 'KAZANILDI', 'KAYBEDILDI', 'BEKLEMEDE', 'KAPATILDI')),
  kazanan_surum bigint,
  kayip_nedeni text CHECK (kayip_nedeni IN ('FIYAT', 'TEKNIK_COZUM', 'TESLIM_SURESI')),
  kayip_aciklamasi text,
  kapatma_gerekcesi text,
  sonuc_ani timestamptz,
  sonucu_yazan text,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  arama text NOT NULL DEFAULT '',
  surum integer NOT NULL DEFAULT 1,
  CHECK (kaynak = 'YENI_IS' OR bagli_proje IS NOT NULL),
  CHECK (durum <> 'KAYBEDILDI' OR kayip_nedeni IS NOT NULL),
  CHECK (durum <> 'KAPATILDI' OR coalesce(btrim(kapatma_gerekcesi), '') <> ''),
  CHECK (durum <> 'KAZANILDI' OR kazanan_surum IS NOT NULL)
);

-- Dosyanın kaydı modülde, dosyanın kendisi şirket sunucusunda (M1.1B ile aynı ilke)
CREATE TABLE mod_m10.talep_dosyalari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  tur text NOT NULL CHECK (tur IN ('SARTNAME', 'FOTOGRAF', 'VIDEO', 'SAHA_NOTU', 'TEDARIKCI_TEKLIFI', 'CIZIM', 'DIGER')),
  ad text NOT NULL,
  konum text NOT NULL CHECK (btrim(konum) <> ''),
  aciklama text,
  parmak_izi text CHECK (parmak_izi ~ '^[0-9a-f]{64}$'),
  ekleyen text NOT NULL,
  ekleme_ani timestamptz NOT NULL
);

CREATE TABLE mod_m10.gereksinimler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  sira integer NOT NULL,
  metin text NOT NULL CHECK (btrim(metin) <> ''),
  belirsiz boolean NOT NULL DEFAULT false,
  soru text,
  cevap text,
  cevap_ani timestamptz,
  UNIQUE (talep, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mod_m10.kapsam_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  tur text NOT NULL CHECK (tur IN ('DAHIL', 'HARIC')),
  sira integer NOT NULL,
  metin text NOT NULL CHECK (btrim(metin) <> ''),
  UNIQUE (talep, tur, sira) DEFERRABLE INITIALLY DEFERRED
);

-- Teklif sürümü (V1, V2…)
CREATE TABLE mod_m10.teklif_surumleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  no integer NOT NULL CHECK (no >= 1),
  durum text NOT NULL DEFAULT 'TASLAK' CHECK (durum IN ('TASLAK', 'ONAY_BEKLIYOR', 'ONAYLANDI', 'GONDERILDI')),
  kaynak_surum bigint REFERENCES mod_m10.teklif_surumleri (kimlik),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  kar_orani numeric(7,2),
  fiyat numeric(14,2) CHECK (fiyat >= 0),
  fiyat_girisi text NOT NULL DEFAULT 'KAR' CHECK (fiyat_girisi IN ('KAR', 'FIYAT')),
  toplam_hafta integer CHECK (toplam_hafta > 0),
  teslim_suresi_hafta integer CHECK (teslim_suresi_hafta > 0),
  gecerlilik_gun integer CHECK (gecerlilik_gun > 0),
  teknik_cozum text,
  odeme_kosullari text,
  teslim_kosullari text,
  notlar text,
  hazirlayan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  onaya_gonderen text,
  onaya_gonderim_ani timestamptz,
  onaylayan text,
  onay_ani timestamptz,
  gonderen text,
  gonderim_ani timestamptz,
  gonderim_sekli text CHECK (gonderim_sekli IN ('E_POSTA', 'ELDEN', 'PORTAL', 'DIGER')),
  gonderim_notu text,
  pdf bytea,
  pdf_parmak_izi text CHECK (pdf_parmak_izi ~ '^[0-9a-f]{64}$'),
  donmus_ozet jsonb,
  surum integer NOT NULL DEFAULT 1,
  UNIQUE (talep, no),
  CHECK (durum IN ('TASLAK', 'ONAY_BEKLIYOR')
         OR (onaylayan IS NOT NULL AND onay_ani IS NOT NULL AND pdf IS NOT NULL AND donmus_ozet IS NOT NULL)),
  CHECK (durum <> 'GONDERILDI' OR (gonderim_ani IS NOT NULL AND gonderen IS NOT NULL))
);

-- Bir talepte aynı anda en çok bir gönderilmemiş sürüm olur
CREATE UNIQUE INDEX teklif_surumleri_tek_acik ON mod_m10.teklif_surumleri (talep) WHERE durum <> 'GONDERILDI';

ALTER TABLE mod_m10.talepler
  ADD CONSTRAINT talepler_kazanan_surum_fk FOREIGN KEY (kazanan_surum) REFERENCES mod_m10.teklif_surumleri (kimlik);

-- Gönderilmiş sürüm değişmez: yalnızca hiçbir alanı değişmeyen güncelleme geçer
CREATE FUNCTION mod_m10.gonderilen_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m10, pg_temp AS $$
BEGIN
  IF OLD.durum = 'GONDERILDI' AND NEW IS DISTINCT FROM OLD THEN
    RAISE EXCEPTION 'Gönderilmiş teklif sürümü değiştirilemez (sürüm %)', OLD.kimlik;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER teklif_surumleri_gonderilen_degismez BEFORE UPDATE ON mod_m10.teklif_surumleri
  FOR EACH ROW EXECUTE FUNCTION mod_m10.gonderilen_degismez();

-- Döviz kurları: sürüm başına, 1 birim = kur_try TL
CREATE TABLE mod_m10.surum_kurlari (
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  kur_try numeric(14,6) NOT NULL CHECK (kur_try > 0),
  kur_tarihi date NOT NULL,
  PRIMARY KEY (surum, para_birimi),
  CHECK (para_birimi <> 'TRY')
);

CREATE TABLE mod_m10.maliyet_kalemleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  sira integer NOT NULL,
  unsur text NOT NULL REFERENCES mod_m10.maliyet_unsurlari (kod),
  katalog_kalemi bigint REFERENCES mod_m10.katalog_kalemleri (kimlik),
  aciklama text NOT NULL CHECK (btrim(aciklama) <> ''),
  adet numeric(12,3) NOT NULL CHECK (adet > 0),
  olcu_birimi text NOT NULL DEFAULT 'adet',
  birim_fiyat numeric(14,2) CHECK (birim_fiyat >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  kaynak_etiketi text NOT NULL DEFAULT 'TAHMIN' CHECK (kaynak_etiketi IN ('TEDARIKCI_TEKLIFI', 'GECMIS_PROJE', 'TAHMIN')),
  kaynak_notu text,
  kaynak_tarihi date,
  kaynak_dosyasi bigint REFERENCES mod_m10.talep_dosyalari (kimlik),
  temin_hafta integer CHECK (temin_hafta >= 0),
  kritik boolean NOT NULL DEFAULT false,
  CHECK ((birim_fiyat IS NULL) = (para_birimi IS NULL)),
  UNIQUE (surum, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mod_m10.iscilik_satirlari (
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  birim text NOT NULL,
  saat numeric(8,1) NOT NULL CHECK (saat >= 0),
  saat_ucreti numeric(14,2) CHECK (saat_ucreti >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  aciklama text,
  PRIMARY KEY (surum, birim),
  CHECK ((saat_ucreti IS NULL) = (para_birimi IS NULL))
);

CREATE TABLE mod_m10.takvim_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  etap_kodu text REFERENCES mod_m10.takvim_sablonu (kod),
  ad text NOT NULL CHECK (btrim(ad) <> ''),
  sira integer NOT NULL,
  paralel_grup text,
  baslangic_hafta integer NOT NULL CHECK (baslangic_hafta >= 0),
  sure_hafta integer NOT NULL CHECK (sure_hafta >= 1),
  UNIQUE (surum, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX takvim_satirlari_etap ON mod_m10.takvim_satirlari (surum, etap_kodu) WHERE etap_kodu IS NOT NULL;

-- Onay ve düzeltme kaydı ("bilgi havuzu") ve işlem geçmişi
CREATE TABLE mod_m10.onay_kayitlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  karar text NOT NULL CHECK (karar IN ('ONAYA_GONDERILDI', 'ONAYLANDI', 'DUZELTME_ISTENDI', 'ONAYCI_DUZELTTI', 'DUZENLEMEYE_ACILDI')),
  gerekce text,
  kim text NOT NULL,
  an timestamptz NOT NULL,
  CHECK (karar NOT IN ('DUZELTME_ISTENDI', 'DUZENLEMEYE_ACILDI') OR coalesce(btrim(gerekce), '') <> '')
);

CREATE TABLE mod_m10.islem_gecmisi (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  surum bigint REFERENCES mod_m10.teklif_surumleri (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL,
  islem text NOT NULL,
  ayrinti jsonb NOT NULL DEFAULT '{}'::jsonb,
  onayci_duzeltmesi boolean NOT NULL DEFAULT false
);

CREATE INDEX islem_gecmisi_talep ON mod_m10.islem_gecmisi (talep, an);
CREATE INDEX talepler_durum ON mod_m10.talepler (durum, cevap_tarihi);
CREATE INDEX maliyet_kalemleri_surum ON mod_m10.maliyet_kalemleri (surum);
CREATE INDEX takvim_satirlari_surum ON mod_m10.takvim_satirlari (surum);
```

### `veritabani/002_varsayilanlar.sql`

```sql
-- Varsayılan veriler. Firma bunları ayarlar ekranından değiştirir.
INSERT INTO mod_m10.para_birimleri (kod, ad, sembol) VALUES
  ('TRY', 'Türk lirası', '₺'),
  ('EUR', 'Avro', '€'),
  ('USD', 'ABD doları', '$');

-- Maliyet unsurları: her biri tek bir bütçe kalemine bağlı (M1.1A ortak katalog eki)
INSERT INTO mod_m10.maliyet_unsurlari (kod, ad, butce_kalemi, sik, sira) VALUES
  ('ROBOT',            'Robot',                         'MALZEME',     true,  10),
  ('PLC',              'PLC ve HMI',                    'MALZEME',     true,  20),
  ('PNOMATIK',         'Pnömatik',                      'MALZEME',     true,  30),
  ('MEKANIK_MALZEME',  'Mekanik malzeme ve hammadde',   'MALZEME',     true,  40),
  ('ELEKTRIK_MALZEME', 'Elektrik malzemesi ve pano',    'MALZEME',     true,  50),
  ('ISIL_ISLEM',       'Isıl işlem',                    'FASON',       false, 60),
  ('FASON_IMALAT',     'Fason imalat',                  'FASON',       true,  70),
  ('NAKLIYE',          'Nakliye ve sevkiyat',           'FASON',       false, 80),
  ('GENEL_GIDER_PAYI', 'Genel gider payı',              'GENEL_GIDER', false, 90),
  ('DIGER',            'Diğer',                         'MALZEME',     false, 999);

-- M1.1B'nin etap şablonuyla aynı on kod, ad, sıra, paralel grup ve oran (ortak etap listesi)
INSERT INTO mod_m10.takvim_sablonu (kod, ad, sira, paralel_grup, bas_orani, bit_orani) VALUES
  ('ACILIS',       'Proje açılışı ve planlama',                       1, NULL,      0.000, 0.040),
  ('MEK_TASARIM',  'Mekanik tasarım (3D/2D)',                         2, 'TASARIM', 0.020, 0.220),
  ('OTO_TASARIM',  'Otomasyon tasarımı (elektrik, PLC/HMI mimarisi)', 3, 'TASARIM', 0.040, 0.300),
  ('SATIN_ALMA',   'Satın alma ve malzeme temini',                    4, 'TEDARIK', 0.150, 0.450),
  ('IMALAT',       'İmalat',                                          5, 'TEDARIK', 0.250, 0.550),
  ('MEK_MONTAJ',   'Mekanik, hidrolik ve pnömatik montaj',            6, 'MONTAJ',  0.500, 0.700),
  ('ELK_YAZILIM',  'Elektrik montajı ve yazılım',                     7, 'MONTAJ',  0.550, 0.750),
  ('TEST_FAT',     'Testler, ön deneme ve ön kabul (FAT)',            8, NULL,      0.720, 0.850),
  ('SEVK_KURULUM', 'Sevkiyat, saha kurulumu ve devreye alma',         9, NULL,      0.850, 0.950),
  ('KESIN_KABUL',  'Kesin kabul',                                     10, NULL,     0.950, 1.000);

INSERT INTO mod_m10.ayarlar (anahtar, deger) VALUES
  ('yonetim_birimleri',       '["YONETIM"]'),
  ('talep_no_deseni',         '"T-{YYYY}-{SIRA4}"'),
  ('varsayilan_para_birimi',  '"EUR"'),
  ('varsayilan_gecerlilik_gun', '30'),
  ('cevap_uyari_gun',         '3'),
  ('firma',                   '{"unvan": "Sibernetik", "adres": "Bursa", "telefon": "", "eposta": "", "web": ""}'),
  ('varsayilan_metinler',     '{"odeme_kosullari": "%40 sipariş ile, %50 sevkten önce, %10 kesin kabulde.", "teslim_kosullari": "Teslim yeri ve şekli sözleşmede belirlenir.", "notlar": ""}'),
  ('son_kurlar',              '{}');
```

## Ek C · `gelistirme/ornek_veriler.sql`

Yalnızca geliştirme ve sınama. Örnek firmanın birimleri (`MEK_TASARIM`, `IMALAT`, `PLANLAMA`) ve Ek D.5'in örneği için. Göç değildir; `veritabani/` altına konmaz.

```sql
-- Yalnızca geliştirme ve sınama: örnek firmanın birimleriyle ayarlar ve Ek D.5'teki örnek teklifin kataloğu.
-- Üründe bunları firma ayarlar ekranından girer.
UPDATE mod_m10.takvim_sablonu SET birim = CASE kod
  WHEN 'ACILIS'       THEN 'PLANLAMA'
  WHEN 'MEK_TASARIM'  THEN 'MEK_TASARIM'
  WHEN 'OTO_TASARIM'  THEN 'MEK_TASARIM'
  WHEN 'SATIN_ALMA'   THEN 'PLANLAMA'
  WHEN 'IMALAT'       THEN 'IMALAT'
  WHEN 'MEK_MONTAJ'   THEN 'IMALAT'
  WHEN 'ELK_YAZILIM'  THEN 'IMALAT'
  WHEN 'TEST_FAT'     THEN 'PLANLAMA'
  WHEN 'SEVK_KURULUM' THEN 'PLANLAMA'
  WHEN 'KESIN_KABUL'  THEN 'PLANLAMA'
END;

INSERT INTO mod_m10.makine_turleri (kod, ad, tipik_toplam_hafta) VALUES
  ('ROBOTIK_HUCRE', 'Robotik hücre', 26),
  ('OZEL_MAKINE',   'Özel makine',   20);

INSERT INTO mod_m10.baslangic_tablosu (makine_turu, birim, tipik_saat, tipik_sure_hafta) VALUES
  ('ROBOTIK_HUCRE', 'MEK_TASARIM', 120, 5),
  ('ROBOTIK_HUCRE', 'IMALAT',      100, 7),
  ('ROBOTIK_HUCRE', 'PLANLAMA',     40, 8);

INSERT INTO mod_m10.saat_ucretleri (birim, ucret, para_birimi) VALUES
  ('MEK_TASARIM', 1760.00, 'TRY'),
  ('IMALAT',      1408.00, 'TRY'),
  ('PLANLAMA',    1500.00, 'TRY');

INSERT INTO mod_m10.katalog_kalemleri (kod, ad, unsur, birim_fiyat, para_birimi, fiyat_tarihi, fiyat_kaynagi, tipik_temin_hafta, kritik) VALUES
  ('ROB-6E-20', 'Robot, 6 eksen, 20 kg', 'ROBOT', 28000.00, 'EUR', '2026-10-15', 'Tedarikçi teklifi', 10, true);

UPDATE mod_m10.ayarlar SET deger = '{"EUR": {"kur_try": "35.200000", "kur_tarihi": "2026-10-20"}}' WHERE anahtar = 'son_kurlar';
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
