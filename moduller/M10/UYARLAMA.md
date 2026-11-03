# Teklif Yönetimi · M10 Uyarlaması

31 Ekim 2026 · Özgün teslim: `disaridan_moduller/Modules/m1.0/`. Gelen 0.1.0, MVP uyarlaması 0.1.1. Özgün teslim değiştirilmedi; ilk dosya özetleri `KAYNAK.json` içindedir.

Python iş hesabı, müşteri/talep, maliyet, sürüm, onay, PDF ve özel `mod_m10` şeması korunur. React arayüzünün yerine mevcut ERP'nin HTML/CSS/JavaScript `ac(host)` ekranı yazıldı. Ortak giriş ve kişi bağlamı kullanılır; ayrı kullanıcı deposu yoktur.

- Gerçek kazanılmış sürüm listesi ve `M10.KAZANAN_SURUM` ortak SDK üzerinden M11A'ya gider. Başka modül tablosu okunmaz.
- Talep dosyası ortak özel dosya kapısıyla gerçek bayt olarak yüklenip indirilir. Teknik devirde şartname/çizim vb. ayrılır; tedarikçi fiyat eki teknik sağlayıcıya açılmaz.
- Onay isteği ortak bildirim kutusuna düşer. Özel MODUL nesnesi kullanılır; henüz olmayan çekirdek projesi uydurulmaz. Kalıcı kuyruk, bildirim hatasında isteği korur.
- Çalışma bağlantısı açıkça verilir; havuz dört, rol sekiz bağlantıyla sınırlıdır. Modül genel veritabanı/servis anahtarı almaz. SDK ortak `onboarding/irp_sozlesme` kaynağından gelir.
- Beyaz ERP, isimli seçimler, formlar, dosya indirme ve taslak koruma kullanılır. Sayısal hesap Python'dadır.

Doğrulama kapsamı `codex/sonuclar/moduller_mvp.json` ve T28'dedir. Otomatik sınama kullanıcı kabulünün yerine geçmez. Fiziksel dosya sınırı MVP için 1 MB'dır; üretim dosya hizmeti bu çalışmanın kapsamı değildir.
