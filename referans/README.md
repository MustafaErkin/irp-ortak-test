# IRP başvuru modeli · cevap anahtarı 10.1.1 (kapsam eki)

Kararlar 1–99 ve T10 sürüm 2 için Python 3.11 standart kütüphaneli başvuru modeli.
Karar 99 ve dondurma tavsiyesi: [15. tur raporu](../codex/sonuclar/tur15_SONUC.md). B52 ve E35 kapandı.

Tasarım sürümü 10.1 kalır. [16. tur raporu](../codex/sonuclar/tur16_SONUC.md)
gerçek yürütme kapsamını, mutasyonları ve 200 karışık akışı kaydeder.
C58 tarihsel denetimde karar 99 istisnasını düzeltir. C59 onay görevindeki
kişi süzgecini düzeltir; eski simülasyonun `onay_bekleyen` tutarları değişir.
Bu fark `DONMUS_DAVRANIS_DEGISTI` olarak teslim edilir. 10.2 sürüm kararı verilmedi.

Model testleri, 194 senaryo (dört yeni KP dahil) ve dört kısa simülasyon:

```powershell
py -3.11 -B referans/dogrula_v10_1.py
```

3.306 adımlı büyük akışı da çalıştırmak için `--buyuk-dahil` ekleyin. Yalnız model testleri: `py -3.11 -B referans/calistir_testler.py`.
Bağımsız paket senaryoları: `py -3.11 -I -B referans/cevap_anahtari/yurut.py --tum --tam-kontrol`.

[KULLANIM.md](cevap_anahtari/KULLANIM.md) sürüm farklarını, olayları, ayrı modül bildirimi adımını, kurtarma ve çıktı sözleşmesini açıklar.
Model testleri I1–I126'yı kapsar. Simülasyonlar I59–I126'yı ve kapsamlı/tam hesap eşitliğini denetler.

Günlük doğrulama beklenenleri değiştirmez. Kapsam araçları ve küçük karşı örnekler [16. tur çalışma klasöründe](../codex/calisma/tur16/README.md).
Sürüm 10 tabanı `02b44ed` commit'indeki pakettir. Eski girdiler korunmuştur. Geçici kopyalar, ham farklar ve günlükler teslim edilmez.
Eski üretim araçları tarihsel işler içindir. 15. turun aracı yalnız Y101c–d'yi üretir; 14. turun girdileri ve beklenenleri korunur. Büyük akış 15. turda çalıştırılmadı; SHA-256 eşitliği ve girdide T10 sürüm olayı/UYELER bulunmadığı denetlendi.
