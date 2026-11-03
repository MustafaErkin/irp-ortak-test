# Ortak Dosya Taşıma Yardımcısı

`modul_platformu/dosya_api.py` mevcut çalışan ortak kodun değiştirilmemiş kopyasıdır. Bu klasör bütün platform sunucusu veya yeni bir motor değildir. Gerçek kurulumda ortak ortam bu yardımcıyı sağlar; ayrı modül geliştirme ortamında gerekirse bu klasör Python arama yoluna eklenebilir. İş nesnesinin iznini modül verir.

`kur(app, baglam, izin)` FastAPI uygulamasına üç uç ekler:

| Uç | İş |
|---|---|
| `GET /api/dosya-yetkisi?kayit=<JSON>&yazma=true/false` | Normal oturumda iş nesnesi izni. |
| `POST /api/ortak-dosyalar` | `{kayit,ad,icerik_base64,tur}`; izin + en çok 1 MB + SDK yükleme. |
| `GET /api/ortak-dosyalar/{kimlik}` | Güncel izni tekrar denetleyen SDK okuması. |

`baglam` modülün normal kullanıcı bağımlılığıdır; `b.oturum` SDK oturumu olmalıdır. `izin(b,kayit,yazma)` modülün kendi iş nesnesinde erişimi doğrular. Bunlar genel servis anahtarıyla veya herkese izin veren sahte fonksiyonla değiştirilmez. Güncel M11B kaynak örneği kullanımını gösterir; iş kuralı yeni modüle kopyalanmaz.
