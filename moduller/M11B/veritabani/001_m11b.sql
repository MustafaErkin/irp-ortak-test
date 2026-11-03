-- M1.1B'nin ilk göçü. Şemayı (mod_m11b) ve rolleri kurulum açar; bu dosya yalnızca içini doldurur.
-- Çekirdeğin kimlikleri (proje, etap, görev, not, kişi, birim) değer olarak tutulur; çekirdeğe yabancı anahtar yok (G08).

-- Olay kimliğinin sırası: kişi ve gün başına, tek işlemle artar (irp_sozlesme/sozlesme/04_veritabani.md › 3).
CREATE TABLE mod_m11b.olay_sayaci (
  kisi text NOT NULL,
  gun text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (kisi, gun)
);

CREATE FUNCTION mod_m11b.olay_sirasi(p_kisi text, p_gun text) RETURNS integer
LANGUAGE sql SET search_path = mod_m11b, pg_temp AS $$
  INSERT INTO mod_m11b.olay_sayaci AS s (kisi, gun, son) VALUES (p_kisi, p_gun, 1)
  ON CONFLICT (kisi, gun) DO UPDATE SET son = s.son + 1
  RETURNING son;
$$;

-- Şablonlar ve ayarlar (firmaya göre YETKILI ayarlar)
CREATE TABLE mod_m11b.etap_sablonu (
  kod text PRIMARY KEY,
  ad text NOT NULL,
  sira integer NOT NULL UNIQUE,
  paralel_grup text,
  varsayilan_birim text,
  tasarim_kapisi boolean NOT NULL DEFAULT false,
  bas_orani numeric(4,3) NOT NULL CHECK (bas_orani BETWEEN 0 AND 1),
  bit_orani numeric(4,3) NOT NULL CHECK (bit_orani BETWEEN 0 AND 1),
  aktif boolean NOT NULL DEFAULT true,
  CHECK (bas_orani <= bit_orani)
);

CREATE TABLE mod_m11b.klasor_sablonu (
  kod text PRIMARY KEY,
  ad text NOT NULL,
  aciklama text NOT NULL,
  sorumlu_birim text,
  sira integer NOT NULL UNIQUE
);

CREATE TABLE mod_m11b.not_kategorileri (
  kod text PRIMARY KEY,
  ad text NOT NULL,
  varsayilan_birim text,
  acilis_listesinde boolean NOT NULL,
  sira integer NOT NULL UNIQUE
);

-- Devir: projenin M1.1B'deki kaydı
CREATE TABLE mod_m11b.devirler (
  proje text PRIMARY KEY,
  baslatan text NOT NULL,
  baslama_ani timestamptz NOT NULL,
  sunum_ani timestamptz,
  sunumu_kaydeden text,
  tamamlanma_ani timestamptz
);

CREATE TABLE mod_m11b.etap_ekleri (
  etap text PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  sablon_kodu text REFERENCES mod_m11b.etap_sablonu (kod),
  sira integer NOT NULL,
  paralel_grup text,
  tasarim_kapisi boolean NOT NULL DEFAULT false
);

-- Klasör ve dosya kayıtları (dosyanın kendisi şirket sunucusunda)
CREATE TABLE mod_m11b.klasorler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  sablon_kodu text NOT NULL REFERENCES mod_m11b.klasor_sablonu (kod),
  ad text NOT NULL,
  sorumlu_birim text,
  UNIQUE (proje, sablon_kodu)
);

CREATE TABLE mod_m11b.dosya_kayitlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  klasor bigint NOT NULL REFERENCES mod_m11b.klasorler (kimlik),
  tur text NOT NULL CHECK (tur IN ('TASARIM_GIRDISI', 'RISK_ANALIZI', 'TGG', 'TUTANAK', 'PLAN_KANITI', 'DIGER')),
  ad text NOT NULL CHECK (length(btrim(ad)) > 0),
  konum text NOT NULL CHECK (length(btrim(konum)) > 0),
  parmak_izi text CHECK (parmak_izi ~ '^[0-9a-f]{64}$'),
  aciklama text,
  kaydeden text NOT NULL,
  kayit_ani timestamptz NOT NULL
);

-- Tasarım girdisi kapısı: gerekçeyle geçiş
CREATE TABLE mod_m11b.kapi_gecisleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  gecen text NOT NULL,
  an timestamptz NOT NULL,
  gerekce text NOT NULL CHECK (length(btrim(gerekce)) > 0)
);

-- Plan: başlangıç (B0) ve değişiklikler; satırlar toplu iş gibi tek tek gönderilir, sonuçları yazılır
CREATE TABLE mod_m11b.plan_degisiklikleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  tur text NOT NULL CHECK (tur IN ('BASLANGIC', 'DEGISIKLIK')),
  durum text NOT NULL CHECK (durum IN ('TASLAK', 'GONDERILIYOR', 'YARIM', 'ONAYLANDI')),
  hazirlayan text NOT NULL,
  hazirlama_ani timestamptz NOT NULL,
  neden text CHECK (neden IN ('MUSTERI_OTELEMESI', 'KARSILIKLI_ANLASMA')),
  gerekce text,
  plan_olayi text,
  surum_no integer CHECK (surum_no >= 0),
  onaylayan text,
  onay_ani timestamptz,
  bildirim_birakildi boolean NOT NULL DEFAULT false,
  CHECK (tur = 'BASLANGIC' OR durum = 'TASLAK' OR (neden IS NOT NULL AND length(btrim(coalesce(gerekce, ''))) > 0)),
  CHECK (durum <> 'ONAYLANDI' OR (plan_olayi IS NOT NULL AND onay_ani IS NOT NULL))
);
CREATE UNIQUE INDEX plan_degisiklikleri_acik ON mod_m11b.plan_degisiklikleri (proje)
  WHERE durum IN ('TASLAK', 'GONDERILIYOR', 'YARIM');
CREATE UNIQUE INDEX plan_degisiklikleri_surum ON mod_m11b.plan_degisiklikleri (proje, surum_no)
  WHERE surum_no IS NOT NULL;

CREATE TABLE mod_m11b.plan_satirlari (
  degisiklik bigint NOT NULL REFERENCES mod_m11b.plan_degisiklikleri (kimlik) ON DELETE CASCADE,
  sira integer NOT NULL,
  islem text NOT NULL CHECK (islem IN ('TANIMLA', 'DEGISTIR')),
  etap text,
  okunan_surum text,
  girdiler jsonb NOT NULL,
  etap_eki jsonb NOT NULL,
  olay_kimligi text,
  sonuc text CHECK (sonuc IN ('BASARILI', 'REDDEDILDI')),
  red_kodu text,
  red_nedeni text,
  PRIMARY KEY (degisiklik, sira),
  CHECK (islem = 'TANIMLA' OR (etap IS NOT NULL AND okunan_surum IS NOT NULL))
);

CREATE TABLE mod_m11b.plan_kanitlari (
  degisiklik bigint NOT NULL REFERENCES mod_m11b.plan_degisiklikleri (kimlik) ON DELETE CASCADE,
  dosya bigint NOT NULL REFERENCES mod_m11b.dosya_kayitlari (kimlik),
  PRIMARY KEY (degisiklik, dosya)
);

-- Bilgi notları: metin çekirdekteki NOT'ta; burada yalnızca modülün bağları
CREATE TABLE mod_m11b.bilgi_notlari (
  not_kimligi text PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  kategori text NOT NULL REFERENCES mod_m11b.not_kategorileri (kod),
  alici_birim text NOT NULL,
  etap text,
  bagli_gorev text,
  yazan text NOT NULL,
  yazma_ani timestamptz NOT NULL
);

CREATE TABLE mod_m11b.not_ekleri (
  not_kimligi text NOT NULL REFERENCES mod_m11b.bilgi_notlari (not_kimligi),
  dosya bigint NOT NULL REFERENCES mod_m11b.dosya_kayitlari (kimlik),
  PRIMARY KEY (not_kimligi, dosya)
);

-- Modülden atanan görevler (çekirdekteki görev kimliği)
CREATE TABLE mod_m11b.gorev_atamalari (
  gorev text PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11b.devirler (proje),
  etap text NOT NULL,
  atayan text NOT NULL,
  atama_ani timestamptz NOT NULL,
  kapi text NOT NULL CHECK (kapi IN ('KAPSAM_DISI', 'GIRDI_VAR', 'GECIS')),
  tgg_dosyasi bigint REFERENCES mod_m11b.dosya_kayitlari (kimlik)
);

CREATE INDEX dosya_kayitlari_proje ON mod_m11b.dosya_kayitlari (proje, tur);
CREATE INDEX bilgi_notlari_proje ON mod_m11b.bilgi_notlari (proje, kategori);
CREATE INDEX gorev_atamalari_proje ON mod_m11b.gorev_atamalari (proje, etap);
CREATE INDEX etap_ekleri_proje ON mod_m11b.etap_ekleri (proje);
