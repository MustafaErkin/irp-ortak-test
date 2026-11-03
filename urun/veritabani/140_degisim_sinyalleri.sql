SET ROLE irp_sahibi;
CREATE TABLE public.degisim_sinyalleri(kimlik bigserial PRIMARY KEY,kanal text NOT NULL,an timestamptz NOT NULL);
CREATE INDEX degisim_sinyalleri_kanal ON public.degisim_sinyalleri(kanal,kimlik);
CREATE INDEX degisim_sinyalleri_an ON public.degisim_sinyalleri(an);
ALTER TABLE public.degisim_sinyalleri ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.degisim_sinyalleri FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.degisim_sinyalleri TO authenticated;
CREATE TABLE okuma.sinyal_kuyrugu(kanal text PRIMARY KEY);
CREATE TABLE okuma.sinyal_tekil(islem bigint NOT NULL,kanal text NOT NULL,an timestamptz NOT NULL,PRIMARY KEY(islem,kanal));
CREATE TABLE okuma.ana_veri_ozeti(tek boolean PRIMARY KEY DEFAULT true CHECK(tek),ozet text);
CREATE FUNCTION public.sinyal_gorebilir(kanal text) RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text; key text=substr(kanal,position(':' IN kanal)+1); BEGIN
 SELECT kisi INTO kim FROM public.kisi_hesaplari WHERE auth_kimligi=auth.uid();
 IF kim IS NULL OR NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN RETURN false; END IF;
 IF kanal='firma' THEN RETURN true;
 ELSIF starts_with(kanal,'kisi:') THEN RETURN okuma.gorebilir(kim,'GUN',key);
 ELSIF starts_with(kanal,'birim:') THEN RETURN okuma.birim_gorebilir(kim,key);
 ELSIF starts_with(kanal,'proje:') THEN RETURN k9.proje_gorebilir('OKUMA',kim,key);
 END IF; RETURN false; END $$;
REVOKE ALL ON FUNCTION public.sinyal_gorebilir(text) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.sinyal_gorebilir(text) TO authenticated;
CREATE POLICY kanal_gorunurlugu ON public.degisim_sinyalleri FOR SELECT TO authenticated USING(public.sinyal_gorebilir(kanal));
CREATE FUNCTION okuma.sinyal_adayi(kanal text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN IF kanal IS NOT NULL AND kanal !~ ':$' THEN INSERT INTO okuma.sinyal_kuyrugu VALUES(kanal) ON CONFLICT DO NOTHING; END IF; END $$;
CREATE FUNCTION okuma.satir_sinyalleri() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE a text=TG_TABLE_NAME; j jsonb; key text; k text; b text; p text; n int; BEGIN
 IF TG_OP='UPDATE' AND OLD.hal=NEW.hal THEN RETURN NULL; END IF;
 FOR n IN 1..2 LOOP
  IF n=1 THEN IF TG_OP='INSERT' THEN CONTINUE; END IF; j=OLD.hal; key=OLD.anahtar;
  ELSE IF TG_OP='DELETE' THEN CONTINUE; END IF; j=NEW.hal; key=NEW.anahtar; END IF;
  k=CASE WHEN a IN ('kisiler','kisi_durumu','listeler') THEN key WHEN a IN ('bildirimler','modul_bildirimleri') THEN j->>'alici' ELSE j->>'kisi' END;
  b=CASE WHEN a='birimler' THEN key ELSE j->>'birim' END;
  IF b IS NULL AND k IS NOT NULL THEN b=okuma.satir('kisiler',k)->>'birim'; END IF;
  p=CASE WHEN a='projeler' THEN key ELSE j->>'proje' END;
  PERFORM okuma.sinyal_adayi('kisi:'||k); PERFORM okuma.sinyal_adayi('birim:'||b); PERFORM okuma.sinyal_adayi('proje:'||p);
  IF a IN ('kisiler','birimler','projeler','kod_listesi','tezgahlar','gun_tanimlari','gun_onay_ayarlari') THEN PERFORM okuma.sinyal_adayi('firma'); END IF;
 END LOOP; RETURN NULL; END $$;
CREATE FUNCTION okuma.sinyalleri_yayinla() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE ozet text; kanal text; islem bigint=txid_current(); BEGIN
 -- Maaş güncellemesi son hal satırını değiştirmez; maliyet ekranı yine yenilenir.
 -- Kabul sınırı yayınlanmamış hassas eki sinyale ve okumaya karıştırmaz.
 SELECT surum.ozet(jsonb_build_object('ana_veri',coalesce(jsonb_object_agg(ad,hal),'{}'),
  'ucret_kabul_no',(SELECT coalesce(max(e.kabul_no),0) FROM public.hassas_ekler h JOIN public.olaylar e ON e.olay_kimligi=h.olay
                    WHERE e.kabul_no<=(SELECT okuma_kabul_no FROM motor.durum WHERE tek))))
 INTO ozet FROM motor.calisma WHERE kip='YAYIN' AND ad IN ('ayarlar','takvimler','tatiller','varsayilan_takvim','yonlendirme');
 IF ozet IS DISTINCT FROM (SELECT a.ozet FROM okuma.ana_veri_ozeti a WHERE tek) THEN
  PERFORM okuma.sinyal_adayi('firma'); INSERT INTO okuma.ana_veri_ozeti VALUES(true,ozet) ON CONFLICT(tek) DO UPDATE SET ozet=excluded.ozet;
 END IF;
 FOR kanal IN SELECT q.kanal FROM okuma.sinyal_kuyrugu q ORDER BY q.kanal COLLATE "C" LOOP
  INSERT INTO okuma.sinyal_tekil VALUES(islem,kanal,saat.simdi()) ON CONFLICT DO NOTHING;
  IF FOUND THEN INSERT INTO public.degisim_sinyalleri(kanal,an) VALUES(kanal,saat.simdi()); END IF;
 END LOOP;
 DELETE FROM okuma.sinyal_kuyrugu WHERE true;
 DELETE FROM public.degisim_sinyalleri WHERE an<saat.simdi()-interval '1 day';
 DELETE FROM okuma.sinyal_tekil WHERE an<saat.simdi()-interval '1 day';
END $$;
CREATE FUNCTION okuma.yayin_sinyali() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN PERFORM okuma.sinyalleri_yayinla(); RETURN NULL; END $$;
DO $$ DECLARE a text; BEGIN
 FOR a IN SELECT ad FROM motor.yayin_tablosu LOOP
  EXECUTE format('CREATE TRIGGER okuma_satir_degisti AFTER INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION okuma.satir_sinyalleri()',a);
 END LOOP;
END $$;
CREATE TRIGGER okuma_yayin_bitti AFTER UPDATE OF son_yayin_ani ON motor.durum FOR EACH ROW EXECUTE FUNCTION okuma.yayin_sinyali();
CREATE TRIGGER okuma_modul_degisti AFTER INSERT OR UPDATE OR DELETE ON public.modul_bildirimleri FOR EACH ROW EXECUTE FUNCTION okuma.satir_sinyalleri();
CREATE TRIGGER okuma_modul_bitti AFTER INSERT OR UPDATE OR DELETE ON public.modul_bildirimleri FOR EACH STATEMENT EXECUTE FUNCTION okuma.yayin_sinyali();
-- Özel şemalarda da RLS açık; sahip rolü hesaplar, istemciye tablo politikası yok.
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE c.relowner='irp_sahibi'::regrole AND c.relkind='r' LOOP
  EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',r.nspname,r.relname);
  IF NOT (r.nspname='public' AND r.relname='degisim_sinyalleri') THEN EXECUTE format('REVOKE ALL ON %I.%I FROM PUBLIC,anon,authenticated,service_role',r.nspname,r.relname); END IF;
 END LOOP;
END $$;
RESET ROLE;
