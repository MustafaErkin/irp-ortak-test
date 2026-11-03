# Cevap 1 · Önceki Paketle Kapsam Farkı

31 Ekim 2026 · Kaynak: Hamdi'nin paylaştığı üç 0.2.0 tesliminin UYUM_RAPORU/TESLIM belgeleri ve mevcut uygulama.

Önceki geliştirici paketi 1.0'ın hazır AI mesajı “Mevcut modülümü incele; önce UYUM_RAPORU hazırla” diyordu. Bu, genel yeni modül geliştirme amacı yerine mevcut M10/M11A/M11B'nin uyarlanmasına yöneltti. Üç 0.2.0 yanıtı bu görevle tutarlıdır. **Paket 2.0'ın varsayılan işi, sahibinin tanımlayacağı yeni modülü geliştirmektir.**

| Konu | Eski Yanıtın Dayandığı Bilgi | Bugünkü Standart |
|---|---|---|
| SDK/çekirdek | SDK 1.1, SQL 153 | SDK 1.2, SQL 154. |
| Dosya/PDF | Gerçek taşıma bekleniyor; PDF düğmesi pasif | Özel gerçek dosya yolu var, 1 MB. Ortak istekte `responseType:'blob'` destekleniyor. |
| Not alıcıları | Tahmini tarama veya henüz okunamıyor | Gerçek `NOT_ALICILARI` okuması var; tahmin nihai yol değildir. |
| Teklif→sipariş→plan | Sağlayıcı parametreleri/devir kabulü bekleniyor | Mevcut MVP sürümlerinde gerçek zincir sınandı. Bu, başka 0.2.0 kolunun kendiliğinden kabulü değildir. |
| `host.istek` hata ayrıntısı | Gövde adları tahmin ediliyor | Haklı bir ortak sınır: bugün `message/code` var; yapılandırılmış gövde henüz taşınmıyor. |
| Genel ekrana geçiş | Projesiz teklif sürümünden diğer modüle geçiş belirsiz | Genel geçiş sözleşmesi henüz yok; mevcut proje bağlamı/menü yolu geçerli. |

Sağlayıcı parametresi normal SDK çağrısında adlandırılmış alanla gider: örneğin `oturum.oku('M10.KAZANAN_SURUM', None, surum=12)`. Sağlayıcı kendi görünürlük/iş kuralını korur. Dosya ve tekrar güvenliği için SDK'nın [08 numaralı sözleşme ekini](irp_sozlesme/sozlesme/08_dosya_ve_kalici_istek.md) kullan.

Hamdi'nin 0.2.0 kaynakları ile mevcut MVP'nin M10/M11A 0.1.1 ve M11B 0.1.2 kaynakları iki ayrı gelişme koludur. Sürüm numarası büyüdü diye birini diğerinin üzerine koymak dosya, bildirim ve devir düzeltmelerini kaybettirebilir. Sonraki birleştirme, gerekli farklar üzerinden yapılır. Bu standart güncellemesi mevcut MVP'yi veya gelen orijinalleri değiştirmez.

Motorların PC/Mac uygulamasında çalışması ve bulutta tutulmaması ayrıca MVP sonrasında görüşülecek. Bu yanıta dayanan güncel modül geliştirme görevi için mimari varsayımı değildir.
