CREATE TABLE mod_m11a.teknik_dosya_devri (
 proje text NOT NULL REFERENCES mod_m11a.projeler(proje),
 kaynak text NOT NULL,
 dosya jsonb NOT NULL,
 PRIMARY KEY(proje,kaynak)
);
