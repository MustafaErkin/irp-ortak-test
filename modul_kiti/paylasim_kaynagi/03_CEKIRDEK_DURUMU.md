# Çekirdeğin Ve Ortak Bağlantının Güncel Durumu

**SDK 1.2 · Ürün SQL 154 · Çekirdek tasarımı 10.2.** Sürüm/kaynak `SURUM.json`, kanıt kapsamı [durum/cekirdek_durumu.json](durum/cekirdek_durumu.json) içindedir. Bu bilgi yeni modül geliştirme girdisidir; yalnız M11B pilotunun eski durumuna göre çalışma.

| Yetenek | Uygulanmış Yol Ve Sınır |
|---|---|
| Ortak web | Tek HTML/CSS/JavaScript beyaz ERP; M10/M11A/M11B aynı oturum, menü ve proje bağlamında. Telefon Flutter'dır. |
| Kurulum/servis | Ayrı şema sahibi ve dar çalışma rolü, ileri göç, tekrar kurulum, pasifleştirme ve veri koruma. Üç modül mevcut Supabase'te kurulu; genel yönetici anahtarı modüle verilmez. |
| Ortak proje | Kullanıcının izinli `PROJELER` listesi; menü izni ve işlem yetkisi ayrıca denetlenir. Projeyi görmek ticari tutar/maaş izni değildir. |
| Plan/Gantt/görev | Çekirdek B0/B1… sürümleri ve etap gerçekleşeni tek kaynak. Modül taslağı özeldir. Atama→kabul→teslim→onay→Gantt ayrı gerçek SQL/tarayıcıda geçti. |
| Sağlayıcı devri | M10→M11A kazanılmış sürüm; M11A→M11B plan/teknik girdi devri çalışıyor. Künyede okuma/bağımlılık ve sağlayıcıda normal kullanıcı izni gerekir. |
| Özel dosya | SDK 1.2 gerçek yükleme/indirme ve izin/bütünlük denetimi. MVP sınırı 1 MB; dosya Mac'in özel dizininde, bilgileri SQL'de. Üretim dosya hizmetinin tamamı değildir. |
| Bildirim/not | Projesiz özel `MODUL` bildirimi; `NOT_ALICILARI` ile gerçek alıcı/kabul. Alıcı kimliği tahmin edilmez, on kişi sınırı konmaz. |
| Yarım kalan işlem | İsteğe bağlı kalıcı olay zarfı: ağdan önce tam istek kendi şemasına yazılır; yanıt kaybı/yeniden başlatmada aynı olay gönderilir. Her HTTP işlemi otomatik tekrar güvenli sayılmaz. |
| Maliyet/ilerleme | Çekirdek proje ilerlemesi ortak tanımdır. Ölçülen atölye saati, ofis zaman değeri, teklif saat ücreti ve maaş ayrı anlamdadır. Satın alma gelmediği için malzeme/fason gerçekleşeni bilgi yoktur. |

Üç modülün teknik zinciri ayrı gerçek PostgreSQL ve tarayıcıda doğrulandı; mevcut Supabase'e kurulum ve dört rolün sayfa/menü okumaları ayrıca doğrulandı. Kullanıcı kabulü, bütün yük/geri alma dalları ve yeni modülün işi bu sonuçla geçmiş sayılmaz.

## Hâlâ Sınır Olanlar

- Ortak `host.istek` hata gövdesinin yapılandırılmış alanlarını ekrana taşımıyor; bugün `message` ve `code` vardır. `govde/body/data/detail` adlarını tahmin ederek çözme. Alan bazlı veri gerekiyorsa somut ortak istek yaz. İkili indirmede `responseType:'blob'` zaten vardır.
- Genel modüller arası ekrana geçiş işlevi yok; izinli proje bağlamı ve kayıtlı modül adresi kullanılır. Projesiz sürüm numarasıyla geçiş kendiliğinden sözleşme sayılmaz.
- Yeni modülün bütün rol/sağlayıcı/şema izinleri kendi kabulünde sınanır; mevcut üç modül için verilen haklar diğerlerine otomatik verilmez.
- Ayrı maaş görme izni, bütün personel/rol/ekip işlemlerinin devri, kişinin kendi tarih tahmini ve ticari geri besleme MVP sonrasıdır.
- Motorları PC/Mac uygulamasında çalıştırmak ve bulutta tutmamak MVP sonrası görüşme başlığıdır; bugünkü çekirdek Supabase'te, modül iş mantığı Mac'te çalışır.

## Kataloğu Doğru Oku

[Çekirdek kataloğunda](irp_sozlesme/arac/cekirdek_katalogu.json) `urunde_mevcut` ve `urun_kaynagi` gerçek ürünü; `simulator` model desteğini ayrı gösterir. `katman:S` tek başına yokluk değildir. `URUN_SQL_GEREKLI` için sahte model başarısı üretme. Genel yetenek envanteri bir kaynak özetidir; yeni modülün bütün iş akışı için ayrıca test gerekir.
