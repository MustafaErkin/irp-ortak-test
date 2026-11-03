# Teslim Ve Kabul

Yeni modül veya mevcut modülün yeni sürümü ayrı klasör/sürümlü commit olarak gelir. Varsa önceki teslim korunur. Bu paket sırf doküman olarak okunmaz; kod, künye ve senaryo tesliminin ölçütüdür.

## Teslim İçeriği

| Dosya / Klasör | Beklenti |
|---|---|
| `UYUM_RAPORU.md` | **Yalnız mevcut modül güncelleniyorsa:** eski sürümle farkların kısa notu. Yeni modül için zorunlu değildir. |
| `GELISTIRME_TALIMATI.md` | Modülün kaynaklı iş kapsamı, veri sahipliği, ekranlar ve kabul senaryoları. |
| `kunye.json` | Yeni semantik sürüm; kullanılan okuma/olay/sağlayıcı, rol, şema, para/kişisel veri beyanları. Kod/harf tahsisleri keyfî değiştirilmez. |
| `on_yuz/ekran.js` | Ortak `ac(host)` HTML/CSS/JS ekranı; kendi giriş veya üst kabuğu yok. |
| Python / ASGI arka yüz | Giriş noktası ve çalışma değişkenlerinin adları; normal kullanıcı oturumu, tek SDK. |
| `veritabani/NNN_*.sql` | Yalnız kendi şeması, yeni ileri göçler. Uygulanmış göçün içeriği değişmez. |
| Bağımlılık dosyası | Kullanılan sürümler ve kendi ortamındaki kurulum sonucu. Canlı adres/şifre/anahtar içermez. |
| `testler/`, `senaryolar/` | Gerçek senaryo girdisi/beklentisi ve gözlenen test çıktısı. Beklenen yetki reddi de açıklanır. |
| `istekler/` | Her açık ihtiyaç ayrı kimlik, kaynak, yeniden üretim ve sahiplik önerisiyle. |
| `TESLIM.md` | Paket/sürüm, komut sonuçları, ekran/izin/kapı listesi ve açık işler. [Şablon](sablonlar/TESLIM.md). |

Modülün çalışma klasöründe `irp_sozlesme/` bu paketteki **aynı** SDK kopyası olmalıdır; eski 1.0/1.1 ile güncel 1.2 karıştırılmaz. Üretimde ortak SDK sağlanır, modüle özel çatallanmış SDK taşınmaz. Modül kaynak kodunda mutlak Mac yolu, sabit servis URL'si veya kullanıcı şifresi bırakılmaz.

## Kontroller

1. Paketin kökünde `python3 -I -B KONTROL.py`.
2. SDK bütünlüğü: `python3 -I -B irp_sozlesme/arac/paket_denetle.py`.
3. SDK testleri: `python3 -I -B -m unittest discover -s irp_sozlesme/testler`.
4. Kendi modül klasöründe `python3 -I -B irp_sozlesme/arac/kunye_denetle.py .`; uyarıları da değerlendir.
5. SDK'nın senaryo doğrulayıcısıyla sözleşme senaryoları ve modülün kendi testleri. Sonuç okumalarının modelde bulunmayan kısmı için gerçek SQL denemesi istenir; sahte başarı üretilmez.

Arayüz önizlemesi görünüş/bağlantı kalıbıdır, bu kontrollerin veya gerçek motor kabulünün yerine geçmez. M11B kaynak örneğinin tam arka yüzünü çalıştırmak ayrıca kendi ayrı PostgreSQL test ortamını ister; canlı gösteri bağlantısı bu pakette yoktur. Eski geliştirme sıfırlama komutları üretim kurulum yolu değildir.

## Teknik Kabul Senaryoları

- Normal kullanıcının işi baştan sona; mevcut çekirdek durumu/onayı ve özel modül verisi doğru sahipte.
- Yetkili ve yetkisiz kişi/proje; menü, işlem, kişisel veri ve para ayrı denetlenir.
- Bayat karar, aynı olayın tekrarı, çift tıklama, yarım gönderim ve yeniden açılış. Başarı sonucu kesin değilse yeni olayla otomatik tekrar yapılmaz.
- Kişi değişimi, oturum yenileme, geç gelen cevap, modülden ayrılma; taslak/pencere/istek temizliği.
- Sağlayıcının açık, kapalı, yetkisiz veya bilgisiz olması; alan ve kaynak sürümü iki tarafta aynı anlamda.
- Tekrar kurulum, modül pasifleştirme ve eski veriyi koruma. Yeni/izinsiz çekirdek yetkisi verilmemesi.

Aynı senaryo önce uygun deneme ortamında, sonra çekirdek ekibinin ayrı gerçek SQL firmasında sınanır. Gerçek depolama/sinyal/giriş gerektiren iddia ilgili gerçek servisle doğrulanır. Teslim eden ekip kendi test sonucunu bildirir; son kullanıcı kabulünü Mustafa yapar. Teknik teslim ve Mustafa'nın kullanım kabulü ayrı aşamadır; eski bir test turunun adı bütün yeni modüllerin kabul planını belirlemez.
