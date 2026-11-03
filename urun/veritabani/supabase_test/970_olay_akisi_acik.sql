-- Supabase test projesinde (gösteri ve hata ayıklama) olay akışı açık (146).
INSERT INTO irp.sozluk(ad,hal) VALUES('olay_akisi_acik','true'::jsonb) ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal;
