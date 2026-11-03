# Teslim: M11A Sipariş alma ve muhasebeye devir · sürüm 0.1.0

*Tarih: 2026-10-30 · Paket: paket 1.0 · çekirdek 10.2 · 2026-10-29 · Sahibi: A ekibi*

## 1. Özet

Gönderilmiş ve kazanılmış teklif sürümünü (M1.0) tek tıkla siparişe dönüştürür: proje kodunu verir, projeyi
kullanıcının gözüyle `PROJE.ACTIM` ile çekirdekte açar, teklifin maliyet kırılımını başlangıç bütçesi, takvimini
başlangıç planı olarak dondurur. Ticari devir formu, eksik bilgi listesi, muhasebeye devir ve muhasebe gelen kutusu,
VEGA kart kodları, gerekçeli tutar değişikliği, bütçe şeridi (dolum ile ilerleme yan yana, ölçüm kullanıcının gözüyle)
ve kesin kabulde kalem bazında kapanış. Dört okuma sağlar (`M11A.BASLANGIC_PLANI`, `M11A.TEKLIF_GIRDILERI`,
`M11A.BUTCE_YUZDELERI`, `M11A.PROJE_BUTCESI`). Kod ve harf (`M11A`, `Q`) geçicidir.

## 2. Denetimler

| Komut | Sonuç |
|---|---|
| `python3 irp_sozlesme/arac/paket_denetle.py` | Paket sağlam. (`irp_sozlesme/.DS_Store` "FAZLA": macOS'un dosyası, pakete ait değil; dokunulmadı) |
| `python3 -m unittest discover -s irp_sozlesme/testler` | 7/7 |
| `python3 irp_sozlesme/arac/kunye_denetle.py .` | 0 hata, 0 uyarı |
| `python3 irp_sozlesme/arac/kunye_denetle.py . ../m1.0 ../m1.1b` | kayıt: 0 hata, 0 uyarı (M10'un 1, M11B'nin 2 uyarısı kendi künyelerinde) |
| `python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json` | 8 senaryo; beklenmeyen ret yok (beklenen retler aşağıda) |
| `pytest` (arka yüz, PostgreSQL 16) | 108/108 |
| `cd on_yuz && npm test` (vitest) | 7/7; `npm run build` (tsc + vite) temiz |
| Ortak ortam duman testi (`gelistirme/ortak_duman.py`) | M1.0 kazanıldı → M1.1A dönüştür, devret → M1.1B devri başlat: geçti |

Python 3.15.1 (`uv venv --python 3.15`). Makinenin `python3`'ü 3.9 olduğu için paketin araçları venv'in Python'uyla koşuldu.

**Senaryolar ve beklenen retler:**

| Senaryo | Çekirdeğin cevabı | Beklenen ret |
|---|---|---|
| `M11A01_siparise_donustur` | 11 olay kabul, 6 okuma | — |
| `M11A02_kod_ve_yetki` | 10 kabul; 1 `DURUM` (kod `2614` kullanılıyor), 1 `YETKI` (K004'ün doğrudan `PROJE.ACTIM`'ı) | `DURUM`, `YETKI` |
| `M11A03_muhasebeye_devir` | 12 kabul, 3 bildirim; 1 okuma hatası (K060 `PROJE` → `YETKI`, erişimden önce) | 1 okuma hatası |
| `M11A04_butce_olcumu` | 20 kabul, 17 okuma | — |
| `M11A05_bildirim_sapma` | 21 kabul, 8 bildirim | — |
| `M11A06_gorunurluk` | 15 kabul; 1 okuma hatası (K017 `PROJE` → `YETKI`) | 1 okuma hatası |
| `M11A07_tutar_ve_kapanis` | 12 kabul, 2 bildirim | — |
| `M11A08_ek_is` | 12 kabul; 1 `DURUM` (ana projenin kendi ana projesi var) | `DURUM` |

Okuma hataları senaryo sayımında `sorgu: hata PermissionError` olarak görünür (çekirdekte `YETKI`).

## 3. Çekirdekle konuşma

Bütün çağrılar `irp_sozlesme.baglanti` üzerinden (`m11a/baglanti.py`); başka yol yok. M1.0'a giden tek kapı
`m11a/saglayicilar.py` (istek M11A-02).

| Yol | Ne için | Senaryo |
|---|---|---|
| olay `PROJE.ACTIM` (kullanıcının gözü; ek işte ana projenin sürümüyle `neyin_ustunde`) | Siparişe dönüştürmede projeyi açmak | M11A01, M11A02, M11A08 |
| okuma `PROJE` | Her proje işinden önce görünürlük; dönüştürmenin doğrulanması ("Yeniden dene") | hepsi |
| okuma `KISILER` | Kişinin rolü (istek başına bir kez), sorumlunun aktifliği | hepsi |
| okuma `BIRIMLER` | Ayarlarda yedek saat ücretinin birimi | — (birim testi) |
| okuma `PROJE_DURUM`, `ETAPLAR`, `NESNELER` | Bütçe ölçümü (etap saati × donmuş ücret; parça ilerlemesi) | M11A04, M11A05, M11A06, M11A07 |
| bildirim `TICARI_DEVIR` (ROL MUHASEBE) | Muhasebeye devir; süzülen kaldıkça yeniden bırakma; tamamda kaldırma | M11A03 |
| bildirim `TUTAR_DEGISTI` (ROL MUHASEBE) | Tutar değişikliği; kapanışta ve proje kapanınca kaldırma | M11A05, M11A07 |
| bildirim `BUTCE_SAPMASI` (KISI satış yöneticisi + ROL YETKILI) | Dolum ilerlemeyi eşikten fazla geçince; yolunda olunca kaldırma | M11A05 |
| servis okuması `PROJE` | Kural işinde yalnızca "proje aktif mi" (para ve saat yok) | M11A05 (servis okuması senaryoya yazılmaz) |

## 4. Ekranlar

Yol: `AYRI_UYGULAMA` (React 18, Vite). Ekran → modülün arka yüzü (`/api`) → bağlantı katmanı; ekran çekirdeği doğrudan
çağırmaz. Derin bağlantı: `PROJE` bağlamında `/proje/{kimlik}` ("Ticari bilgiler ve bütçe (M1.1A)").

| Ekran | Ne gösterir | Kim görür | Okuma | Olay |
|---|---|---|---|---|
| Siparişe dönüştür (`/donustur?surum=`) | Önizleme: kod, sipariş adı, tarihler, sorumlu, PO ve sözleşme, bütçe ve takvim; sonuç ve M1.1B geçişi; "Yeniden dene" | `SATIS`, `YETKILI` | `M10.KAZANAN_SURUM` (M1.0'dan), `PROJE`, `KISILER` | `PROJE.ACTIM` |
| Proje kartı (`/proje/{kimlik}`) | Üstte bütçe şeridi; sekmeler Özet (sipariş, PO, VEGA, devir durumu), Ticari, Bütçe, Başlangıç planı, Teklif girdileri (PDF) | Projeyi gören; Ticari ve bütçe paneli tutarları görene | `PROJE`, `PROJE_DURUM`, `ETAPLAR`, `NESNELER`, `KISILER` | — |
| Ticari sekmesi | Ödeme takvimi, teminat, faturalama, teslim, ihracat, teşvik; eksikler; devret / aldım / tamamla; VEGA | `SATIS`, `MUHASEBE`, `YETKILI` | `PROJE` | — |
| Bütçe sekmesi ve tutar değişikliği formu | Dört kalemin başlangıç, güncel, tahmini gerçekleşen çubukları; tutarlar; değişiklikler; işçilik ve ilerleme ayrıntısı; kapanış ve düzeltme | Panel `SATIS`, `MUHASEBE`, `YETKILI`; form `SATIS`, `YETKILI`; kapanış `MUHASEBE`, `YETKILI` | `PROJE`, `PROJE_DURUM`, `ETAPLAR`, `NESNELER` | — |
| Muhasebe gelen kutusu | Devredilen ve görülen projeler, eksikler, VEGA (satırda), yaklaşan ödeme ve teminat tarihleri | `MUHASEBE`, `YETKILI` | `PROJE` | — |
| Bütçeler listesi | Bütün görülen projelerin şeridi; kırmızılar önce | `SATIS`, `MUHASEBE`, `YETKILI` | `PROJE`, `PROJE_DURUM`, `ETAPLAR`, `NESNELER` | — |
| Ayarlar | Kalıplar, sıra kapsamı, sapma eşiği, yaklaşan tarih günü, yedek saat ücretleri | `YETKILI` | `BIRIMLER` | — |
| Geliştirme girişi | Kişi seçimi | Yalnızca `M11A_GELISTIRME=1` | — | — |

Mavi yakanın telefonuna düğme eklenmedi. Bildirimler çekirdeğin kutusundadır; modülün ayrı kutusu yok.

## 5. Modülün tabloları

Şema `mod_m11a` (`veritabani/001_m11a.sql`, `002_varsayilanlar.sql`). Çekirdeğe yabancı anahtar yok (G08).

| Tablo | Ne tutar | Çekirdeğe bağı (kimlik) |
|---|---|---|
| `olay_sayaci` + `olay_sirasi()` | Olay kimliğinin kişi ve gün başına sırası | kişi |
| `sayaclar` + `sayac_ilerlet()` | Proje kodu ve yıllık sipariş sırası | — |
| `ayarlar`, `saat_ucretleri` | Kalıplar, eşik, gün; yedek saat ücreti | birim |
| `projeler` | Projenin M1.1A kaydı, donmuş teklif, PDF, sözleşme ve güncel tutar, kurlar, VEGA, bütçe durumu ve kapanış | proje, kişi (sorumlu, açan) |
| `butce_satirlari`, `proje_saat_ucretleri`, `baslangic_plani` | Dört kalem (başlangıç donmuş), donmuş birim ücretleri, tarihlenmiş teklif takvimi | proje, birim |
| `dosya_kayitlari` | PO, sözleşme, teminat, tutar değişikliği belgesi, fatura: ad, konum, parmak izi | proje |
| `ticari_kosullar`, `odeme_satirlari`, `teminatlar` | Ticari devir formu | proje |
| `devirler`, `eksik_bilgiler` | Muhasebeye devir, son alıcılar ve süzülenler; eksik listesi | proje, kişi |
| `tutar_degisiklikleri` | Eski ve yeni güncel tutar ve bütçe, gerekçe, belge | proje, kişi |
| `butce_olcumleri` | Yalnızca yüzdeler, kapsam, eşik, uyarı, bilinmeyen saat | proje, kişi |
| `acik_bildirimler` | Çekirdekte açık duran bildirimlerimiz | proje |
| `kapanis_farklari`, `kapanis_sonrasi_duzeltmeler` | Kalem bazında fark; kilitten sonraki fatura | proje, kişi |

Değişmezler tetikleyiciyle korunur: sözleşme tutarı, para birimi, teklif sürümü, donmuş teklif, kurlar, PDF'in parmak
izi ve başlangıç bütçesi. Bir teklif sürümü bir kez dönüştürülür (`teklif_surumu` tekil).

## 6. Çekirdeğe istekler

| Kod | Başlık | Önem |
|---|---|---|
| M11A-01 | Muhasebe ve projeyi açan satış yöneticisi projeyi göremiyor (UYELER) | KRITIK |
| M11A-02 | Modüller arası okumaların yönlendirmesi yok | ONEMLI |
| M11A-03 | Parça ilerlemesi çekirdekte hesaplansın | ONEMLI |
| M11A-04 | Proje ve birim bazında saat okuması simülatörde yok | ONEMLI |
| M11A-05 | M3'e: proje bazında satın alma ve fason sipariş tutarları | ONEMLI |
| M11A-06 | `PROJE.ACTIM`'da kaynak kayıt alanı yok | DUSUK |
| M11A-07 | Dosya depolama kapısı yok | ONEMLI |
| M11A-08 | Sahte bulut tek künye kuruyor | DUSUK |
| M11A-09 | `PROJE.ACTIM` retlerinin nedeni ayırt edilemiyor (uygulama sırasında bulundu) | DUSUK |

## 7. Kişisel veri ve para

- **Kişisel veri:** Donmuş teklifteki müşteri iletişim kişileri (ad, unvan, telefon, e-posta), muhasebenin eksik
  ticari bilgiyi müşteriden istemesi için (KVKK m.5/2-c). Künyede beyanlı. Sağlanan okumalarda ve ekranlarda gösterilmez.
- **Para:** `para: true`. Modül kendi tutarlarını tutar (sözleşme ve güncel tutar, bütçe, ödeme, teminat, kapanış).
  Çekirdekten para okunmaz (`ISCILIK_MALIYETI`, `PROJE_MALIYETI`, `SAAT_MALIYETI` yok); servis gözüyle para ya da saat
  okunmaz. Tahmini işçilik = çekirdeğin saatleri × tekliften donmuş saat ücreti (karar 104). Tutarlar yalnızca
  `SATIS`, `MUHASEBE`, `YETKILI`'ye gösterilir; görmeyenin cevabında tutar alanı hiç yoktur. Bildirim metinlerinde ve
  yüzde okumalarında tutar yoktur.
