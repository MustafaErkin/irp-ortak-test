# 05 · Sınama: simülatör ve sözleşme senaryoları

## 1. Simülatör

**Ne:** `simulator/` çekirdeğin çalışan Python modelidir. Python 3.11 ya da üstü, yalnızca standart kütüphane. Gerçek çekirdek bu modelin çevirisidir ve aynı senaryolarla sınanır; simülatörde doğru çalışan modül gerçek çekirdekte de çalışır.

**Bağlantı:** Bağlantı katmanı varsayılan olarak simülatöre bağlanır (`IRP_CEKIRDEK` verilmemişse). Her `Cekirdek.ac(...)`:
1. örnek firmayı kurar (`simulator/ornek_firma.md`: 16 kişi, 2 proje, birimler, tezgâhlar, `PARCA` ve `BELGE` türleri; proje görünürlüğü "yalnızca üyeler");
2. künyeden modülü kurar: modülün kaydı, rolleri, türleri;
3. temiz bir firmayla başlar. Her test kendi çekirdeğini açar.

**Saat:**
- Her yazmadan sonra bir saniye ilerler.
- Testte belli bir an gerekiyorsa: `cekirdek.surucu.saat('2026-11-02T09:00:00+03:00')`. Bu yalnızca simülatörde var; modülün kodunda kullanılmaz.

**Kişiler ve roller:** `simulator/ornek_firma.md`. Modülün rolünü bir kişiye vermek gibi, firmanın yetkilisinin çekirdeğin ekranından yaptığı işler testte simülatörden yazılır (yalnızca sınamada):

```python
cekirdek.surucu.yetkili_olay('KISI.DEGISTIRDIM', {'kisi': 'K004', 'degisenler': {'roller': ['YONETICI', 'KALITECI']},
                                                  'gecerli_baslangic': cekirdek.simdi()})
```

## 2. Sözleşme senaryosu

**Senaryo nedir:** Modülün çekirdeğe gönderdiği adımların kaydıdır: olaylar, kullanıcı gözüyle okumalar, bildirimler. Biçimi çekirdeğin cevap anahtarıyla aynıdır (`simulator/KULLANIM.md` › Girdi sözleşmesi).

**Ne için:** Biz aynı dosyayı gerçek çekirdeğe oynatıp cevapları karşılaştırırız. **Modülün bağlanmasının kanıtı budur.**

**Nasıl kaydedilir:** Simülatör her adımı kendiliğinden kaydeder. Testin sonunda yazılır:

```python
cekirdek.surucu.senaryo_yaz('senaryolar/KAL01_kabul.girdi.json')
```

**Doğrulama:** Simülatörün baştan, tek başına oynatmasıdır:

```
python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json
```

Her girdinin yanına `.beklenen.json` yazılır. Ekrana, çekirdeğin modülün adımlarına verdiği cevapların sayımı çıkar: kabul, ret (koduyla), okuma hatası. Beklemediğin bir ret varsa modülde ya da künyede bir yanlış vardır. Ya da çekirdekte bir eksik vardır; o zaman istek yazılır.

**Python dışında:** Sahte bulut (`simulator/sunucu.py`) aynı kaydı tutar. `POST /sahte/senaryo` kayıtlı senaryoyu verir, dosyaya yazarsın, sonra aynı doğrulama.

## 3. Hangi senaryolar

**Modülün çekirdekle konuştuğu her yol için en az bir senaryo:**

| Ne | Örnek |
|---|---|
| Her olay türü, olağan yolda | Parça aç, aşama geçir, not yaz |
| Her yönetim kararı için `BAYAT` | Eski sürümle karar → `BAYAT` |
| Yetkisi olmayan kullanıcı | Projeyi görmeyen kişi okuyamaz, aşama geçiremez |
| Her bildirim kuralı | Bırak, yeniden bırak (güncellenir), kaldır |
| Süzülen alıcı | Projeyi görmeyen alıcı süzülür |
| Modülün türü varsa | Her geçiş; geçiş tablosunda olmayan geçiş reddedilir |
| Plan yazıyorsa | `PLAN.TARIHLEDIM` bütün olarak kabul ya da ret |

**Adlandırma:** `<KOD><NN>_<kısa ad>.girdi.json`, ör. `KAL01_giris_kontrolu.girdi.json`.

## 4. Testler

- **Modülün testleri:** Kendi klasöründe durur; `irp_sozlesme/` içine test konmaz.
- **Örnek:** `ornekler/M3_mini/test_satin_alma.py`. Koşmak: `python3 -m unittest irp_sozlesme/ornekler/M3_mini/test_satin_alma.py`
- **Paketin testleri:** `python3 -m unittest discover -s irp_sozlesme/testler`. Ortamın sağlam olduğunu gösterir; modülü sınamaz.
