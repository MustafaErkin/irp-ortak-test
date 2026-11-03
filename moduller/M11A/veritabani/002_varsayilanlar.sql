-- Varsayılan ayarlar. YETKILI ayarlar ekranından değiştirir.
INSERT INTO mod_m11a.ayarlar (anahtar, deger) VALUES
  ('proje_kodu_deseni',        '"{YY}{AA}{SIRA3}"'),
  ('proje_kodu_sira_kapsami',  '"YIL"'),
  ('siparis_adi_deseni',       '"{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}"'),
  ('sapma_esigi_puan',         '15'),
  ('yaklasan_tarih_gun',       '30');
