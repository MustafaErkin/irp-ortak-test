-- Varsayılan şablonlar. Birim eşlemesi firmaya göredir; YETKILI ayarlar ekranından yapar.
INSERT INTO mod_m11b.etap_sablonu (kod, ad, sira, paralel_grup, tasarim_kapisi, bas_orani, bit_orani) VALUES
  ('ACILIS',       'Proje açılışı ve planlama',                       1, NULL,      false, 0.000, 0.040),
  ('MEK_TASARIM',  'Mekanik tasarım (3D/2D)',                         2, 'TASARIM', true,  0.020, 0.220),
  ('OTO_TASARIM',  'Otomasyon tasarımı (elektrik, PLC/HMI mimarisi)', 3, 'TASARIM', true,  0.040, 0.300),
  ('SATIN_ALMA',   'Satın alma ve malzeme temini',                    4, 'TEDARIK', false, 0.150, 0.450),
  ('IMALAT',       'İmalat',                                          5, 'TEDARIK', false, 0.250, 0.550),
  ('MEK_MONTAJ',   'Mekanik, hidrolik ve pnömatik montaj',            6, 'MONTAJ',  false, 0.500, 0.700),
  ('ELK_YAZILIM',  'Elektrik montajı ve yazılım',                     7, 'MONTAJ',  false, 0.550, 0.750),
  ('TEST_FAT',     'Testler, ön deneme ve ön kabul (FAT)',            8, NULL,      false, 0.720, 0.850),
  ('SEVK_KURULUM', 'Sevkiyat, saha kurulumu ve devreye alma',         9, NULL,      false, 0.850, 0.950),
  ('KESIN_KABUL',  'Kesin kabul',                                     10, NULL,     false, 0.950, 1.000);

INSERT INTO mod_m11b.klasor_sablonu (kod, ad, aciklama, sira) VALUES
  ('3D_JPEG',              '3D JPEG',               'Genel montaj, alt grup ve parça görselleri', 1),
  ('3D_TASARIM',           '3D TASARIM',            '3D modeller, teknik çizimler ve tasarım sürümleri', 2),
  ('ALINAN_BELGELER',      'ALINAN BELGELER',       'Müşteriden alınan çizimler ve teknik belgeler', 3),
  ('CD',                   'CD',                    'Müşteriye teslim edilen nihai teknik dokümanlar', 4),
  ('ETUD_ONAY',            'ETUD ONAY DOSYALARI',   'Müşteri onayları ve yazışmalar', 5),
  ('PROJE_GOZDEN_GECIRME', 'PROJE GÖZDEN GEÇİRME',  'Tasarım gözden geçirme (TGG) kayıtları', 6),
  ('RESIMLER_VIDEOLAR',    'RESİMLER – VİDEOLAR',   'Saha görüntüleri, videolar ve referans materyaller', 7),
  ('TEKNIK_DOKUMANLAR',    'TEKNİK DOKÜMANLAR',     'Mühendislik hesaplamaları ve teknik veri sayfaları', 8),
  ('TEKNIK_SARTNAMELER',   'TEKNİK ŞARTNAMELER',    'Müşteri şartnameleri ve uygulanacak standartlar', 9),
  ('TOPLANTI_PLANLAMA',    'TOPLANTI PLANLAMA',     'Gantt planları, toplantı kararları ve tutanaklar', 10);

INSERT INTO mod_m11b.not_kategorileri (kod, ad, acilis_listesinde, sira) VALUES
  ('TASARIM',    'Tasarım (mekanik ve otomasyon)', false, 1),
  ('SATIN_ALMA', 'Planlama ve satın alma',         true,  2),
  ('IMALAT',     'İmalat',                         true,  3),
  ('MONTAJ',     'Mekatronik montaj',              true,  4),
  ('KABUL',      'Test, devreye alma, ön ve kesin kabul', true, 5);
