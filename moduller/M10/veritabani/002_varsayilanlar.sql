-- Varsayılan veriler. Firma bunları ayarlar ekranından değiştirir.
INSERT INTO mod_m10.para_birimleri (kod, ad, sembol) VALUES
  ('TRY', 'Türk lirası', '₺'),
  ('EUR', 'Avro', '€'),
  ('USD', 'ABD doları', '$');

-- Maliyet unsurları: her biri tek bir bütçe kalemine bağlı (M1.1A ortak katalog eki)
INSERT INTO mod_m10.maliyet_unsurlari (kod, ad, butce_kalemi, sik, sira) VALUES
  ('ROBOT',            'Robot',                         'MALZEME',     true,  10),
  ('PLC',              'PLC ve HMI',                    'MALZEME',     true,  20),
  ('PNOMATIK',         'Pnömatik',                      'MALZEME',     true,  30),
  ('MEKANIK_MALZEME',  'Mekanik malzeme ve hammadde',   'MALZEME',     true,  40),
  ('ELEKTRIK_MALZEME', 'Elektrik malzemesi ve pano',    'MALZEME',     true,  50),
  ('ISIL_ISLEM',       'Isıl işlem',                    'FASON',       false, 60),
  ('FASON_IMALAT',     'Fason imalat',                  'FASON',       true,  70),
  ('NAKLIYE',          'Nakliye ve sevkiyat',           'FASON',       false, 80),
  ('GENEL_GIDER_PAYI', 'Genel gider payı',              'GENEL_GIDER', false, 90),
  ('DIGER',            'Diğer',                         'MALZEME',     false, 999);

-- M1.1B'nin etap şablonuyla aynı on kod, ad, sıra, paralel grup ve oran (ortak etap listesi)
INSERT INTO mod_m10.takvim_sablonu (kod, ad, sira, paralel_grup, bas_orani, bit_orani) VALUES
  ('ACILIS',       'Proje açılışı ve planlama',                       1, NULL,      0.000, 0.040),
  ('MEK_TASARIM',  'Mekanik tasarım (3D/2D)',                         2, 'TASARIM', 0.020, 0.220),
  ('OTO_TASARIM',  'Otomasyon tasarımı (elektrik, PLC/HMI mimarisi)', 3, 'TASARIM', 0.040, 0.300),
  ('SATIN_ALMA',   'Satın alma ve malzeme temini',                    4, 'TEDARIK', 0.150, 0.450),
  ('IMALAT',       'İmalat',                                          5, 'TEDARIK', 0.250, 0.550),
  ('MEK_MONTAJ',   'Mekanik, hidrolik ve pnömatik montaj',            6, 'MONTAJ',  0.500, 0.700),
  ('ELK_YAZILIM',  'Elektrik montajı ve yazılım',                     7, 'MONTAJ',  0.550, 0.750),
  ('TEST_FAT',     'Testler, ön deneme ve ön kabul (FAT)',            8, NULL,      0.720, 0.850),
  ('SEVK_KURULUM', 'Sevkiyat, saha kurulumu ve devreye alma',         9, NULL,      0.850, 0.950),
  ('KESIN_KABUL',  'Kesin kabul',                                     10, NULL,     0.950, 1.000);

INSERT INTO mod_m10.ayarlar (anahtar, deger) VALUES
  ('yonetim_birimleri',       '["YONETIM"]'),
  ('talep_no_deseni',         '"T-{YYYY}-{SIRA4}"'),
  ('varsayilan_para_birimi',  '"EUR"'),
  ('varsayilan_gecerlilik_gun', '30'),
  ('cevap_uyari_gun',         '3'),
  ('firma',                   '{"unvan": "Sibernetik", "adres": "Bursa", "telefon": "", "eposta": "", "web": ""}'),
  ('varsayilan_metinler',     '{"odeme_kosullari": "%40 sipariş ile, %50 sevkten önce, %10 kesin kabulde.", "teslim_kosullari": "Teslim yeri ve şekli sözleşmede belirlenir.", "notlar": ""}'),
  ('son_kurlar',              '{}');
