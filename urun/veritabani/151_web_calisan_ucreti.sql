-- Çalışan ayrıntısında yalnız mevcut YETKILI yetkisiyle güncel aylık maaş.
-- Devredilebilir maaş görme yetkisi MVP sonrası kararıdır; burada genişletilmez.
SET ROLE irp_sahibi;
CREATE FUNCTION okuma.web_kisi_ayrintisi(kim text,kisi text) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE r jsonb; BEGIN
 r=okuma.web_oku(kim,'WEB_KISI',kisi,'{}');
 IF okuma.satir('kisiler',kim)->'roller' ? 'YETKILI' THEN
  r=r||jsonb_build_object('brut_maas',okuma.kodlu_tutar(okuma.tutar_bul(kisi,'MAAS_AYLIK',saat.gun(saat.kodla(saat.simdi()))::text)));
 END IF;
 RETURN r;
END $$;
REVOKE ALL ON FUNCTION okuma.web_kisi_ayrintisi(text,text) FROM PUBLIC,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION public.oku(veri text,hedef text DEFAULT NULL,g jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text; deger jsonb;
BEGIN
 IF g IS NULL OR jsonb_typeof(g)<>'object' THEN RAISE EXCEPTION 'IRP|BICIM|Okuma parametreleri'; END IF;
 IF g ? 'kim' THEN
  IF coalesce(current_setting('role',true),'')<>'service_role' OR auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'IRP|YETKI|g.kim yalniz cekirdek servis rolune aittir'; END IF;
  kim=g->>'kim';
 ELSE kim=kapi.oturum_kisi(); END IF;
 IF kim IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 IF veri='WEB_KISI' THEN deger=okuma.web_kisi_ayrintisi(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
