SET ROLE irp_sahibi;
-- Modelin bildirim kutusu eklenme sırasını korur; güncelleme sırayı değiştirmez.
ALTER TABLE public.modul_bildirimleri ADD COLUMN okuma_sira bigint GENERATED ALWAYS AS IDENTITY;
CREATE FUNCTION okuma.bildirim_kutusu(kisi text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; x jsonb; p text; uygun boolean; BEGIN
 IF cagiran IS NOT NULL AND cagiran IS DISTINCT FROM kisi THEN RAISE EXCEPTION 'IRP|YETKI|Bildirim kutusu aliciya aittir'; END IF;
 SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('bildirimler') WHERE x->>'alici'=kisi AND irp.dogru(x->'gecerli');
 FOR x IN SELECT hal FROM public.modul_bildirimleri WHERE hal->>'alici'=kisi AND irp.dogru(hal->'gecerli') ORDER BY okuma_sira LOOP
  uygun=yetki_v6.istihdamda('OKUMA',kisi,saat.simdi()) AND coalesce((okuma.satir('kisiler',kisi)->>'aktif')::boolean,true);
  FOREACH p IN ARRAY k9.bagli_projeler('OKUMA',x#>>'{kayit,tur}',x#>>'{kayit,kimlik}') LOOP uygun=uygun AND k9.proje_gorebilir('OKUMA',kisi,p); END LOOP;
  IF uygun THEN r=r||jsonb_build_array(x); END IF;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.surumler(nesne text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce(jsonb_agg(x ORDER BY (x->>'surum_no')::int),'[]') FROM okuma.satirlar('nesne_surumleri')
 WHERE x->>'nesne'=nesne AND (cagiran IS NULL OR okuma.surum_gorebilir(cagiran,x)) $$;
CREATE FUNCTION okuma.gecerli_surum(nesne text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; BEGIN
 IF cagiran IS NOT NULL AND NOT okuma.gorebilir(cagiran,'NESNE',nesne) THEN RETURN NULL; END IF;
 x=k10_1.gecerli('OKUMA',nesne); RETURN CASE WHEN cagiran IS NULL OR okuma.surum_gorebilir(cagiran,x) THEN x END; END $$;
CREATE FUNCTION okuma.surum_olayi_gorebilir(kim text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; BEGIN
 IF e->>'eylem_kodu' NOT LIKE 'NESNE.SURUM\_%' ESCAPE '\' THEN RETURN true; END IF;
 SELECT s.x INTO x FROM okuma.satirlar('nesne_surumleri') s WHERE s.x->>'nesne'=e#>>'{girdiler,hedef}'
 AND (s.x->>'doguran_olay'=e->>'olay_kimligi' OR s.x->'surum_no'=e#>'{girdiler,surum_no}') ORDER BY (s.x->>'surum_no')::int LIMIT 1;
 RETURN x IS NOT NULL AND okuma.surum_gorebilir(kim,x); END $$;
CREATE FUNCTION okuma.top_kimde(kimlik text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb=okuma.satir('nesneler',kimlik); s jsonb; sureler jsonb='{}'; BEGIN
 IF x IS NULL THEN RAISE EXCEPTION 'IRP|BICIM|Nesne'; END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(x->'asama_gecmisi') LOOP sureler=okuma.ekle(sureler,s->>'asama',extract(epoch FROM saat.an(s->>'bitis')-saat.an(s->>'baslangic'))/60); END LOOP;
 sureler=okuma.ekle(sureler,x->>'asama',extract(epoch FROM saat.simdi()-saat.an(x->>'asama_ani'))/60);
 RETURN jsonb_build_object('asama',x->'asama','sorumlu',x->'sorumlu','asama_ani',x->'asama_ani','asama_dakikalari',sureler); END $$;
CREATE FUNCTION okuma.plan_karsilastir(proje text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ss jsonb=coalesce(okuma.satir('plan_surumleri',proje),'[]'); b0 jsonb; son jsonb; guncel jsonb; sapma jsonb='{}'; gercek jsonb='{}'; k text; x jsonb; BEGIN
 b0=coalesce(ss->0->'etaplar','{}'); son=coalesce(ss->-1->'etaplar','{}');
 SELECT coalesce(jsonb_object_agg(k,jsonb_build_object('ad',x->'ad','birim',x->'birim','baslangic',x->'baslangic','bitis',x->'bitis','hedef_saat',x->'hedef_saat')),'{}') INTO guncel FROM okuma.satirlar('etaplar') WHERE x->>'proje'=proje;
 FOR k,x IN SELECT * FROM jsonb_each(guncel) LOOP
  gercek=gercek||jsonb_build_object(k,okuma.etap_gostergesi(k)); IF b0 ? k THEN sapma=sapma||jsonb_build_object(k,jsonb_build_object('bitis_gun',saat.gun(x->>'bitis')-saat.gun(b0->k->>'bitis'),'hedef_saat',(x->>'hedef_saat')::numeric-(b0->k->>'hedef_saat')::numeric)); END IF;
 END LOOP; RETURN jsonb_build_object('B0',b0,'son_onayli',son,'guncel',guncel,'onaysiz_degisti',ss<>'[]' AND guncel<>son,'sapma',sapma,'gerceklesen',gercek); END $$;
CREATE FUNCTION okuma.plan_cakismalari(kaynak jsonb,bas text,bit_ text DEFAULT NULL,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); aday jsonb='[]'; r jsonb='[]'; z record; x jsonb; y jsonb; hs jsonb; h jsonb; p timestamptz; q timestamptz; i int; j int; key text; tur text; BEGIN
 IF jsonb_typeof(kaynak)='string' THEN key=kaynak#>>'{}'; tur=CASE WHEN okuma.tablo('kisiler') ? key THEN 'KISI' ELSE 'TEZGAH' END;
 ELSE key=kaynak->>'kimlik'; tur=kaynak->>'tur'; END IF;
 IF cagiran IS NOT NULL AND NOT yetki_v6.istihdamda('OKUMA',cagiran,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 FOR z IN SELECT * FROM okuma.kaynak_satirlari(tur,key,bas,bit_) ORDER BY cins COLLATE "C",k COLLATE "C" LOOP aday=aday||jsonb_build_array(jsonb_build_object('tur',z.cins,'kimlik',z.k,'p',saat.kodla(z.p),'q',saat.kodla(z.q))); END LOOP;
 FOR i IN 0..jsonb_array_length(aday)-1 LOOP FOR j IN i+1..jsonb_array_length(aday)-1 LOOP
  x=aday->i; y=aday->j; p=greatest(ab[1],saat.an(x->>'p'),saat.an(y->>'p')); q=least(ab[2],saat.an(x->>'q'),saat.an(y->>'q'));
  IF p>=q THEN CONTINUE; END IF; hs='[]';
  FOR h IN SELECT value FROM jsonb_array_elements(jsonb_build_array(x,y)) LOOP hs=hs||jsonb_build_array(CASE WHEN cagiran IS NOT NULL AND NOT okuma.gorebilir(cagiran,h->>'tur',h->>'kimlik') THEN '{"tur":"ERISIM_DISI"}'::jsonb ELSE h-'p'-'q' END); END LOOP;
  r=r||jsonb_build_array(jsonb_build_object('hedefler',hs,'baslangic',saat.kodla(p),'bitis',saat.kodla(q)));
 END LOOP; END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.sapma(durum text,p timestamptz,q timestamptz,bas timestamptz,bit_ timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN IF durum='IPTAL' THEN RETURN NULL; END IF;
 IF bit_ IS NOT NULL AND q IS NOT NULL THEN RETURN jsonb_build_object('tur','BITIS','dakika',extract(epoch FROM bit_-q)/60); END IF;
 IF q<saat.simdi() THEN RETURN '{"tur":"GERIDE"}'; END IF;
 IF p<saat.simdi() AND bas IS NULL THEN RETURN '{"tur":"BASLAMADI"}'; END IF; RETURN NULL; END $$;
CREATE FUNCTION okuma.gantt_aralikta(x jsonb,a timestamptz,b timestamptz) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT coalesce(((x->>'planlanan_baslangic' IS NOT NULL OR x->>'planlanan_bitis' IS NOT NULL) AND greatest(a,coalesce(saat.an(x->>'planlanan_baslangic'),a))<least(b,coalesce(saat.an(x->>'planlanan_bitis'),b)))
 OR (x->>'gerceklesen_baslangic' IS NOT NULL AND greatest(a,saat.an(x->>'gerceklesen_baslangic'))<least(b,coalesce(saat.an(x->>'gerceklesen_bitis'),saat.simdi()))),false) $$;
CREATE FUNCTION okuma.gantt(proje text,bas text,bit_ text DEFAULT NULL,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); r jsonb='[]'; satirlar jsonb='[]'; z record; x jsonb; pq timestamptz[]; u timestamptz; v timestamptz; plan jsonb; alt jsonb; gorunen jsonb; etkin jsonb; s jsonb; p timestamptz; q timestamptz; durum text; BEGIN
 IF cagiran IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,proje) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
 FOR z IN SELECT * FROM (SELECT 'IS' AS tur,k,x FROM okuma.satirlar('isler') UNION ALL SELECT 'GOREV',k,x FROM okuma.satirlar('gorevler')) q0 ORDER BY tur DESC,k COLLATE "C" LOOP
  x=z.x; IF x->>'proje' IS DISTINCT FROM proje OR (cagiran IS NOT NULL AND NOT okuma.gorebilir(cagiran,z.tur,z.k)) THEN CONTINUE; END IF;
  pq=okuma.plan_araligi(z.tur,x);
  IF z.tur='IS' THEN SELECT min(saat.an(e->>'oldugu_an')) INTO u FROM jsonb_array_elements(okuma.tablo('olaylar')) e WHERE e->>'eylem_kodu'='IS.BASLADIM' AND NOT okuma.tablo('supheliler') ? (e->>'olay_kimligi') AND z.k=ANY(kapi.hedefler(e,'IS'));
  ELSE u=saat.an(coalesce(x->>'ilk_kabul_ani',x->>'kabul_ani')); END IF;
  v=CASE WHEN x->>'durum'='BITTI' THEN saat.an(x->>'bitis_ani') END;
  s=jsonb_build_object('tur',z.tur,'kimlik',z.k,'etap',x->'etap','tezgah',x->'tezgah','kisi',x->'kisi','planlanan_baslangic',saat.kodla(pq[1]),'planlanan_bitis',saat.kodla(pq[2]),'gerceklesen_baslangic',saat.kodla(u),'gerceklesen_bitis',saat.kodla(v),'durum',x->'durum','ilerleme',CASE WHEN x->>'durum'='BITTI' THEN 100 ELSE 0 END,'sapma',okuma.sapma(x->>'durum',pq[1],pq[2],u,v))||okuma.gecikme_olculeri(z.tur,x);
  satirlar=satirlar||jsonb_build_array(s);
 END LOOP;
 plan=coalesce(okuma.satir('plan_surumleri',proje)->-1->'etaplar','{}');
 FOR z IN SELECT k,x FROM okuma.satirlar('etaplar') WHERE x->>'proje'=proje ORDER BY k COLLATE "C" LOOP
  SELECT coalesce(jsonb_agg(x),'[]') INTO alt FROM jsonb_array_elements(satirlar) x WHERE x->>'etap'=z.k;
  SELECT coalesce(jsonb_agg(x),'[]') INTO gorunen FROM jsonb_array_elements(alt) x WHERE okuma.gantt_aralikta(x,ab[1],ab[2]);
  p=saat.an(plan->z.k->>'baslangic'); q=CASE WHEN plan ? z.k THEN saat.gun_ani(saat.gun(plan->z.k->>'bitis')+1) END;
  IF gorunen='[]' AND NOT coalesce(p IS NOT NULL AND greatest(ab[1],p)<least(ab[2],q),false) THEN CONTINUE; END IF;
  SELECT coalesce(jsonb_agg(x),'[]') INTO etkin FROM jsonb_array_elements(alt) x WHERE x->>'durum'<>'IPTAL';
  SELECT min(saat.an(x->>'gerceklesen_baslangic')),CASE WHEN bool_and(x->>'gerceklesen_bitis' IS NOT NULL) THEN max(saat.an(x->>'gerceklesen_bitis')) END,
  CASE WHEN bool_and(x->>'durum'='BITTI') THEN 'BITTI' ELSE 'ACIK' END INTO u,v,durum FROM jsonb_array_elements(etkin) x;
  s=jsonb_build_object('tur','ETAP','kimlik',z.k,'etap',NULL,'tezgah',NULL,'kisi',NULL,'planlanan_baslangic',saat.kodla(p),'planlanan_bitis',saat.kodla(q),'gerceklesen_baslangic',saat.kodla(u),'gerceklesen_bitis',saat.kodla(v),'durum',durum,'ilerleme',okuma.etap_gostergesi(z.k)->'yuzde','sapma',okuma.sapma(durum,p,q,u,v),'gecikme_takvim_dk',NULL,'gecikme_mesai_dk',NULL);
  r=r||jsonb_build_array(s)||gorunen;
 END LOOP;
 SELECT r||coalesce(jsonb_agg(x),'[]') INTO r FROM jsonb_array_elements(satirlar) x WHERE NOT coalesce(okuma.tablo('etaplar') ? (x->>'etap'),false) AND okuma.gantt_aralikta(x,ab[1],ab[2]);
 RETURN r; END $$;
RESET ROLE;
