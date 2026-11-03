-- Yalnız --test ile kurulur; parametre adları sorgu kataloğundan üretilir.
SET ROLE irp_sahibi;
CREATE OR REPLACE FUNCTION test.giris(k text) RETURNS uuid LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE u uuid; BEGIN
 INSERT INTO public.kisi_hesaplari(auth_kimligi,kisi) VALUES(gen_random_uuid(),k) ON CONFLICT(kisi) DO NOTHING;
 SELECT auth_kimligi INTO u FROM public.kisi_hesaplari WHERE kisi=k;
 INSERT INTO irp.kisiler_oturum(kisi,oturum) VALUES(k,u) ON CONFLICT(kisi) DO UPDATE SET oturum=excluded.oturum;
 RETURN u; END $$;
ALTER FUNCTION test.sifirla() RENAME TO sifirla_motor;
CREATE FUNCTION test.sifirla() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 DELETE FROM public.kisi_hesaplari WHERE true;
 DELETE FROM okuma.yayin_yardimci WHERE true;
 DELETE FROM okuma.yayin_sirasi WHERE true;
 DELETE FROM okuma.kapanis_sonuclari WHERE true;
 DELETE FROM okuma.duzeltme_ozeti WHERE true;
 IF to_regclass('public.degisim_sinyalleri') IS NOT NULL THEN DELETE FROM public.degisim_sinyalleri WHERE true; END IF;
 PERFORM test.sifirla_motor();
 IF to_regclass('public.degisim_sinyalleri') IS NOT NULL THEN DELETE FROM public.degisim_sinyalleri WHERE true; END IF;
END $$;
CREATE FUNCTION test.coz(j jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; BEGIN
 IF jsonb_typeof(j)='object' THEN
  IF (SELECT count(*) FROM jsonb_object_keys(j))=1 AND j ?| ARRAY['$an','$gun','$ondalik','$kume'] THEN RETURN coalesce(j->'$an',j->'$gun',j->'$ondalik',j->'$kume'); END IF;
  SELECT coalesce(jsonb_object_agg(key,test.coz(value)),'{}') INTO r FROM jsonb_each(j); RETURN r;
 ELSIF jsonb_typeof(j)='array' THEN SELECT coalesce(jsonb_agg(test.coz(value)),'[]') INTO r FROM jsonb_array_elements(j); RETURN r;
 END IF; RETURN j; END $$;
CREATE FUNCTION test.sorgu(modul text,ad text,args jsonb DEFAULT '[]',kwargs jsonb DEFAULT '{}') RETURNS jsonb LANGUAGE plpgsql VOLATILE AS $$
#variable_conflict use_column
DECLARE izin jsonb='{"irp.gorunum_v9.proje_kaydi": ["proje", "t", "cagiran"], "irp.gorev.son_teslim_ani": ["g", "m"], "irp.gorunumler.adil_performans": ["kisi", "bas", "bit", "cagiran"], "irp.gorunumler.etap_gostergesi": ["etap", "t"], "irp.gorunumler.gorev_isaretleri": ["gorev", "ay"], "irp.gorunumler.gorev_payi": ["g", "bas", "bit", "yuk", "kisi"], "irp.gorunumler.maas_dagilimi": ["kisi", "ay", "canli"], "irp.gorunumler.proje_gostergesi": ["proje", "cagiran"], "irp.gorunumler.yuk": ["kisi", "bas", "bit"], "irp.is_.emek": ["kimlik"], "irp.gorunum_v7.fazla_mesai_kayitlari": [], "irp.gorunum_v7.gecmis_gorunumu": ["t"], "irp.gorunum_v7.gun_agirligi": ["tarih", "kisi"], "irp.gorunum_v7.gun_sonu_raporu": ["kisi", "tarih"], "irp.gorunum_v7.hatirlatmalar": [], "irp.gorunum_v7.kapasite": ["kisi", "bas", "bit"], "irp.gorunum_v9.gecikme_raporu": ["bas", "bit", "kirilim", "cagiran"], "irp.gorunum_v9.gun_isleri": ["kisi", "t"], "irp.gorunum_v9.okunmamis_bildirimler": ["kisi"], "irp.gorunum_v9.sorumluluk_ekleri": ["kisi", "bas", "bit", "tur"], "irp.gorunumler.elle_sureler": ["birim", "bas", "bit"], "irp.gorunumler.gorev_gunluk_paylar": ["g", "yuk"], "irp.gorunumler.is_gunleri": ["bas", "bit", "kisi"], "irp.gorunumler.iscilik_maliyeti": ["proje", "bas", "bit", "canli", "iptal"], "irp.gorunumler.kapasite": ["kisi", "bas", "bit"], "irp.gorunumler.kisinin_gunu": ["kisi", "tarih"], "irp.kisi_gunu.kapi": ["kod", "is_", "bas", "sabit"], "irp.gorunum_v10_1.bildirim_kutusu": ["kisi", "cagiran"], "irp.gorunum_v10_1.gantt": ["proje", "bas", "bit", "cagiran"], "irp.gorunum_v10_1.gecerli_surum": ["nesne", "t", "cagiran"], "irp.gorunum_v10_1.plan_cakismalari": ["kaynak", "bas", "bit", "cagiran"], "irp.gorunum_v10_1.surumler": ["nesne", "cagiran"], "irp.gorunum_v6.iptal_edilenler": ["proje", "bas", "bit"], "irp.gorunum_v7.kisi_uygun_mu": ["kisi", "bas", "bit", "cagiran"], "irp.gorunum_v7.onceki_donem_duzeltmeleri": [], "irp.gorunum_v7.plan_karsilastir": ["proje"], "irp.gorunum_v7.tezgah_gostergesi": ["tezgah", "bas", "bit"], "irp.gorunum_v7.tezgah_uygun_mu": ["tezgah", "bas", "bit"], "irp.gorunum_v7.top_kimde": ["kimlik"], "irp.gorunum_v9.degisiklik_gecmisi": ["kaynak", "cagiran"], "irp.gorunum_v9.gorebilir_mi": ["kim", "veri", "hedef"], "irp.gorunum_v9.gorev_listesi": ["kisi"], "irp.gorunum_v9.proje_degisiklikleri": ["proje", "bas", "bit", "cagiran"], "irp.gorunum_v9.proje_erisim_gecmisi": ["proje", "cagiran"], "irp.gorunum_v9.proje_gorebilir_mi": ["kim", "proje", "t"], "irp.gorunumler.onay_listesi": ["kisi"], "irp.surum.liste_surumu": ["kisi"]}'::jsonb; alanlar jsonb; g jsonb=test.coz(kwargs); a jsonb=test.coz(args); i int; alan text; BEGIN
 alanlar=izin->(modul||'.'||ad); IF alanlar IS NULL THEN RAISE EXCEPTION 'IRP|BICIM|Bilinmeyen sorgu'; END IF;
 IF modul='irp.kisi_gunu' AND ad='kapi' THEN RETURN to_jsonb(kg.kapi(a->0,a->>1,a->2,a->>3,coalesce((a->>4)::boolean,(g->>'sabit')::boolean,false))); END IF;
 IF modul='irp.gorev' AND ad='son_teslim_ani' THEN RETURN to_jsonb(saat.kodla(gorev.son_teslim_ani(coalesce(a->0,g->'g')))); END IF;
 IF jsonb_array_length(a)>jsonb_array_length(alanlar) THEN RAISE EXCEPTION 'IRP|BICIM|Fazla sorgu argumani'; END IF;
 FOR i IN 0..jsonb_array_length(a)-1 LOOP
  alan=alanlar->>i; IF g ? alan THEN RAISE EXCEPTION 'IRP|BICIM|Yinelenen sorgu argumani'; END IF; g=g||jsonb_build_object(alan,a->i);
 END LOOP;
 RETURN okuma.ic(ad,g);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA test FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
