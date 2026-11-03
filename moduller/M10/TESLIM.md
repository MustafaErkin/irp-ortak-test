# Teslim: M10 Teklif hazırlama · sürüm 0.1.0

*Tarih: 2026-10-29 · Paket: paket 1.0 · çekirdek 10.2 · 2026-10-29 · Sahibi: A ekibi*

## 1. Özet

M1.0, müşterinin ilk temasından onaylı teklifin müşteriye gönderilmesine kadar olan işi taşır.

- **Talep:** Satış yöneticisi talebi açar: müşteri, kaynak (yeni iş, ek iş, servis), makine türü, gereksinimler, kapsam, dosya kayıtları.
- **Sürüm (V1, V2…):** Boş başlatılır ya da bu talepten veya eski bir talepten kopyalanır. Dört bölümü vardır:
  - maliyet: kaynak etiketi, temin süresi, para birimi ve kurla
  - işçilik: başlangıç tablosu ve geçmiş projelerin önerisiyle
  - takvim: şablon, Gantt, uzun temin süreli kalemle "en erken teslim"
  - fiyat: kâr ile fiyat birbirinden hesaplanır; iki anlamı da görünür
- **Onay:** Teklifi CEO onaylar (telefondan da), kendisi düzeltir ya da gerekçeyle geri gönderir.
- **Kapı:** Onaylanmamış teklif hiçbir rolle "gönderildi" yapılamaz. Gönderilen sürüm donar.
- **Sipariş:** Kazanılan sürüm `M10.KAZANAN_SURUM` okumasıyla M1.1A'nın siparişe dönüştürme penceresine geçer.
- **Çekirdekle konuşma:** M1.0 çekirdeğe olay yazmaz (künye: `olay_yolu: YOK`). Yalnızca kullanıcının gözüyle `KISILER`, `BIRIMLER` ve `PROJE`'yi okur. Teklif projesizdir; çekirdeğe açılmaz (K-30).

## 2. Denetimler

Hepsi `uv venv --python 3.15` ortamında (Python 3.15.1), modülün klasöründen koşuldu.

| Komut | Sonuç |
|---|---|
| `python3 irp_sozlesme/arac/paket_denetle.py` | Paket sağlam (1.0 · çekirdek 10.2 · 99 dosya). Not: `irp_sozlesme/.DS_Store` "fazla" görünüyor; macOS Finder'ın dosyasıdır. Pakete dokunulmadı; git'te yok sayılır |
| `python3 -m unittest discover -s irp_sozlesme/testler` | 7/7 |
| `python3 irp_sozlesme/arac/kunye_denetle.py .` | 0 hata, 1 uyarı. Uyarı V17: `PROJE.ACTIM` modülün olaylarında yok. Beklenen: yetkiyi `SATIS`'in sahibi M1.0 önerir, olayı M1.1A yazar (SPEC › 5, 12). G01–G09 göç denetimi temiz (`003_iscilik_sira.sql` dahil) |
| `python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json` | 2 senaryo. `M1001`: 8 olay kabul (kurulum ve zemin), 34 okuma tamam, ret yok. `M1002`: 9 olay kabul, 5 okuma tamam, **1 okuma hatası (YETKI)**: beklenen (bkz. 3). Beklenmeyen ret yok |
| Modülün kendi testleri | `pytest`: 203/203 (saf fonksiyonlar, API ve yetki, veritabanı kısıtları, PDF, sözleşme). `npm test` (on_yuz): 11/11 |

## 3. Çekirdekle konuşma

| Yol | Ne için | Senaryo |
|---|---|---|
| okuma `KISILER` (kullanıcının gözü) | İsteği yapan kişiyi tanımak: rol, birim, M1.0'a erişim; ekranda kişi adları. İstek başına bir kez | `M1001_teklif_dongusu`, `M1002_bagli_proje` |
| okuma `BIRIMLER` (kullanıcının gözü) | İşçilik, başlangıç tablosu, saat ücreti, etap birimi ve yönetim birimleri çekirdeğin birim listesinden doğrulanır | `M1001_teklif_dongusu` |
| okuma `PROJE` (kullanıcının gözü) | Ek iş ve servis talebinin bağlı projesi. Göremeyen 403 alır, talep açılmaz | `M1002_bagli_proje` (1 beklenen `YETKI`, sonra kabul) |
| sağlanan `M10.KAZANAN_SURUM {surum}` | M1.1A'nın siparişe dönüştürmesi. `GET /api/saglanan/…`, kullanıcının anahtarıyla (Ek D.4–D.5; istek M10-02) | `M1001_teklif_dongusu`: cevap Ek D.5'e eşit (kimlik, an, PDF dışında); K041 403; taslak sürüm 409 `KAPI` |
| sağlanan `M10.KATALOG_TEMIN_SURELERI` | Katalog kalemlerinin tipik temin süresi; fiyat yok (Ek D.6) | `testler/test_sozlesme.py` |
| olay | Yok (`olay_yolu: YOK`) | — |
| bildirim | Yok: projesiz kayda bildirim kapısı yok (istek M10-01) | — |

## 4. Ekranlar

Ön yüz: `on_yuz/` (React 18, TypeScript, Vite). Ekran → modülün arka yüzü (`/api`) → bağlantı katmanı; ekran çekirdeği çağırmaz. Görünüş Ek D.12 (M1.1B ile ortak). Derin bağlantı yok: teklif projesizdir.

| Ekran | Ne gösterir | Kim görür | Okuma | Olay |
|---|---|---|---|---|
| Talepler listesi (`/`) | Tablo, arama ("çakma autoliv"), süzgeçler (müşteri, makine türü, durum, yıl), sayaç şeridi (kazanılan, kaybedilen, oran, kayıp nedenleri, açık), ▲ cevap tarihi; yeni talep. Onaycıya her sayfada "Onayınızı bekleyen N teklif" şeridi | M1.0'a erişimi olan | `KISILER`, `PROJE` (yeni talepte) | — |
| Talep kartı (`/talep/:t`) | Müşteri, kaynak ve bağlı proje, tarihler, durum; gereksinimler (belirsiz/cevapsız sayısı), kapsam, dosya kayıtları (SHA-256 parmak izi tarayıcıda); sürümler, yeni sürüm (boş, bu talepten, eski talepten); teklif vermiyoruz; müşterinin cevabı; geri aç; geçmiş ve "onaycı düzeltmeleri" süzgeci | M1.0'a erişimi olan; düzenleme `SATIS`, `YETKILI` | `KISILER`, `PROJE` | — |
| Teklif sürümü (`/surum/:s`) | Sabit özet şeridi (maliyet, fiyat, kâr, marj, en erken teslim, durum). Alt alta: Genel ve kurlar, Maliyet (katalogdan çek, "Diğer…", kataloğa da kaydet, kaynak, temin, kritik, kırılım), İşçilik (öneri, önerileri doldur), Takvim (şablondan doldur, SVG Gantt, kayma ▲), Fiyat (iki anlam). PDF, onaya gönder; onaycıya onayla / kendim düzelt / geri gönder; gönderildi; düzenlemeye aç; "Kazanıldı · Siparişe dönüştür" | M1.0'a erişimi olan; düzenleme SPEC › 6'ya göre | `KISILER`, `BIRIMLER` | — |
| Telefondan onay (`/onay/:s`) | Dar ekran: müşteri, konu, maliyet, fiyat, kâr ve marj, teslim ve en erken teslim, taslak PDF; "Onayla" ve "Gerekçeyle geri gönder" | `YETKILI` | `KISILER` | — |
| Müşteriler (`/musteriler`, `/musteri/:m`) | Liste ve kart: firma, adres, vergi, iletişim kişileri, strateji notu; aynı ad uyarısı; pasifleştirme | M1.0'a erişimi olan; düzenleme `SATIS`, `YETKILI` | `KISILER` | — |
| Ayarlar ve geçmiş veri (`/ayarlar`) | İki sekme. Ayarlar: unsurlar, kalem kataloğu, makine türleri, başlangıç tablosu (makine türü × birim), saat ücretleri, takvim şablonu (birim ve aktiflik), firma ve varsayılanlar, para birimleri, yönetim birimleri (yalnız `YETKILI`). Geçmiş proje formu | `SATIS`, `YETKILI`, yönetim birimleri | `KISILER`, `BIRIMLER` | — |
| Geliştirme girişi (`/giris`) | Örnek firmanın kişilerinden seçim | Yalnızca `M10_GELISTIRME=1` | — | — |

Elle duman testi: `gelistirme/BENIOKU.md`.

## 5. Modülün tabloları

Şema `mod_m10`. Göçler `veritabani/001_m10.sql` ve `002_varsayilanlar.sql` (SPEC Ek B, aynen), `003_iscilik_sira.sql`.

| Tablo | Ne tutar | Çekirdeğe bağı (kimlik) |
|---|---|---|
| `ayarlar`, `sayaclar` | Anahtar–değer ayarlar (`yonetim_birimleri` birim kodlarıdır); talep numarasının yıllık sırası (`sayac_ilerlet`) | `guncelleyen`: kişi kodu |
| `para_birimleri`, `maliyet_unsurlari`, `katalog_kalemleri` | Para birimleri; unsur → bütçe kalemi; tekrar kullanılan kalemler | `ekleyen`: kişi kodu |
| `makine_turleri`, `baslangic_tablosu` | Makine türü; tür × birim tipik saat ve süre | `birim`: birim kodu |
| `saat_ucretleri` | Birim başına teklif saat ücreti (varsayım; karar 104) | `birim`: birim kodu |
| `takvim_sablonu` | On etap (M1.1B ile ortak kodlar) ve firmanın birim eşlemesi | `birim`: birim kodu |
| `gecmis_projeler`, `gecmis_proje_saatleri` | Kapanmış projelerin birim bazında gerçek saatleri, elle | `proje_kodu` serbest metin; `birim`: birim kodu |
| `musteriler`, `musteri_kisileri` | Müşteri ve iletişim kişileri (kişisel veri) | — |
| `talepler`, `talep_dosyalari`, `gereksinimler`, `kapsam_satirlari` | Talep, dosya kaydı, gereksinim, kapsam | `bagli_proje`: proje kimliği; `olusturan`, `ekleyen`: kişi kodu |
| `teklif_surumleri`, `surum_kurlari`, `maliyet_kalemleri`, `iscilik_satirlari`, `takvim_satirlari` | Sürüm, onaylı PDF ve donmuş özet; kurlar; dört bölümün satırları | `hazirlayan`, `onaylayan`, `gonderen`: kişi kodu; `iscilik_satirlari.birim`: birim kodu |
| `onay_kayitlari`, `islem_gecmisi` | Onay ve düzeltme kaydı (bilgi havuzu); her değişiklik: kim, ne, ne zaman, ayrıntı | `kim`: kişi kodu |

Çekirdeğe yabancı anahtar yok (G08). Gönderilmiş sürüm satırını tetikleyici korur, çocuk satırlarını modülün kuralı (409).

`003_iscilik_sira.sql` neden var: Ek D.5 işçilik satırlarını girildiği sırayla verir. Ek B'nin `iscilik_satirlari` tablosunda sıra sütunu yok. Modülün kendi şemasına yalnızca `sira` sütunu eklendi.

## 6. Çekirdeğe istekler

| Kod | Başlık | Önem |
|---|---|---|
| M10-01 | Projesiz modül kaydına bildirim yok: onay bekleyen teklif ve cevap tarihi hatırlatması çekirdeğin bildirim kutusuna düşemiyor | ONEMLI |
| M10-02 | Modüller arası okumaların yönlendirmesi yok: `oku('M10.KAZANAN_SURUM')` simülatörde `TANIMSIZ_VERI` | ONEMLI |
| M10-03 | Ortak katalog çekirdekte değil (maliyet unsuru ve bütçe kalemi, etap şablonu); M3'ten ortalama temin süresi ve kapanış farkı geri beslemesi bağımlılık döngüsüne (R08) takılıyor | ONEMLI |
| M10-04 | Kapanan projenin departman bazında gerçek saatleri okunamıyor (`PROJE_ISCILIGI` simülatörde yok) | DUSUK |
| M10-05 | Dosya depolama kapısı yok (yükleme, dosya kimliği, parmak izi); talep dosyaları yalnızca kayıt | ONEMLI |
| M10-06 | Ek iş ve servis talebinde bağlı proje seçilemiyor: `PROJELER` simülatörde yok, satış yöneticisi projeyi göremiyor (UYELER) | ONEMLI |

Kanıtlar 2026-10-29'da simülatörde yeniden denendi (`istekler/*.md`).

## 7. Kişisel veri ve para

- **Kişisel veri:** Yalnızca müşteri firmanın iletişim kişileri: ad, unvan, telefon, e-posta (`musteri_kisileri`). Nedeni teklifin hazırlanması ve sözleşmenin kurulmasıdır (KVKK m.5/2-c); künyede beyanlı.
  - Çalışanların yalnızca kodları tutulur; adlar ekranda `KISILER`'den okunur.
  - Müşterinin strateji notu yalnızca M1.0 ekranlarındadır; PDF'e ve `M10.KAZANAN_SURUM`'a girmez.
- **Para (`para: true`):**
  - Modül teklifin maliyetini, kurlarını, fiyatını ve saat ücreti varsayımını tutar.
  - Çekirdekten para okumaz: maaş ve saat maliyeti okunmaz, taklit edilmez.
  - Maliyet ve kâr yalnızca M1.0'a erişimi olana görünür; PDF'e ve `M10.KATALOG_TEMIN_SURELERI`'ne girmez.
  - `M10.KAZANAN_SURUM` yalnızca `SATIS`, `YETKILI` ve yönetim birimlerine açıktır.
