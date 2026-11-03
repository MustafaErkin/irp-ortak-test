# Arayüz Kaynağı Ve Önizleme

`ortak/` mevcut webden alınan stil ve yardımcıların değiştirilmemiş kopyasıdır. Üretimde bunları modülün içine çoğaltmak yerine ortak kabuk kullanılır. `on_yuz/ekran.js` ortak `ac(host)` bağlantısını, temizlemeyi, geç cevabı engellemeyi, tablo/pencere/boş/hata görünümünü ve yenilemede taslak metnini korumayı gösteren küçük örnektir.

Paket kökünden `python3 -m http.server 8765 --bind 127.0.0.1` çalıştırıp `http://127.0.0.1:8765/arayuz/` adresini aç. Koyu sistem teması altında da beyaz kalır. Boş/hata seçenekleri ve pencere denenebilir. Çalışma notu bu örnekte yalnız ekrandaki taslaktır; sunucuya kaydedilmiş veya çekirdeğe gönderilmiş sayılmaz. Ekranı Yeniden Aç bu örneği kapatıp yeni örnek açar; taslak temizlenir.

`onizleme.js` yalnız görünüş için sentetik cevap verir. Örnekteki `/projeler/<kimlik>/ornek` modüle ait örnek API adıdır; ortak çekirdekte böyle bir kapı tanımlanmaz. Gerçek modül kendi API'sinde kullanıcının normal oturumuyla SDK'yı çağırır. Bu sayfanın çalışması backend/izin/iş akışı kabulü değildir.

`proje_planlama_ornegi.png` ayrı sentetik test firmasındaki gerçek M11B ekranıdır. Büyük kaynak örneği `../ornekler/M11B/` içindedir; küçük örneğin görsel kalıbından üretim iş kuralı çıkarılmaz.

`requirements-ornek.txt` mevcut Python 3.13 ortamındaki arka yüz bağımlılık sürümleridir. Önizleme veya SDK'nın standart kütüphane testleri için bu bağımlılıkları kurmak gerekmez. M11B arka yüzü ayrıca kendi ayrı PostgreSQL test ortamını ve açık ortam ayarını ister.
