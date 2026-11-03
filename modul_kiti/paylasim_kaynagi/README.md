# Sibernetik IRP · Genel Modül Geliştirme Standardı

Bu paket **yeni bir IRP modülü geliştirmek için ortak girdidir**. Satın alma, kalite, bakım veya başka bir iş alanı için aynı standart kullanılır. Modülün ne yapacağını sahibi belirler; paket bu işi çekirdeğin mevcut yetenekleri, ortak teknoloji ve arayüzle nasıl geliştireceğini anlatır.

## Yapay Zekâya Verilecek Metin

> Bu klasördeki BASLA.md dosyasını oku. Bu paket bütün yeni IRP modülleri için ortak geliştirme standardıdır. Benim vereceğim modül iş tanımı ve kaynaklardan başlayarak GELISTIRME_TALIMATI.md hazırla: kapsam, veri sahipliği, roller, ekranlar, çekirdekte kullanacağın okumalar/olaylar, diğer modüllerle bağlantı ve kabul senaryoları. Ardından bu kapsamda modülü geliştir. Yeni modülde eski sürüm uyum raporu isteme. Mevcut modülü güncellemeni ayrıca istersem eski sürümle farkları kısa not et. M10/M11A/M11B örneklerini kendiliğinden değiştirme; bunlar ortak kuralların nereden geldiğini ve bağlantı biçimini gösterir. Çekirdeğin işini modülde tekrar yazma. SDK 1.2 ve HTML/CSS/JavaScript beyaz ERP standardını kullan.

**İlk çıktı:** modüle özgü [Geliştirme Talimatı](sablonlar/GELISTIRME_TALIMATI.md). İş tanımı verilmediyse modül adı ve iş akışını modül sahibinden öğren; paketteki üç modülü otomatik çalışma listesi sayma.

Başlangıç: [BASLA.md](BASLA.md). Yeni modül adımları: [07_YENI_MODUL_BASLANGICI.md](07_YENI_MODUL_BASLANGICI.md). Eski üç modülün geri bildirimleri [04](04_GERI_BILDIRIMLER.md) içinde yalnız ilgili geliştirme için başvurudur. [08](08_HAMDI_CEVAP1_ACIKLAMASI.md) önceki paketin neden üç modül uyarlaması olarak anlaşıldığını açıklar.

Görünüş için bu klasörde `python3 -m http.server 8765 --bind 127.0.0.1` çalıştır, `http://127.0.0.1:8765/arayuz/` adresini aç. Windows'ta `python` kullanılabilir. Bu önizleme sentetiktir; çekirdek kabul testi değildir.

Paketin tamamını paylaş; `SURUM.json` sürümü/kaynak commit'i, `BUTUNLUK.json` dosya bütünlüğünü gösterir. Kontrol: `python3 -I -B KONTROL.py`. Canlı ayar, şifre veya firma iş verisi içermez.
