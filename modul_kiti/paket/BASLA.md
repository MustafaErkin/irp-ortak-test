# BAŞLA: Bu modül Sibernetik IRP çekirdeğine bu klasörün kurallarıyla bağlanır

*Modül sözleşmesi paketi · sürümü `SURUM` dosyasında · Bu dosyayı okuyan yapay zekâ için. Bu klasör (`irp_sozlesme/`), üzerinde çalıştığın modülün klasörüne konmuştur.*

## Ne oluyor

- **Sibernetik:** Siparişe göre makine tasarlayıp üreten, yaklaşık 50 kişilik bir firma.
- **Yazılım:** Adı Sibernetik IRP. İki katmanlıdır:
  - **Çekirdek:** İnsanı, işi, zamanı ve parayı izleyen ortak motor. Kim neyi ne zaman yaptı, top kimde, proje nerede? Bulutta (Supabase, PostgreSQL) çalışır. Başka bir ekip yazar; sen ona dokunmazsın.
  - **Modüller:** Çekirdeğin üstüne kurulan iş alanları: satın alma, kalite, bakım, İK… Senin yazdığın modül bunlardan biri.
- **Bu klasör, modülün çekirdeğe bağlanmasının tek yoludur.** İçinde şunlar var:
  - kurallar (`sozlesme/`)
  - bağlantı katmanı (`baglanti/`)
  - çekirdeğin model tabanlı deneme ortamı (`simulator/`; kapsamı katalogda ayrı belirtilir)
  - denetim araçları (`arac/`)
  - çalışan bir örnek modül (`ornekler/M3_mini/`)

**Amaç:** Sözleşmeye uygun modül aynı bağlantı katmanıyla gerçek çekirdeğe bağlanır. Web ekranı `07_on_yuz.md` içindeki HTML/CSS/JavaScript standardını kullanır. Sözleşme dışı bir teslimde gereken uyarlama ve eksik işler açıkça ayrılır.

**İki belgenin adı ve görevi:** Bu paket **Modül Sözleşmesi**dir: ortak veri sahipliği, kapılar, kimlik, ekran ve teslim sınırlarını belirler. Her modül ayrıca **Modül Geliştirme Talimatı** alır (`sablonlar/GELISTIRME_TALIMATI.md`): o modülün iş kapsamı, kaynak maddeleri, ekranları ve kabul senaryolarıdır. Modülün SPEC'i ortak sözleşmeyi değiştiremez. “Çekirdekte olmalı” diye yazılan madde bir istektir; kaynağı ve sahibi değerlendirilmeden çekirdek işi veya onaylanmış özellik sayılmaz.

## Kurallar

1. **Bu klasör salt okunurdur.** İçindeki hiçbir dosyayı değiştirme, silme, taşıma.
   - Yeni sürümü biz gönderiz; eskisinin yerine aynen konur.
   - Bir şey eksik ya da yanlışsa klasörü düzeltme; **çekirdeğe istek** yaz (`sozlesme/06_teslim.md` › 3).
   - `python3 irp_sozlesme/arac/paket_denetle.py` klasörün bozulmadığını söyler.
2. **Modül çekirdeğe yalnızca `irp_sozlesme.baglanti` üzerinden konuşur.**
   - Modülün kodunda çekirdeğe doğrudan istek, SQL ya da başka bir yol olmaz.
   - Modül Python değilse aynı kapıları aynı biçimle çağıran tek bir katman yazılır (`sozlesme/01_baglanti.md` › 3).
3. **Çekirdeğin verisi modülde kopyalanmaz.** Kişi, birim, proje, tezgâh, takvim, izin ve parçanın aşaması çekirdektedir.
   - Modül okur; kendi tablosunda yalnızca çekirdeğin kimliğini **değer olarak** tutar.
4. **Çekirdeğin kuralı modülde tekrar edilmez.** Kapasite, uygunluk, çalışılan saat, maaş, görünürlük ve aşama geçişi çekirdeğindir.
5. **Olayı insan yazar.** Modül, kullanıcının yaptığı işi kullanıcının oturumuyla çekirdeğe gönderir.
   - Modülün kendi kuralının sonucu (termin geçti, bakım zamanı geldi) olay değildir; **bildirimdir**.
6. **Görünürlüğü çekirdek uygular.** Kullanıcıya gösterilen her şey kullanıcının gözüyle okunur.
   - Servis gözüyle okunan veri yalnızca modülün kuralı içindir, ekrana gitmez.
7. **Künye modülün kimlik kartıdır** (`kunye.json`). Modülün çekirdekte kullandığı her şeyi orada beyan edersin:
   - okumalar ve olaylar
   - bildirim kuralları
   - nesne türleri ve roller
   - kişisel veri ve para

   Künyede olmayanı bağlantı katmanı da yapmaz.
8. **Modülün verisi kendi şemasındadır** (`mod_<kod>`). Çekirdeğin tablosuna dokunan SQL yazılmaz (`sozlesme/04_veritabani.md`).
9. **Mavi yakanın (atölye çalışanının) telefonuna modül düğmesi eklenmez.** Mavi yakanın tek yolu çekirdeğin telefon uygulamasıdır.
10. **Etrafından dolaşma, sor.** Çekirdek bir şeyi vermiyorsa taklit etme, başka yoldan alma; istek yaz. Bu, bizim için en değerli geri bildirimdir.

## Okuma sırası

1. Bu dosya.
2. `sozlesme/01_baglanti.md`: bağlantı katmanı; okuma, olay, bildirim, hatalar.
3. `sozlesme/02_kurallar.md`: yap ve yapma listesi, nedenleriyle.
4. `sozlesme/03_kunye.md`: künye.
5. `sozlesme/04_veritabani.md`: modülün kendi tabloları.
6. `sozlesme/05_sinama.md`: simülatörle sınama ve sözleşme senaryoları.
7. `sozlesme/06_teslim.md`: teslim, çekirdeğe istek, sorun çıkınca.
8. `sozlesme/07_on_yuz.md`: ekranlar.
9. **Gerektikçe:**
   - `kaynak/02_modul_sozlesmesi.md`: kapıların ayrıntısı, okuma kataloğu, olay tablosu
   - `kaynak/16_okumalar.md`: her okumanın görme kuralı
   - `kaynak/18_modul_sozlesmesi.md`: kuralların tamamı ve gerekçeleri
   - `kaynak/01_cekirdek.md`, `kaynak/03_sozluk.md`
   - `simulator/ornek_firma.md`: denemede kullanılan firma, kişiler, roller
   - `simulator/olay_semasi.json`: her olayın girdileri

## Çalışma akışı

1. **Ortamı sına:** `python3 -m unittest discover -s irp_sozlesme/testler`. Python 3.11 ya da üstü, yalnızca standart kütüphane. Geçmiyorsa dur, çıktıyı modülün sahibine ver.
2. **Örneği oku ve koş:** `ornekler/M3_mini/`. Bağlantının bütün kalıpları orada.
3. **Künyeyi yaz:**
   - `sablonlar/kunye.json`'dan başla; en yakın örnek `ornekler/kunyeler/`'de.
   - Denetle: `python3 irp_sozlesme/arac/kunye_denetle.py .` (modülün klasöründen). Hata kalmayana kadar düzelt.
4. **Modülü yaz.** Çekirdeğe giden her şey `Cekirdek` üzerinden gider (`sozlesme/01_baglanti.md`).
5. **Sına:**
   - Modülün çekirdekle konuştuğu her yol için simülatöre karşı bir test yaz.
   - Testler sözleşme senaryolarını `senaryolar/` altına kaydeder.
   - `python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json` ile doğrula (`sozlesme/05_sinama.md`).
6. **Çekirdekte bulamadığını** `istekler/` altına yaz (`sablonlar/istek.md`).
7. **Teslim:** `sozlesme/06_teslim.md` › kontrol listesi.

## Bitirince

Modülün sahibine şunları söyle:
- künye denetimi: hata ve uyarı sayısı
- paket denetimi: sağlam mı
- senaryo sayısı; çekirdeğin reddettiği adımlar varsa hangileri ve neden
- çekirdeğe istek sayısı
- "Teslim klasörünü (`sozlesme/06_teslim.md` › 1) Mustafa'ya gönder."
