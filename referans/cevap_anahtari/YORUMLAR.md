# Cevap anahtarı 10.1.1 yorumları · 16. tur kapsam eki

## Y16-01 · Model düzeltmeleri ve dondurulmuş sonuç

C58: Karar 99 ile izin verilen sorumlu taslağı, I106/I107 tarihsel denetiminde
de geçerlidir. İstisna başka kişi veya ek proje hedefi için uygulanmaz.
C59: ONAY görevinin saati yalnız kendi onaylayanına aittir. `kisi` ile sorulan
görev payı başka kişide sıfırdır; maaştaki `onay_bekleyen` buna göre hesaplanır.
Eski simülasyon tutarlarının değişmesi `DONMUS_DAVRANIS_DEGISTI` olarak raporlanır.
Tasarım değiştirilmedi; 10.2 kararı verilmedi.

## Y16-02 · B58 davranış kilidi

T8 §8 sayısal `gun_sonu_hatirlatma` değerinin birimini açıkça söylemez.
Mevcut model bunu ertesi iş günü mesai başlangıcına eklenen saat olarak yorumlar.
0/3 sınırları bu turda **davranış kilidi** testidir; tasarım hükmü değildir.
Öneri, kullanıcıya birimi açıkça göstererek bu yorumu karara bağlamaktır.

## Y16-03 · B59 davranış kilidi

T10 Gantt sorgusunun tam uç eşitliğini açıkça belirtmez. Mevcut görünüm,
sorgu başlangıcında bitmiş gerçekleşen aralığı dışarıda tutar; bir dakikalık
kesişimi içerir. An olarak verilen bitiş aynen kullanılır. Bu sınama tasarım
hükmü değildir; ardışık pencerelerde çift gösterimi önleyen `[başlangıç, bitiş)`
yorumunun açıkça karara bağlanması önerilir.

## Y16-04 · B60 ve B61

B60: modül bildiriminin ilk bırakma/kaldırma anıyla eşit zaman damgasındaki
geç görülme iki uçta da saklanır. Bu yorum davranış kilididir; T10da eşit
zaman damgası ve kabul sırası açıklaştırılmalıdır.

B61: yük hesabının `1e-9` saatlik iç toleransına tam eşitlik tasarımda
tanımlı değildir. Bu sınırdaki mutasyon hayatta tutuldu; eşdeğerlik veya
tasarımdan türetilmiş doğru sonuç iddiası yoktur. Süre hassasiyeti ve
yuvarlama anının açıkça tanımlanması önerilir.

## Önceki sözleşme · 15. tur

Karar sırası: [kararlar](../../tasarim/00_kararlar.md) > [T10](../../tasarim/10_surum_10_1.md) > T9 > T8 > T1–T7. Tasarım ve senaryo belgeleri değiştirilmedi. Aşağıdaki seçimler başvuru modelinin açık sözleşmesidir. Öneriler tasarım kararı yerine geçmez.

## Y15-01 · B52 kapandı: sorumlunun dar taslak hakkı

**Karar 99 ile kapandı.** Projeyi gören nesne sorumlusu UYELER ayarında kendi belgesine taslak ekler. İstisna yalnız `NESNE.SURUM_EKLEDIM` içindir. Üstler ve YETKILI için T9 §6.2 aynen geçerlidir.

Y101c'de K041 görevi nedeniyle projeyi görür ve sürüm ekler; kendi onayı ve görev atama girişimi reddedilir. K044 nesnenin sorumlusu olsa da projeyi görmediği için ekleyemez. Ek erişimle görme de yeterlidir; erişim kalkınca ekleme ve okuma kapanır.

Onay ve geri çekme türün yetkisinde kalır. Sürümü ekleyen kendi sürümünü onaylayamaz veya geri çekemez. İstisna başka proje hedeflerine, nesne güncellemeye, görev atamaya veya plan yazmaya taşınmaz.

14. turun eski B52 kanıtı ve yorumu `b1f11c3` commit'inde tarihsel olarak korunur. B53–B57 seçimleri karar 99 ve T10 sürüm 2 ile kabul edildi; modelde değiştirilmedi.

## Y14-02 · Plan tarihleri

- Atamada alanlar isteğe bağlıdır. Eski kayıtlara zorunlu boş alan eklenmedi; eski nesne özetleri korunur. İki tarih doluysa başlangıç bitişten küçük olmalıdır. Görevde yalnız başlangıç verilirse teslim anı son sınırdır.
- `PLAN.TARIHLEDIM` her hedef için iki tarih ister. Hedefler tekildir. Bütün hedeflerin sürüm özetleri `neyin_ustunde` içinde taşınır. Bir biçim, yetki, durum veya tazelik hatasında hiçbir plan değişmez.
- Plan işin kimliğine bağlıdır. Devirde aynı plan yeni kişinin listesindeki iş olur. İptalde plan geçmişi korunur; iş çakışma kümesinden çıkar.
- Çakışma aralıkları yarı açıktır: başlangıç dahil, bitiş hariç. Kesişim sorgu penceresine kırpılır. Kişi ve tezgâh anahtarları türüyle de verilebilir.
- B0/B1 etap planları değişmedi. Gantt etap planını son onaylı sürümden alır. Onaylı sürüm yoksa etap için plan uydurulmaz.
- **B56, kabul edildi:** İş/görev için ara yüzde kaynağı yoktur. Model bitende 100, diğer durumlarda 0 gösterir. Etap yüzdesi mevcut tamamlanan saat/hedef hesabıdır. Teslim sınırı başlangıç uyarısından önce gelir: iki sınır da geçmişse “geride” görünür. Kısmi plan aralığında eksik uç tahmin edilmez. T10 sürüm 2 bunu açıkça yazar.

## Y14-03 · Sürüm kimliği, zaman ve eşzamanlı istek

- Sürüm numarası kabul kilidi altında atanır ve yeni olayın sunucu alanı `nesne_surum_no` içinde saklanır. İstemci bu numarayı atayamaz. Yeniden kurma sırasında numara verilmez.
- Geç gelen, daha eski saatli bir taslak yeni numara alır. Önceden onaylanmış dosyanın numarası değişmez. C55'in karşı örneği: 10:00 R0, 11:00 R0 onayı, sonra gelen 09:59 R1. Düzeltme öncesinde onay R1'e kayıyordu; düzeltme sonrasında R0 geçerli, R1 taslaktır.
- Yeni T10 kararlarında aynı iş saatinin sırası sunucunun `kabul_sirasi` alanıyla belirlenir. İstemcinin bu alanı silinip sunucuda yeniden atanır. Önceki olayların sıralama kuralı değişmedi.
- Aynı nesne özetini taşıyan iki eşzamanlı isteğin yalnız biri kabul edilir. İkinci `BAYAT` alır; yeniden okuması gerekir. Bu kilit Python başvuru modelinin işlem sınırıdır; üretimde aynı işlem veritabanında atomik kurulmalıdır.
- Nesnenin doğumundan önce sürüm; sürümün son geçişinden önce onay/geri çekme; gelecekte T10 yönetim olayı kabul edilmez. Geri çekilen sürüm tekrar onaylanmaz; yeni sürüm eklenir.
- **B53, orta:** Türün `surum_onaylayanlar` tanımı değişince eski taslağa güncel yetki uygulanır. Önceden kabul edilmiş onaylar geri alınmaz. Böylece yetkisi kaldırılan kişi eski taslak üzerinden onay veremez.

## Y14-04 · Taslak görünürlüğü ve R43

- **E35, karar 99 ile kapandı:** Taslağı nesneyi gören ekleyen, sorumlu, sorumlunun üstleri ve onaylayabilecek kişiler görür. Y101d'de özel tür yalnız YETKILI onayına açıktır; K012 üst olduğu için okur, onaylayamaz. K044 okuyamaz. Varsayılan tabloda üst zaten onaylayabildiğinden eski Y101 değişmez.
- Süzgeç sürüm listesiyle sınırlı değildir. Doğrudan dosya okuma ve ham olay okuma da taslak erişimini denetler. C53 bu yolların birlikte kapatılmasıdır.
- Geçmişteki geçerli sürüm okunurken güncel proje erişimi de aranır. Tarih parametresi eski erişimi geri kazandırmaz. C57 bu denetimdir.
- R43 yalnız geçerli sürüm kimliği değişirse üretilir. Daha küçük numaranın onayı ve taslağın geri çekilmesi bildirim üretmez. Son onay geri çekilince “yok”a geçiş de değişimdir.
- Açık işte güncel liste sahibi, görevde görev kişisi alıcıdır. Birden çok nesne bağı ve birden çok alt iş dikkate alınır; kişi bir olay için tek bildirim alır. Bitmiş/iptal işler ve olayı yazan kişi çıkarılır. C54 ilk nesne dışındaki bağların da denetlenmesidir.

## Y14-05 · Modül kapısının kalıcılığı ve alıcılar

- Kapı çağrısı olay değildir. `Depo.modul_bildirimleri` kalıcı tablosuna yazar. `Motor` bu tabloyu taşımaz veya yeniden hesap girdisi yapmaz. `olaylar`, `_kayitlar` ve `olay_nesneleri` kapı çağrısı içermez.
- Kurtarmada tablo ayrı kopyalanır. I90 ve paket tam hesap karşılaştırması da bu ayrı kaynağı taşır. C56, eski I90 kurtarma yardımcısının bu tabloyu unuttuğu uyarlama hatasıdır.
- Alıcı tanımları `{tur, kimlik}` biçimindedir. Kişiye çevrilmiş liste saklanır. Geçersiz tür biçim hatasıdır; olmayan/istihdam dışı kişiler süzülür. Son liste boşsa `alici_kalmadi: true` döner ve yazma olmaz.
- Aynı servis kimliği iki modüle atanamaz. `CEKIRDEK` kaynak adı ayrılmıştır. Pasif modül yeni bildirim bırakamaz; kendi eski kaydını kaldırabilir. Eski geçerli kayıtlar görünmeye devam eder.
- **B57, kabul edildi:** `MODUL.TANIMLADIM` yalnız YETKILI'ye açıktır. Yetki tablosuyla devredilemez. T10 sürüm 2 bu sabit güvenceyi açıkça yazar. Servis kimliği yalnız kendi modülüyle bildirim bırakabilir.
- Proje süzgeci hem bırakmada hem okumada uygulanır. Ek erişimi sonradan kaldırılan kişinin kutusundan bildirim gizlenir; kayıt ve görülme bilgisi silinmez. İş geçmişi nedeniyle projeyi görmeye devam eden kişide gizlenmez.
- Kayıt anahtarına tür de dahildir. Ayraç karakterleri yüzde kodlamasıyla kaçırılır; farklı modül/kural/kayıt bileşimleri aynı anahtar olamaz.

## Y14-06 · B54: kapıdaki an

**B54, kabul edildi.** `an` modülün kaynak anıdır; gelecekte olamaz, geçmişte olabilir. Alıcılar bırakma anındaki güncel çekirdek durumundan çözülür. `birakma_ani` ve `guncelleme_ani` çekirdeğin saatinden gelir. Geç tekrar metni son kabul sırasına göre günceller. İnsan olaylarının saatleri değiştirilmez.

Bu davranış T10 sürüm 2'ye işlendi. Gerçek servis kimliğinin doğrulanması ürünün kimlik doğrulama katmanının işidir; modeldeki parametre doğrulanmış oturum kimliğini temsil eder.

## Y14-07 · B55: kaldırma, tekrar ve görülme

**Orta.** Kaldırılan aynı anahtar tekrar bırakılırsa aynı kayıt etkinleşir; görülme korunur. Kısalmış bir alıcı listesi eski alıcıları kendiliğinden kaldırmaz. Kaldırma bütün alıcılar içindir. Yeni alıcıya yeni satır açılır. Ayrı bir iş vakası için modül ayrı kural/kayıt anahtarı kullanır.

Etkinlik aralıkları tabloda tutulur. Bildirim kaldırıldıktan sonra gelen çevrimdışı `BILDIRIM.GORDUM`, kişinin bildirimi etkin olduğu sırada gördüğünü taşıyorsa görülme işlenir. Bildirimin var olmadığı aralık için görülme üretilmez. Bu aralıklar kural motoruna kaynak yapılmaz.

## Y14-08 · Senaryo ve eski sürüm

Y100, Y101, Y101b, Y102 ve Y102b'nin yazılı beklentileri aynen geçti. SN1 gerektiren senaryo hesap veya beklenti hatası bulunmadı. İlk ay T10 akışı ayrı dosyadır; eski dört simülasyon girdisi ve 183 senaryo girdisi değiştirilmedi.

Yeni kurulumun varsayılanı 10.1'dir. Tarihsel ortak veri sürüm 9 yetki tablosuna bağlı kalır. T10'a ait iki yeni yetki satırı eski girdilere kendiliğinden eklenmez. Eski bayat özetler için yeni bir gevşetme yapılmadı.

## Y14-09 · Büyük akışın çalışma kaydı

İlk başlatma C55'in geçmiş saatli sürüm karşı örneği doğrulanınca, 500 adımlık ilerleme kaydından sonra durduruldu. Tam büyük akış tamamlanmamıştı. Kusur düzeltildikten ve 548 test, 188 senaryo, dört kısa simülasyon geçtikten sonra bir tam son koşu tamamlandı. Son koşu 3.306 adım ve 2.051,353 saniyedir; tam/kapsamlı hesap eşit, I59–I126 geçti, işleme hatası sıfırdır. Kaynak ve paket modelinin dosya özetleri koşunun başında ve sonunda aynı kaldı. Toplam iki başlatma, bir tamamlanmış tam koşu vardır; kesilen başlangıç başarıya eklenmedi.

## Y14-10 · Kalıcılık belgelerinin sınırı

- **E36, orta:** T2 §0, üç kaynak dışındaki her tablonun silinip yeniden kurulabileceğini söylüyor. T10 §3 bu genellemenin yeni istisnasıdır. Modül bildirimi ayrıca yedeklenir ve kurtarılır; yeniden hesap kaynağı yapılmaz. T2'ye T10 istisnasını gösteren kısa bir bağlantı eklenmesi önerilir. T1 motor sorumluluğundaki “her bildirim” ve T5 `yeniden_kur` açıklaması da aynı ayrımı anmalıdır.
- **E37, orta:** T8 §12, modülün çekirdeğe yalnızca kullanıcının insan olayıyla yazabileceğini söylüyor. Karar 97 ile T10 §3, servis kimlikli bildirim kapısını ekler. Bu, modüle çekirdek tablolarına doğrudan yazma yetkisi vermez. T8'in sözleşmesine bu kapının bağlantısı eklenmesi önerilir.

Bu iki noktada model T10'u uygular. Yeni bir kullanıcı onayı veya ekran adımı gerekmez. Kaynak tasarım belgeleri bu turun yetkisi gereği değiştirilmedi.


---

## Korunan sürüm 10 yorumları

Aşağıdaki metin sürüm 10 paketinden aynen korunmuştur. Tarihsel ölçü ve önerileri anlatır; T10 ile çelişen yerde yukarıdaki 14. tur yorumları uygulanır.

# 13. tur uygulama yorumları

Öncelik: büyük numaralı karar > T9 sürüm 2 > T8 > T1–T7. Kararlar 91–93 uygulandı. Tasarım ve senaryo belgeleri salt okunur bırakıldı. Aşağıdaki seçimler başvuru modelinin açık sözleşmesidir.

| Konu | Uygulanan yorum ve sınır |
|---|---|
| Projeyi görmek / yönetmek | Bir projeyi görmek o projeye yönetim kararı yazma yetkisi vermez. Güncel proje sorumlusu, üstleri, projedeki etapların birim yöneticileri/üstleri, açık etap sorumlusu/üstleri ve genel yönetim yetkilidir. Eski proje sorumlusu geçmiş ilişkisiyle görür; başka güncel yetkisi yoksa yazamaz. |
| Departman / çalışan | Etap, departmanı projeye dahil eder. Departmanın sıradan çalışanı yalnız bu nedenle projeyi görmez; iş/görev veya ek erişim gerekir. Ek erişim kişiye iş verilmesine izin verir, yönetim yetkisi vermez. |
| Atama | Yeni işte yazan ve alıcı kapıları birlikte denetlenir. Çoklu atamanın tek satırı yetkisizse bütün olay reddedilir. İşi başka kişiye/projeye taşımak yeniden atamadır. Ek erişimi kalkmış mevcut işin açıklamasını değiştirmek yeniden atama sayılmaz. |
| Çevrimdışı tanıklık | Kişinin kendi açık işindeki tanıklığı kişisel kapılardan geçer. Daha sonra erişimin kalkması geçmişteki tanıklığı iptal etmez. Yönetim olayında hem kabul anının mevcut kapıları hem olay anının proje yetkisi aranır. |
| B49 · farklı ekibin sorumluluk satırı | Karar 92'nin kişi/birim payına itiraz, doğrulama ve üst çözümü hakkı, karar 91'in proje yönetim kapısından ayrıdır. Başka ekibin sorumlu kişisi/üstü kendi sorumluluk satırında işlem yapabilir. Bu işlem projeyi görme veya başka iş atama hakkı vermez. **Öneri:** T9 §6'ya bu dar istisna açıkça yazılmalı. |
| B50 · etap tarihi | Etabın bitiş tarihi plan tarihidir. Departmanı projeden otomatik çıkarmaz; açık iş ve sorumluluk devam edebilir. **Öneri:** üyelik kaldırılacaksa ayrı, geçmişi koruyan bir işlem tasarlansın. Bir tarih aşımıyla görünmez yetki kaybı üretilmesin. |
| Servis bağı | Ana proje ve doğrudan bağlı servis ilişkisi okuma içindir. Servis kendi proje sorumlusu/etaplarıyla yönetilir. Ana projenin departman üyeliği ve yönetim yetkisi servise kendiliğinden aktarılmaz. Kardeş servislere sınırsız geçişli görünürlük verilmez. |
| Etap ve plan | Yeni tablo etap açma/değiştirmeyi YETKILI'ye verir. PROJE_SORUMLUSU devri ilgili proje ve üst zinciriyle sınırlıdır. Plan onayında proje sorumlusu/üstleri ve genel yetkili kullanılır. Eski HERKES ortak verisi sürüm 9 tablosunu korur. |
| B51 · Y98b | “Aynı adımlar” ile “eski yetki tablosu sabit” ifadeleri 13:00'daki yetki değiştirme olayında çakışır. Eski tabloyu koruma önceliklidir: Y98b bu devir olayını uygulamaz; diğer denemeler eski beklentiyle kabul edilir. **Öneri:** senaryoya “13:00 yetki değiştirme adımı hariç” eklensin. Bu bir hesap hatası değildir; SN1 açılmadı. |
| Yalnız not | Geç ilk teslimde neden seçilmeden açıklama verilirse neden BELIRTILMEDI olur. Hem neden hem açıklama yoksa önceki GIRILMEDI davranışı sürer. Atölye duruşunda da not yeterlidir. Normal zamanında teslimde gecikme notu zorunlu değildir. |
| Kredi | Dış neden payı ile doğrulanmış/etkin başka kişi veya birim payı toplanır. Kendi payı kredi değildir. Doğrulanmamış ve itirazdaki başka pay sıfır kredi verir. Kalan yük `1 - kredi` ile teslim edendedir. Kaldırılan pay için yeni sorumluluk olayı veya sahte satır oluşturulmaz. |
| Kesinleşmedi | Bekleyen sayısı yalnız son gecikme değerlendirmesinin pozitif ve henüz etkin olmayan/itirazdaki satırlarını sayar. Eski değerlendirmelerin itirazları yeni göstergenin sayısını şişirmez. Bu alan bütün kalite, maliyet veya eksik süre verisinin tamamlık göstergesi değildir. |
| Sessiz kabul | Sayaç değerlendirme olayından sonraki iş günlerini sayar; değerlendirme saatini korur. Kişi payında kişinin, birim payında birimin takvimi kullanılır. 26 Ekim 11:00 → 27, 28 ve 30 Ekim; 29 Ekim tatildir. Sonuç 30 Ekim 11:00'da etkinleşir. Eski kurulumda ayar 0'dır. |
| Geç olay ve itiraz | Süre teslim zamanından değil olay anından hesaplanır. Geç gelen, süresinde yapılmış itiraz geçmişi yeniden kurar; sessiz kabul geri hesaplanır. Açık itiraz süre dolunca kapanmaz. Üst kabul ederse pay kalkar; reddederse kalan pay açıkça doğrulanır (C52 düzeltmesi). |
| Kaynak / türeyen durum | Sessiz kabul kaynak olay günlüğüne hayali ONAY yazmaz. Kaynak `dogrulandi` alanı açık onayı gösterir; `etkin_pay` zamanla doğan kabulü de içerir. Raporlar bu etkin değeri kullanır. Üründe bu ayrım arayüzde kişiye iki ayrı onay işi çıkarmamalıdır. |
| Takvim ufku | Sürekli kapalı takvimde sessiz kabul tarihi yoktur. Hesap mevcut görünümün zaman ufkuyla sınırlıdır; sonsuz döngü yoktur. Aynı tarihteki izin/takvim değişikliği mevcut tarihli hesap kurallarıyla yeniden değerlendirilir. |
| Hata / gecikme | Üç iş günü kuralı yalnız GECIKME kaynağına uygulanır. Kalite/hata sorumluluğunun eski onay ve gerekçe koşulları değişmez. |
| İtirazın yenilenmesi | Yeni gecikme değerlendirmesi yeni satır kimlikleri üretir. Eski itirazın kabul/ret sonucu yeni satırlara taşınmaz; tarihsel kaynakta kalır. |
| Eski paket özeti | Eski girdi biçimi 1/2 veya açık v8/v9 uyumu, yalnız mevcut kaydın eski alan özetine tam eşleşirse dönüştürülür. Bilinmeyen ve bayat SHA-256 güncellenmez. Canlı modelde bu köprü yoktur. |
| Gerileme sayısı | JSON dizileri indeksleriyle karşılaştırılır. Eski UYELER akışında bir işin reddi, sonraki aralık dizisini kaydırarak binlerce yaprak farkı doğurabilir. Fark sayısı bağımsız kusur sayısı değildir. Kabul/ret olayları ayrıca listelenir. |
| Yeni ay / eski ay | 773 adımlı eski T9 girdisi değiştirilmeden gerilemede kullanıldı. Karar 91–92'ye uygun yeni T9 ayı 844 adımdır. Birbirinden farklı bu iki girdinin çıktıları gerileme farkı diye sayılmaz. |
| Bölünmüş dosya | İlk ay T9'un 51.966.877 baytlık mantıksal çıktısı kök ve beş ara görüntü parçasına ayrıldı. Birleştirme sonrası aynı JSON elde edildi; küçük boş depoların `ara_haller: []` alanı korundu. |
| Değişmezlerin gücü | I106/I107 tarihsel olayları tekrar kurar; I108 ve I110 pay/takvim hesabını denetler. Bazı kontroller aynı yardımcıları da kullanır. Bağımsız elle beklenen Y98/Y99 sonuçları ve hatalı yüzdeyle değişmez bozma denemesi bu nedenle ayrıca vardır. Tam hesap eşitliği tek başına iş kuralının doğruluğunu kanıtlamaz. |
| Şartname hükmü | 2.552 çekirdek kaydının tamamına v10 hükmü verildi. 1.097 eski açık birebir ve komşularıyla okundu. Modülün fatura, stok, onay belgesi ve ekranı hazır çekirdek işlevi sayılmadı. KRITIK önemi yalnız yeni olay/alan gereksinimine dayanarak verilmedi. |
| Görsel sınırı | Bu turda 11. turun görsel metin dökümleri yeniden okundu; 24 kaynak görsel tekrar açılmadı. Yeni OCR veya yeni piksel incelemesi yapıldığı iddia edilmez. |
| Ürün sınırı | Başvuru modeli standart kütüphaneli Python'dur. Gerçek veritabanı satır yetkisi, süreçler arası kilit, ağ yarışı, saat altyapısı ve yük altında performans ürün aşamasında doğrulanmalıdır. İç ham hesaplar kullanıcı API'si olarak açılmamalıdır. |

Y98/Y99'un sayısal beklentilerinde hesap hatası bulunmadı. Kaynak senaryo değerleri değiştirilmedi. B49–B51 için yukarıdaki uygulanabilir yorumlar seçildi; kullanıcıdan karar beklenmedi.

## Önceki sürümlerin yorumları

Sürüm 8–9 yorumları `3295dda` commit’inde korunur. Özellikle Y12-07, Y12-08 ve Y12-12 artık geçerli değildir; kararlar 91–92 yukarıdaki kuralları getirir.
