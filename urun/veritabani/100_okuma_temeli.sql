-- T16: okuma kimliği ve modelin görme kuralları. Normal hesaplar son yayını okur.
CREATE SCHEMA okuma AUTHORIZATION irp_sahibi;
REVOKE ALL ON SCHEMA okuma FROM PUBLIC,anon,authenticated,service_role;
SET ROLE irp_sahibi;
CREATE TABLE public.kisi_hesaplari(auth_kimligi uuid PRIMARY KEY,kisi text UNIQUE NOT NULL);
ALTER TABLE public.kisi_hesaplari ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.kisi_hesaplari FROM PUBLIC,anon,authenticated,service_role;
INSERT INTO public.kisi_hesaplari(auth_kimligi,kisi)
SELECT oturum,kisi FROM irp.kisiler_oturum ON CONFLICT DO NOTHING;
CREATE FUNCTION kapi.oturum_kisi() RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE k text; BEGIN
 SELECT kisi INTO k FROM public.kisi_hesaplari WHERE auth_kimligi=auth.uid();
 IF k IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF; RETURN k;
END $$;
-- Yazma ve cihaz kapıları da aynı işletim eşlemesini kullanır.
CREATE OR REPLACE FUNCTION kapi.oturum() RETURNS text LANGUAGE sql STABLE AS
$$ SELECT kisi FROM public.kisi_hesaplari WHERE auth_kimligi=auth.uid() $$;
CREATE FUNCTION okuma.tablo(ad text) RETURNS jsonb LANGUAGE sql STABLE AS
$$ SELECT motor.oku('OKUMA',ad,coalesce(irp.sabit('bos_hal')->ad,'{}')) $$;
CREATE FUNCTION okuma.satir(ad text,k text) RETURNS jsonb LANGUAGE sql STABLE AS
$$ SELECT okuma.tablo(ad)->k $$;
CREATE FUNCTION okuma.satirlar(ad text) RETURNS TABLE(k text,x jsonb) LANGUAGE sql STABLE AS
$$ SELECT anahtar,hal FROM motor.satirlar('OKUMA',ad) $$;
CREATE FUNCTION okuma.para(n numeric) RETURNS jsonb LANGUAGE sql IMMUTABLE AS
$$ SELECT to_jsonb(round(n,2)::text) $$;
-- Decimal'ın kanonik iki basamaklı gösterimi (hesapta hassasiyet korunur).
CREATE FUNCTION okuma.kodlu_tutar(n numeric) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT to_jsonb(round(CASE WHEN abs(n*100-trunc(n*100))=0.5 AND mod(abs(trunc(n*100)),2)=0
 THEN trunc(n*100)/100 ELSE n END,2)::text) $$;
CREATE FUNCTION okuma.ekle(j jsonb,k text,n numeric) RETURNS jsonb LANGUAGE sql IMMUTABLE AS
$$ SELECT j||jsonb_build_object(k,coalesce((j->>k)::numeric,0)+n) $$;
CREATE FUNCTION okuma.gunler(bas text,bit_ text) RETURNS SETOF date LANGUAGE sql STABLE AS
$$ SELECT saat.gun(bas)+n FROM generate_series(0,saat.gun(bit_)-saat.gun(bas)) n $$;
CREATE FUNCTION okuma.pencere(bas text,bit_ text DEFAULT NULL) RETURNS timestamptz[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a timestamptz=saat.an(bas); b timestamptz; BEGIN
 b=CASE WHEN position('T' IN coalesce(bit_,''))>0 THEN saat.an(bit_) ELSE saat.gun_ani(saat.gun(coalesce(bit_,bas))+1) END;
 IF a IS NULL OR a>=b THEN RAISE EXCEPTION 'IRP|BICIM|Gorunum araligi'; END IF;
 RETURN ARRAY[a,b]; END $$;
CREATE FUNCTION okuma.saatler(xs jsonb) RETURNS numeric LANGUAGE sql STABLE AS
$$ SELECT coalesce(sum(extract(epoch FROM saat.an(x->>1)-saat.an(x->>0))/3600),0) FROM jsonb_array_elements(xs) x $$;
CREATE FUNCTION okuma.temel_gorebilir(kim text,veri text,hedef text DEFAULT NULL) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE yetkili boolean; BEGIN
 IF NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN RETURN false; END IF;
 yetkili=okuma.satir('kisiler',kim)->'roller' ? 'YETKILI';
 IF veri IN ('MAAS','UCRET','SAAT_MALIYETI','TUTAR','MALIYET','PROJE_TUTAR') THEN RETURN yetkili; END IF;
 IF veri IN ('GUN','GOREV','IS','PERFORMANS','FAZLA_MESAI','IZIN','IZIN_DETAY') THEN
  RETURN coalesce(okuma.tablo('kisiler') ? hedef AND (yetkili OR kim=hedef OR kim=ANY(yetki_v6.ustler('OKUMA',hedef))),false);
 END IF;
 IF veri='BIRIM_PERFORMANS' THEN RETURN coalesce(okuma.tablo('birimler') ? hedef AND
  (yetkili OR okuma.satir('kisiler',kim)->>'birim'=hedef OR kim=ANY(yetki_v6.yoneticiler('OKUMA',hedef)||yetki_v6.birim_ustleri('OKUMA',hedef))),false); END IF;
 IF veri IN ('PROJE_DURUM','ETAP_DURUM','UYGUNLUK','NESNE') THEN RETURN true; END IF;
 IF veri='HAM_OLAY' THEN RETURN coalesce(yetkili OR kim=hedef,false); END IF;
 RETURN false; END $$;
CREATE FUNCTION okuma.surum_gorebilir(kim text,s jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb=okuma.satir('nesneler',s->>'nesne'); BEGIN
 IF x IS NULL OR NOT okuma.gorebilir(kim,'NESNE',s->>'nesne') THEN RETURN false; END IF;
 RETURN s->>'durum'<>'TASLAK' OR kim IN (s->>'ekleyen',x->>'sorumlu') OR kim=ANY(yetki_v6.ustler('OKUMA',x->>'sorumlu')) OR k10_1.onaylayabilir('OKUMA',kim,x,s);
END $$;
CREATE FUNCTION okuma.gorebilir(kim text,veri text,hedef text DEFAULT NULL) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE tur text=coalesce('{"ADIL_PERFORMANS":"PERFORMANS","PROJE":"PROJE_DURUM","ETAP":"ETAP_DURUM","PLAN":"PROJE_DURUM","NOT":"PROJE_DURUM","DOSYA":"PROJE_DURUM","KIM_NEREDE":"UYGUNLUK","SAAT_NEREYE_GITTI":"UYGUNLUK"}'::jsonb->>veri,veri);
 k text=hedef; x jsonb; p text; ps text[]; BEGIN
 IF veri='DOSYA' AND EXISTS(SELECT FROM okuma.satirlar('nesne_surumleri') WHERE x->'dosyalar' ? hedef)
 AND NOT EXISTS(SELECT FROM okuma.satirlar('nesne_surumleri') s WHERE s.x->'dosyalar' ? hedef AND okuma.surum_gorebilir(kim,s.x)) THEN RETURN false; END IF;
 IF veri IN ('IS','GOREV') AND NOT coalesce(okuma.tablo('kisiler') ? hedef,false) THEN
  x=okuma.satir(CASE WHEN veri='IS' THEN 'isler' ELSE 'gorevler' END,hedef); IF x IS NULL THEN RETURN false; END IF;
  k=x->>'kisi'; IF k IS NULL OR k='' THEN tur='PROJE_DURUM'; END IF;
 END IF;
 IF NOT okuma.temel_gorebilir(kim,tur,k) THEN RETURN false; END IF;
 ps=CASE WHEN veri IN ('PROJE','PROJE_DURUM','PROJE_TUTAR','MALIYET','PLAN') AND okuma.tablo('projeler') ? hedef THEN ARRAY[hedef]
  WHEN veri='ETAP_DURUM' THEN k9.bagli_projeler('OKUMA','ETAP',hedef) ELSE k9.bagli_projeler('OKUMA',veri,hedef) END;
 FOREACH p IN ARRAY ps LOOP IF NOT k9.proje_gorebilir('OKUMA',kim,p) THEN RETURN false; END IF; END LOOP;
 RETURN true; END $$;
CREATE FUNCTION okuma.ayikla(j jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; k text; v jsonb; BEGIN
 IF jsonb_typeof(j)='object' THEN r='{}'; FOR k,v IN SELECT * FROM jsonb_each(j) LOOP
  IF k NOT IN ('maliyet','iscilik','tezgah','maas','tutar','tutarlar','prim') THEN r=r||jsonb_build_object(k,okuma.ayikla(v)); END IF; END LOOP; RETURN r;
 ELSIF jsonb_typeof(j)='array' THEN SELECT coalesce(jsonb_agg(okuma.ayikla(value)),'[]') INTO r FROM jsonb_array_elements(j); RETURN r;
 END IF; RETURN j; END $$;
CREATE FUNCTION okuma.birim_gorebilir(kim text,b text) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) AND coalesce(okuma.satir('kisiler',kim)->'roller' ? 'YETKILI'
 OR kim=ANY(yetki_v6.yoneticiler('OKUMA',b)||yetki_v6.birim_ustleri('OKUMA',b)),false) $$;
CREATE FUNCTION public.simdi() RETURNS timestamptz LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$ SELECT saat.simdi() $$;
CREATE FUNCTION public.oku(veri text,hedef text DEFAULT NULL,g jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text; deger jsonb; BEGIN
 IF g IS NULL OR jsonb_typeof(g)<>'object' THEN RAISE EXCEPTION 'IRP|BICIM|Okuma parametreleri'; END IF;
 IF g ? 'kim' THEN
  IF coalesce(current_setting('role',true),'')<>'service_role' OR auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'IRP|YETKI|g.kim yalniz cekirdek servis rolune aittir'; END IF;
  kim=g->>'kim';
 ELSE kim=kapi.oturum_kisi(); END IF;
 IF kim IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 deger=okuma.oku(kim,veri,hedef,g-'kim');
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
GRANT EXECUTE ON FUNCTION public.oku(text,text,jsonb),public.simdi() TO anon,authenticated,service_role;
REVOKE ALL ON FUNCTION kapi.oturum_kisi() FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
