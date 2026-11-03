# Değişiklikler

Her sürümde neyin değiştiği ve modülün ne yapması gerektiği. Paketin sürümü `SURUM` dosyasında.

## 1.2 · 31 Ekim 2026 · Ürün SQL 154

- Normal kullanıcıyla özel fiziksel dosya yükleme/okuma ve künye dosya kapısı eklendi. MVP sınırı 1 MB, mevcut sunucunun özel dizini; model testi kabul sayılmaz.
- İsteğe bağlı kalıcı olay zarfı eklendi; M11A proje açılışında yanıt kaybı ve süreç yeniden başlatma gerçek SQL'de sınanır.
- Özel modül nesnesine bildirim ve gerçek `NOT_ALICILARI` okuması eklendi. Kullanıcı/rol ve nesne izinleri korunur.
- Ayrıntı: `sozlesme/08_dosya_ve_kalici_istek.md`. M10/M11A/M11B gerçek MVP bağlantısı, ayrı test firmasında normal kullanıcı akışıyla sınanır; kullanıcı kabulü ayrıca yapılır.

## 1.1 · 31 Ekim 2026 · Çekirdek Tasarımı 10.2 / Ürün SQL 153

- Ortak web standardı kesinleşti: HTML/CSS/JavaScript, `ac(host)`, tek oturum ve sabit beyaz ERP. React/iframe teslimi uyarlama gerektirir.
- Modül Sözleşmesi ile modüle özgü Modül Geliştirme Talimatı ayrıldı; talimat şablonu eklendi.
- Gerçek SQL durumu ile eski tasarım katmanı/model kapsamı katalogda ayrıldı. Maliyet/sonuç kapılarının tamamı modele eklenmiş sayılmaz.
- PROJELER, PLAN.surumler ve GANTT.adlar/ortak etap özeti model uyarlamasına eklendi. Ürün SQL 153 bu isteğe bağlı alanları sağlar.
- Birden çok künye aynı sahte firmada ayrı servis kimliğiyle çalışabilir. Yetkili işletim ucu yalnız yerel testte özel anahtarla açılır.
- Mevcut PROJE_SORUMLUSU ve birim sözde rolleri V17'de tanınır; FIRMA/BIRIM kapsamı korunur.
- Ortak kurulum, dar servis rolü ve kullanıcı oturumuyla sağlayıcı yönlendirmesi belgelendi. İlk gerçek bağlantı M11B'dir; üç modülün tüm akışlarının kabulü anlamına gelmez.

## 1.0 · 29 Ekim 2026 · çekirdek 10.2

İlk sürüm.
- **Bağlantı katmanı:** `baglanti/`, iki sürücüyle: simülatör ve HTTP (Supabase biçimi).
- **Sahte bulut:** `simulator/sunucu.py`.
- **Araçlar:** künye, kayıt ve göç denetimi; senaryo doğrulama; paket denetimi.
- **Örnekler:** Çalışan bir örnek modül (`ornekler/M3_mini/`) ve altı örnek künye.
- **Açık:**
  - Ekranların yolu kesinleşmedi (`sozlesme/07_on_yuz.md`).
  - Servis okuması gerçek bulutta MVP'den sonra gelecek.
