# Ortak Modül Bağlantısı

Çalışma kaydı `moduller/kayit.json`, kabul edilmiş uyarlamalar `moduller/<KOD>/` altındadır. Gelen paketler `disaridan_moduller/Modules/` altında korunur. Çalışma listesinde Teklif Yönetimi (M10), Sipariş Ve Bütçe (M11A) ve Proje Planlama (M11B) bulunur. Üçlü entegrasyonun kapsamı ve sınırları `tasarim/28_moduller_gercek_mvp.md` ile `codex/sonuclar/moduller_mvp_SONUC.md` içindedir; kullanıcı kabulü ayrı aşamadır.

```text
bash istemci/mac_derle.sh web --modul-paket-sina --modul-sina --tam-sinama
bash istemci/mac_derle.sh web --modul-hazirla --bulut-guncelle --modul-kur --calistir --canli-sina
```

İlk komut ayrı geçici PostgreSQL TEST firması ve Chrome profili kullanır. İkinci komut mevcut gösteri ortamına ileri göç ve modül kurulumu yapar; firma işlerini sıfırlamaz. `--senaryo1-hazirla` bu işte kullanılmaz. Sırlar mevcut özel ortam dosyasından komut içinde yüklenir; konsola veya depoya yazılmaz.

`bagimliliklar.py` sabitlenmiş bağımlılıkları `.runtime/python` içine hazırlar. `kur.py` künye ve göç denetimi, şema/rol oluşturma ve göç özeti kontrolü yapar. Ayrı NOLOGIN sahip göçleri kurar; LOGIN çalışma rolü kendi verisinde CRUD yapar, şema DDL'si yapamaz. Çalışma rolünün bağlantı/sorgu sınırı vardır. Normal kurulum olayları `isletim.Yetkili` ile yetkilinin normal oturumundan gelir. Künyedeki yetki önerileri otomatik uygulanmaz.

`gecit.Platform` ortak web sunucusunda çalışır; sadece kayıtlı modülleri başlatır. Her arka yüz ayrı yerel süreçte kendi şema rolünü alır. Genel çekirdek DSN'si ve yönetici servis anahtarı alt süreç ortamına geçmez. Bu süreç ayrımı kötü niyetli yerel kod için işletim sistemi yalıtımı iddiası değildir; devreye alınan modül kodu ve göçleri güvenilir incelemeden geçer.

Tarayıcı tek normal kullanıcı oturumuyla `/irp/moduller/<KOD>/api/...` çağırır. Arka yüzün SDK çağrısı `/irp/cekirdek/<KOD>/rest/v1/rpc/...` üzerinden künye ve gerçek kişi denetiminden geçer. Genel okuyucuya kişi değiştiren `g.kim` verilmez. Dar servis kimliği yalnız servis okuması ve kendi bildirimleri içindir; kullanıcı olayı yazamaz. Sağlayıcı adresi istekten alınmaz; künyedeki bağımlılık ve çalışma kaydıyla bulunur.

Pasifleştirme `kur.kapat` ile kendi açık bildirimlerini kapatır, normal MODUL.TANIMLADIM olayıyla modülü pasifleştirir. Menü ve yeni API/olay yolu kapanır; çalışma rolü NOLOGIN olur ve mevcut bağlantıları kesilir. Eski çekirdek/modül verisi silinmez. Bu, veritabanı göçlerini geriye sarma veya bütün sürüm indirme senaryolarının kabulü değildir.

Ön yüz sözleşmesi: `modul_kiti/paket/sozlesme/07_on_yuz.md`. Mimari/sahiplik: `tasarim/27_ortak_modul_baglantisi.md`. Gerçek test kanıtı: `codex/sonuclar/modul_ortak_baglanti.json`.
