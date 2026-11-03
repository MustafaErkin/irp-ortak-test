# Örnek firma (simülatörün zemini)

*Üretildi: `modul_kiti/paket_uret.py` · çekirdek 10.2 · Sentetik veri. Simülatör bu firmayla açılır; sonra modülün künyesinden kurulum olayları yetkili K001 adına yazılır.*

- **Saat:** Zemin 2026-10-26T07:47:00+03:00 anında biter. Kurulum bir dakika sonra başlar.
- **Proje görünürlüğü:** `UYELER`. "UYELER": bir kişi yalnızca ekibinde olduğu projeyi görür (T9 › 6).
- **Şifre:** Simülatörde ve yerel sahte bulutta şifre denetlenmez.

## Kişiler

| Kod | Ad | Birim | Yaka | Roller |
|---|---|---|---|---|
| K001 | Genel Müdür | YONETIM | BEYAZ | YETKILI |
| K004 | Planlama Müdürü | PLANLAMA | BEYAZ | YONETICI |
| K006 | Planlama Uzmanı | PLANLAMA | BEYAZ | BEYAZ_YAKA |
| K009 | İmalat Ekip Lideri | IMALAT | MAVI | EKIP_LIDERI |
| K012 | Tasarım Müdürü | MEK_TASARIM | BEYAZ | YONETICI |
| K017 | Kaynakçı (V1) | IMALAT | MAVI | CALISAN |
| K023 | CNC Operatörü (V2) | IMALAT | MAVI | CALISAN |
| K041 | Tasarım Mühendisi | MEK_TASARIM | BEYAZ | BEYAZ_YAKA |
| K045 | Satın Alma Uzmanı | PLANLAMA | BEYAZ | BEYAZ_YAKA |

## Birimler

| Kod | Ad | Üst birim | Başı |
|---|---|---|---|
| IMALAT | İmalat | PLANLAMA | K009 |
| MEK_TASARIM | Mekanik Tasarım | YONETIM | K012 |
| PLANLAMA | Planlama ve Satın Alma | YONETIM | K004 |
| YONETIM | Genel Yönetim | — | K001 |

## Projeler

| Kimlik | Kod | Ad | Sorumlu |
|---|---|---|---|
| 2611 | 2611 | Arka plan projesi | K012 |
| 2614 | 2614 | Servo Döner Tablalı Robotik Kaynak Hücresi | K004 |

## Tezgâhlar

| Kod | Birim |
|---|---|
| ABK-01 | IMALAT |
| CNC-5X | IMALAT |
| CNC-F1 | IMALAT |
| CNC-F2 | IMALAT |
| CNC-F3 | IMALAT |
| CNC-T1 | IMALAT |
| CNC-T2 | IMALAT |
| KYN-01 | IMALAT |
| KYN-02 | IMALAT |
| KYN-03 | IMALAT |
| LZR-01 | IMALAT |
| MTK-01 | IMALAT |
| TSL-01 | IMALAT |
| TST-01 | IMALAT |

## Nesne türleri

- **PARCA** (Parça): SIPARIS_VERILMELI → SIPARISTE → GELDI → ISLEMDE → KALITE_ONAYLI → MONTAJA_HAZIR → MONTAJDA
- **BELGE** (Teknik resim): CALISILIYOR → TAMAM
