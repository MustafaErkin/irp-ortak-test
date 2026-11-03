SET ROLE irp_sahibi;
-- Geçmiş ve dönem düzeltmesi kendi süzülmüş kaynağını hazırlar. Canlı
-- motor.hazirla'nın _hazirlik_anahtari önbelleği bu yolda kullanılmaz.
CREATE VIEW okuma.gecmis_olaylar AS SELECT * FROM public.olaylar
WHERE oldugu_an<=saat.simdi() AND bulut_ulasma_ani<=saat.simdi();
CREATE FUNCTION okuma.gecmis_hazirla(m text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kaynak jsonb; BEGIN
 SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]'::jsonb)
  INTO kaynak FROM okuma.gecmis_olaylar;
 PERFORM motor.hazirla_kaynak(m,kaynak);
END $$;
CREATE FUNCTION okuma.gecmis(t text,ad text,g jsonb) RETURNS jsonb LANGUAGE plpgsql VOLATILE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb; n motor.noktalar; bas timestamptz=saat.an(t); BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 BEGIN
  UPDATE saat.ayar SET simdi=bas WHERE tek;
  PERFORM set_config('irp.gecmis_okuma','evet',true);
  -- DELETE MVCC'yi korur; TRUNCATE ile sıradan okumalar kilitlenmez.
  DELETE FROM motor.hal WHERE true; DELETE FROM motor.baglam WHERE true; DELETE FROM motor.noktalar WHERE true;
  PERFORM motor.bosalt('MOTOR');
  PERFORM motor.yaz('MOTOR','kod_listesi',irp.sabit('kodlar9'));
  PERFORM motor.yaz('MOTOR','yetki_kurallari',irp.sabit('yetkiler9'));
  DELETE FROM public.ay_kapanislari WHERE left(anahtar,10) NOT IN
   (SELECT left(anahtar,10) FROM public.ay_kapanislari WHERE saat.an(hal->>'kapanis_ani')<=bas);
  PERFORM okuma.gecmis_hazirla('MOTOR');
  FOR n IN SELECT * FROM motor.noktalar WHERE an<=bas ORDER BY konum COLLATE "C" LOOP PERFORM motor.nokta_isle('MOTOR',n); END LOOP;
  DELETE FROM motor.yayin WHERE true; PERFORM motor.yayinla();
  IF ad='gecmis_gorunumu' THEN
   SELECT jsonb_object_agg(a,CASE WHEN a='ay_kapanislari' THEN (SELECT coalesce(jsonb_object_agg(anahtar,hal),'{}') FROM public.ay_kapanislari) ELSE okuma.tablo(a) END)
    INTO sonuc FROM unnest(ARRAY['kisi_durumu','listeler','isler','gorevler','araliklar','ay_kapanislari']) a;
  ELSIF ad='oku' THEN sonuc=okuma.oku(g->>'kim',g->>'veri',g->>'hedef',g-'t'-'kim'-'veri'-'hedef');
  ELSE sonuc=okuma.ic(ad,g-'t'); END IF;
  RAISE EXCEPTION USING ERRCODE='P2222',MESSAGE='Gecmis okuma tamamlandi';
 EXCEPTION WHEN SQLSTATE 'P2222' THEN NULL;
 END;
 RETURN sonuc;
END $$;
RESET ROLE;
