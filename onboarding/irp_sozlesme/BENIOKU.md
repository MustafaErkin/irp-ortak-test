# Sibernetik IRP · Modül sözleşmesi paketi

Bu paket, yazdığınız modülün Sibernetik IRP çekirdeğine bağlanmasının yoludur. Kurallarına uyan modül, bize geldiğinde kodu değişmeden çekirdeğe bağlanır.

## Kurulum

1. **Klasörü yerleştirin:** Zip'i modülünüzün klasörünün köküne açın. Klasörün adı `irp_sozlesme` kalsın.

   ```
   modulunuz/
     irp_sozlesme/     ← bu paket; değiştirilmez
     kunye.json        ← modülünüzün kimlik kartı (siz yazarsınız)
     veritabani/       ← modülünüzün tabloları
     senaryolar/       ← sözleşme senaryoları (testler üretir)
     istekler/         ← çekirdeğe istekler
     ...               ← modülünüzün kodu
   ```

2. **Yapay zekânıza haber verin:** Çalıştığınız yapay zekânın kök talimat dosyasına (Claude için `CLAUDE.md`, Codex için `AGENTS.md`) şu satırları ekleyin:

   ```
   ## Sibernetik IRP çekirdeği
   Bu modül çekirdeğe yalnızca `irp_sozlesme/` klasörünün kurallarıyla bağlanır.
   Çekirdekle ilgili her işten önce `irp_sozlesme/BASLA.md`'yi oku.
   `irp_sozlesme/` içindeki hiçbir dosyayı değiştirme.
   ```

3. **Ortamı sınayın:** Python 3.11 ya da üstü gerekir; ek paket gerekmez. Modülün klasöründen:

   ```
   python3 -m unittest discover -s irp_sozlesme/testler
   ```

## Bilmeniz gerekenler

- **Paketin kuralları:** Kurallar `irp_sozlesme/sozlesme/` altındadır; yapay zekânız `BASLA.md`'den başlar.
- **Çalışırken çekirdeğe ihtiyacınız yok:** Paketin içinde çekirdeğin çalışan bir kopyası (simülatör) ve örnek bir firma var. Modülünüz geliştirirken ona bağlanır.
- **Kod ve harf:** Modülün kodunu ve cihaz harfini biz veririz. Mustafa'ya sorun.
- **Sorun çıkarsa:** Paketi değiştirmeyin. Çekirdekte eksik gördüğünüzü `istekler/` altına yazın (`irp_sozlesme/sablonlar/istek.md`). Hangi sorunu kimin çözdüğü `sozlesme/06_teslim.md` › 4'te.
- **Teslim:** Kontrol listesi `sozlesme/06_teslim.md` › 1'de. Modülün klasörü bütün olarak Mustafa'ya gelir.
- **Yeni sürüm:** Paketin yeni sürümü gelince eski `irp_sozlesme/` klasörünü silin, yenisini koyun. Neyin değiştiği `DEGISIKLIKLER.md`'de.
