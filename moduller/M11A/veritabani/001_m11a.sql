-- M1.1A Sipariş alma ve muhasebeye devir · modülün tabloları (şema mod_m11a)
-- Çekirdeğin kimlikleri (proje, kişi, birim, olay) metin olarak, değer olarak tutulur; çekirdeğe yabancı anahtar yoktur (G08).
-- M1.0'ın kimlikleri (teklif sürümü, müşteri) de değer olarak tutulur; başka modülün şeması okunmaz (G02).

-- Olay kimliğinin sırası (04_veritabani.md › 3)
CREATE TABLE mod_m11a.olay_sayaci (
  kisi text NOT NULL,
  gun text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (kisi, gun)
);

CREATE FUNCTION mod_m11a.olay_sirasi(p_kisi text, p_gun text) RETURNS integer
LANGUAGE sql SET search_path = mod_m11a, pg_temp AS $$
  INSERT INTO mod_m11a.olay_sayaci AS s (kisi, gun, son) VALUES (p_kisi, p_gun, 1)
  ON CONFLICT (kisi, gun) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

-- Proje kodu ve yıllık sipariş sırası
CREATE TABLE mod_m11a.sayaclar (
  ad text NOT NULL,
  donem text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (ad, donem)
);

CREATE FUNCTION mod_m11a.sayac_ilerlet(p_ad text, p_donem text) RETURNS integer
LANGUAGE sql SET search_path = mod_m11a, pg_temp AS $$
  INSERT INTO mod_m11a.sayaclar AS s (ad, donem, son) VALUES (p_ad, p_donem, 1)
  ON CONFLICT (ad, donem) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

CREATE TABLE mod_m11a.ayarlar (
  anahtar text PRIMARY KEY,
  deger jsonb NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Teklifte işçiliği olmayan birim için yedek saat ücreti (karar 104: varsayım)
CREATE TABLE mod_m11a.saat_ucretleri (
  birim text PRIMARY KEY,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Dosyanın kaydı modülde, dosyanın kendisi şirket sunucusunda
CREATE TABLE mod_m11a.dosya_kayitlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL,
  tur text NOT NULL CHECK (tur IN ('PO', 'SOZLESME', 'TEMINAT', 'TUTAR_DEGISIKLIGI', 'FATURA', 'DIGER')),
  ad text NOT NULL,
  konum text NOT NULL CHECK (btrim(konum) <> ''),
  aciklama text,
  parmak_izi text CHECK (parmak_izi ~ '^[0-9a-f]{64}$'),
  ekleyen text NOT NULL,
  ekleme_ani timestamptz NOT NULL
);

-- Projenin M1.1A kaydı: teklifin donmuş kopyası, sipariş, ticari özet
CREATE TABLE mod_m11a.projeler (
  proje text PRIMARY KEY,
  durum text NOT NULL CHECK (durum IN ('ACILIYOR', 'ACIK')),
  teklif_surumu bigint NOT NULL UNIQUE,
  teklif_etiketi text NOT NULL,
  talep_no text NOT NULL,
  m10_musteri bigint,
  musteri_adi text NOT NULL,
  proje_adi text NOT NULL,
  kaynak text NOT NULL CHECK (kaynak IN ('YENI_IS', 'EK_IS', 'SERVIS')),
  ana_proje text,
  sorumlu text NOT NULL,
  satis_yoneticisi text NOT NULL,
  siparis_tarihi date NOT NULL,
  teslim_tarihi date NOT NULL,
  kesin_kabul_tarihi date,
  yil integer NOT NULL,
  yillik_sira integer NOT NULL,
  po_no text,
  po_dosyasi bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  sozlesme_dosyasi bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  vega_cari_kodu text,
  vega_proje_kodu text,
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  sozlesme_tutari numeric(14,2) NOT NULL CHECK (sozlesme_tutari >= 0),
  guncel_tutar numeric(14,2) NOT NULL CHECK (guncel_tutar >= 0),
  kurlar jsonb NOT NULL DEFAULT '[]'::jsonb,
  teslim_suresi_hafta integer,
  donmus_teklif jsonb NOT NULL,
  pdf bytea NOT NULL,
  pdf_ad text NOT NULL,
  pdf_parmak_izi text NOT NULL CHECK (pdf_parmak_izi ~ '^[0-9a-f]{64}$'),
  acan text NOT NULL,
  acilis_ani timestamptz NOT NULL,
  acilis_olayi text,
  butce_durumu text NOT NULL DEFAULT 'ACIK' CHECK (butce_durumu IN ('ACIK', 'KAPALI')),
  kapanis_kesin_kabul date,
  kapanis_ani timestamptz,
  kapatan text,
  surum integer NOT NULL DEFAULT 1,
  UNIQUE (yil, yillik_sira),
  CHECK (kaynak = 'YENI_IS' OR ana_proje IS NOT NULL),
  CHECK (butce_durumu = 'ACIK' OR (kapanis_ani IS NOT NULL AND kapanis_kesin_kabul IS NOT NULL AND kapatan IS NOT NULL))
);

ALTER TABLE mod_m11a.dosya_kayitlari
  ADD CONSTRAINT dosya_kayitlari_proje_fk FOREIGN KEY (proje) REFERENCES mod_m11a.projeler (proje);

-- Sözleşme tutarı, teklifin donmuş kopyası ve PDF değişmez
CREATE FUNCTION mod_m11a.donmus_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m11a, pg_temp AS $$
BEGIN
  IF NEW.sozlesme_tutari IS DISTINCT FROM OLD.sozlesme_tutari
     OR NEW.para_birimi IS DISTINCT FROM OLD.para_birimi
     OR NEW.teklif_surumu IS DISTINCT FROM OLD.teklif_surumu
     OR NEW.donmus_teklif IS DISTINCT FROM OLD.donmus_teklif
     OR NEW.kurlar IS DISTINCT FROM OLD.kurlar
     OR NEW.pdf_parmak_izi IS DISTINCT FROM OLD.pdf_parmak_izi THEN
    RAISE EXCEPTION 'Sözleşme tutarı ve teklifin donmuş kopyası değiştirilemez (proje %)', OLD.proje;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER projeler_donmus_degismez BEFORE UPDATE ON mod_m11a.projeler
  FOR EACH ROW EXECUTE FUNCTION mod_m11a.donmus_degismez();

-- Bütçe: dört kalem; başlangıç donmuş, güncel yalnızca tutar değişikliği formuyla
CREATE TABLE mod_m11a.butce_satirlari (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  baslangic numeric(14,2) NOT NULL CHECK (baslangic >= 0),
  guncel numeric(14,2) NOT NULL CHECK (guncel >= 0),
  PRIMARY KEY (proje, kalem)
);

CREATE FUNCTION mod_m11a.baslangic_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m11a, pg_temp AS $$
BEGIN
  IF NEW.baslangic IS DISTINCT FROM OLD.baslangic THEN
    RAISE EXCEPTION 'Başlangıç bütçesi değiştirilemez (proje %, kalem %)', OLD.proje, OLD.kalem;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER butce_satirlari_baslangic_degismez BEFORE UPDATE ON mod_m11a.butce_satirlari
  FOR EACH ROW EXECUTE FUNCTION mod_m11a.baslangic_degismez();

-- Tekliften donmuş birim saat ücretleri (tahmini gerçekleşen işçilik için)
CREATE TABLE mod_m11a.proje_saat_ucretleri (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  birim text NOT NULL,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  PRIMARY KEY (proje, birim)
);

-- Tekliften donmuş takvim, sipariş tarihine göre tarihlenmiş (M11A.BASLANGIC_PLANI)
CREATE TABLE mod_m11a.baslangic_plani (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  sira integer NOT NULL,
  etap_kodu text,
  ad text NOT NULL,
  paralel_grup text,
  baslangic_hafta integer NOT NULL CHECK (baslangic_hafta >= 0),
  sure_hafta integer NOT NULL CHECK (sure_hafta >= 1),
  baslangic date NOT NULL,
  bitis date NOT NULL,
  PRIMARY KEY (proje, sira),
  CHECK (baslangic <= bitis)
);

-- Ticari devir formu
CREATE TABLE mod_m11a.ticari_kosullar (
  proje text PRIMARY KEY REFERENCES mod_m11a.projeler (proje),
  faturalama_bicimi text CHECK (faturalama_bicimi IN ('PESIN', 'KADEMELI', 'SEVKTE', 'ON_KABULDE', 'KESIN_KABULDE', 'HAKEDIS')),
  faturalama_notu text,
  teslim_sekli text,
  ihracat boolean,
  tesvik text CHECK (tesvik IN ('VAR', 'YOK')),
  tesvik_belge_no text,
  teminat_gerekli text CHECK (teminat_gerekli IN ('VAR', 'YOK')),
  notlar text,
  guncelleyen text,
  guncelleme_ani timestamptz,
  surum integer NOT NULL DEFAULT 1
);

CREATE TABLE mod_m11a.odeme_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  sira integer NOT NULL,
  kosul text NOT NULL CHECK (kosul IN ('SIPARIS', 'SEVK', 'ON_KABUL', 'KESIN_KABUL', 'TARIH', 'DIGER')),
  tarih date,
  tutar numeric(14,2) NOT NULL CHECK (tutar >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  aciklama text,
  UNIQUE (proje, sira) DEFERRABLE INITIALLY DEFERRED,
  CHECK (kosul <> 'TARIH' OR tarih IS NOT NULL)
);

CREATE TABLE mod_m11a.teminatlar (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  tur text NOT NULL CHECK (tur IN ('AVANS', 'KESIN', 'DIGER')),
  tutar numeric(14,2) NOT NULL CHECK (tutar >= 0),
  para_birimi text NOT NULL CHECK (para_birimi ~ '^[A-Z]{3}$'),
  banka text,
  bitis_tarihi date,
  dosya bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  aciklama text
);

-- Muhasebeye devir ve eksik bilgi
CREATE TABLE mod_m11a.devirler (
  proje text PRIMARY KEY REFERENCES mod_m11a.projeler (proje),
  durum text NOT NULL DEFAULT 'DEVREDILDI' CHECK (durum IN ('DEVREDILDI', 'MUHASEBE_GORDU', 'EKSIK_VAR', 'TAMAM')),
  devreden text NOT NULL,
  devir_ani timestamptz NOT NULL,
  goren text,
  gorme_ani timestamptz,
  tamamlayan text,
  tamamlanma_ani timestamptz,
  bildirim_birakildi boolean NOT NULL DEFAULT false,
  son_alicilar jsonb NOT NULL DEFAULT '[]'::jsonb,
  son_suzulenler jsonb NOT NULL DEFAULT '[]'::jsonb,
  CHECK (durum = 'DEVREDILDI' OR gorme_ani IS NOT NULL),
  CHECK (durum <> 'TAMAM' OR tamamlanma_ani IS NOT NULL)
);

CREATE TABLE mod_m11a.eksik_bilgiler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  alan text,
  ne text NOT NULL CHECK (btrim(ne) <> ''),
  kimden text CHECK (kimden IN ('MUSTERI', 'SATIS', 'DIGER')),
  durum text NOT NULL DEFAULT 'EKSIK' CHECK (durum IN ('EKSIK', 'ISTENDI', 'ALINDI')),
  aciklama text,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz,
  CHECK (durum <> 'ISTENDI' OR kimden IS NOT NULL)
);

CREATE UNIQUE INDEX eksik_bilgiler_alan ON mod_m11a.eksik_bilgiler (proje, alan) WHERE alan IS NOT NULL;

-- Kapsam ya da fiyat değişikliği: güncel tutar ve güncel bütçe
CREATE TABLE mod_m11a.tutar_degisiklikleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  eski_tutar numeric(14,2) NOT NULL,
  yeni_tutar numeric(14,2) NOT NULL CHECK (yeni_tutar >= 0),
  butce_eski jsonb NOT NULL,
  butce_yeni jsonb NOT NULL,
  gerekce text NOT NULL CHECK (btrim(gerekce) <> ''),
  belge bigint NOT NULL REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL,
  bildirim_birakildi boolean NOT NULL DEFAULT false
);

-- Bütçe ölçümü: yalnızca yüzdeler (tutar tutulmaz)
CREATE TABLE mod_m11a.butce_olcumleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  an timestamptz NOT NULL,
  olcen text NOT NULL,
  dolum_yuzde numeric(6,1),
  ilerleme_yuzde numeric(6,1),
  sapma_puan numeric(6,1),
  kapsam text[] NOT NULL DEFAULT '{}',
  esik_puan numeric(5,1) NOT NULL,
  uyari boolean NOT NULL,
  bilinmeyen_saat numeric(10,1) NOT NULL DEFAULT 0
);

CREATE INDEX butce_olcumleri_proje ON mod_m11a.butce_olcumleri (proje, an DESC);

-- Çekirdekte açık duran bildirimlerimiz (kaldırmak için)
CREATE TABLE mod_m11a.acik_bildirimler (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kural text NOT NULL CHECK (kural IN ('TICARI_DEVIR', 'TUTAR_DEGISTI', 'BUTCE_SAPMASI')),
  modul_kaydi text NOT NULL,
  metin text NOT NULL,
  an timestamptz NOT NULL,
  PRIMARY KEY (proje, kural)
);

-- Kesin kabulde kapanış: kalem bazında fark (donmuş)
CREATE TABLE mod_m11a.kapanis_farklari (
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  butce numeric(14,2) NOT NULL,
  gerceklesen numeric(14,2),
  fark numeric(14,2),
  kaynak text NOT NULL,
  PRIMARY KEY (proje, kalem)
);

-- Kapanış sonrası düzeltme: kilitten sonra gelen fatura
CREATE TABLE mod_m11a.kapanis_sonrasi_duzeltmeler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje text NOT NULL REFERENCES mod_m11a.projeler (proje),
  kalem text NOT NULL CHECK (kalem IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  tutar numeric(14,2) NOT NULL,
  gerekce text NOT NULL CHECK (btrim(gerekce) <> ''),
  belge bigint REFERENCES mod_m11a.dosya_kayitlari (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL
);

CREATE INDEX dosya_kayitlari_proje ON mod_m11a.dosya_kayitlari (proje, tur);
CREATE INDEX odeme_satirlari_tarih ON mod_m11a.odeme_satirlari (tarih);
CREATE INDEX teminatlar_bitis ON mod_m11a.teminatlar (bitis_tarihi);
CREATE INDEX projeler_musteri ON mod_m11a.projeler (m10_musteri);
