# IRP cevap anahtarı · sürüm 10.2 / T11

Karar 112–113 düzeltmeleri dahil Python 3.11 başvuru modeli. Yalnız standart kütüphane gerekir. Paket başka klasöre taşınıp Python `-I` ile çalıştırılabilir. 18. tur düzeltmeleri ve dondurma tavsiyesi depo kökündeki `codex/sonuclar/tur18_A.md` içindedir. Önceki yorumların geçmişi `tur17_yorumlar.md` ve `tur17_SONUC.md` içindedir.

## 18. tur düzeltmesi · sürüm adı 10.2 kalır

- Karar 112: `AKTARIM`, SIRA kapısından muaftır. I127 yalnız kullanıcının yönetim kararını denetler. Y26'nın cevabı `cevap-anahtari-v10.1.1` ile aynıdır.
- Karar 113: GANTT iş/görev satırlarında `gecikme_takvim_dk` ve `gecikme_mesai_dk` vardır. Son teslim anından (işte planlanan bitişten) gerçek bitişe, bitmediyse şimdiye kadar hesaplanır. Erken teslimde ikisi de sıfırdır. Teslim sınırı olmayan, iptal edilen veya kişi takvimi tanımlanmamış ETAP özetinde `null` döner.
- Mesai dakikası A12 kapasitesidir: kişinin takvimi + onaylı ek mesai − izin. Mola ve tatil sayılmaz. Atanmamış işte havuz biriminin takvimi kullanılır. `gecikme_raporu` mevcut satırlarında bu iki değeri sorumluluk yüzdesiyle toplar; performans alanlarını ve raporun mevcut seçim kuralını değiştirmez.
- Tezgâhın planlı kapasitesi vardiya ve ilgili ek mesai pencerelerinin birleşiminden hesaplanır. Aynı saat iki kişi için sayılmaz; bakım her iki pencereyi de kapatır. Plansız duruş kapasite paydasını azaltmaz, uygunluğu engeller. `EK_MESAI.PLANLADIM`, atama içindeki ek mesai ve gerçekleşen `ONAYLADIM` kapsanır; iptal edilenler çıkarılır. Hedef işin tezgâhı esas alınır.
- `TEZGAH_GOSTERGESI`, `TEZGAH_UYGUNLUK` ve `TAKVIM(tur=TEZGAH)` aynı pencereleri kullanır. `KAYNAK_YUKU` mevcut liste cevabını korur. `tur=TEZGAH, kapasite_dahil=True` verilirse `{satirlar:[...], planli_kullanilabilir:6.0}` döner. Sayı bütün sorgu penceresinin saatidir; yük satırı olmasa da kapasite döner. Satırların gizlilik maskeleri aynıdır. T11 kapasite özetinin JSON biçimini belirtmediği için bu isteğe bağlı biçim seçildi.
- Y113, Y113b ve Y114 eklendi; toplam **213 sözleşme çifti** vardır. Eski girdiler değişmedi. Adım ve alan bazında gerileme `tur18_gerileme.json` içindedir.

## 10.1.1'den 10.2'ye

- Nesnenin projesi tek PROJE bağından tamamlanır. Çelişkili proje bağı BICIM alır. Proje yetkisi bağ üzerinden de uygulanır.
- Kullanıcının yönetim kararı, kabul anında dayandığı etkin kaydın olayından önce sıralanıyorsa `REDDEDILDI / BAYAT / SIRA` döner. `AKTARIM` muaftır (karar 112). Tanıklık eskisi gibi kabul edilir. Sıra `(oldugu_an, olay_kimligi)`dir. İstemci saati yeniden ölçer, kaydı yeniler ve yeni basışla gönderir.
- Projeyi gören nesne sorumlusu kendi nesnesinin aşamasını geçirir. Diğer yönetim hakları değişmez. R43 nesne bağlarını iki yönde tek basamak izler. NESNE hedefli not kabul edilir.
- `KISI.YETKINLIK_TANIMLADIM`, işte `yetkinlik`, modülde `cihaz_harfi` eklendi. Yetkinlik atamayı engellemez. Yeni Sibernetik tür verisi `model/irp/varsayilanlar_v10_2.py` içindedir. Eski PARCA türü ve yetki olayları kendiliğinden değiştirilmez.
- `MALIYET` yalnız tezgâh ücretini okuyabilir. Maaş ve kişinin saat maliyeti YETKILI'ye aittir. `SAAT_MALIYETI` tezgâh hedefinde SAAT_UCRETI döndürür.
- Gantt satırlarına `tezgah`, `kisi`; bildirim bırakma cevabına `suzulenler: [{kisi,neden}]` eklendi. Nedenler PROJEYI_GOREMEZ, AYRILDI, ISTIHDAM_DISI'dır.
- Y103–Y112 ve Modül 3'ün altı ayrı senaryosu eklendi: 210 dosya çifti. I127–I131 eklendi. Eski girdiler değişmedi; izinli cevap farkları `tur17_gerileme.md` içinde adım adım listelidir.

## Yeni dış okumalar

Python çağrısı `oku(d, kim, veri, hedef=None, **parametre)` biçimindedir. Aşağıdaki kimlik parametreleri `hedef` olarak da verilebilir. An penceresi `[bas, bit)`; tarih verilirse bitiş günü dahildir. Para JSON'da iki ondalıklı metin, modelde Decimal'dir.

| veri | Parametreler | Cevap |
|---|---|---|
| KISILER | birim isteğe bağlı | `[{kimlik,ad,birim,yaka,roller,aktif,yetkinlikler}]` |
| BIRIMLER | yok | `[{kimlik,ad,ust,basi,yoneticileri,takvim}]` |
| TEZGAHLAR | birim isteğe bağlı | `[{kod,ad,birim,aktif,vardiyalar}]` |
| TAKVIM | tur=KISI/BIRIM/TEZGAH, kimlik, bas, bit | `{calisma:[{bas,bit}],kapali:[{bas,bit,neden}]}` |
| ETAPLAR | proje | Projenin etap kayıtları |
| NESNELER | proje, tur, kod isteğe bağlı | Görünür nesnelerin ana kayıtları |
| TOP_KIMDE | nesne | Aşama, sorumlu, başlangıç ve aşama süreleri |
| KAPASITE | kisi, bas, bit | Saat cinsinden sayı |
| TEZGAH_UYGUNLUK | tezgah, bas, bit | `{uygun,neden}` |
| TEZGAH_GOSTERGESI | tezgah, bas, bit | Planlı kullanılabilir/gerçekleşen saat, duruşlar, oran, alınmayı bekleme dakikası |
| TEZGAH_UCRETI | tezgah, gun | Saat ücreti veya VERI_EKSIK |
| ISCILIK_MALIYETI | proje, bas, bit | `{iscilik,tezgah,eksik_veri,onay_bekleyen}`; kapanmış ay yalnız tam ay |
| LISTE | kisi | `{isler:[...],surum}`; LISTE hedefi bu sürümle gönderilir |
| KAYNAK_YUKU | tur=KISI/TEZGAH, kimlik, bas, bit; TEZGAH için kapasite_dahil isteğe bağlı | Görünür iş/görev plan aralıkları; kapasite_dahil=True ise satirlar ve planli_kullanilabilir saat özeti |

TAKVIM izin açıklamasını yetkisize MUSAIT_DEGIL yapar. KAYNAK_YUKU görünmeyen proje için yalnız `{proje:ERISIM_DISI,planlanan_baslangic,planlanan_bitis}` döndürür. Başkasının kişisel işlerini okuyamayan kişi yalnız `{durum:MESGUL,bas,bit}` alır. PLAN_CAKISMALARI gizli tarafı `{tur:ERISIM_DISI}` olarak korur. Tanımsız veri görünürlük kontrolünden önce `ValueError('TANIMSIZ_VERI')` verir.

## Çalıştırma ve dosyalar

Depo kökünde günlük komut: `py -3.11 -B referans/dogrula_v10_2.py`. Büyük akışı da istemek için `--buyuk-dahil` eklenir.

Modül 3: `py -3.11 -I -B referans/cevap_anahtari/yurut.py --modul M3 --tam-kontrol`.
Tüm çekirdek ve modül senaryoları: `py -3.11 -I -B referans/cevap_anahtari/yurut.py --tum --tam-kontrol`.

`modul_sozlesmeleri/modul3/` Modül 3'e aittir. Altı özgün girdi dizisi korunur; yalnız sona 10.2 ekleri konur. `senaryo_dizini.json` bu kayıtları `modul: M3` olarak ayırır. Yeni ay akışı `simulasyon/ilk_ay_t10_2` eski T10.1 akışını genişletir.

Büyük ara durumlar yaklaşık 20 MB'lık `.araNN.json` dosyalarına bölünür. Ana beklenen dosyadaki `ara_haller_dosyalari` sırası korunur; `karsilastir.oku` bunları birleştirir. Her dosya 50 MB'ın altında tutulur. Araçların ham ölçümleri, günlükler ve rastgele akışlar pakete girmez.

Modül harfi cihazlara ayrılmaz; `d.cihaz_kaydol(kim,cihaz)` bulut tarafındaki örnek kayıt işlevidir. O harfle gelen olayın `cihaz`ı `MODUL-<kod>` olmalıdır. Harf bir kez ayrılınca yeniden tanımda silinmez veya değiştirilmez.

## Önceki sürümlerin geçmişi

Aşağıdaki sürüm sayıları ve denetim notları ait oldukları turun tarihsel kaydıdır. Güncel paket 213 sözleşme çifti ve altı simülasyon içerir; günlük komut büyük akış dışındaki beş simülasyonu çalıştırır. Güncel değişmez denetimi I59–I131'dir; I1–I58 test takımında ve tur17 rastgele denetiminde ayrıca çalışır. 18. turda büyük akış, rastgele akış ve mutasyon çalıştırılmadı.

## 16. tur · kapsam eki

Dört KP senaryosu eklendi: karar 99 tarihsel denetimi, kişi bazında onay maliyeti,
modül bildirimi tekilliği/ret ve çok biçimli dosya kanıtları. Toplam 194 dosya çifti vardır.
Yeni testlerde tasarımdan çıkarılamayan beklentiler ayrıca işaretlidir:
sayısal hatırlatma ayarının birimi B58, Gantt penceresinin uçları B59,
modül bildirimi etkinlik aralığının uçları B60 **davranış kilidi** testleridir.
Bu dört yorum karar 100 / T11 §9 ile kapandı. B61 model toleransıdır; ürün tam sayı saniye kullanır.

C58, I106/I107 denetiminin karar 99 istisnasını yanlış ihlal saymasını düzeltir.
C59, ONAY görevinde kişi süzgecini uygular. Bu düzeltme eski kısa simülasyonun
`onay_bekleyen` tutarlarını değiştirir: **DONMUS_DAVRANIS_DEGISTI**.
Eski girdiler korunur. Değişen dosyalar ve her eski/yeni tutar
[16. tur raporundadır](../../codex/sonuclar/tur16_SONUC.md).
Bu iki düzeltme karar 100 ile kabul edildi; 10.1.1 etiketi gerileme tabanıdır.

Üretici, 200 sabit tohum, 308 mutasyon ve küçültülmüş karşı örnekler
`codex/calisma/tur16/` altındadır. Büyük akış, C59 ortak maliyet hesabına
dokunduğu için bu turda yalnız bir kez denetlenir; kapsam yüzdesine katılmaz.

## 14. turdan farklar · sürüm 10.1 son hali

- `UYELER` ayarında projeyi gören nesne sorumlusu, projede yönetim yetkisi olmadan kendi belgesine taslak sürüm ekleyebilir. İstisna yalnız `NESNE.SURUM_EKLEDIM` içindir. Onay/geri çekme türün yetkisinde kalır; ekleyen kendi sürümünü onaylayamaz veya geri çekemez. Üstler için T9 proje yazma kapısı sürer.
- Taslağı nesneyi gören ekleyen, sorumlu, sorumlunun üstleri ve onaylayabilecek kişiler görür. Sürüm listesi, dosya ve ham olay aynı taslak süzgecini kullanır. Diğer okuma kapıları ve güncel proje erişimi korunur. I119 bu erişimin hem eksik hem fazla verilmesini denetler.
- Y101c ve Y101d eklendi: toplam **190 dosya çifti**, **124 ana senaryo**. 14. turun 188 senaryosu ve beş simülasyonunun girdileri ile beklenen dosyaları aynıdır. İlk ay T10.1'de de çıktı farkı yoktur. B53–B57 davranışları korunur.
- Büyük akış 15. turda çalıştırılmadı. Beklenen dosyasının ham SHA-256 özeti 14. turla aynıdır; girdide `NESNE.SURUM_*` veya `UYELER` yoktur. Diğer dört simülasyon tam hesap ve I59–I126 ile doğrulanır.
- Turun üretim ve denetim araçları `codex/calisma/tur15/` altındadır. Yeni kayıt aracı yalnız Y101c–d'yi üretir; eski cevapları yeniden yazmaz.

## Sürüm 10'dan farklar

- İş/görev plan tarihleri atamada veya atomik `PLAN.TARIHLEDIM` ile yazılır. `gantt` ve `plan_cakismalari` aynı planı okur. Çakışma reddetmez; bitişi sonraki başlangıca değen aralık çakışmaz. B0/B1 etap planları değişmez.
- `NESNE.SURUM_EKLEDIM`, `NESNE.SURUM_ONAYLADIM`, `NESNE.SURUM_GERI_CEKTIM` ve `surum_onaylayanlar` eklendi. Geçerli sürüm en büyük numaralı ONAYLI sürümdür. Taslak dosyaları da görünürlük kapısından geçer. Geçerli sürüm değişirse R43 açık iş/görev kişilerine gider.
- `MODUL.TANIMLADIM` bir insan olayıdır. Modülün bırakma/kaldırma çağrısı **olay değildir**; ayrı adım ve ayrı kalıcı tablo kullanır. `BILDIRIM.GORDUM` iki bildirim türüne de uygulanır.
- Yeni tablolar: `nesne_surumleri`, `moduller`, `modul_bildirimleri`. Eski girdilerde boştur. Çekirdek bildirimlerine `kaynak=CEKIRDEK`, `onem=BILGI` eklenir. İsteğe bağlı plan ve onaylayan alanları verilmediyse eski kayıtlara zorunlu boş alan eklenmez. Eski kabul/ret ve sayılar korunur.
- Yeni kurulumda iki yeni yetki satırı vardır. Eski ortak veri v9 yetki tablosunu kullanmaya devam eder. Eski SHA-256 özet köprüsü genişletilmedi.
- Yeni girdiler `bicim_surumu: 4` taşır. 14. turda 188 dosya çifti, 124 ana senaryoyu kapsıyordu. Y100, Y101, Y101b, Y102, Y102b eklendi. Eski 183 senaryo ve dört simülasyonun girdi baytları korunur. Yeni `ilk_ay_t10_1` 900 kayıtlı adımdır.
- I114–I126 eklendi. Model testi takımı I1–I126'yı, simülasyon denetimi I59–I126'yı kapsar. Yeni iş akışında zaman/kimlik çakışması ve kalıcı tablonun kurtarılması ayrıca sınanır.

## Modül bildirimi adımı

```json
{
  "tur": "modul_bildirimi",
  "ad": "birak",
  "saat": {"simdi": "2026-10-22T10:00:00+03:00", "gercek": "2026-10-22T10:00:00+03:00", "demo": false},
  "args": [],
  "kwargs": {
    "servis_kimligi": "SRV-M3", "modul": "M3", "kural": "SIPARIS_GECIKTI",
    "kayit": {"tur": "PROJE", "kimlik": "2509084"},
    "alicilar": [{"tur": "KISI", "kimlik": "K009"}],
    "metin": "Sipariş gecikti", "onem": "UYARI", "an": "2026-10-22T10:00:00+03:00"
  }
}
```

Bu örnekten önce modülün normal `MODUL.TANIMLADIM` olayıyla tanımlanmış olması gerekir. `ad: kaldir` aynı kimlik, modül, kural, kayıt ve anı alır; alıcı/metin/önem almaz. `args` dizisinde aynı sırayla konumsal argümanlar da taşınabilir. `modul_bildirimi_semasi.json` iki kapının alanlarını tanımlar. Olay şeması kapı çağrısını kabul etmez.

Alıcı türleri: KISI, BIRIM_YONETICILERI, ROL, PROJEDE_YETKILILER, NESNE_SORUMLUSU. Her biri `{tur, kimlik}` biçimindedir. Kayıt türleri: PROJE, IS, GOREV, NESNE. `kayit.modul_kaydi` isteğe bağlı metindir; çekirdek tekillik anahtarını değiştirmez.

Başarılı bırakma `alicilar`, `yeni`, `guncellenen`, `alici_kalmadi` döndürür. Liste süzülüp boşalırsa başarılı fakat yazmasız sonuç verir. Kaldırma `kaldirilan` sayısını döndürür. Red kodları YETKI, BICIM, DURUM'dur.

Anahtar `<modul>/<kural>/<tur:kimlik>/<alici>` bileşenlerinin her biri yüzde kodlamasıyla kaçırılarak kurulur. Örneğin `M3/SIPARIS_GECIKTI/PROJE%3A2509084/K009`. Aynı anahtar metin/önemi günceller; görülmeyi korur. Kaldırılmış kayıt tekrar bırakılırsa aynı satır etkinleşir. Yeni alıcı eklenebilir; alıcı listesini kısaltmak eskileri silmez.

`an` kaynak anıdır; geçmişte olabilir, gelecekte olamaz. Alıcılar bırakma anındaki güncel durumla çözülür. `birakma_ani` ve `guncelleme_ani` çekirdek saatidir. Pasif modül yeni bırakma yapamaz; kendi kaydını kaldırabilir. Güncel proje erişimi okumada yeniden süzülür.

## Kalıcılık ve okuma kapıları

`modul_bildirimleri` son halde geçersiz kayıtları ve görülmeleriyle birlikte bulunur. Olay günlüğünün, `olay_nesneleri`nin veya Motor yeniden hesap girdisinin parçası değildir. Yedekten kurtarmada olaylar, hassas ekler, ay kapanışları ve bu tablo ayrı taşınır. Tabloyu olaylara dönüştürmek yanlış uygulamadır. İnsan görülme olayı kaynak olmaya devam eder.

`oku` dış okuma kapısına GANTT, PLAN_CAKISMALARI, SURUMLER, GECERLI_SURUM, BILDIRIMLER eklendi. `okunmamis_bildirimler` iki türü birlikte döndürür. Bildirim kutusu yalnız kendi alıcısına açılır. İç hesap fonksiyonlarında çağıran verilmemesi kullanıcı yetkisini kaldıran bir ürün API'si değildir.

T10 yönetim hedefleri güncel nesne özetini taşır. Yeni olaylardaki `kabul_sirasi` ve sürüm eklemedeki `nesne_surum_no` yalnız sunucuda atanır; istemci değerleri kullanılmaz. Numaralar kabulde verildiği için geçmiş saatli yeni taslak önceki onayı başka dosyaya taşıyamaz. Aynı ana iki yönetim isteği aynı özeti taşıyorsa biri BAYAT alır. Nesne doğumundan önce sürüm ve önceki geçişten eski onay/geri çekme reddedilir.

## Bölünmüş beklenen dosyalar

Hiçbir dosya 50.000.000 bayta çıkamaz. Büyük ara görüntüler yazılmadan önce parçalara bölünür. `ilk_ay`, `ilk_ay_t9`, `ilk_ay_t10_1` kökleri `ara_haller_dosyalari` alanıyla kardeş dosyaları gösterir. Kök ile bütün başvurduğu parçaları birlikte taşıyın. `karsilastir.oku` ve oynatıcı bunları kayıpsız birleştirir. Parça yolu paket klasöründen dışarı çıkamaz.

Depo kökünde günlük doğrulama: `py -3.11 -B referans/dogrula_v10_1.py`. Büyük akış için `--buyuk-dahil` eklenir. Aşağıdaki `--simulasyon` seçeneği de uzun büyük akışı içerir.

## Çalıştırma

Paket klasöründe:

```powershell
py -B yurut.py --tum
py -B yurut.py senaryolar/Y45b.girdi.json --dogrula
py -B yurut.py senaryolar/Y44.girdi.json --cikti model_sonuc.json
py -B karsilastir.py senaryolar/Y44.beklenen.json urun_sonuc.json
py -B yurut.py --simulasyon --tam-kontrol
```

`--tum`, 190 senaryo dosyasını çalıştırır: S1–S18, D1–D4 ve Y1–Y102 aralığındaki 124 ana senaryonun alt durumları. `--simulasyon` farklı firma, eski ilk ay, ilk ay T9, ilk ay T10 ve büyük akışı çalıştırır. `--tam-kontrol` her 100 adımda, kapanışta ve sonda kapsamlı hesabı boş motordaki tam hesapla karşılaştırır. `--degismez-kontrol` simülasyon sonunda I59–I126'i denetler; tarihsel yetki ve kapanış da yeniden hesaplanır. I1–I58 model test takımındadır. T8/T9/T10 bağlantılarında tam hesaba geri dönüş kullanılır; artımlı hızlandırma iddiası yoktur. Büyük akış uzun sürer; yalnız kısa kontrol için `--tum` veya tek simülasyon yolu kullanın.

Başarı çıkış kodu 0, karşılaştırma farkı 1'dir. `karsilastir.py` okunamayan/bozuk JSON için 2 döner. Beklenen dosyalar çalışma sırasında değiştirilmez. Yeni kural için bu sürümü değiştirip eski sonucu kaybetmeyin; yeni sürüm ve gerekçeli fark üretin.

## Dosyalar

| Yol | İçerik |
|---|---|
| `model/irp/` | Depo, kabul, durum, hesap, cihaz ve zaman kodu; yalnız standart kütüphane |
| `olay_semasi.json` | JSON Schema 2020-12; olay alanları, eyleme bağlı girdi şemaları, sınıflar, yetki matrisi ve anlamsal kurallar |
| `senaryolar/*.girdi.json` | Kendi ortak verisini içeren, bağımsız çalıştırılabilir girdi |
| `senaryolar/*.beklenen.json` | Kabul/retler, ara durumlar, istenen sorgular ve tam iş sonucu |
| `senaryo_dizini.json` | 124 ana senaryoyu kapsayan 190 dosya çifti ve kaynak test eşlemesi |
| `simulasyon/buyuk.girdi.json` | Büyük akışın gerçek geliş sırası, tekrarları, ret denemeleri, hassas ekleri ve ay kapanışı |
| `simulasyon/buyuk.beklenen.json` | Büyük akışın beklenen cevapları, durumları ve panoları |
| `simulasyon/ilk_ay.girdi.json` / `ilk_ay.beklenen.json` | Tek kurulum sonrası normal yollarla işletilen ilk ayın girdisi ve beklenen sonucu |
| `simulasyon/ilk_ay_t9.*` | T9 olaylarıyla genişletilmiş ilk ay; 124 ek olay, 844 adım (843 ana akış + 1 yardımcı) |
| `uyum_v8.py` | Eski girdilerin somut nesne özetleri için sınırlı geçiş köprüsü |
| `yurut.py` | Bağımsız oynatıcı ve çıktı dönüştürücüsü |
| `karsilastir.py` | Alan yolu gösteren karşılaştırıcı |
| `kanonik_ornekler.json` | PostgreSQL ve Dart için metin/SHA-256 deneme vektörleri |
| `manifest.json` | Bu paket dosyalarının SHA-256 listesi |

## Girdi sözleşmesi ve geliş sırası

Tarihsel girdiler `bicim_surumu: 1` veya `2`, sürüm 10 girdileri `bicim_surumu: 3` taşır. İlk ay T9 biçim 3 yanında `surum_uyumu: v8` taşır; eski adımların somut özetleri korunur. `depolar` birbirinden bağımsız yürütmelerdir; her depo boş başlar. Bazı senaryolar aynı akışın iki farklı anını veya iki geliş sırasını ayrı depolarla sınar. Ortak kişiler, takvim, projeler ve işler de `olay` adımlarıdır; dışarıdan gizli başlangıç verisi yüklenmez.

Her depo şu alanları taşır:

- `baslangic`, `son_saat`: `simdi`, `gercek`, `demo`. İş saati ile gerçek teslim saati ayrı verilmiştir.
- `yontem`: başvuru modeli için kapsamlı/tam hesap tercihi. Ürünün aynı iç mimariyi kullanması gerekmez.
- `adimlar`: **Geliş sırası bu dizinin sırasıdır. Olay zamanına göre yeniden sıralamayın.** Sıralamayı motor kendi içinde yapar.
- Her adımda `saat`, o çağrıdan hemen önceki saattir. Bu alanı ayarlamak kendi başına yeniden hesap çağrısı sayılmaz. `ilerlet` adımı zaman sınırlarını ayrıca hesaplatır.

`tur: olay` adımında `args[0]` olay JSON'udur; `kwargs` içinde `oturum`, `servis`, `hassas_ek` bulunabilir. `AKTARIM` tarihsel ortak veriyi taşır. Canlı denemelerin `LISTE`/`ELLE` girişi ve taşınan **gerçek sürüm özetleri** korunmuştur. Yalnız yukarıdaki tarihsel özet köprüsü, mevcut nesnenin eski alan özeti tam eşleştiğinde dönüşüm yapar. Diğer özetler değiştirilmez: Y49'un bayat isteğinin reddedilmesi gerekir.

`kapanis`, `ilerlet`, `yeniden_kur`, `demo_sifirla`, `olay_koru`, `cihaz_esitle` adımları karşılık gelen işlemi çağırır. Sonuncusu cihazın son eşitleme zamanını iletişim metaverisi olarak kaydeder. `kontrol: true`, işlemden sonra iş sonucunun anlık görüntüsünü de ister. `sorgu` adımı `modul`, `ad`, `args`, `kwargs` ile belirtilen görünüm/kapı/yetki sorgusudur. Modül adları ürün için uygulama zorunluluğu değildir; adaptörünüz bunları kendi SQL/Dart fonksiyonlarına eşler.

JSON içinde `$an`, `$gun`, `$ondalik`, `$kume` etiketli tek alanlı nesneler, yalnız **test çağrısının argümanlarını** tipli taşır. Olay JSON'unun anları normal ISO 8601 metinleridir. `coz()` bu etiketleri açar.

`cihaz_denemeleri`, sayaç ve cihaz kapısı gibi yerel fonksiyonların bağımsız deneme vektörleridir. Her vektörün `veri`, `harf`, `saat` alanları çağrı öncesi durumdur; saat geri alınması/depo kaybı gibi test müdahaleleri böyle açıkça verilir. Sayaç eşitlemede `bulut_kimlikleri` okunacak kimlik kümesidir. Bu bölüm gerçek disk kalıcılığı veya süreçler arası kilidi kanıtlamaz.

`saf_sorgular` depodan bağımsız kapı ve benzeri saf fonksiyon vektörleridir. Ürünün düğme kapılarını bunlarla kontrol edin. Sayısal pano beklentileri `sorgu` adımlarının cevaplarında bulunur.

## Ürünün çıktı biçimi

Ürün adaptörünün üretmesi gereken JSON, ilgili `.beklenen.json` ile aynı biçimdedir:

```json
{
  "depolar": [{
    "cevaplar": [{"deger": {"sonuc": "BASARILI", "tekrar": false}}],
    "ara_haller": [{"adim": 12, "son_hal": {}}],
    "son_hal": {}
  }],
  "cihaz_denemeleri": [],
  "saf_sorgular": []
}
```

Örnek yalnız zarfı gösterir; boş `son_hal` gerçek sonuç için geçerli değildir. Her adım için bir cevap gerekir. Reddedilen ekleme normal bir cevap nesnesidir (`REDDEDILDI`, `kod`, `neden`); istisna atan test API'leri `hata_turu` ve `neden` taşır. Kapanış cevabı `{"deger":"KAPANDI"}` olarak kısaltılmıştır; kapanış verisi son halde karşılaştırılır. Ürün kendi hata mesajlarını farklı yazıyorsa adaptörde bu sözleşmenin neden/kod değerlerine eşleyin; karşılaştırıcı nedeni kendiliğinden yok saymaz.

`son_hal` nesnesinde `kod_listesi`, `yetki_kurallari`, `isler`, `gorevler`, `kisiler`, `birimler`, `projeler`, `tezgahlar`, `etaplar`, `notlar`, `listeler`, `kisi_durumu`, `araliklar`, `bildirimler`, `supheliler`, `sonuclar`, `bekletmeler`, `dosyalar`, `kisi_gecmisi`, `ay_kapanislari`, `olay_kimlikleri`, `isleme_hatalari` bulunur. Nesne tabloları kimlikle anahtarlanmış sözlüklerdir; aralık/geçmiş tabloları dizidir. Atölye kova ve aktif iş alanları dahil bütün mevcut iş alanları karşılaştırılır.

SQL tablonuz birebir bu iç temsil olmak zorunda değildir. Örneğin `kisi_durumu.acik_is`/`aktif_is` eşlemesini adaptör kurar. Uyarlama yaparken iş anlamını değiştirmeyin. Sadece pano ekran görüntüsünü kıyaslamak, doğru toplamın altında yanlış kişi veya iş dağılımını gizler.

## Kanonikleştirme ve B36

İki farklı amaç vardır:

1. **Nesne sürümü:** `model/irp/surum.py` içindeki `is_alanlari` ile temizlenmiş alanların `olay.kodla` çıktısının UTF-8 SHA-256'sı. Anahtarlar sıralı, ayraçlar `,` ve `:`, ek boşluk yok, Türkçe karakterler kaçırılmadan UTF-8, `null` ve boole değerleri JSON biçiminde. Dizi sırası korunur. Sürümde yuvarlama/tolerans uygulanmaz. `kanonik_ornekler.json` tam metin ve beklenen özeti gösterir. Modelin an temsili `+03:00`'dır; ürün UTC saklayabilir, hash adaptöründe aynı metni üretmelidir. `kabul_ani` gibi iş anlarını özete katın. Kimliği `LISTE` olan hedefin özeti doğrudan sıralı iş kimliği dizisindendir.
2. **Sonuç karşılaştırması:** aynı beş alanı dışarıda bırakır, eşdeğer saat dilimli anları `+03:00`'a çevirir. Sayısal saatlerde mutlak tolerans `0.000001` saat, para alanlarında iki ondalıklı metin ve tam eşitlik vardır. Para değerleri `"1111.11"` gibi verilmelidir. `null`, eksik alan ve boş dizi aynı sayılmaz; boole ile 0/1 aynı sayılmaz.

Her iki işlemde de dışarıda bırakılan B36 alanları: `surum`, `son_hesap_ani`, `son_olay`, `olusma_ani`, `kural_versiyonu`. İç içe nesneler de aynı kurala uyar. Alan adlarının keyfi kullanıcı JSON anahtarları olarak kullanılması bu sözleşmede öngörülmez.

Karşılaştırıcı `araliklar`, `hassas_ekler`, `kisi_gecmisi`, `olay_kimlikleri` satırlarını sırasız küme gibi kanonik sıralar; tekrar satırlar korunur. **Listelerin iş sırası ve olay/cevap sırası korunur.** İlk 100 fark varsayılan olarak okunur alan yollarıyla gösterilir (`--sinir` ile değişir).

Çekirdeğin geçersizleşmiş bildirimlerinin gösterim geçmişi son halden çıkarılır; geçerli bildirimler, alıcıları ve iş anları karşılaştırılır. `isleme_hatalari` içindeki kayıt zamanı dışarıda, hata/çözüldü içeriği içeridedir. Gerçek ağ gecikmeleri, CPU süreleri, DB fiziksel satır kimlikleri, Auth şifreleri, dosya baytları, push bildiriminin teslimi ve gerçek cihaz diski bu cevap anahtarının kapsamına girmez. Olay kimlikleri, gönderim tekrarı/çakışması, kanıt dosya kimliği ve parmak izi kapsam içindedir.

## Karar 50 ve açık model yorumları

Kapanış tutarına ek olarak görev bazındaki günlük payları da kaynakta saklıyoruz: `ay_kapanislari["2026-10-01:GOREV_PAYLARI"][gorev]` altında `maas` ve `yuk` dizileri; satırda `gun`, `kisi`, `saat`. Bu, T4 A14'ün istediği sabit görev payını yeniden kurmak için gereken ayrıntıdır. T2'deki proje toplamı tek başına bu bilgiyi geri üretmez. Para ve maliyet kapanışları önceki kaynak biçimini korur.

Y45b'de Ekim 10 saat sabit kalır; Kasım 20 saat üç iş gününe bölünür. Tatil/takvim açık ayın geçmiş günlerini değiştirebilir. İptal gününden sonrası yazılmaz. Onay görevi maaşta karar gününe, yükte doğduğu güne düşer. Normal görev henüz kabul edilmediyse yük atamadan planlanır; kabulden sonra B30'un özel hükmüyle ilk kabul günü kullanılır. Yeniden atanan kişinin kabulü bu başlangıcı değiştirmez. Karar 52 bu başlangıcı ve kapanıştaki görev/gün/kişi payını belgeye bağladı.

Kapanış, zamanın kendisinden çıkarılan gizli bir yan etki değildir: girdideki `kapanis` adımı açıkça çağrılmalıdır. Ürün zamanlanmış işi veya demo oynatıcısı aynı sınırda çağırır. Kaynaklardan kurtarmada olaylarla birlikte hassas ekleri, kapanışın günlük pay kaynağını ve ayrı kalıcı modül bildirimi tablosunu da taşıyın.

## Nasıl kullanılmalı

Önce olay kabul kodlarını, sonra kişi-gün aralıkları/listeleri/görevleri, ardından payları ve panoları karşılaştırın. Hata ayıklarken ilk farklı adımda durun. Son hal eşitliği tek başına bayat kabulü veya bir ara durum hatasını kanıtlamaz; bu yüzden cevaplar ve ara durumlar pakettedir.

Beklenen JSON'lar, elle hesaplanmış beklentileri geçen senaryo testlerinin gerçek yürütmelerinden kaydedildi. Daha sonra bağımsız oynatıcıyla yeniden üretildi ve karşılaştırıldı. Bu, geniş kapsamlı regresyon anahtarıdır; her JSON alanının ayrı bir insan tarafından elle hesaplandığı anlamına gelmez. Eşzamanlı SQL işlemleri, RLS, ağ kopması ve kalıcı cihaz sayacı için üründe ayrıca entegrasyon testleri gerekir.

## Tarihsel not: sürüm 6'dan 7'ye geçiş

- Yeni olaylar ve tablolar: gün tanımları, ek mesai planı/damgası, izin, makine takvimi/bakımı/duruşu, toplu duruş, gün sonu raporu, plan sürümü, doğrulanan sorumluluk ve ortak nesneler. Olayların tamamı `olay_semasi.json` içindedir. `NESNE` hedef türü ve `IZIN`/`DURUS` kod listeleri eklendi.
- Kişisel süre/performans üst zincirine açıldı; maaş, saat maliyeti ve prim tutarı yalnız YETKILI'ye görünür. Dış modüller `oku` ve `modul_yaz` kapılarını kullanır.
- Saat maliyeti maaş ve gider toplamı / 180'dir. Eski saat ücreti ve ayarlanabilir maaş paydası hesapta kullanılmaz. Eksik maaş `VERI_EKSIK` üretir. Beyaz yaka payları günün ücretinden hesaplanır; 180 saati aşınca maaş üstü dağıtım görülebilir.
- Kapanışa `DEFTER_V7`, `RAPORLAR`, `DUZELTMELER`, `CIHAZ_UYARILARI` eklendi. Geç olaylar eski tutarı değiştirmeden ilk açık döneme fark yazar. B0/B1 onay anındaki bilgiyi korur.
- Eski `sebep_olan` doğrulanmamış %100 öneridir; doğrulama gelene kadar kalite/gecikme puanı oluşmaz ve revizyon puanı kesilmez. Bu, Y28'in günlük ücret etkisi ve Y66'nın sabit paydasıyla birlikte eski izinli gerileme listesinde yer almayan farklardır; v6 beklenenleri değiştirilmeden raporlandı.
- Y77'de kaynak tarih aynı hafta kuralına aykırıdır. Paketin başarılı çalışması bu tasarım çelişkisini ortadan kaldırmaz. Seçilen ayrıntılar `YORUMLAR.md` içinde kayıtlıdır.
- 147 senaryo çifti ve üç simülasyon çifti vardır. İlk ay ve büyük akış T8 olaylarını normal kabul yolundan işler; somut sürüm hash'leri ve bayat istekler aynen saklanır.

Tam paket denetimi:

```powershell
py -I -B yurut.py --tum --simulasyon --tam-kontrol --degismez-kontrol
```

## Tarihsel not: sürüm 5'ten 6'ya geçiş

- Karar 57–61 uygulandı; beş eylem eklendi: `IS.BAGLANTI_DUZELTTIM`, `YETKI.TANIMLADIM`, `KOD.TANIMLADIM`, `TATIL.KALDIRDIM`, `KURULUM.TAMAMLADIM`. Rol kodları ve yetki satırları olay verisidir. Sabit ilişkiler, bütün birim zinciri, kendi onayını engelleme ve son yetkili güvencesi birlikte uygulanır.
- Bağlantı düzeltmesi açık ayı yeni projeye taşır; kapanmış ayın tutarı ve günlük kaynağı korunur. İptal edilen işler/görevler aktif proje emeğinden ayrılır, kişinin kaydı korunur. Bitmiş atölye işi iptal edilebilir; kısmi alt iş iptali ana durumu kalan alt işlere göre belirler.
- İstihdam dönemleri, yeniden giriş, orantılı maaş/payda, R28/R29, ileri rol değişikliği ve gelecekteki ayrılışı düzeltme/iptal eklendi. Hiyerarşi yalnız birim ağacından gelir. Üstün onayladığı/reddettiği görevin asıl onay görevi sıfır payla iptal olur.
- Y62’de 12:02 birim başı değişikliği; Y64’te açık rol listesi/yetki tablosu ve son kurulum olayı vardır. 21 yeni alt senaryoyla 126 dosya çifti, S1–S18/D1–D4/Y1–Y73’ün 95 ana senaryosunu kapsar.
- İlk ayda tek atomik kurulumdan sonra yalnız normal olaylar kullanılır. Büyük akışın tohumu 42’dir. `simulasyon/farkli_firma.*`, Sibernetik rollerine dayanmayan USTA/DAGITICI ve altı satırlık tabloyla çalışır. `--simulasyon` üç girdiyi de çalıştırır.
- `tur: kurulum`, `args: [olaylar, kod_listeleri]`, `kwargs: {"servis": true}` biçimindedir. Gerçek kaynak, paket içindeki KOD/YETKI olayları ve son `KURULUM.TAMAMLADIM` olayıdır. İkinci argüman önceki biçimle uyumlu bilgi alanıdır; yeni yetki kaynağı değildir. Canlı kurulum sonrası aktarım kapalıdır; demo istisnası korunur.
- `kod_listesi` ve `yetki_kurallari` son halde görünür. Kişide `istihdam_donemleri`; iş/aralıklarda iptal ve bağlantı alanları; görevde takvimden türeyen teslim saati bulunur. Maaşın iptal kalemleri `iptal:proje` anahtarı taşır. `iptal_edilenler` ayrı emek/maliyet görünümüdür.
- Kapanışa `:IPTAL_MALIYET` ve `:MALIYET_IZLERI` eklenir. İkincisi iş/görev, proje ve gün bazında donmuş kaynak taşır. Kapanıştan sonra iptal veya bağlantı düzeltmesi, geçmiş muhasebe tutarını değiştirmez. İptal görünümü bugünkü duruma göre o donmuş kaynağı gösterir; tarihi aktif kapanış tutarıyla toplanacak ikinci bir gider değildir.

Tek simülasyon:

```powershell
py -B yurut.py simulasyon/farkli_firma.girdi.json --dogrula --tam-kontrol
py -B yurut.py simulasyon/ilk_ay.girdi.json --dogrula --tam-kontrol
```

Eski beklenen dosyalar değiştirilmeden karşılaştırıldı. Ayrıntılı gerileme dökümü ve tasarım yorumları ana çalışmadadır; paketin çalışması bu dosyalara bağlı değildir. Seçilen yorumlar paketteki `YORUMLAR.md` dosyasındadır. Python 3.8 gramer ve API taraması, gerçek Python 3.8 çalıştırmasının yerine geçmez.
