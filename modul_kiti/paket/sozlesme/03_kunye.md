# 03 · Künye: modülün kimlik kartı

**Ne:** `kunye.json` modülün klasörünün kökünde durur. Modülün çekirdekte kullandığı her şey burada beyan edilir.
- **Bağlantı katmanı:** Künyede olmayanı yapmaz.
- **Kurulum:** Çekirdeği künyeye göre hazırlar: modülün kaydı, rolleri, türleri, yetki önerileri.
- **Bize ne söyler:** Modülü açmadan çekirdekle neyi konuştuğunu görürüz.

**Başlangıç:**
- şablon: `sablonlar/kunye.json`
- örnekler: `ornekler/kunyeler/` (M3 satın alma, KAL kalite, BAK bakım, IK insan kaynakları, VEGA muhasebe köprüsü, YZ tahmin) ve `ornekler/M3_mini/`
- alanların biçimi: `arac/kunye_semasi.json` (editör yardımı)

## Alanlar

| Alan | Ne yazılır |
|---|---|
| `kunye_surumu` | `1` |
| `kod` | Modülün değişmez kodu: 2–6 büyük harf ya da rakam, harfle başlar (`M3`, `KAL`). **Biz veririz** |
| `ad`, `aciklama`, `sahip` | Modülün adı, ne yaptığı, kim yazıyor |
| `surum` | Modülün sürümü, `0.1.0` biçiminde; her teslimde artar |
| `cekirdek` | Gereken en eski çekirdek: `>=10.2` |
| `servis_kimligi` | `SRV-<kod>` |
| `arka_yuz` | Modülün kendi sunucusu var mı: bildirim, servis okuması, zamanlanmış kural için gerekir |
| `olay_yolu` | Olayı kim gönderir. `ARKA_YUZ`: modülün sunucusu, bu paketin katmanıyla. `ISTEMCI`: modülün ekranı, çekirdeğin istemci paketiyle (`07_on_yuz.md`). `YOK`: modül olay yazmaz |
| `cihaz_harfi` | Yalnızca `ARKA_YUZ`'da: olay kimliğinin son harfi. **Biz veririz** |
| `kapilar.okumalar` | Kullanıcının gözüyle okunanlar (`kaynak/02_modul_sozlesmesi.md` › 2) |
| `kapilar.servis_okumalari` | Servis gözüyle okunanlar. Kişisel veri ve para yok |
| `kapilar.olaylar` | Kullanıcı adına gönderilen eylemler |
| `kapilar.plan`, `kapilar.belge_surumu` | Plan tarihi yazıyor mu (`PLAN.TARIHLEDIM`), belge sürümü kullanıyor mu |
| `kapilar.dosyalar` | Ortak özel fiziksel dosya kapısını kullanıyor mu; normal kullanıcı + nesne izni, en fazla 1 MB (`08_dosya_ve_kalici_istek.md`) |
| `kapilar.bildirimler` | Modülün bildirim kuralları: `kural`, `ad`, `onem`, `kayit_turleri`, `alici_turleri`, gerekirse `roller` |
| `kapilar.abonelikler` | Arka yüzün dinlediği değişiklik kanalları: `proje:*`, `firma` |
| `nesne_turleri` | Modülün sahip olduğu nesne türleri: aşamalar, başlangıç, geçişler (kim geçirir), bağlanabilir türler, kim açar |
| `tur_uzantilari` | Hangi türe hangi tabloyla uzanıyor: `{"tur": "PARCA", "tablo": "mod_m3.siparisler"}` |
| `roller` | Modülün yeni rolleri: `{"kod": "KALITECI", "ad": "Kaliteci"}` |
| `kod_listeleri` | Çekirdeğin listelerine eklenecek kodlar (`YETKINLIK`, `ARIZA`, …) |
| `yetki_onerileri` | Çekirdeğin bir eylemine önerilen yetki: `{"eylem_kodu", "kimler", "kapsam"}`. Yetkili kurulumda onaylar |
| `veritabani` | `{"sema": "mod_<kod>", "gocler": "veritabani/"}` |
| `on_yuz` | Ekranların yeri (`UYGULAMA_ICI`, `AYRI_UYGULAMA`, `YOK`) ve çekirdeğin ekranlarındaki **derin bağlantılar** (`07_on_yuz.md`) |
| `saglananlar`, `bagimliliklar` | Modüller arası okuma (`02_kurallar.md` › 7) |
| `kisisel_veri` | `[{"alan", "neden"}]`, KVKK beyanı |
| `para` | Modül para okuyor ya da tutuyor mu |
| `sinirlar` | Dakikadaki üst sınırlar: `bildirim_dakika`, `okuma_dakika`, `servis_okuma_dakika` |
| `istekler` | Çekirdeğe açılan istekler ve durumları (`06_teslim.md` › 3) |

## Denetim

```
python3 irp_sozlesme/arac/kunye_denetle.py .                       # modülün klasöründen
python3 irp_sozlesme/arac/kunye_denetle.py . irp_sozlesme/ornekler/kunyeler/*   # örneklerle birlikte
python3 irp_sozlesme/arac/kunye_denetle.py --kurulum kunye.json     # kurulumda yazılacak olaylar
```

- **Denetlenenler:**
  - künye (V01–V24)
  - modüller birlikte (R01–R11): aynı kod, aynı harf, aynı tür ya da rolün iki sahibi, döngülü bağımlılık
  - `veritabani/*.sql` göçleri (G01–G09, `04_veritabani.md`)
- **Sonuç:** Hata varsa çıkış kodu 1 olur. Uyarılar okunur ama durdurmaz. Örnek: MVP'de henüz olmayan bir okuma.

## Kurulumda ne olur

1. Yetkili, künyeden üretilen olayları yazar:
   - modülün kaydı (`MODUL.TANIMLADIM`)
   - roller ve kodlar (`KOD.TANIMLADIM`)
   - türler (`NESNE_TURU.TANIMLADIM`)
   - yetki önerileri (`YETKI.TANIMLADIM`)
2. Modülün şeması ve rolleri açılır, göçleri koşar.
3. Yetkili rolleri kişilere verir.

Simülatör de modülü böyle kurar. Simülatörde çalışan künye, ürünün kurulumunda da çalışır.
