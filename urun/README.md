# Yerel PostgreSQL ürünü

İş kuralları `veritabani/` içindeki PL/pgSQL fonksiyonlarında çalışır. Python yalnız kurulum ve test istemcisidir. Kurulum kodu cevap anahtarını içe aktarmaz.

Windows'ta Python 3.11 ile:

```powershell
py -3.11 -m pip install "psycopg[binary]>=3.2,<4"
py -3.11 -B urun/yerel/yonet.py kur
py -3.11 -B urun/yerel/yonet.py baslat
$env:IRP_TEST_DB=[Environment]::GetEnvironmentVariable('IRP_TEST_DB','User')
py -3.11 -B urun/kur.py --sifirdan --test
py -3.11 -B test/oynatici/oynat.py --surucu urun --katman K0,A --karsilastirma tam
py -3.11 -m pytest test/testler -m yerel_db
py -3.11 -B urun/yerel/yonet.py durum
py -3.11 -B urun/yerel/yonet.py durdur
```

`--sifirdan` uygulamanın şemalarını ve sahibi `irp_sahibi` olan public nesnelerini siler. Yalnız adı `test` içeren veritabanı kabul edilir. `--test` verilmezse test kapıları kurulmaz. Yerel Supabase taklidi yalnız localhost bağlantısında uygulanır. Mevcut göçün özeti değişmişse kurulum durur; geliştirme sırasında yeniden kurulum gerekir.

Sunucu `%LOCALAPPDATA%\irp_pg` içinde, yalnız localhost:5433 üzerinde çalışır. Windows hizmeti kurulmaz. Saat iş kurallarında `saat.simdi()` üzerinden okunur; duvar saati yalnız çalışma süresi bütçesi içindir. Varsayılan veritabanı sıralaması ICU en-US'tur; motor anahtar sıralaması açıkça `COLLATE "C"` kullanır.

Bu sürüm geliştirme aşamasındadır. Gün onayı, plan onayı, gecikme ve sorumluluk, yetkinlik, değişiklik işi, manuel süre ve dolu firmanın ay kapanışı yerel motorda hesaplanır. Son doğrulama ve kalanlar `codex/sonuclar/tur21_SONUC.md` içinde tutulur. Okuma kapıları ayrı turun kapsamındadır.

Ay kapanışının parasal iç hesapları `065_kapanis_hesaplari.sql` ve `066_kapanis_izleri.sql` içindedir. `085_kapanis.sql` bütün hesaplar tamamlanınca kaynak kapanışını atomik yazar; yeniden kurma bu kaynağı korur. `074_fotograf.sql` onay anında bilinen olayları ve önceki dönem düzeltmelerini aynı SQL motorunun ayrı çalışma kopyasında yürütür.

Canlı hesap bütçesi, kapının kilit bekleme ve kabul denetimi süresi dahil, hazırlık, tarihsel fotoğraf ve yayın boyunca denetlenir. Bütçe aşımında kaynak korunur ve hesap arka plana devredilir. Arka plan parçası hazırlıktan sonra bütçelenir ve en az bir nokta ilerler. Aynı kaynak ve saatin hazırlığı ile aynı işlenmiş sınırın ham çalışma kopyası yeniden kullanılır; geri sarma ve baştan kurma gereken önbellekleri geçersiz kılar.

Supabase kurulumunda 001–099 motor göçleridir; 100–149 okuma katmanına ayrılmıştır. Üretimde `090_test.sql` ve `yerel/000_supabase_taklidi.sql` kurulmaz. Yönetim bağlantısı `motor.arka_plan_calistir()` ve `motor.saat_isi()` işlerini ayrı işlemlerde çağırmalıdır. Saat işi, takvim ve ileri geçerlilik noktalarının yanında gün sonu R32/R33 hatırlatmalarını da yayınlar. Ay kapanışı açık bir yönetim çağrısıdır; zamanlayıcı kendiliğinden ay kapatmaz.
