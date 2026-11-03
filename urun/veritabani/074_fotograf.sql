SET ROLE irp_sahibi;
-- gorunum_v7.py:277 onay fotoğrafı / kurallar_v7.py:304 planın bilinen hali.
-- Aynı nokta ve bitirme fonksiyonları ayrı çalışma kopyasında yürür. Kaynak,
-- motor tarihçesi, yayın ve bekleyen işler değişmez. Nokta listesi ve saat
-- dönüşte aynen yerine konur; hata halinde alt işlem bütün değişikliği alır.
CREATE FUNCTION motor.fotograf(es jsonb,t timestamptz,istenen text DEFAULT NULL,
 kisi text DEFAULT NULL,tarih date DEFAULT NULL,bitis date DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE m text='FOTOGRAF:'||gen_random_uuid(); once saat.ayar%ROWTYPE;
 noktalar jsonb; n motor.noktalar; sonuc jsonb;
BEGIN
 PERFORM motor.butce_denetle();
 SELECT * INTO once FROM saat.ayar WHERE tek;
 SELECT coalesce(jsonb_agg(to_jsonb(z)),'[]') INTO noktalar FROM motor.noktalar z;
 PERFORM motor.bosalt(m);
 UPDATE saat.ayar SET simdi=t,gercek=t,demo=false WHERE tek;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(es) z WHERE z->>'eylem_kodu'='KURULUM.TAMAMLADIM' AND saat.an(z->>'oldugu_an')<=t) THEN
  PERFORM motor.yaz(m,'kod_listesi',irp.sabit('kodlar9'));
  PERFORM motor.yaz(m,'yetki_kurallari',irp.sabit('yetkiler9'));
 END IF;
 PERFORM motor.hazirla_kaynak(m,es);
 FOR n IN SELECT * FROM motor.noktalar ORDER BY konum COLLATE "C" LOOP
  PERFORM motor.butce_denetle();
  PERFORM motor.nokta_isle(m,n);
 END LOOP;
 PERFORM motor.bitir(m);
 IF istenen='gun_ozeti' THEN sonuc=k7.gun_ozeti(m,kisi,tarih);
 ELSIF istenen='donem_defteri' THEN sonuc=zaman.donem_defteri(m,tarih,bitis);
 ELSE SELECT jsonb_object_agg(ad,hal) INTO sonuc FROM motor.calisma WHERE kip=m; END IF;
 DELETE FROM motor.calisma WHERE kip=m;
 DELETE FROM motor.anahtar_sirasi WHERE kip=m;
 DELETE FROM motor.noktalar WHERE true;
 INSERT INTO motor.noktalar SELECT * FROM jsonb_populate_recordset(NULL::motor.noktalar,noktalar);
 UPDATE saat.ayar SET simdi=once.simdi,gercek=once.gercek,demo=once.demo WHERE tek;
 RETURN sonuc;
EXCEPTION WHEN OTHERS THEN
 -- PL/pgSQL hata bloğu girişinden beri yapılan bütün yazıları geri alır.
 RAISE;
END $$;
RESET ROLE;
