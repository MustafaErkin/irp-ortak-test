# IRP Genel Modül Geliştirme Talimatı

Önce BASLA.md'yi oku. Bu paket yalnız üç mevcut modülü uyarlama görevi değildir; bütün yeni modüller için ortak sözleşme, teknoloji, arayüz, SDK ve güncel çekirdek girdisidir. Geliştirilecek modülün işini sahibi verir. İlk çıktı modüle özel GELISTIRME_TALIMATI.md'dir; ardından o kapsamda geliştirme yapılır. İş tanımı yoksa modül sahibinden öğren. Yeni modül için eski sürüm uyum raporu isteme.

HTML/CSS/JavaScript beyaz ERP ve ac(host) kullanılır; Python arka yüz tek SDK 1.2 ile konuşur. Ürün tabanı SQL 154'tür. Çekirdek davranışını taklit etme. M10/M11A/M11B'nin geri bildirimlerini ve örneklerini yalnız ilgili bağımlılık/başvuru için oku; onları kendiliğinden değiştirme. Mevcut modül güncellemesi açıkça istendiyse fark notu tut ve entegrasyon ekibinin son değişikliklerini koru.

Bu klasör ve SDK sürümlü başvurudur; çalışmayı kendi modül klasöründe yap. SDK yeni sürümle bütünüyle yenilenebilir, içinde çatallama yapılmaz. Teslim ölçütü 05_TESLIM_VE_KABUL.md'dedir. Gelecekte motorları PC/Mac'te çalıştırma konusu ertelenmiş görüşmedir; mevcut mimariyi değiştirmez.
