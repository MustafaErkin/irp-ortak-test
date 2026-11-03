# Modül Geliştirici Paketini Üretme

Arkadaşa ve geliştiren yapay zekâsına verilecek klasör `onboarding/modul_gelistirici_paketi_v2/`, arşiv aynı adlı `.zip` dosyasıdır. Bunlar üretilen çıktıdır; git'te kaynakları tutulur. Paketi dışarı gönderme işi bu komutların kapsamı değildir.

```sh
python3 -I -B modul_kiti/gelistirici_paketi_uret.py
python3 -I -B modul_kiti/gelistirici_paketi_sina.py
```

Mac'te ayrı tarayıcıyla görsel/davranış kontrolü:

```sh
bash istemci/mac_derle.sh web --gelistirici-paketi-sina
```

Bu seçenek normal web derlemesinden önce yalnız paket denetimini çalıştırıp çıkar; çalışan web dağıtımı, SQL veya canlı iş verisi değişmez.

Kaynaklar: `paylasim_kaynagi/` bütün yeni modüller için ortak standart/önizleme/şablonlar; mevcut `onboarding/irp_sozlesme/` değişmeden SDK; `istemci/web/` gerçek stil/yardımcılar; `moduller/M11B/` uyarlanmış kaynak örneği; katalog/yetenek/istek JSON'ları paylaşılabilir durum özeti. Mevcut SDK'nın kaynağı hâlâ `modul_kiti/paket/` ve `paket_uret.py`dır; bu yeni üretici SDK'yı değiştirmez.

Yeni bilgi geldiğinde önce ilgili gerçek kaynak ve `paylasim_kaynagi/` anlatımı güncellenir, paket sürümü değerlendirilir, klasör yeniden üretilip sınanır. Ürün SQL'i eski yetenek kanıtından ayrışırsa üretim durur. Her isteğin güncel cevabı numaralı geri bildirim tablosundan JSON'a da taşınır; eski sınıflandırma güncel tamamlanma durumu gibi sunulmaz. Yerel üretilmiş klasöre eklenmiş/değiştirilmiş dosya varsa üzerine yazılmaz; kullanıcı notu kaybedilmez. Kaynak commit ve dosya özetleri `SURUM.json`/`BUTUNLUK.json` içindedir.

**Sürüm 2.0:** Genel yeni modül başlangıcı önce gelir. İlk çıktı modüle özgü Geliştirme Talimatı; eski sürüm fark notu yalnız güncelleme görevinde kullanılır. SDK 1.2/SQL 154 ve güncel kaynaklar eklenir. Mevcut üç modülün notları başvuru ekidir; onları yeniden uyarlamak varsayılan görev değildir. Eski 1.0 klasörü/ZIP'i geçmiş olarak korunur; yeni çıktı `_v2` adını kullanır.

Cevap 1 dosyaları `onboarding/hamdi_gelen/cevap1/` altında okunur; üretici bunları çalıştırmaz veya değiştirmez. Yeni paket dışarı gönderilmez; Mustafa paylaşır.
