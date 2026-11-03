# Yeni Modüle Başlarken

## Modül Sahibinin Vereceği Girdi

- Modülün adı ve çözdüğü iş; başlangıç, kullanıcı kararı ve beklenen son durum.
- Şartname maddeleri/görüşmeler ve varsa onaylı akış. İş akışı sırf paket örneğinden türetilmez.
- Hangi rolün hangi bilgiyi görüp hangi işlemi yapacağı; bu teslimin kapsamı ve sonraya ayrılanlar.
- Varsa başka modülden gereken bilgi ve ona verilecek sonuç.

Modül kodu/cihaz harfi entegrasyon ekibiyle tahsis edilir; örnekteki M3/M11B kodunu veya başka modülün şemasını kullanma. Bunlar netleşene kadar iş tanımı, ekran ve veri sahipliği çalışması ilerleyebilir.

## Geliştiricinin Çıktısı

1. [GELISTIRME_TALIMATI.md](sablonlar/GELISTIRME_TALIMATI.md) doldur: iş kapsamı, özel veriler, çekirdek kapıları, ekran/izin ve kabul senaryoları.
2. [Künye şablonunu](irp_sozlesme/sablonlar/kunye.json) kendi modülüne uyarla; yalnız kullanılan yetenekleri bildir. Sözleşme ve talimat ayrı belgelerdir.
3. Kendi çalışma alanına SDK'yı değişmeden al. [SDK testlerini](05_TESLIM_VE_KABUL.md) ve künye denetimini çalıştır.
4. [Ekran örneğinden](arayuz/on_yuz/ekran.js) tek giriş/bağlam ve beyaz ERP kalıbını kullan; kendi iş akışını, Python API'sini ve özel şemasını geliştir.
5. Başarı, yetki reddi, eksik/kapalı sağlayıcı, taslak koruma, tekrar ve yarım gönderim senaryolarını sınayıp [teslimi](sablonlar/TESLIM.md) hazırla. Gerçek çekirdek kabulü entegrasyon ekibiyle yapılır.

Yeni modül için `UYUM_RAPORU.md` ön koşul değildir. Eski sürümü uyarlama görevi verilirse mevcut davranışla farklar kısa not edilir. M10/M11A/M11B'nin işleri, yalnız adı aynı olduğu için yeni modülün kapsamına girmez.

## Çekirdekte Olması Gereken Bir İhtiyaç Çıkarsa

Önce güncel katalog ve sağlayıcılarla karşılanıp karşılanmadığını kontrol et. Karşılanmıyorsa [Geri Dönüş](sablonlar/GERI_DONUS.md) şablonuyla gereken girdi/çıktı, rol, kaynak ve işlevin bekleme durumunu yaz. Yeni motor, ikinci görev durumu veya doğrudan çekirdek SQL'i ekleme. Yeni iş kuralını onaylanmış sayma.
