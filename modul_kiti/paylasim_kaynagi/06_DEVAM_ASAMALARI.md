# Yeni Modül İçin Geliştirme Sırası

| Aşama | Sorumlu | Somut Sonuç |
|---|---|---|
| 1. İşi tanımla | Modül sahibi + geliştirici | Şartname/görüşme kaynaklarıyla modüle özel GELISTIRME_TALIMATI.md: kullanıcı işi, kapsam, veri sahibi, roller, ekranlar ve kabul senaryoları. |
| 2. Bağlantıyı eşle | Modül geliştiricisi | Güncel katalogla okuma/olay/sağlayıcılar; künye, özel şema ve bağımlılıklar. Gerçek eksik varsa kaynaklı istek; çekirdeği taklit etmeden etkilenmeyen işlere devam. |
| 3. Geliştir | Modül geliştiricisi | Python iş mantığı ve özel veri, ortak HTML/CSS/JavaScript ekranı, testler ve senaryolar. |
| 4. Teslim et | Modül geliştiricisi | Kaynak/sürüm, künye, ileri göçler, bağımlılıklar, gözlenen test sonuçları ve açık ihtiyaçlar. Eski modül yenileniyorsa kısa fark notu. |
| 5. Gerçek çekirdeğe bağla | Entegrasyon ekibi + gerekirse geliştirici | Ayrı gerçek SQL firmasında izin/sağlayıcı/tekrar/iş akışı; sonra mevcut işleri koruyan kurulum. |
| 6. Kullanım ve düzeltme | Mustafa + ilgili ekip | Gerçek kullanım, madde madde geri bildirim, etkilenen yolları tekrar deneme. Genel bağlantı bulgularını standarda işleme. |

M10/M11A/M11B için entegrasyon ve teknik test aşaması zaten tamamlandı (karar 160). Mustafa'nın bütün ekran rehberi hazırdır (161). Hamdi'den gelen 0.2.0 teslimleri ayrı gelişme koludur; bunların farkları ayrıca karşılaştırılmadan mevcut MVP sürümlerinin üzerine konmaz. Bu paket yeni modül geliştirmeyi yalnız o üç modüle geri döndürmez.

PC/Mac motorlarının ve bulut kullanımının yeniden değerlendirilmesi MVP sonrasına ayrıldı; bu sıranın ön koşulu değildir.
