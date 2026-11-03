# Proje Planlama · M11B Uyarlaması

31 Ekim 2026 · Kaynak: `disaridan_moduller/Modules/m1.1b/` · Gelen sürüm 0.1.0, uyarlama 0.1.2.

Teslim edilen klasör değiştirilmedi. Kaynak Python/SQL dosyalarının ilk özetleri `KAYNAK.json` içinde korunur. Bu klasör çalıştırılacak, incelenmiş uyarlamadır; orijinal teslimin aynısı olduğu iddia edilmez.

- React ekranı taşınmadı. `on_yuz/ekran.js`, karar 157'deki ortak HTML/CSS/JavaScript ve beyaz ERP düzenini kullanır. Ortak oturum, kişi, proje, düğme, tablo ve Gantt yardımcıları kullanılır.
- Python iş mantığı ve özel şema korunur. Ortak SDK dağıtım kökündeki `onboarding/irp_sozlesme` paketinden gelir; ikinci SDK kopyası tutulmaz.
- PLAN okuması `surumler=True` ile çekirdek B0/B1… listesini alır; modül dışındaki onaylar da görünür. Gönderimden sonra numara çekirdekten alınır. Modülün eski özel defteri ortak planın kaynağı değildir.
- GANTT `adlar=True` kullanır; yetkili görev adları gösterilir. Etap özeti tüm gerçekleşmeden gelirken alt görevler izinle süzülür.
- Projeler listesi gerçek PROJELER okumasını kullanır; henüz devredilmeyen yeni proje hazır plan sayılmaz. Ortak ekrandaki mevcut etaplar esas alınır. CEO şablon etap ekleyebilir; yöneticiye yeni etap açma yetkisi eklenmez.
- Bağlantı havuzu en çok dört bağlantıdır ve hazırlanmış sorgular kapalıdır; sekiz bağlantıyla sınırlı dar rol ve işlem havuzuyla uyumludur.
- Çalışma/test veritabanı bağlantısı açık ortam ayarı gerektirir; teslimin varsayılan yerel yönetici bağlantısına kendiliğinden düşülmez.
- Kullanıcı ekranında iç kimlik, kişi kodu ve ham olay adı yazılmaz. Kişi değişiminde istek ve modül pencereleri kapanır. Kaydedilmemiş plan otomatik yenilemeyle silinmez.

T28'de M11A başlangıç planı/teknik girdilerinin gerçek tüketimi ve özel fiziksel dosya devri eklendi. Aynı kaynak ikinci kez alınmaz. Belgeler ortak dosya kapısıyla yüklenip indirilir (MVP 1 MB). Not dökümü `NOT_ALICILARI` gerçek okumasından gelir; on kişi sınırı veya görev kimliği tahmini kullanılmaz. Alıcı kabulü çekirdeğin normal görev ekranındadır.

Ekranda devir/açılış adımları, plan sürümleri, görev ve tasarım gözden geçirme alanları, not/ek/alıcılar, belge yükleme/indirme ve birim eşleme ayarları vardır. Gerekçeli tasarım kapısı geçişi yalnız proje sorumlusunundur. Otomatik sınama kullanıcı kabulü sayılmaz; gelen 18 eski senaryonun tümü yeniden oynatılmış iddia edilmez. İlk bağımsız planlama kanıtı `codex/sonuclar/modul_ortak_baglanti.json`, üçlü gerçek akış kanıtı `codex/sonuclar/moduller_mvp.json` içindedir.
