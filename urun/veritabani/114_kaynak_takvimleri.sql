SET ROLE irp_sahibi;
CREATE FUNCTION okuma.kirp(xs jsonb,a timestamptz,b timestamptz) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_array(saat.kodla(greatest(a,saat.an(x->>0))),saat.kodla(least(b,saat.an(x->>1))))),'[]')
 FROM jsonb_array_elements(xs) x WHERE greatest(a,saat.an(x->>0))<least(b,saat.an(x->>1)) $$;
CREATE FUNCTION okuma.tezgah_calisma_pencereleri(tezgah text,tarih date) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; v jsonb; r jsonb='[]'; ab jsonb; a timestamptz=saat.gun_ani(tarih); b timestamptz=saat.gun_ani(tarih+1); BEGIN
 SELECT s.x INTO x FROM okuma.satirlar('tezgah_takvimleri') s WHERE s.x->>'tezgah'=tezgah AND saat.gun(s.x->>'gecerli_baslangic')<=tarih ORDER BY s.x->>'gecerli_baslangic' DESC,s.x->>'kimlik' COLLATE "C" DESC LIMIT 1;
 IF x IS NULL THEN r=takvim.normal('OKUMA',tarih,true,NULL,okuma.satir('tezgahlar',tezgah)->>'birim');
 ELSE FOR v IN SELECT value FROM jsonb_array_elements(x->'vardiyalar') WHERE value->'gunler' @> to_jsonb(extract(isodow FROM tarih)::int) LOOP r=r||jsonb_build_array(jsonb_build_array(saat.kodla(saat.gun_ani(tarih,v->>'bas')),saat.kodla(saat.gun_ani(tarih,v->>'bit')))); END LOOP; END IF;
 FOR x IN SELECT s.x FROM okuma.satirlar('ek_mesai_planlari') s WHERE NOT irp.dogru(s.x->'iptal') LOOP
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(x->'hedef') h WHERE h->>'tur'='IS' AND okuma.satir('isler',h->>'kimlik')->>'tezgah'=tezgah) THEN CONTINUE; END IF;
  r=r||okuma.kirp(jsonb_build_array(takvim.pencere(x)),a,b);
 END LOOP; RETURN takvim.birlesim(r); END $$;
CREATE FUNCTION okuma.tezgah_planli_araliklar(tezgah text,a timestamptz,b timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; eng jsonb; t date; BEGIN
 IF NOT coalesce(okuma.tablo('tezgahlar') ? tezgah,false) OR a>=b THEN RAISE EXCEPTION 'IRP|BICIM|Tezgah/aralik'; END IF;
 FOR t IN SELECT okuma.gunler(saat.kodla(a),saat.kodla(b-interval '1 microsecond')) LOOP r=r||okuma.kirp(okuma.tezgah_calisma_pencereleri(tezgah,t),a,b); END LOOP;
 SELECT coalesce(jsonb_agg(jsonb_build_array(x->'baslangic',x->'bitis')),'[]') INTO eng FROM okuma.satirlar('bakimlar') WHERE x->>'tezgah'=tezgah AND NOT irp.dogru(x->'iptal');
 RETURN takvim.cikar(r,eng); END $$;
CREATE FUNCTION okuma.tezgah_engelleri(tezgah text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_array(x->'baslangic',coalesce(nullif(x->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))),x->'neden')),'[]')
 FROM (SELECT x FROM okuma.satirlar('tezgah_duruslari') WHERE x->>'tezgah'=tezgah UNION ALL
 SELECT x FROM okuma.satirlar('duruslar') WHERE takvim.birim_kapsamda('OKUMA',okuma.satir('tezgahlar',tezgah)->>'birim',x->'kapsam')) s $$;
CREATE FUNCTION okuma.tezgah_uygun_mu(tezgah text,bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a timestamptz=saat.an(bas); b timestamptz=saat.an(bit_); dis jsonb; BEGIN
 IF NOT coalesce(okuma.tablo('tezgahlar') ? tezgah,false) OR a>=b THEN RAISE EXCEPTION 'IRP|BICIM|Tezgah/aralik'; END IF;
 IF EXISTS(SELECT FROM okuma.satirlar('bakimlar') WHERE x->>'tezgah'=tezgah AND NOT irp.dogru(x->'iptal') AND greatest(a,saat.an(x->>'baslangic'))<least(b,saat.an(x->>'bitis'))) THEN RETURN '{"uygun":false,"neden":"bakim"}'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(okuma.tezgah_engelleri(tezgah)) x WHERE greatest(a,saat.an(x->>0))<least(b,saat.an(x->>1))) THEN RETURN '{"uygun":false,"neden":"durus"}'; END IF;
 dis=takvim.cikar(jsonb_build_array(jsonb_build_array(bas,bit_)),okuma.tezgah_planli_araliklar(tezgah,a,b));
 RETURN jsonb_build_object('uygun',dis='[]','neden',CASE WHEN dis<>'[]' THEN 'vardiya disi' END); END $$;
CREATE FUNCTION okuma.kisi_uygun_mu(kisi text,bas text,bit_ text,cagiran text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a timestamptz=saat.an(bas); b timestamptz=saat.an(bit_); t date; x jsonb; izinli jsonb='[]'; dis jsonb; BEGIN
 IF a>=b THEN RAISE EXCEPTION 'IRP|BICIM|Aralik'; END IF;
 IF NOT okuma.gorebilir(cagiran,'UYGUNLUK') THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 FOR t IN SELECT okuma.gunler(bas,saat.kodla(b-interval '1 microsecond')) LOOP IF NOT yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(t)) THEN RETURN '{"uygun":false,"neden":"istihdam disi"}'; END IF; END LOOP;
 FOR x IN SELECT s.x FROM okuma.satirlar('izinler') s WHERE s.x->>'kisi'=kisi AND s.x->>'durum'='ONAYLI' LOOP
  IF greatest(a,saat.an(x->>'baslangic'))<least(b,saat.an(x->>'bitis')) THEN RETURN jsonb_build_object('uygun',false,'neden',CASE WHEN okuma.gorebilir(cagiran,'IZIN_DETAY',kisi) THEN 'izin ('||(x->>'tur')||')' ELSE 'musait degil' END); END IF;
 END LOOP;
 FOR t IN SELECT okuma.gunler(bas,bit_) LOOP izinli=izinli||takvim.normal('OKUMA',t,false,kisi)||takvim.ekler('OKUMA',kisi,t); END LOOP;
 dis=takvim.cikar(jsonb_build_array(jsonb_build_array(bas,bit_)),izinli);
 RETURN jsonb_build_object('uygun',dis='[]','neden',CASE WHEN dis<>'[]' THEN 'takvim' END); END $$;
CREATE FUNCTION okuma.tezgah_gostergesi(tezgah text,bas text,bit_ text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); payda numeric; nedenler jsonb='{}'; x jsonb; n text; xs jsonb; gercek numeric; bekleme numeric; BEGIN
 payda=okuma.saatler(okuma.tezgah_planli_araliklar(tezgah,ab[1],ab[2]));
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.tezgah_engelleri(tezgah)) LOOP
  xs=okuma.kirp(jsonb_build_array(x),ab[1],ab[2]); IF xs='[]' THEN CONTINUE; END IF;
  n=coalesce(x->>2,'None'); nedenler=nedenler||jsonb_build_object(n,coalesce(nedenler->n,'[]')||xs);
 END LOOP;
 FOR n,xs IN SELECT * FROM jsonb_each(nedenler) LOOP nedenler=nedenler||jsonb_build_object(n,okuma.saatler(xs)); END LOOP;
 SELECT coalesce(sum(extract(epoch FROM least(ab[2],coalesce(saat.an(x->>'bitis'),saat.simdi()))-greatest(ab[1],saat.an(x->>'baslangic')))/3600),0) INTO gercek FROM jsonb_array_elements(okuma.tablo('araliklar')) x
 WHERE x->>'tezgah'=tezgah AND x->>'kova'='TEZGAH' AND greatest(ab[1],saat.an(x->>'baslangic'))<least(ab[2],coalesce(saat.an(x->>'bitis'),saat.simdi()));
 SELECT coalesce(sum(extract(epoch FROM least(ab[2],saat.an(x->>'bitis_ani'))-greatest(ab[1],saat.an(x->>'makine_bitis_ani')))/60),0) INTO bekleme FROM okuma.satirlar('isler')
 WHERE x->>'tezgah'=tezgah AND x->>'makine_bitis_ani' IS NOT NULL AND greatest(ab[1],saat.an(x->>'makine_bitis_ani'))<least(ab[2],saat.an(x->>'bitis_ani'));
 RETURN jsonb_build_object('bitti_alinmayi_bekledi_dk',bekleme,'planli_kullanilabilir',payda,'gerceklesen',gercek,'durus',nedenler,'kullanim_orani',CASE WHEN payda<>0 THEN gercek/payda END); END $$;
CREATE FUNCTION okuma.takvim(kim text,tur text,key text,bas text,bit_ text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); t date; u timestamptz; v timestamptz; xs jsonb; calisma jsonb='[]'; kapali jsonb='{}'; eng jsonb='[]'; sonuc jsonb='[]'; neden text; b text; x jsonb; ar jsonb;
 tablo text=CASE tur WHEN 'KISI' THEN 'kisiler' WHEN 'BIRIM' THEN 'birimler' WHEN 'TEZGAH' THEN 'tezgahlar' END; BEGIN
 IF tablo IS NULL OR NOT coalesce(okuma.tablo(tablo) ? key,false) THEN RAISE EXCEPTION 'IRP|BICIM|Takvim turu veya kimligi'; END IF;
 FOR t IN SELECT okuma.gunler(bas,saat.kodla(ab[2]-interval '1 microsecond')) LOOP
  u=greatest(ab[1],saat.gun_ani(t)); v=least(ab[2],saat.gun_ani(t+1));
  xs=CASE WHEN tur='TEZGAH' THEN okuma.tezgah_calisma_pencereleri(key,t) WHEN tur='BIRIM' THEN takvim.normal('OKUMA',t,true,NULL,key)
   WHEN yetki_v6.istihdamda('OKUMA',key,saat.gun_ani(t)) THEN takvim.normal('OKUMA',t,true,key)||takvim.ekler('OKUMA',key,t) ELSE '[]'::jsonb END;
  xs=okuma.kirp(xs,u,v); calisma=calisma||xs;
  neden=CASE WHEN okuma.tablo('tatiller') ? t::text THEN 'TATIL' WHEN tur='TEZGAH' THEN 'VARDIYA_DISI' ELSE 'MESAI_DISI' END;
  kapali=kapali||jsonb_build_object(neden,coalesce(kapali->neden,'[]')||takvim.cikar(jsonb_build_array(jsonb_build_array(saat.kodla(u),saat.kodla(v))),xs));
 END LOOP;
 IF tur='KISI' THEN
  neden=CASE WHEN okuma.gorebilir(kim,'IZIN_DETAY',key) THEN 'IZIN' ELSE 'MUSAIT_DEGIL' END;
  kapali=kapali||jsonb_build_object(neden,okuma.kirp(takvim.izinler('OKUMA',key),ab[1],ab[2]));
 END IF;
 IF tur='TEZGAH' THEN
  SELECT coalesce(jsonb_agg(jsonb_build_array(x->'baslangic',x->'bitis')),'[]') INTO xs FROM okuma.satirlar('bakimlar') WHERE x->>'tezgah'=key AND NOT irp.dogru(x->'iptal');
  kapali=kapali||jsonb_build_object('BAKIM',okuma.kirp(xs,ab[1],ab[2]),'DURUS',okuma.kirp(okuma.tezgah_engelleri(key),ab[1],ab[2]));
 ELSE
  b=CASE WHEN tur='BIRIM' THEN key ELSE okuma.satir('kisiler',key)->>'birim' END;
  SELECT coalesce(jsonb_agg(jsonb_build_array(x->'baslangic',coalesce(nullif(x->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))))),'[]') INTO xs FROM okuma.satirlar('duruslar') WHERE takvim.birim_kapsamda('OKUMA',b,x->'kapsam');
  kapali=kapali||jsonb_build_object('DURUS',okuma.kirp(xs,ab[1],ab[2]));
 END IF;
 FOR neden,xs IN SELECT * FROM jsonb_each(kapali) LOOP
  eng=eng||xs; FOR ar IN SELECT value FROM jsonb_array_elements(takvim.birlesim(xs)) LOOP sonuc=sonuc||jsonb_build_array(jsonb_build_object('bas',ar->0,'bit',ar->1,'neden',neden)); END LOOP;
 END LOOP;
 SELECT coalesce(jsonb_agg(jsonb_build_object('bas',x->0,'bit',x->1)),'[]') INTO calisma FROM jsonb_array_elements(takvim.cikar(takvim.birlesim(calisma),eng)) x;
 SELECT coalesce(jsonb_agg(x ORDER BY x->>'bas',x->>'bit',x->>'neden' COLLATE "C"),'[]') INTO sonuc FROM jsonb_array_elements(sonuc) x;
 RETURN jsonb_build_object('calisma',calisma,'kapali',sonuc); END $$;
CREATE FUNCTION okuma.plan_araligi(tur text,x jsonb) RETURNS timestamptz[] LANGUAGE sql STABLE AS $$
 SELECT ARRAY[saat.an(x->>'planlanan_baslangic'),coalesce(saat.an(x->>'planlanan_bitis'),CASE WHEN tur='GOREV' THEN gorev.son_teslim_ani(x,'OKUMA') END)] $$;
CREATE FUNCTION okuma.kaynak_satirlari(tur text,key text,bas text,bit_ text DEFAULT NULL) RETURNS TABLE(cins text,k text,x jsonb,p timestamptz,q timestamptz) LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); z record; pq timestamptz[]; ait boolean; BEGIN
 IF tur NOT IN ('KISI','TEZGAH') OR NOT coalesce(okuma.tablo(CASE WHEN tur='KISI' THEN 'kisiler' ELSE 'tezgahlar' END) ? key,false) THEN RAISE EXCEPTION 'IRP|BICIM|Kaynak turu veya kimligi'; END IF;
 FOR z IN SELECT * FROM (SELECT 'IS' AS cins,s.k,s.x FROM okuma.satirlar('isler') s UNION ALL SELECT 'GOREV',s.k,s.x FROM okuma.satirlar('gorevler') s) q0 ORDER BY cins DESC,k COLLATE "C" LOOP
  IF z.x->>'durum' IN ('BITTI','IPTAL') THEN CONTINUE; END IF;
  ait=CASE WHEN tur='KISI' THEN CASE WHEN z.cins='IS' THEN coalesce(okuma.satir('listeler',key),'[]') ? z.k ELSE z.x->>'kisi'=key END ELSE z.cins='IS' AND z.x->>'tezgah'=key END;
  pq=okuma.plan_araligi(z.cins,z.x);
  IF ait AND pq[1] IS NOT NULL AND pq[2] IS NOT NULL AND greatest(ab[1],pq[1])<least(ab[2],pq[2]) THEN cins=z.cins; k=z.k; x=z.x; p=pq[1]; q=pq[2]; RETURN NEXT; END IF;
 END LOOP; END $$;
CREATE FUNCTION okuma.kaynak_yuku(kim text,tur text,key text,bas text,bit_ text DEFAULT NULL,kapasite_dahil boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; z record; a jsonb; ab timestamptz[]; BEGIN
 FOR z IN SELECT * FROM okuma.kaynak_satirlari(tur,key,bas,bit_) LOOP
  IF tur='KISI' AND NOT okuma.temel_gorebilir(kim,'IS',key) THEN a=jsonb_build_object('durum','MESGUL','bas',saat.kodla(z.p),'bit',saat.kodla(z.q));
  ELSIF z.x->>'proje' IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',kim,z.x->>'proje') THEN a=jsonb_build_object('proje','ERISIM_DISI','planlanan_baslangic',saat.kodla(z.p),'planlanan_bitis',saat.kodla(z.q));
  ELSE a=jsonb_build_object('tur',z.cins,'kimlik',z.k,'ad',coalesce(z.x->'ad',z.x->'islem'),'proje',z.x->'proje','planlanan_baslangic',saat.kodla(z.p),'planlanan_bitis',saat.kodla(z.q),'durum',z.x->'durum'); END IF;
  r=r||jsonb_build_array(a);
 END LOOP;
 IF kapasite_dahil THEN IF tur<>'TEZGAH' THEN RAISE EXCEPTION 'IRP|BICIM|Kapasite ozeti TEZGAH icindir'; END IF;
  ab=okuma.pencere(bas,bit_); RETURN jsonb_build_object('satirlar',r,'planli_kullanilabilir',okuma.saatler(okuma.tezgah_planli_araliklar(key,ab[1],ab[2]))); END IF;
 RETURN r; END $$;
CREATE FUNCTION okuma.gecikme_olculeri(tur text,x jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE son timestamptz; b timestamptz; BEGIN
 son=coalesce(CASE WHEN tur='GOREV' THEN gorev.son_teslim_ani(x,'OKUMA') END,saat.an(x->>'planlanan_bitis'));
 IF son IS NULL OR x->>'durum'='IPTAL' THEN RETURN '{"gecikme_takvim_dk":null,"gecikme_mesai_dk":null}'; END IF;
 b=CASE WHEN x->>'durum'='BITTI' AND x->>'bitis_ani' IS NOT NULL THEN saat.an(x->>'bitis_ani') ELSE saat.simdi() END;
 RETURN jsonb_build_object('gecikme_takvim_dk',greatest(0,extract(epoch FROM b-son)/60),'gecikme_mesai_dk',60*okuma.kapasite_araligi(x->>'kisi',son,b,x->>'birim')); END $$;
RESET ROLE;
