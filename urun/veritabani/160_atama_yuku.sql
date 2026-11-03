-- Tur 2.1: yalnız okuma; mevcut normal mesaiye göre dağıtım aynen kullanılır.
SET ROLE irp_sahibi;
CREATE FUNCTION okuma.atama_yuku(kim text,satirlar jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE s jsonb; paylar jsonb='[]'; p jsonb; weeks jsonb='[]'; warnings jsonb='[]'; w record; kisi text;
 bugun date=saat.gun(saat.kodla(saat.simdi())); geciken bigint; yetkili boolean;
BEGIN
 IF NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 SELECT EXISTS(SELECT FROM okuma.satirlar('birimler') WHERE yetki_v6.tablo_izni('OKUMA',kim,'GOREV.ATADIM',k)) INTO yetkili;
 IF NOT yetkili THEN RAISE EXCEPTION 'IRP|YETKI|Atama'; END IF;
 IF jsonb_typeof(satirlar) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'IRP|BICIM|Satirlar'; END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(satirlar) LOOP
  kisi=s->>'kisi';
  IF kisi IS NULL OR NOT yetki_v6.istihdamda('OKUMA',kisi,saat.simdi()) THEN RAISE EXCEPTION 'IRP|BICIM|Calisan'; END IF;
  IF kim=kisi OR NOT yetki_v6.tablo_izni('OKUMA',kim,'GOREV.ATADIM',okuma.satir('kisiler',kisi)->>'birim') THEN RAISE EXCEPTION 'IRP|YETKI|Atama kapsami'; END IF;
  IF s->>'teslim_tarihi' IS NULL OR coalesce((s->>'zaman_degeri')::numeric,0)<=0 THEN RAISE EXCEPTION 'IRP|BICIM|Teslim ve emek'; END IF;
  -- Önizlemeye eski görev kimliği/kapanış payı taşınmaz; hesap işlevi ortaktır.
  p=okuma.gorev_gunluk_paylar(jsonb_build_object('kisi',kisi,'atama_ani',saat.kodla(saat.simdi()),'teslim_tarihi',s->>'teslim_tarihi','zaman_degeri',s->'zaman_degeri'),true);
  IF jsonb_array_length(p)=0 THEN warnings=warnings||jsonb_build_array(jsonb_build_object('kisi',kisi,'dagitilamadi',true)); END IF;
  paylar=paylar||p;
 END LOOP;
 FOR w IN SELECT x->>'kisi' kisi,date_trunc('week',(x->>'gun')::date)::date bas,sum((x->>'saat')::numeric) yeni FROM jsonb_array_elements(paylar) x GROUP BY 1,2 ORDER BY 1,2 LOOP
  weeks=weeks||jsonb_build_array(jsonb_build_object('kisi',w.kisi,'bas',w.bas,'bit',w.bas+6,'yeni',w.yeni,
   'yuk',okuma.oku(kim,'YUK',w.kisi,jsonb_build_object('bas',w.bas,'bit',w.bas+6)),
   'kapasite',okuma.oku(kim,'KAPASITE',w.kisi,jsonb_build_object('bas',w.bas,'bit',w.bas+6))));
 END LOOP;
 FOR kisi IN SELECT DISTINCT x->>'kisi' FROM jsonb_array_elements(satirlar) x LOOP
  SELECT count(*) INTO geciken FROM okuma.satirlar('gorevler') WHERE x->>'kisi'=kisi AND x->>'tur' NOT IN ('ONAY','NOT') AND x->>'durum' NOT IN ('BITTI','IPTAL') AND (x->>'teslim_tarihi')::date<bugun AND okuma.gorebilir(kim,'GOREV',k);
  IF geciken>0 THEN warnings=warnings||jsonb_build_array(jsonb_build_object('kisi',kisi,'geciken',geciken)); END IF;
 END LOOP;
 RETURN jsonb_build_object('haftalar',weeks,'uyarilar',warnings);
END $$;
REVOKE ALL ON FUNCTION okuma.atama_yuku(text,jsonb) FROM PUBLIC,anon,authenticated,service_role;

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
 IF veri='ATAMA_YUKU' THEN deger=okuma.atama_yuku(kim,g->'satirlar');
 ELSIF veri='GOREV_AYRINTISI' THEN deger=okuma.gorev_ayrintisi(kim,hedef);
 ELSIF veri='WEB_KISI' THEN deger=okuma.web_kisi_ayrintisi(kim,hedef);
 ELSIF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 IF veri='WEB_BAGLAM' THEN
  deger=deger||jsonb_build_object('atama_adaylari',(SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') FROM okuma.satirlar('kisiler')
   WHERE k<>kim AND yetki_v6.istihdamda('OKUMA',k,saat.simdi()) AND coalesce((x->>'aktif')::boolean,true) AND yetki_v6.tablo_izni('OKUMA',kim,'GOREV.ATADIM',x->>'birim')));

  deger=deger||jsonb_build_object('sorumlu_adaylari',(SELECT jsonb_object_agg(kod,adaylar) FROM (
   SELECT kod,(SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') FROM okuma.satirlar('kisiler') WHERE yetki_v6.sorumlu_atayabilir('OKUMA',kim,k,kod)) adaylar
   FROM unnest(ARRAY['PROJE.ACTIM','PROJE.DEGISTIRDIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM']) kod) q));
 END IF;
 IF veri='PROJE_DURUM' AND deger IS NOT NULL THEN
  -- Ana okuma proje yetkisini denetledi. Etapsız emek proje toplamının içindedir.
  deger=deger||jsonb_build_object('etap_disi',jsonb_build_object('harcanan_emek',
   coalesce((SELECT sum(okuma.gorev_payi(x,'1900-01-01',saat.kodla(saat.simdi()))) FROM okuma.satirlar('gorevler') WHERE x->>'proje'=hedef AND nullif(x->>'etap','') IS NULL AND x->>'durum'<>'IPTAL'),0)
   +coalesce((SELECT sum(okuma.emek(k)/60) FROM okuma.satirlar('isler') WHERE x->>'proje'=hedef AND nullif(x->>'etap','') IS NULL AND x->>'durum'<>'IPTAL' AND coalesce((x->>'kisi_sayisi')::int,1)=1),0)));
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
