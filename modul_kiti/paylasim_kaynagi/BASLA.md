# Yeni Modül Geliştirmek İçin Başlangıç

Bu, **bütün IRP modüllerine uygulanacak genel geliştirme standardıdır**. Yalnız mevcut M10/M11A/M11B'yi düzeltme görevi değildir. Hangi modülün geliştirileceğini modül sahibi söyler; üç modülün geçmişi veya örnek kaynaklar yeni görev listesi oluşturmaz.

## Birbirinden Ayrı Üç Girdi

| Girdi | Neyi Belirler? |
|---|---|
| **Modül Sözleşmesi** | Her modülün çekirdeğe/başka modüle bağlantısı, veri sahipliği, izinler ve teslim biçimi. `irp_sozlesme/` içindedir. |
| **Ortak Teknoloji Ve Arayüz Standardı** | HTML/CSS/JavaScript beyaz ERP, Python arka yüz, aynı oturum ve `ac(host)` ekran bağlantısı. |
| **Modül Geliştirme Talimatı** | Yalnız geliştirilecek modülün işi: kaynakları, kapsamı, rolleri, ekranları, özel verisi ve kabul senaryoları. Modül sahibi ve geliştirici birlikte netleştirir. |

## Okuma Ve Çalışma Sırası

1. [Sözleşme Ve Sahiplik](01_SOZLESME_VE_SAHIPLIK.md).
2. [Teknoloji Ve Arayüz](02_TEKNOLOJI_VE_ARAYUZ.md).
3. [Çekirdek Durumu](03_CEKIRDEK_DURUMU.md): SDK **1.2**, ürün SQL **154**. Eski durumla çalışma.
4. [Yeni Modül Başlangıcı](07_YENI_MODUL_BASLANGICI.md) ve [Geliştirme Talimatı şablonu](sablonlar/GELISTIRME_TALIMATI.md).
5. [SDK başlangıcı](irp_sozlesme/BASLA.md), oradaki teknik sözleşme ve [Teslim Ve Kabul](05_TESLIM_VE_KABUL.md).
6. Yalnız ilgiliyse [mevcut üç modülün geri bildirimleri](04_GERI_BILDIRIMLER.md) ve [Cevap 1 açıklaması](08_HAMDI_CEVAP1_ACIKLAMASI.md).

**İlk çıktı `GELISTIRME_TALIMATI.md`'dir.** Yeni modülde eski sürüm veya `UYUM_RAPORU.md` aranmaz. Eski bir modülün güncellenmesi açıkça istendiyse farkları [uyum notunda](sablonlar/UYUM_RAPORU.md) özetle; rapor ayrı bir bekleme aşaması değildir. Kaynakta olmayan iş kuralını öneri olarak ayır; modül sahibi adına karar verme.

## Uygulama

- Kendi modül klasöründe çalış; bu standart, SDK ve referansları yerinde düzenleme. Yeni SDK sürümü geldiğinde klasör bütünüyle, değiştirilmeden yenilenebilir; her dosya için ayrı izin beklenmez.
- Önce künyeyi ve kendi iş senaryolarını hazırla; ardından iş mantığı, özel şema ve ortak web ekranını geliştir. [SDK M3 mini örneği](irp_sozlesme/ornekler/M3_mini/modul/satin_alma.py) bağlantıyı, [küçük arayüz örneği](arayuz/on_yuz/ekran.js) görünüş/bağlamı gösterir. M3 mini, tamamlanmış satın alma ürünü değildir.
- Çekirdeğe yalnız `irp_sozlesme.baglanti` ile git. Kullanıcı işlemi normal oturumla yapılır. Servis kimliği, izinleri genişleten ekran okuması değildir.
- Çekirdek kişi/proje/etap/görev/plan/gerçekleşme/yetki/maaş kurallarını tekrar yazma. Olmayan ortak yetenek için [somut istek](sablonlar/GERI_DONUS.md) yaz; etkilenmeyen modül işlerini sürdürebilirsin.
- `ornekler/M11B/` mevcut MVP'nin 0.1.2 kaynak örneğidir. Onun planlama işini başka modüle kopyalama. Bir modülün yeni 0.2.0 teslimi, çekirdek ekibinin ayrı entegrasyon değişikliklerini kendiliğinden içermez.
- Teknik testleri ve gözlenen sonuçları bildir. Kullanıcı kabulünü Mustafa verir; simülatör sonucu gerçek SQL/servis kabulü değildir.

Motorların PC/Mac uygulamasında çalıştırılması ve bulutta tutulmaması konusu MVP sonrasında konuşulacaktır. **Bugün alınmış bir mimari değişiklik kararı değildir**; yeni modülü bu gelecekteki varsayımla geliştirme.
