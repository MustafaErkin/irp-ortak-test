-- KAL modülünün ilk göçü. Şemayı (mod_kal) ve rolü kurulum açar; göç yalnızca içini doldurur (T18 › 7).

CREATE TABLE mod_kal.parca_kriterleri (
  nesne_kimligi text PRIMARY KEY,          -- çekirdekteki PARCA nesnesinin kimliği, değer olarak (yabancı anahtar yok)
  olcu_toleransi numeric,
  sertifika_gerekli boolean NOT NULL DEFAULT false
);

CREATE TABLE mod_kal.olcumler (
  kimlik bigserial PRIMARY KEY,
  kalite_kaydi text NOT NULL,              -- çekirdekteki KALITE_KAYDI nesnesinin kimliği
  parca text NOT NULL,                     -- çekirdekteki PARCA nesnesinin kimliği
  olcen text NOT NULL,                     -- kişi kodu
  deger numeric,
  an timestamptz NOT NULL DEFAULT now(),
  kabul_edilen integer, reddedilen integer, bekleyen integer   -- miktarlar modülde (N:P1398)
);

CREATE INDEX olcumler_parca ON mod_kal.olcumler (parca);

CREATE TABLE mod_kal.olcum_kriteri (
  kimlik bigserial PRIMARY KEY,
  parca text NOT NULL REFERENCES mod_kal.parca_kriterleri (nesne_kimligi),
  ad text NOT NULL
);

-- Bekleyen kontrolleri her sabah yeniden değerlendirir; bırakma tekrar güvenlidir (aynı anahtar = güncelleme).
CREATE FUNCTION mod_kal.bekleyenleri_bildir() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = mod_kal, pg_temp AS $$
DECLARE r record;
BEGIN
  FOR r IN SELECT DISTINCT parca FROM mod_kal.olcumler WHERE bekleyen > 0 LOOP
    PERFORM public.modul_bildirimi_birak('SRV-KAL', 'KAL', 'KABUL_BEKLIYOR',
      jsonb_build_object('tur', 'NESNE', 'kimlik', r.parca),
      jsonb_build_array(jsonb_build_object('tur', 'ROL', 'kimlik', 'KALITECI')),
      'Kalite kontrolü bekleyen miktar var', 'UYARI', public.simdi());
  END LOOP;
END $$;

SELECT cron.schedule('mod_kal_sabah', '0 6 * * 1-6', 'SELECT mod_kal.bekleyenleri_bildir()');
