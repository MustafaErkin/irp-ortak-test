SET ROLE irp_sahibi;
CREATE FUNCTION okuma.gecikme_satirlari(bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; hedef text; h jsonb; g jsonb; e jsonb; ev jsonb; neden text; baslik text; dakika numeric; ss jsonb; x jsonb; olcu jsonb; pay numeric; etkin boolean; BEGIN
 FOR hedef IN SELECT k FROM okuma.satirlar('gorevler') WHERE x->>'ilk_teslim_ani' IS NOT NULL UNION SELECT e->>'olay_kimligi' FROM jsonb_array_elements(okuma.tablo('olaylar')) e WHERE e->>'eylem_kodu'='IS.ARIZA_BILDIRDIM' ORDER BY 1 LOOP
  h=NULL; g=okuma.satir('gorevler',hedef);
  IF g->>'tur' IN ('NORMAL','DEGISIKLIK') AND saat.an(g->>'ilk_teslim_ani')>gorev.son_teslim_ani(g,'OKUMA') THEN h=jsonb_build_object('tur','GOREV','kisi',g->'kisi','birim',okuma.satir('kisiler',g->>'kisi')->'birim','proje',g->'proje','an',g->'ilk_teslim_ani','zaman_degeri',g->'zaman_degeri'); END IF;
  SELECT a INTO e FROM jsonb_array_elements(okuma.tablo('olaylar')) a WHERE a->>'olay_kimligi'=hedef AND a->>'eylem_kodu'='IS.ARIZA_BILDIRDIM' LIMIT 1;
  IF h IS NULL AND e IS NOT NULL AND NOT okuma.tablo('supheliler') ? hedef THEN
   x=okuma.satir('isler',(kapi.hedefler(e,'IS'))[1]); h=jsonb_build_object('tur','DURUS','kisi',coalesce(e->>'adina',e->>'kim'),'birim',x->'birim','proje',x->'proje','an',e->'oldugu_an','zaman_degeri',0);
  END IF;
  IF h IS NULL OR saat.gun(h->>'an') NOT BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN CONTINUE; END IF;
  ev=okuma.son_degerlendirme(hedef); neden=coalesce(ev->>'neden',CASE WHEN h->>'tur'='GOREV' THEN coalesce(g->>'gecikme_nedeni','GIRILMEDI') ELSE coalesce(e#>>'{girdiler,neden}','BELIRTILMEDI') END);
  baslik=coalesce(okuma.satir('kod_listesi','DURUS_NEDENI:'||regexp_replace(neden,'^DURUS_NEDENI\.',''))->>'ust',CASE WHEN neden LIKE 'ARIZA.%' THEN 'ESKI_ARIZA' ELSE 'GIRILMEDI' END);
  SELECT coalesce(sum(extract(epoch FROM coalesce(saat.an(a->>'bitis'),saat.simdi())-saat.an(a->>'baslangic'))/60),0) INTO dakika FROM jsonb_array_elements(okuma.tablo('araliklar')) a WHERE a->>'kova'='BEKLEME_ARIZA' AND a->>'acan_olay'=hedef;
  SELECT coalesce(jsonb_agg(x),'[]') INTO ss FROM okuma.satirlar('sorumluluklar') WHERE ev IS NOT NULL AND x->>'ret'=ev->>'kimlik';
  IF ss='[]' THEN ss=jsonb_build_array(jsonb_build_object('tur','KISI','kimlik',h->'kisi','yuzde',100,'dogrulandi',false,'itirazda',false)); END IF;
  olcu=CASE WHEN h->>'tur'='GOREV' THEN okuma.gecikme_olculeri('GOREV',g) ELSE '{"gecikme_takvim_dk":0,"gecikme_mesai_dk":0}'::jsonb END;
  FOR x IN SELECT value FROM jsonb_array_elements(ss) LOOP
   etkin=okuma.etkin_pay(x); pay=(x->>'yuzde')::numeric/100;
   r=r||jsonb_build_array(h||jsonb_build_object('hedef',hedef,'neden',neden,'baslik',baslik,'sorumlu_turu',x->'tur','sorumlu',x->'kimlik','yuzde',x->'yuzde','degerlendirildi',ev IS NOT NULL,'dogrulandi',etkin,'itirazda',x->'itirazda',
    'durus_dk',dakika*pay,'gec_teslim',CASE WHEN h->>'tur'='GOREV' THEN pay ELSE 0 END,'gecikme_saati',(h->>'zaman_degeri')::numeric*pay,
    'gecikme_takvim_dk',coalesce((olcu->>'gecikme_takvim_dk')::numeric,0)*pay,'gecikme_mesai_dk',coalesce((olcu->>'gecikme_mesai_dk')::numeric,0)*pay,
    'sebep_olunan_bekleme_dk',CASE WHEN etkin AND NOT irp.dogru(x->'itirazda') THEN dakika*pay ELSE 0 END,
    'sebep_olunan_gecikme',CASE WHEN etkin AND NOT irp.dogru(x->'itirazda') AND x->>'kimlik'<>h->>'kisi' THEN (h->>'zaman_degeri')::numeric*pay ELSE 0 END));
  END LOOP;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.gecikme_raporu(bas text,bit_ text,kirilim text DEFAULT 'sorumlu',cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; sira text[]='{}'; x jsonb; s jsonb; key text; kimlik text; a text; izin boolean; BEGIN
 IF kirilim NOT IN ('baslik','neden','sorumlu','proje','birim','kisi') THEN RAISE EXCEPTION 'IRP|BICIM|Gecikme kirilimi'; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.gecikme_satirlari(bas,bit_)) LOOP
  IF cagiran IS NOT NULL THEN
   izin=CASE WHEN x->>'sorumlu_turu'='KISI' THEN okuma.gorebilir(cagiran,'PERFORMANS',x->>'sorumlu') ELSE okuma.gorebilir(cagiran,'BIRIM_PERFORMANS',x->>'birim') END;
   IF NOT izin OR (x->>'proje' IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,x->>'proje')) THEN CONTINUE; END IF;
  END IF;
  kimlik=CASE WHEN kirilim='sorumlu' THEN (x->>'sorumlu_turu')||':'||(x->>'sorumlu') ELSE x->>kirilim END;
  key=jsonb_build_array(kimlik,x->'degerlendirildi',x->'dogrulandi',x->'itirazda',x->'neden')::text;
  IF NOT r ? key THEN sira=array_append(sira,key); END IF;
  s=coalesce(r->key,jsonb_build_object('kimlik',kimlik,'degerlendirildi',x->'degerlendirildi','dogrulandi',x->'dogrulandi','itirazda',x->'itirazda','neden',x->'neden','durus_dk',0,'gec_teslim',0,'zaman_degeri',0,'sebep_olunan_bekleme_dk',0,'sebep_olunan_gecikme',0,'gecikme_takvim_dk',0,'gecikme_mesai_dk',0));
  FOREACH a IN ARRAY ARRAY['durus_dk','gec_teslim','sebep_olunan_bekleme_dk','sebep_olunan_gecikme','gecikme_takvim_dk','gecikme_mesai_dk'] LOOP s=okuma.ekle(s,a,(x->>a)::numeric); END LOOP;
  s=okuma.ekle(s,'zaman_degeri',(x->>'gecikme_saati')::numeric); r=r||jsonb_build_object(key,s);
 END LOOP; RETURN (SELECT coalesce(jsonb_agg(r->k ORDER BY n),'[]') FROM unnest(sira) WITH ORDINALITY a(k,n)); END $$;
CREATE FUNCTION okuma.sorumluluk_ekleri(kisi text,bas text,bit_ text,tur text DEFAULT 'KISI') RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kalite numeric; gec numeric; bek numeric; BEGIN
 IF okuma.tablo('gecikme_degerlendirmeleri')='{}' AND NOT EXISTS(SELECT FROM okuma.satirlar('sorumluluklar') WHERE x->>'kaynak_turu'='DEGISIKLIK') THEN RETURN '{"kalite_ret":0,"sebep_olunan_gecikme":0,"sebep_olunan_bekleme_dk":0}'; END IF;
 SELECT coalesce(sum((x->>'yuzde')::numeric/100),0) INTO kalite FROM okuma.satirlar('sorumluluklar') WHERE x->>'kaynak_turu'='DEGISIKLIK' AND x->>'tur'=tur AND x->>'kimlik'=kisi AND irp.dogru(x->'dogrulandi') AND NOT irp.dogru(x->'itirazda') AND saat.gun(x->>'an') BETWEEN saat.gun(bas) AND saat.gun(bit_);
 SELECT coalesce(sum((x->>'sebep_olunan_gecikme')::numeric),0),coalesce(sum((x->>'sebep_olunan_bekleme_dk')::numeric),0) INTO gec,bek FROM jsonb_array_elements(okuma.gecikme_satirlari(bas,bit_)) x WHERE x->>'sorumlu_turu'=tur AND x->>'sorumlu'=kisi;
 RETURN jsonb_build_object('kalite_ret',kalite,'sebep_olunan_gecikme',gec,'sebep_olunan_bekleme_dk',bek); END $$;
CREATE FUNCTION okuma.degisiklik_gez(k text,tablo jsonb,gezilen jsonb DEFAULT '[]') RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x text; BEGIN IF gezilen ? k THEN RETURN gezilen; END IF; gezilen=gezilen||jsonb_build_array(k);
 FOR x IN SELECT key FROM jsonb_each(tablo) WHERE value->>'degisiklik_kaynagi'=k ORDER BY key COLLATE "C" LOOP gezilen=okuma.degisiklik_gez(x,tablo,gezilen); END LOOP; RETURN gezilen; END $$;
CREATE FUNCTION okuma.degisiklik_gecmisi(kaynak text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE tablo jsonb=okuma.tablo('isler')||okuma.tablo('gorevler'); p text; BEGIN
 IF NOT tablo ? kaynak THEN RAISE EXCEPTION 'IRP|BICIM|Kaynak yok'; END IF; p=tablo->kaynak->>'proje';
 IF cagiran IS NOT NULL AND p IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,p) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
 RETURN okuma.degisiklik_gez(kaynak,tablo); END $$;
CREATE FUNCTION okuma.proje_erisim_gecmisi(proje text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; e jsonb; hedef text; BEGIN
 IF cagiran IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,proje) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
 SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('proje_erisimleri') WHERE x->>'proje'=proje;
 FOR e IN SELECT value FROM jsonb_array_elements(okuma.tablo('olaylar')) WHERE value->>'eylem_kodu' IN ('ETAP.TANIMLADIM','ETAP.DEGISTIRDIM') LOOP
  hedef=CASE WHEN e->>'eylem_kodu'='ETAP.TANIMLADIM' THEN e->>'olay_kimligi' ELSE (kapi.hedefler(e,'ETAP'))[1] END;
  IF okuma.satir('etaplar',hedef)->>'proje'=proje THEN r=r||jsonb_build_array(jsonb_build_object('kimlik',e->'olay_kimligi','an',e->'oldugu_an','yazan',e->'kim','proje',proje,'etap',hedef,'eylem',e->'eylem_kodu','girdiler',e->'girdiler')); END IF;
 END LOOP; RETURN (SELECT coalesce(jsonb_agg(x ORDER BY x->>'an',x->>'kimlik' COLLATE "C"),'[]') FROM jsonb_array_elements(r) x); END $$;
CREATE FUNCTION okuma.proje_degisiklikleri(proje text,bas text,bit_ text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; x jsonb; e jsonb; s jsonb; a jsonb; neden text; t date; k text; sa numeric; oran numeric; tutar numeric; at numeric; BEGIN
 IF cagiran IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,proje) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
 FOR x IN SELECT z.x FROM okuma.satirlar('gorevler') z UNION ALL SELECT z.x FROM okuma.satirlar('isler') z LOOP
  IF x->>'proje' IS DISTINCT FROM proje OR x->>'degisiklik_kaynagi' IS NULL THEN CONTINUE; END IF;
  SELECT value INTO e FROM jsonb_array_elements(okuma.tablo('olaylar')) WHERE value->>'olay_kimligi'=x->>'doguran_olay' LIMIT 1;
  IF saat.gun(e->>'oldugu_an') NOT BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN CONTINUE; END IF;
  neden=x#>>'{degisiklik,neden}'; s=coalesce(r->neden,'{"is_sayisi":0,"zaman_degeri":0,"atolye_saati":0,"maliyet":0}'); s=okuma.ekle(s,'is_sayisi',1);
  tutar=CASE WHEN s->>'maliyet'='VERI_EKSIK' THEN NULL ELSE (s->>'maliyet')::numeric END; at=0;
  IF okuma.tablo('gorevler') ? (x->>'kimlik') THEN
   s=okuma.ekle(s,'zaman_degeri',(x->>'zaman_degeri')::numeric);
   FOR t IN SELECT okuma.gunler(bas,bit_) LOOP FOR k IN SELECT x->>'kisi' UNION SELECT h->>'kisi' FROM jsonb_array_elements(coalesce(x->'kisi_gecmisi','[]')) h LOOP
    sa=okuma.gorev_payi(x,t::text,t::text,false,k); IF sa<>0 THEN tutar=tutar+sa*okuma.saat_maliyeti(k,t::text); END IF;
   END LOOP; END LOOP;
  ELSE
   FOR a IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) WHERE value->>'is'=x->>'kimlik' AND value->>'kisi' IS NOT NULL AND saat.gun(value->>'gun') BETWEEN saat.gun(bas) AND saat.gun(bit_) AND value->>'kova' IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') LOOP
    sa=extract(epoch FROM coalesce(saat.an(a->>'bitis'),saat.simdi())-saat.an(a->>'baslangic'))/3600; IF a->>'kova' IN ('CALISMA','YENIDEN_ISLEME') THEN at=at+sa; END IF;
    IF sa<>0 THEN tutar=tutar+sa*okuma.saat_maliyeti(a->>'kisi',a->>'gun'); END IF;
   END LOOP;
  END IF;
  s=okuma.ekle(s,'atolye_saati',at)||jsonb_build_object('maliyet',coalesce(to_jsonb(tutar),'"VERI_EKSIK"')); r=r||jsonb_build_object(neden,s);
 END LOOP;
 FOR neden,s IN SELECT * FROM jsonb_each(r) LOOP
  IF cagiran IS NULL OR NOT okuma.gorebilir(cagiran,'TUTAR') THEN s=s-'maliyet'; ELSIF s->>'maliyet'<>'VERI_EKSIK' THEN s=s||jsonb_build_object('maliyet',okuma.para((s->>'maliyet')::numeric)); END IF; r=r||jsonb_build_object(neden,s);
 END LOOP; RETURN r; END $$;
RESET ROLE;
