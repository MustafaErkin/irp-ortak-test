CREATE TABLE mod_m10.bildirim_kuyrugu (
 surum bigint PRIMARY KEY REFERENCES mod_m10.teklif_surumleri(kimlik),
 acik boolean NOT NULL,
 metin text NOT NULL,
 an timestamptz NOT NULL,
 bekliyor boolean NOT NULL DEFAULT true
);
