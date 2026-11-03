-- Çekirdek yanıtı kaybolsa ve süreç yeniden başlasa da açılış aynı olayla tamamlanır.
CREATE TABLE mod_m11a.acilis_zarflari (
 kisi text NOT NULL,
 istek text NOT NULL,
 proje text NOT NULL REFERENCES mod_m11a.projeler(proje) ON DELETE CASCADE,
 olay jsonb NOT NULL,
 PRIMARY KEY(kisi,istek)
);
