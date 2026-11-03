-- Bu dosya yalnız --test ile kurulur. İstemci rollerine test kapısı açılmaz.
CREATE SCHEMA test AUTHORIZATION irp_sahibi;
REVOKE ALL ON SCHEMA test FROM PUBLIC,anon,authenticated,service_role;
SET ROLE irp_sahibi;
UPDATE saat.ayar SET test_ortami=true WHERE tek;
CREATE FUNCTION test.ortam() RETURNS text LANGUAGE sql STABLE AS $$ SELECT CASE WHEN test_ortami AND current_database() ILIKE '%test%' THEN 'TEST' ELSE 'CANLI' END FROM saat.ayar WHERE tek $$;
CREATE FUNCTION test.giris(k text) RETURNS uuid LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE u uuid; BEGIN
 INSERT INTO irp.kisiler_oturum(kisi,oturum) VALUES(k,gen_random_uuid()) ON CONFLICT DO NOTHING;
 SELECT oturum INTO u FROM irp.kisiler_oturum WHERE kisi=k; RETURN u; END $$;
CREATE FUNCTION test.saat(s timestamptz,g timestamptz,d boolean) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 UPDATE saat.ayar SET simdi=s,gercek=g,demo=d WHERE tek; END $$;
CREATE FUNCTION test.sifirla() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 IF test.ortam()<>'TEST' THEN RAISE EXCEPTION 'Test ortami gerekli'; END IF;
 ALTER TABLE public.olaylar DISABLE TRIGGER olaylar_degismez;
 TRUNCATE public.hassas_ekler,public.olaylar,public.ay_kapanislari,public.isleme_hatalari,public.modul_bildirimleri,public.cihaz_harfleri,public.cihaz_esitlemeleri,motor.hal,motor.baglam,motor.calisma,motor.anahtar_sirasi,motor.yayin,motor.noktalar,motor.olcumler,motor.arka_plan_isleri,irp.kisiler_oturum RESTART IDENTITY;
 ALTER TABLE public.olaylar ENABLE TRIGGER olaylar_degismez;
 TRUNCATE motor.rapor_onay_onbellegi;
 DELETE FROM motor.durum WHERE true; INSERT INTO motor.durum(tek) VALUES(true);
 PERFORM motor.bosalt('MOTOR'); PERFORM motor.yaz('MOTOR','kod_listesi',irp.sabit('kodlar9')); PERFORM motor.yaz('MOTOR','yetki_kurallari',irp.sabit('yetkiler9'));
 PERFORM motor.yayinla(); END $$;
CREATE FUNCTION test.ilerlet() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 SELECT min(motor.konum(etki_ani,0,'')) COLLATE "C" INTO k FROM public.olaylar WHERE oldugu_an>(SELECT son_yayin_ani FROM motor.durum WHERE tek) AND oldugu_an<=saat.simdi();
 PERFORM motor.iste(k); END $$;
CREATE FUNCTION test.bekleyen() RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT bekleyen_sinir IS NOT NULL FROM motor.durum WHERE tek $$;
CREATE FUNCTION test.bekle() RETURNS integer LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 RETURN motor.arka_plan_calistir();
END $$;
CREATE FUNCTION test.butce(nokta integer,saniye double precision) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 IF nokta<=0 OR saniye<=0 THEN RAISE EXCEPTION 'Butce pozitif olmali'; END IF;
 UPDATE motor.durum SET nokta_butcesi=coalesce(nokta,2000),saniye_butcesi=coalesce(saniye,2) WHERE tek; END $$;
CREATE FUNCTION test.yeniden_kur() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 PERFORM motor.yeniden_kur();
END $$;
CREATE FUNCTION test.demo_sifirla(baslangic timestamptz) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE cihazlar jsonb; esitlemeler jsonb; sim timestamptz; ger timestamptz; BEGIN
 IF NOT saat.demo() THEN RAISE EXCEPTION 'IRP|YETKI|Yalniz demo'; END IF;
 SELECT coalesce(jsonb_object_agg(anahtar,hal),'{}') INTO cihazlar FROM public.cihaz_harfleri;
 SELECT coalesce(jsonb_object_agg(anahtar,hal),'{}') INTO esitlemeler FROM public.cihaz_esitlemeleri;
 ger=saat.gercek(); PERFORM test.sifirla(); PERFORM test.saat(baslangic,ger,true);
 INSERT INTO public.cihaz_harfleri SELECT * FROM jsonb_each(cihazlar); INSERT INTO public.cihaz_esitlemeleri SELECT * FROM jsonb_each(esitlemeler);
 PERFORM motor.iste(''); END $$;
CREATE FUNCTION test.surum(tur text,kimlik text) RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT kapi.nesne('YAYIN',tur,kimlik)->'surum' $$;
CREATE FUNCTION test.dok(tablolar jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE sonuc jsonb='{}'; a text; x jsonb; kaynak text; BEGIN
 FOR a IN SELECT jsonb_array_elements_text(tablolar) LOOP
  IF a='olay_kimlikleri' THEN SELECT coalesce(jsonb_agg(olay_kimligi ORDER BY olay_kimligi COLLATE "C"),'[]') INTO x FROM public.olaylar;
  ELSIF a='isleme_hatalari' THEN SELECT coalesce(jsonb_agg(hal-'an' ORDER BY sira),'[]') INTO x FROM public.isleme_hatalari;
  ELSIF a IN ('ay_kapanislari','cihaz_harfleri','cihaz_esitlemeleri','modul_bildirimleri') THEN
   EXECUTE format('SELECT coalesce(jsonb_object_agg(anahtar,hal),''{}''::jsonb) FROM public.%I',a) INTO x;
   IF a='cihaz_harfleri' AND x='{}' THEN CONTINUE; END IF;
  ELSIF a='kurulum' THEN IF NOT (SELECT kurulum_tamamlandi FROM motor.durum WHERE tek) THEN CONTINUE; END IF;
   SELECT jsonb_build_object('tamamlandi',true,'kod_listeleri',kod_listeleri) INTO x FROM motor.durum WHERE tek;
  ELSE x=motor.oku('YAYIN',a,coalesce(irp.sabit('bos_hal')->a,'{}'));
   IF a='bildirimler' THEN SELECT coalesce(jsonb_object_agg(key,value),'{}') INTO x FROM jsonb_each(x) WHERE irp.dogru((value->'gecerli')); END IF;
  END IF; sonuc=sonuc||jsonb_build_object(a,x);
 END LOOP; RETURN sonuc; END $$;
CREATE FUNCTION test.olcumler() RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT coalesce(jsonb_agg(to_jsonb(o) ORDER BY sira),'[]') FROM motor.olcumler o $$;
-- T15 v5 D5: saat ayarı yayın başlatmaz; yeniden kurma son yayın anını kullanır.
CREATE FUNCTION test.yayin_saati() RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT jsonb_build_object('simdi',saat.kodla(coalesce(son_yayin_ani,saat.simdi())),
  'gercek',saat.kodla(saat.gercek()),'demo',saat.demo()) FROM motor.durum WHERE tek $$;
CREATE FUNCTION test.kabul_sirasi() RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT coalesce(jsonb_agg(jsonb_build_object('olay_kimligi',olay_kimligi,'kabul_no',kabul_no) ORDER BY kabul_no),'[]') FROM public.olaylar $$;
CREATE FUNCTION test.kapanis(ay date) RETURNS jsonb LANGUAGE sql AS $$ SELECT zaman.ay_kapanisi(ay) $$;
CREATE FUNCTION test.kurulum(olaylar jsonb,kod_listeleri jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN RETURN kapi.kurulum(olaylar,kod_listeleri); END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA test FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
