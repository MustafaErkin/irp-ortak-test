# Modül kiti

Yeni bir modülü çekirdeğe bağlamak için gereken araçlar. Kurallar: `tasarim/18_modul_sozlesmesi.md` (T18). Kapıların ayrıntısı: `onboarding/cekirdek_paketi/02_modul_sozlesmesi.md`.

Güncel paket **1.1**. İlk çalışan ortak bağlantı Proje Planlama (M11B) ile `modul_platformu/` ve `moduller/` altındadır (T27). Web ekranları ortak HTML/CSS/JavaScript kullanır. Paket ortak **Modül Sözleşmesi**dir; modüle özel **Modül Geliştirme Talimatı** şablonu `paket/sablonlar/` içindedir. Katalog gerçek SQL uygulamasını ve model kapsamını ayrı gösterir; bütün gelen modüllerin kabulü değildir.

| Dosya | Ne işe yarar |
|---|---|
| `kunye_semasi.json` | Künyenin alanları; editör yardımı için |
| `kunye_denetle.py` | Künye (V01–V24), kayıt (R01–R11) ve göç (G01–G09) denetimi; kurulum olaylarının üretimi |
| `cekirdek_katalogu.json` | Çekirdeğin okumaları, eylemleri, rolleri, kod listeleri ve sınıfları. **Üretilir, elle değiştirilmez** |
| `katalog_uret.py` | Kataloğu modelden ve T16'dan üretir |
| `cekirdek_yetenekleri.json` | Gerçek ürün yolları ve kapsamı açık kanıt envanteri; sözleşme kataloğunun yerine geçmez. **Üretilir** |
| `yetenek_tanimlari.json` | Yetenek başlıklarının kapsamı, durumu ve dayanakları; yeni ürün kabulü oldukça güncellenir |
| `yetenek_envanteri.py` | SQL yönlendirmelerini/eylem şemalarını çıkarır; kaynakla uyuşmayan eski SQL kanıtını kullanmaz; T25'i de üretir |
| `yetenek_denetle.py` | Mevcut tam web sınamasının ayrı gerçek SQL firmasında salt okunur yetenek kanıtını toplar; canlıda çalışmaz |
| `istek_degerlendirmeleri.json` | Gelen isteklerin dosya özetleri, sahipleri, ortak işleri, öncelikleri, karar sınırları ve kabul ölçütleri. T26'nın yapılandırılmış değerlendirmesi; uygulanmış/kabul edilmiş demek değildir |
| `ornekler/` | Altı örnek künye: M3 (gerçek), KAL, BAK, IK, VEGA, YZ. KAL'da örnek göç var |
| `paket/` | Modül yazan ekibe giden paketin elle yazılan kısmı: talimatlar, bağlantı katmanı, sahte bulut, araçlar, örnek modül (karar 131) |
| `paket_uret.py` | Paketi üretir: `onboarding/irp_sozlesme/` ve `.zip`. Kaynaklardan biri değişince yeniden koşulur; test eskiyse kırılır |

## Kullanım

Komutlar `mvp/` klasöründen çalışır. Python 3.11 ya da üstü gerekir.

```
python3 -I -B modul_kiti/kunye_denetle.py <modül klasörü>                    # tek modül
python3 -I -B modul_kiti/kunye_denetle.py <modül klasörü> modul_kiti/ornekler/*   # başkalarıyla birlikte
python3 -I -B modul_kiti/kunye_denetle.py --kurulum <künye.json>             # kurulum olayları
python3 -I -B modul_kiti/katalog_uret.py                                     # çekirdek değişince
python3 -I -B modul_kiti/paket_uret.py                                       # paketi yeniden üret
python3 -I -B modul_kiti/yetenek_envanteri.py                                # ürün/kanıt envanteri ve T25
```

- **Sonuç:** Hata varsa çıkış kodu 1 olur. Uyarılar okunur ama kurulumu durdurmaz.
- **Testler:** `python3 -I -B -m unittest discover -s test/modul_sozlesmesi -t test/modul_sozlesmesi`

Yetenek envanterinin SQL kanıtını yenilemek için mevcut `bash istemci/mac_derle.sh web --tam-sinama` yolu kullanılır. Bu komut ayrı geçici test veritabanını kurar; Auth/Storage/Realtime taşıması yerel taklittir. Yeni gelen modüllerin uçtan uca kabulü anlamına gelmez. GANTT/PLAN'ın eski katalogdaki T16 katmanı ürünün mevcut yeteneğiyle aynı ölçü değildir; ayrıntı `tasarim/25_cekirdek_yetenek_durumu.md`.
