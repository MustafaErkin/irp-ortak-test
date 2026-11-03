# 06 · Teslim, çekirdeğe istek, sorun çıkınca

## 1. Teslim

Modülün klasörü bize **bütün olarak** gelir. Klasörde şunlar bulunur:

| Ne | Nerede |
|---|---|
| Künye | `kunye.json` |
| Modülün göçleri | `veritabani/NNN_ad.sql` |
| Sözleşme senaryoları ve beklenenleri | `senaryolar/*.girdi.json`, `senaryolar/*.beklenen.json` |
| Çekirdeğe istekler | `istekler/*.md` |
| Teslim notu | `TESLIM.md` (`sablonlar/TESLIM.md`'den) |
| Modülün kodu ve testleri | Modülün kendi düzeni |
| Ortak web ekranı | `on_yuz/ekran.js`; `07_on_yuz.md` sözleşmesi |
| Modüle özgü iş talimatı | `GELISTIRME_TALIMATI.md`; kaynak, sahiplik, kapsam ve kabul senaryoları |
| Paket | `irp_sozlesme/`; bize geldiği gibi, değiştirilmemiş |

**Kontrol listesi.** Teslimden önce modülün klasöründen şunlar koşulur; sonuçları `TESLIM.md`'ye yazılır:

```
python3 irp_sozlesme/arac/paket_denetle.py                          # "Paket sağlam."
python3 -m unittest discover -s irp_sozlesme/testler                # paketin testleri geçiyor
python3 irp_sozlesme/arac/kunye_denetle.py .                        # 0 hata
python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json   # beklenmeyen ret yok
(modülün kendi testleri)
```

- [ ] Künyenin `surum`'u bir önceki teslimden büyük.
- [ ] Modülün çekirdekle konuştuğu her yolun senaryosu var (`05_sinama.md` › 3).
- [ ] Çekirdeğe giden her çağrı `irp_sozlesme.baglanti`'den geçiyor; başka yol yok.
- [ ] Kişisel veri ve para beyan edildi.
- [ ] Çekirdekte bulunamayan her şey istek olarak yazıldı; modülde taklit edilmedi.

## 2. Bizim tarafta ne olur

1. **Paket denetimi:** Paket sağlam mı, hangi sürüm?
2. **Künye ve kayıt denetimi:** Modül öbür modüllerle birlikte denetlenir. Kodu, harfi, rolleri ve türleri çakışmamalı. Kodu ve harfi biz veririz.
3. **Senaryolar ürüne oynatılır:** Modülün senaryoları gerçek çekirdeğe oynatılır, beklenenle karşılaştırılır. Fark varsa nedeni bölüm 4'teki tabloyla ayrılır.
4. **Kurulum:** Künyeden kurulum olayları, modülün şeması, rolleri, göçleri.
5. **Bağlantı ayarı:** Modülün ortamına `IRP_CEKIRDEK=http`, `IRP_TABAN`, `IRP_ANON`, `IRP_SERVIS` verilir.
6. **Ön yüz:** `07_on_yuz.md`'deki yola göre çekirdeğin uygulamasına bağlanır; derin bağlantılar açılır.
7. **Kabul:** Modülü Mustafa kabul eder (karar 129).

Paket 1.1'de ortak kurulum `modul_platformu/kur.py` ile künye/göç özetlerini denetler, yalnız modül şemasına sahip dar giriş rolü oluşturur ve kurulum olaylarını yetkilinin normal oturumuyla yazar. Yetki önerileri kendiliğinden uygulanmaz; onaylı listeye ayrı alınır. Aynı göç yeniden işletilmez, uygulanmış göç değişmişse kurulum durur. Pasifleştirme kendi açık bildirimlerini kapatır, menü/API/olay yolunu durdurur; çekirdek ve modülün eski verisini silmez.

Teslimin değerlendirilme sırası: istek/kaynak/sahiplik → künye/paket denetimi → ayrı gerçek SQL firmasında senaryo → ortak ekrana uyarlama → ileri kurulum → kullanıcı kabulü. Simülatör geçişi, HTTP 200 veya menüde görünmesi tek başına kabul değildir. Donmuş referans ve teslim edilen eski paketler değiştirilmez.

## 3. Çekirdeğe istek

**Ne zaman:** Modülün çekirdekte bulamadığı ya da çekirdeğin engellediği her şey için yazılır:
- bir okuma
- bir alan
- bir görme kuralı
- bir aşama ya da geçiş kuralı
- bir bildirim türü

**Biçim:** Her istek ayrı dosyadır: `istekler/<KOD>-NN_kisa_ad.md` (`sablonlar/istek.md`). Şunlar yazılır:
- ne
- neden modülde çözülemiyor
- kanıt: senaryo ya da akış
- şartname maddesi (biliniyorsa)
- önerin
- önem

| Önem | Ne zaman |
|---|---|
| `KRITIK` | Modülün ana işi hiç yapılamıyor |
| `ONEMLI` | Yeni okuma, alan, kural ya da bildirimle eklenebilecek eksik |
| `DUSUK` | Ayrıntı |

**Künyedeki karşılığı:** `istekler` listesinde kod, başlık, durum (`ACIK`).

**Bekleme süresince:** İstek karşılanana kadar o özellik modülde yazılmaz ya da kapalı tutulur. Etrafından dolaşılmaz:
- başka yoldan veri alınmaz
- çekirdeğin kuralı modülde taklit edilmez

**Yol:**
1. Biz karar veririz: çekirdeğe mi, modüle mi?
2. Çekirdeğe ise çekirdeğin yeni sürümü, sonra bu paketin yeni sürümü gelir.
3. Künyedeki istek `KARSILANDI` olur.

## 4. Sorun çıkınca: kim ne yapar

| Belirti | Neden | Kim çözer |
|---|---|---|
| `paket_denetle` "bozulmuş" diyor | Paketin bir dosyası değişmiş | Modül: paketi zip'ten yeniden açar |
| Künye denetiminde hata | Künye kurala uymuyor | Modül: mesaj neyin yanlış olduğunu ve kuralın numarasını söyler |
| Simülatörde `YETKI`, `DURUM`, `BICIM` reddi | Modülün akışı ya da künye yanlış; ya da çekirdekte eksik | Modül düzeltir; çekirdekte eksikse istek yazar |
| Simülatörde geçen senaryo üründe geçmiyor | Gerçek çekirdek simülatörden sapıyor | **Biz.** Modül değişmez |
| Kod, harf ya da rol başka modülle çakışıyor | Kayıt defteri | **Biz** yeni kod ya da harf veririz; modül künyeyi günceller |
| `BAGLANTI` hatası | Ağ ya da bağlantı ayarı | **Biz** ayarı düzeltiriz |
| `URUN` hatası | Beklenmeyen hata | **Biz.** Modül hatanın metnini ve senaryoyu gönderir |
| Çekirdeğin yeni sürümü çıktı | Kural, okuma ya da alan değişti | Biz paketin yeni sürümünü göndeririz, değişiklik notuyla (`DEGISIKLIKLER.md`). Modül paketi değiştirir, senaryolarını yeniden doğrular |

**İlke:** Simülatörde geçen modül, gerçek çekirdeğe bağlandığında modül değişmeden çalışmalıdır. Çalışmıyorsa sorun bizdedir.
