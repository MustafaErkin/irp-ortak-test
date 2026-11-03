-- Karar 207: Birim ağacıyla proje/etap sorumlusu atama sınırı.
SET ROLE irp_sahibi;
CREATE FUNCTION yetki_v6.sorumlu_atayabilir(d text,kim text,aday text,kod text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE roller text[]=irp.dizi(motor.kayit(d,'kisiler',kim)->'roller'); BEGIN
 IF aday IS NULL OR aday='' THEN RETURN true; END IF;
 IF NOT yetki_v6.istihdamda(d,aday,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 IF aday=kim THEN RETURN true; END IF;
 -- Üst kişiye atama, genel işlem yetkisi verilmiş olsa da yapılamaz.
 IF aday=ANY(yetki_v6.ustler(d,kim)) THEN RETURN false; END IF;
 IF kim=ANY(yetki_v6.ustler(d,aday)) THEN RETURN true; END IF;
 -- Başka birime yalnız doğrudan verilmiş firma kapsamlı işlem yetkisi.
 RETURN 'YETKILI'=ANY(roller) OR EXISTS(SELECT FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) r
  WHERE r->>'eylem_kodu'=kod AND r->>'kapsam'='FIRMA' AND NOT irp.dogru(r->'gecerli_bitis') AND irp.dizi(r->'kimler')&&roller);
END $$;
ALTER FUNCTION yetki_v6.yetkili_mi(text,jsonb,boolean) RENAME TO yetkili_mi_156;
CREATE FUNCTION yetki_v6.yetkili_mi(d text,e jsonb,servis boolean DEFAULT false) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; aday text; eski text; BEGIN
 IF NOT yetki_v6.yetkili_mi_156(d,e,servis) THEN RETURN false; END IF;
 IF kod IN ('PROJE.ACTIM','ETAP.TANIMLADIM') THEN aday=g->>'sorumlu';
 ELSIF kod IN ('PROJE.DEGISTIRDIM','ETAP.DEGISTIRDIM') AND g->'degisenler' ? 'sorumlu' THEN
  aday=g->'degisenler'->>'sorumlu';
  eski=motor.kayit(d,CASE WHEN kod='PROJE.DEGISTIRDIM' THEN 'projeler' ELSE 'etaplar' END,(kapi.hedefler(e,split_part(kod,'.',1)))[1])->>'sorumlu';
  IF aday IS NOT DISTINCT FROM eski THEN RETURN true; END IF;
 ELSE RETURN true; END IF;
 RETURN yetki_v6.sorumlu_atayabilir(d,e->>'kim',aday,kod);
END $$;
REVOKE ALL ON FUNCTION yetki_v6.sorumlu_atayabilir(text,text,text,text),yetki_v6.yetkili_mi(text,jsonb,boolean) FROM PUBLIC;

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
 ELSIF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 IF veri='WEB_BAGLAM' THEN
  deger=deger||jsonb_build_object('sorumlu_adaylari',(SELECT jsonb_object_agg(kod,adaylar) FROM (
   SELECT kod,(SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') FROM okuma.satirlar('kisiler') WHERE yetki_v6.sorumlu_atayabilir('OKUMA',kim,k,kod)) adaylar
   FROM unnest(ARRAY['PROJE.ACTIM','PROJE.DEGISTIRDIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM']) kod) q));
 END IF;
 IF veri='PLAN' AND coalesce((g->>'surumler')::boolean,false) THEN
  deger=deger||jsonb_build_object('surumler',coalesce(okuma.satir('plan_surumleri',hedef),'[]'));
 END IF;
 IF veri='GANTT' AND coalesce((g->>'adlar')::boolean,false) THEN
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('ad',okuma.satir(CASE x->>'tur' WHEN 'ETAP' THEN 'etaplar' WHEN 'IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->'ad')),'[]') INTO deger
  FROM jsonb_array_elements(deger) x;
 END IF;
 IF veri='PROJE' AND coalesce((g->>'ekip')::boolean,false) AND deger IS NOT NULL THEN
  -- Ana oku çağrısı proje görünürlüğünü denetledi. Yalnız güncel ek erişim listesi.
  deger=deger||jsonb_build_object('ek_erisim',coalesce((SELECT jsonb_agg(k) FROM okuma.satirlar('kisiler') WHERE k10.ek_erisim('OKUMA',k,hedef)),'[]'::jsonb));
 END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
