# 03 · Sözlük

| Terim | Anlam |
|---|---|
| Çekirdek | İnsan, iş, zaman ve parayı izleyen ortak motor; modüller üstüne kurulur |
| Modül | Çekirdeğin üstüne kurulan iş alanı (M1 teklif … M8 muhasebe; İK; iletişim) |
| Olay | Bir insanın sistemde yaptığı tek bir şey; değişmez kayıt (`olaylar`) |
| Künye (zarf) | Her olayın ortak alanları: kimlik, kim, ne zaman, nereden, neyin üstünde |
| Eylem kodu | Olayın türü: `IS.BASLADIM`, `NESNE.ASAMA_GECIRDIM`… |
| Tanıklık | Olan bir şeyin kaydı; çevrimdışı yazılabilir, durum uymasa da kabul edilir (şüpheli) |
| Yönetim kararı | Birinin başkası için verdiği karar; yalnızca çevrimiçi; durum uymazsa reddedilir |
| Kapı | Olayın kabul denetimi (`olay_ekle`) ya da bir eylemin durum koşulu |
| `RED(BICIM / YETKI / DURUM / BAYAT / CAKISMA)` | Ret nedenleri |
| Bayat | Kullanıcının gördüğü hal artık güncel değil (`surum` tutmuyor) |
| `surum` | Bir kaydın iş alanlarının SHA-256 özeti; içerik aynıysa aynı |
| Nesne / son hal | Bir şeyin şu anki hali; olaylarından kurallarla hesaplanır |
| Türetilmiş tablo | Olaylardan yeniden kurulabilen tablo |
| Kural | "Şu halde şu olay gelirse yeni hal budur"; yan ürünleri bildirim, aralık, sonuç kaydı |
| R01–R43 | Çekirdeğin bildirim ve yan kayıt kuralları |
| Dağıtıcı | Olayın etkilediği nesneleri ve onların bağımlılarını yeniden hesaplayan işleyiş |
| Doğum | Bir olaydan yeni nesne çıkması (iş, görev, onay görevi, revizyon görevi…) |
| Etkin olay | Geçersiz sayılmamış olay; hesaplar yalnızca bunlarla yapılır |
| Aralık, kova | Kişinin gününün parçaları ve türleri (`CALISMA`, `MOLA`, `TANIMSIZ`…) |
| İş | Atölye işi (mavi yaka); havuzdan kişinin listesine atanır |
| Görev | Masa başı görev (beyaz yaka); atanır, kabul, teslim, onay |
| Zaman değeri | Görevin saat olarak emeği; beyaz yakada maaşın projelere dağılım anahtarı |
| Etap | Bir departmanın projedeki iş paketi (tarih, hedef saat, sorumlu); departmanı projeye dahil etmenin yolu |
| Plan sürümü (B0, B1) | Etap düzeyindeki onaylı plan |
| Plan tarihleri | İş ve görevin planlanan başlangıç ve bitişi (`PLAN.TARIHLEDIM`) |
| Ortak nesne katmanı | Şirket nesnelerinin (parça, belge…) çekirdekteki ana gövdesi; türler veridir |
| Nesne türü | Aşamalar, geçişler, kimin açacağı ve onaylayacağı; veri olarak tanımlanır |
| Modül uzantısı | Modülün tablosu; nesnenin çekirdekteki kimliğini taşır |
| Top kimde | Nesnenin aşaması, sorumlusu, o aşamada ne zamandan beri durduğu |
| Sürüm (belge) | Nesneye eklenen dosya sürümü: taslak, onaylı, geri çekilmiş |
| Bildirim kapısı | Modülün bildirim bıraktığı yol; olay değil |
| Servis kimliği | Bir modülün bildirim kapısındaki kimliği |
| Cihaz harfi (modül) | Modüle ayrılan olay kimliği harfi; normal cihaza verilmez |
| `RED(BAYAT, SIRA)` | Karar, dayandığı kaydın sonradan sıralanan bir olayından önceye düşüyor; yeni anla yeniden gönderilir |
| `TANIMSIZ_VERI` | Okuma kapısında böyle bir okuma yok |
| `ERISIM_DISI`, `MESGUL` | Okuyanın göremediği proje ya da kişi işi; ayrıntısız gösterilir |
| `MALIYET` | Tezgâh saat ücretini gören rol; maaş görmez (karar 104) |
| Yetkinlik | Kişinin yapabildiği işler (kaynak, 5 eksen…); liste veridir; atamayı engellemez (karar 106) |
| Yetki tablosu | Hangi rolün hangi eylemi hangi kapsamda yapabileceği; veri |
| Sözde rol | Atanmayan, ilişkiden çıkan rol: `BIRIM_YONETICISI`, `BIRIM_BASI`, `BIRIM_UYESI`, `PROJE_SORUMLUSU` |
| Hiyerarşi zinciri | Birim ağacından çıkan üstler; üst, astının yapabildiğini yapar ve gördüğünü görür |
| UYELER / HERKES | Proje görünürlüğü ayarı; UYELER'de proje ekibi kuralları geçerli |
| Projede yetkili | Proje sorumlusu, projede etabı olan birimin yöneticisi, bunların üstleri, genel yönetim |
| Genel yönetim | Kök birimin yöneticileri ve `YETKILI` |
| Saat maliyeti | (Maaş + genel gider payı) ÷ firmanın paydası (Sibernetik 180) |
| `VERI_EKSIK` | Bilinmeyen tutar; sıfır değildir |
| Ay kapanışı | Ayın tutarlarının donması; sonraki fark sonraki aya |
| Cevap anahtarı | Donmuş girdiler ve beklenen çıktılar; ürün ve modüller bununla sınanır |
| Değişmez (I1–I126) | Her geçerli durumda doğru olması gereken kural |
| Senaryo | Olaylar dizisi ve beklenen sonuç; `kaynak/senaryolar.md` |
| `N:P1325` | Şartname paragraf numarası |
| Karar N | `kaynak/tasarim/00_kararlar.md`'deki karar |
| T1–T10 | `kaynak/tasarim/` altındaki tasarım belgeleri |
