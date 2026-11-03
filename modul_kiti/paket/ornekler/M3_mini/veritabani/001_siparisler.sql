-- Örnek modülün ilk göçü. Şemayı (mod_m3) ve rolleri kurulum açar; göç yalnızca içini doldurur.

CREATE TABLE mod_m3.siparisler (
  nesne_kimligi text PRIMARY KEY,       -- çekirdekteki PARCA nesnesinin kimliği (değer olarak; yabancı anahtar yok)
  tedarikci text NOT NULL,
  birim_fiyat numeric,                  -- para modülde kalır (künyede para: true)
  termin timestamptz NOT NULL,
  verildi timestamptz NOT NULL
);

-- Arka yüzün olay kimliği sırası: kişi ve gün başına, tek işlemle artar (sozlesme/04_veritabani.md › 3).
CREATE TABLE mod_m3.olay_sayaci (
  kisi text NOT NULL,
  gun text NOT NULL,
  son integer NOT NULL DEFAULT 0,
  PRIMARY KEY (kisi, gun)
);

CREATE FUNCTION mod_m3.olay_sirasi(p_kisi text, p_gun text) RETURNS integer
LANGUAGE sql SET search_path = mod_m3, pg_temp AS $$
  INSERT INTO mod_m3.olay_sayaci AS s (kisi, gun, son) VALUES (p_kisi, p_gun, 1)
  ON CONFLICT (kisi, gun) DO UPDATE SET son = s.son + 1
  RETURNING son;
$$;
