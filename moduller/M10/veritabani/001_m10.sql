-- M1.0 Teklif hazırlama · modülün tabloları (şema mod_m10)
-- Çekirdeğin kimlikleri (kişi, birim, proje) metin olarak, değer olarak tutulur; çekirdeğe yabancı anahtar yoktur (G08).
-- Şemayı kurulum açar; bu dosya yalnızca içini doldurur (G03).

-- Ayarlar ve sayaçlar
CREATE TABLE mod_m10.ayarlar (
  anahtar text PRIMARY KEY,
  deger jsonb NOT NULL,
  guncelleyen text,
  guncelleme_ani timestamptz
);

CREATE TABLE mod_m10.sayaclar (
  ad text NOT NULL,
  donem text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (ad, donem)
);

CREATE FUNCTION mod_m10.sayac_ilerlet(p_ad text, p_donem text) RETURNS integer
LANGUAGE sql SET search_path = mod_m10, pg_temp AS $$
  INSERT INTO mod_m10.sayaclar AS s (ad, donem, son) VALUES (p_ad, p_donem, 1)
  ON CONFLICT (ad, donem) DO UPDATE SET son = s.son + 1 RETURNING son; $$;

-- Kataloglar (ayarlar ekranı)
CREATE TABLE mod_m10.para_birimleri (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z]{3}$'),
  ad text NOT NULL,
  sembol text,
  aktif boolean NOT NULL DEFAULT true
);

CREATE TABLE mod_m10.maliyet_unsurlari (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z][A-Z0-9_]{1,39}$'),
  ad text NOT NULL,
  butce_kalemi text NOT NULL CHECK (butce_kalemi IN ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')),
  sik boolean NOT NULL DEFAULT false,
  aktif boolean NOT NULL DEFAULT true,
  sira integer NOT NULL DEFAULT 100,
  ekleyen text,
  ekleme_ani timestamptz
);

CREATE TABLE mod_m10.katalog_kalemleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kod text NOT NULL UNIQUE CHECK (btrim(kod) <> ''),
  ad text NOT NULL,
  unsur text NOT NULL REFERENCES mod_m10.maliyet_unsurlari (kod),
  olcu_birimi text NOT NULL DEFAULT 'adet',
  birim_fiyat numeric(14,2) CHECK (birim_fiyat >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  fiyat_tarihi date,
  fiyat_kaynagi text,
  tipik_temin_hafta integer CHECK (tipik_temin_hafta >= 0),
  kritik boolean NOT NULL DEFAULT false,
  aktif boolean NOT NULL DEFAULT true,
  CHECK ((birim_fiyat IS NULL) = (para_birimi IS NULL))
);

CREATE TABLE mod_m10.makine_turleri (
  kod text PRIMARY KEY CHECK (kod ~ '^[A-Z][A-Z0-9_]{1,39}$'),
  ad text NOT NULL,
  tipik_toplam_hafta integer CHECK (tipik_toplam_hafta > 0),
  aktif boolean NOT NULL DEFAULT true
);

-- Başlangıç tablosu: makine türü × birim → tipik saat ve süre (8a)
CREATE TABLE mod_m10.baslangic_tablosu (
  makine_turu text NOT NULL REFERENCES mod_m10.makine_turleri (kod),
  birim text NOT NULL,
  tipik_saat numeric(8,1) NOT NULL CHECK (tipik_saat >= 0),
  tipik_sure_hafta integer CHECK (tipik_sure_hafta >= 0),
  PRIMARY KEY (makine_turu, birim)
);

-- Teklif için standart saat ücreti (karar 104: varsayım, maaşın kopyası değil)
CREATE TABLE mod_m10.saat_ucretleri (
  birim text PRIMARY KEY,
  ucret numeric(14,2) NOT NULL CHECK (ucret >= 0),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  guncelleyen text,
  guncelleme_ani timestamptz
);

-- Takvim şablonu: M1.1B'nin etap şablonuyla aynı kodlar (ortak etap listesi)
CREATE TABLE mod_m10.takvim_sablonu (
  kod text PRIMARY KEY,
  ad text NOT NULL,
  sira integer NOT NULL UNIQUE,
  paralel_grup text,
  birim text,
  bas_orani numeric(4,3) NOT NULL CHECK (bas_orani BETWEEN 0 AND 1),
  bit_orani numeric(4,3) NOT NULL CHECK (bit_orani BETWEEN 0 AND 1),
  aktif boolean NOT NULL DEFAULT true,
  CHECK (bas_orani <= bit_orani)
);

-- Geçmiş proje formu (8b): kapanmış projelerin birim bazında gerçek saatleri, elle
CREATE TABLE mod_m10.gecmis_projeler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proje_kodu text NOT NULL UNIQUE,
  ad text NOT NULL,
  makine_turu text NOT NULL REFERENCES mod_m10.makine_turleri (kod),
  kapanis_tarihi date,
  aciklama text,
  giren text NOT NULL,
  giris_ani timestamptz NOT NULL
);

CREATE TABLE mod_m10.gecmis_proje_saatleri (
  gecmis_proje bigint NOT NULL REFERENCES mod_m10.gecmis_projeler (kimlik) ON DELETE CASCADE,
  birim text NOT NULL,
  gercek_saat numeric(8,1) NOT NULL CHECK (gercek_saat >= 0),
  PRIMARY KEY (gecmis_proje, birim)
);

-- Müşteri
CREATE TABLE mod_m10.musteriler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ad text NOT NULL CHECK (btrim(ad) <> ''),
  kisa_ad text,
  adres text,
  ulke text NOT NULL DEFAULT 'TR',
  vergi_dairesi text,
  vergi_no text,
  strateji_notu text,
  aktif boolean NOT NULL DEFAULT true,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  arama text NOT NULL DEFAULT ''
);

CREATE TABLE mod_m10.musteri_kisileri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  musteri bigint NOT NULL REFERENCES mod_m10.musteriler (kimlik),
  ad text NOT NULL,
  unvan text,
  telefon text,
  eposta text,
  aktif boolean NOT NULL DEFAULT true
);

-- Talep: tek kayıt, altında sürümler
CREATE TABLE mod_m10.talepler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep_no text NOT NULL UNIQUE,
  musteri bigint NOT NULL REFERENCES mod_m10.musteriler (kimlik),
  kaynak text NOT NULL CHECK (kaynak IN ('YENI_IS', 'EK_IS', 'SERVIS')),
  bagli_proje text,
  tur text NOT NULL CHECK (tur IN ('KURUMSAL_SARTNAME', 'SAHA_NOTU', 'ARGE')),
  makine_turu text REFERENCES mod_m10.makine_turleri (kod),
  konu text NOT NULL CHECK (btrim(konu) <> ''),
  aciklama text,
  gelis_tarihi date NOT NULL,
  cevap_tarihi date,
  durum text NOT NULL DEFAULT 'ACIK'
    CHECK (durum IN ('ACIK', 'TEKLIF_VERILDI', 'KAZANILDI', 'KAYBEDILDI', 'BEKLEMEDE', 'KAPATILDI')),
  kazanan_surum bigint,
  kayip_nedeni text CHECK (kayip_nedeni IN ('FIYAT', 'TEKNIK_COZUM', 'TESLIM_SURESI')),
  kayip_aciklamasi text,
  kapatma_gerekcesi text,
  sonuc_ani timestamptz,
  sonucu_yazan text,
  olusturan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  arama text NOT NULL DEFAULT '',
  surum integer NOT NULL DEFAULT 1,
  CHECK (kaynak = 'YENI_IS' OR bagli_proje IS NOT NULL),
  CHECK (durum <> 'KAYBEDILDI' OR kayip_nedeni IS NOT NULL),
  CHECK (durum <> 'KAPATILDI' OR coalesce(btrim(kapatma_gerekcesi), '') <> ''),
  CHECK (durum <> 'KAZANILDI' OR kazanan_surum IS NOT NULL)
);

-- Dosyanın kaydı modülde, dosyanın kendisi şirket sunucusunda (M1.1B ile aynı ilke)
CREATE TABLE mod_m10.talep_dosyalari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  tur text NOT NULL CHECK (tur IN ('SARTNAME', 'FOTOGRAF', 'VIDEO', 'SAHA_NOTU', 'TEDARIKCI_TEKLIFI', 'CIZIM', 'DIGER')),
  ad text NOT NULL,
  konum text NOT NULL CHECK (btrim(konum) <> ''),
  aciklama text,
  parmak_izi text CHECK (parmak_izi ~ '^[0-9a-f]{64}$'),
  ekleyen text NOT NULL,
  ekleme_ani timestamptz NOT NULL
);

CREATE TABLE mod_m10.gereksinimler (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  sira integer NOT NULL,
  metin text NOT NULL CHECK (btrim(metin) <> ''),
  belirsiz boolean NOT NULL DEFAULT false,
  soru text,
  cevap text,
  cevap_ani timestamptz,
  UNIQUE (talep, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mod_m10.kapsam_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  tur text NOT NULL CHECK (tur IN ('DAHIL', 'HARIC')),
  sira integer NOT NULL,
  metin text NOT NULL CHECK (btrim(metin) <> ''),
  UNIQUE (talep, tur, sira) DEFERRABLE INITIALLY DEFERRED
);

-- Teklif sürümü (V1, V2…)
CREATE TABLE mod_m10.teklif_surumleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  no integer NOT NULL CHECK (no >= 1),
  durum text NOT NULL DEFAULT 'TASLAK' CHECK (durum IN ('TASLAK', 'ONAY_BEKLIYOR', 'ONAYLANDI', 'GONDERILDI')),
  kaynak_surum bigint REFERENCES mod_m10.teklif_surumleri (kimlik),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  kar_orani numeric(7,2),
  fiyat numeric(14,2) CHECK (fiyat >= 0),
  fiyat_girisi text NOT NULL DEFAULT 'KAR' CHECK (fiyat_girisi IN ('KAR', 'FIYAT')),
  toplam_hafta integer CHECK (toplam_hafta > 0),
  teslim_suresi_hafta integer CHECK (teslim_suresi_hafta > 0),
  gecerlilik_gun integer CHECK (gecerlilik_gun > 0),
  teknik_cozum text,
  odeme_kosullari text,
  teslim_kosullari text,
  notlar text,
  hazirlayan text NOT NULL,
  olusturma_ani timestamptz NOT NULL,
  onaya_gonderen text,
  onaya_gonderim_ani timestamptz,
  onaylayan text,
  onay_ani timestamptz,
  gonderen text,
  gonderim_ani timestamptz,
  gonderim_sekli text CHECK (gonderim_sekli IN ('E_POSTA', 'ELDEN', 'PORTAL', 'DIGER')),
  gonderim_notu text,
  pdf bytea,
  pdf_parmak_izi text CHECK (pdf_parmak_izi ~ '^[0-9a-f]{64}$'),
  donmus_ozet jsonb,
  surum integer NOT NULL DEFAULT 1,
  UNIQUE (talep, no),
  CHECK (durum IN ('TASLAK', 'ONAY_BEKLIYOR')
         OR (onaylayan IS NOT NULL AND onay_ani IS NOT NULL AND pdf IS NOT NULL AND donmus_ozet IS NOT NULL)),
  CHECK (durum <> 'GONDERILDI' OR (gonderim_ani IS NOT NULL AND gonderen IS NOT NULL))
);

-- Bir talepte aynı anda en çok bir gönderilmemiş sürüm olur
CREATE UNIQUE INDEX teklif_surumleri_tek_acik ON mod_m10.teklif_surumleri (talep) WHERE durum <> 'GONDERILDI';

ALTER TABLE mod_m10.talepler
  ADD CONSTRAINT talepler_kazanan_surum_fk FOREIGN KEY (kazanan_surum) REFERENCES mod_m10.teklif_surumleri (kimlik);

-- Gönderilmiş sürüm değişmez: yalnızca hiçbir alanı değişmeyen güncelleme geçer
CREATE FUNCTION mod_m10.gonderilen_degismez() RETURNS trigger
LANGUAGE plpgsql SET search_path = mod_m10, pg_temp AS $$
BEGIN
  IF OLD.durum = 'GONDERILDI' AND NEW IS DISTINCT FROM OLD THEN
    RAISE EXCEPTION 'Gönderilmiş teklif sürümü değiştirilemez (sürüm %)', OLD.kimlik;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER teklif_surumleri_gonderilen_degismez BEFORE UPDATE ON mod_m10.teklif_surumleri
  FOR EACH ROW EXECUTE FUNCTION mod_m10.gonderilen_degismez();

-- Döviz kurları: sürüm başına, 1 birim = kur_try TL
CREATE TABLE mod_m10.surum_kurlari (
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  para_birimi text NOT NULL REFERENCES mod_m10.para_birimleri (kod),
  kur_try numeric(14,6) NOT NULL CHECK (kur_try > 0),
  kur_tarihi date NOT NULL,
  PRIMARY KEY (surum, para_birimi),
  CHECK (para_birimi <> 'TRY')
);

CREATE TABLE mod_m10.maliyet_kalemleri (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  sira integer NOT NULL,
  unsur text NOT NULL REFERENCES mod_m10.maliyet_unsurlari (kod),
  katalog_kalemi bigint REFERENCES mod_m10.katalog_kalemleri (kimlik),
  aciklama text NOT NULL CHECK (btrim(aciklama) <> ''),
  adet numeric(12,3) NOT NULL CHECK (adet > 0),
  olcu_birimi text NOT NULL DEFAULT 'adet',
  birim_fiyat numeric(14,2) CHECK (birim_fiyat >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  kaynak_etiketi text NOT NULL DEFAULT 'TAHMIN' CHECK (kaynak_etiketi IN ('TEDARIKCI_TEKLIFI', 'GECMIS_PROJE', 'TAHMIN')),
  kaynak_notu text,
  kaynak_tarihi date,
  kaynak_dosyasi bigint REFERENCES mod_m10.talep_dosyalari (kimlik),
  temin_hafta integer CHECK (temin_hafta >= 0),
  kritik boolean NOT NULL DEFAULT false,
  CHECK ((birim_fiyat IS NULL) = (para_birimi IS NULL)),
  UNIQUE (surum, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE mod_m10.iscilik_satirlari (
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  birim text NOT NULL,
  saat numeric(8,1) NOT NULL CHECK (saat >= 0),
  saat_ucreti numeric(14,2) CHECK (saat_ucreti >= 0),
  para_birimi text REFERENCES mod_m10.para_birimleri (kod),
  aciklama text,
  PRIMARY KEY (surum, birim),
  CHECK ((saat_ucreti IS NULL) = (para_birimi IS NULL))
);

CREATE TABLE mod_m10.takvim_satirlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  etap_kodu text REFERENCES mod_m10.takvim_sablonu (kod),
  ad text NOT NULL CHECK (btrim(ad) <> ''),
  sira integer NOT NULL,
  paralel_grup text,
  baslangic_hafta integer NOT NULL CHECK (baslangic_hafta >= 0),
  sure_hafta integer NOT NULL CHECK (sure_hafta >= 1),
  UNIQUE (surum, sira) DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX takvim_satirlari_etap ON mod_m10.takvim_satirlari (surum, etap_kodu) WHERE etap_kodu IS NOT NULL;

-- Onay ve düzeltme kaydı ("bilgi havuzu") ve işlem geçmişi
CREATE TABLE mod_m10.onay_kayitlari (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  surum bigint NOT NULL REFERENCES mod_m10.teklif_surumleri (kimlik),
  karar text NOT NULL CHECK (karar IN ('ONAYA_GONDERILDI', 'ONAYLANDI', 'DUZELTME_ISTENDI', 'ONAYCI_DUZELTTI', 'DUZENLEMEYE_ACILDI')),
  gerekce text,
  kim text NOT NULL,
  an timestamptz NOT NULL,
  CHECK (karar NOT IN ('DUZELTME_ISTENDI', 'DUZENLEMEYE_ACILDI') OR coalesce(btrim(gerekce), '') <> '')
);

CREATE TABLE mod_m10.islem_gecmisi (
  kimlik bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  talep bigint NOT NULL REFERENCES mod_m10.talepler (kimlik),
  surum bigint REFERENCES mod_m10.teklif_surumleri (kimlik),
  kim text NOT NULL,
  an timestamptz NOT NULL,
  islem text NOT NULL,
  ayrinti jsonb NOT NULL DEFAULT '{}'::jsonb,
  onayci_duzeltmesi boolean NOT NULL DEFAULT false
);

CREATE INDEX islem_gecmisi_talep ON mod_m10.islem_gecmisi (talep, an);
CREATE INDEX talepler_durum ON mod_m10.talepler (durum, cevap_tarihi);
CREATE INDEX maliyet_kalemleri_surum ON mod_m10.maliyet_kalemleri (surum);
CREATE INDEX takvim_satirlari_surum ON mod_m10.takvim_satirlari (surum);
