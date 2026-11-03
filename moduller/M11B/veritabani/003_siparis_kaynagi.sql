-- Onaylı çekirdek planı değildir: M11A'nın donmuş teklif planı/girdisinin devir anındaki kopyasıdır.
CREATE TABLE mod_m11b.siparis_kaynagi (
 proje text PRIMARY KEY REFERENCES mod_m11b.devirler(proje),
 kaynak text NOT NULL,
 plan jsonb NOT NULL,
 girdiler jsonb NOT NULL,
 aktaran text NOT NULL,
 an timestamptz NOT NULL
);
CREATE TABLE mod_m11b.kaynak_dosyalari (
 proje text NOT NULL REFERENCES mod_m11b.devirler(proje),
 kaynak text NOT NULL,
 yerel bigint NOT NULL REFERENCES mod_m11b.dosya_kayitlari(kimlik),
 PRIMARY KEY(proje,kaynak)
);
