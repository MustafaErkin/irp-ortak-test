# Sipariş Ve Bütçe · M11A Uyarlaması

31 Ekim 2026 · Özgün teslim: `disaridan_moduller/Modules/m1.1a/`. Gelen 0.1.0, MVP uyarlaması 0.1.1. İlk dosya özetleri `KAYNAK.json` içindedir; özgün klasör değiştirilmedi.

Python iş kuralları, donmuş teklif/sözleşme, muhasebeye devir, ödeme/teminat, bütçe/kapanış ve `mod_m11a` şeması korunur. Ekran mevcut ERP içinde HTML/CSS/JavaScript, ortak kullanıcı oturumu ve sabit beyaz düzenle çalışır.

- Çalışma sırasında M10 sağlayıcısı ortak SDK ve aynı normal kullanıcıyla okunur. Sahte sağlayıcı yalnız eski testler içindir; gerçek akışta seçilmez.
- `PROJE.ACTIM` gerçek çekirdeğe gider. Yerel dönüşüm önce ACILIYOR tutulur; ağ yanıtı belirsizse silinmez. Göç 004 tam olay zarfını ağdan önce kalıcılaştırır. Yeniden deneme/süreç yeniden başlatma aynı olayı gönderir; kod ve müşteri benzerliği başarı sayılmaz.
- Başlangıç planı ve teknik girdiler M11B'ye normal kullanıcı sağlayıcılarıyla gider. Teknik dosyalar yetkili proje alanına fiziksel kopyalanır; eksik aktarım tamamlanmış gösterilmez. Ekrandan tekrar denenebilir. Ticari teklif PDF'si tutar görme rolü ister.
- Bütçe ilerlemesi `PROJE_DURUM.yuzde` değeridir; ayrı parça oranı hesaplanmaz. Tahmini işçilik çekirdekteki emek payı/atölye saati ile teklif saat ücretinden gelir. Maaş okuma yetkisi açılmaz. Eksik ücret/kur sıfır gerçekleşen sayılmaz.
- Dar SQL rolü, istekle sınırlı bağlantı ve ortak SDK kullanılır; genel servis anahtarı modüle geçmez. Dosya sınırı 1 MB ve mevcut MVP sunucusunun özel deposudur.

Gerçek dönüşüm, kaynak devri, yanıt kaybı ve ekran kanıtı `codex/sonuclar/moduller_mvp.json` içindedir. Satın alma modülü gelmediğinden malzeme/fason gerçekleşeni bilgi yoktur; sıfır veya tamam sayılmaz. Kullanıcı kabulü ayrıca yapılır.
