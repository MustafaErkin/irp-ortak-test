SET ROLE irp_sahibi;
-- kisi_gunu.py:11 bos_hal; 15 kapi; 39 gecis. Saf geçiş JSON döndürür.
CREATE FUNCTION kg.bos_hal() RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT '{"durum":"MESAI_DISI","kova":null,"acik_is":null,"aralik_is":null,"neden":null,"onceki_kova":"CALISMA","devam_izni":false,"mola_onceki":null,"baslangic":null,"acan_olay":null,"acan_kural":null,"son_olay_ani":null}'::jsonb $$;
CREATE FUNCTION kg.kapi(d jsonb,kod text,i jsonb,bas text,sabit boolean DEFAULT false) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE durum text=(d->>'durum'); ayni boolean=(d->>'acik_is')=(i->>'kimlik'); BEGIN
 IF sabit AND irp.sabit('calisan') ? kod THEN RETURN false; END IF;
 IF kod='MESAI.GIRDIM' THEN RETURN durum='MESAI_DISI'; ELSIF kod='MESAI.CIKTIM' THEN RETURN durum<>'MESAI_DISI'; END IF;
 IF NOT irp.dogru(i) THEN RETURN false; END IF;
 RETURN coalesce(CASE kod
 WHEN 'IS.BASLADIM' THEN durum='CALISMIYOR' AND bas=(i->>'kimlik') AND (i->>'tur')='SURELI' AND (i->>'durum') IN ('SIRADA','YARIM') AND NOT irp.dogru((i->'kilitli'))
 WHEN 'IS.MOLA_VERDIM' THEN durum='CALISIYOR' AND ayni
 WHEN 'IS.ARIZA_BILDIRDIM' THEN (durum='CALISIYOR' AND ayni) OR ((i->>'tur')='ANLIK' AND bas=(i->>'kimlik') AND durum<>'MESAI_DISI')
 WHEN 'IS.DEVAM_ETTIM' THEN (i->>'durum')<>'BITTI' AND ((ayni AND (durum IN ('MOLADA','DEVAM_BEKLIYOR') OR (durum='ARIZADA' AND irp.dogru((d->'devam_izni'))))) OR (durum='CALISMIYOR' AND bas=(i->>'kimlik') AND (i->>'durum')='REDDEDILDI'))
 WHEN 'IS.TAMAMLADIM' THEN ((i->>'tur')='SURELI' AND ayni AND durum IN ('CALISIYOR','DEVAM_BEKLIYOR')) OR ((i->>'tur')='ANLIK' AND durum='CALISMIYOR' AND bas=(i->>'kimlik') AND (i->>'durum')='SIRADA' AND NOT irp.dogru((i->'kilitli'))) ELSE true END,false);
END $$;
CREATE FUNCTION kg.ac(h jsonb,durum text,kova text,k text,neden text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT h||jsonb_build_object('durum',durum,'kova',kova,'aralik_is',k,'neden',neden) $$;
CREATE FUNCTION kg.gecis(hal jsonb,kod text,i jsonb DEFAULT NULL,bas_is jsonb DEFAULT NULL,neden text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column

DECLARE d jsonb=hal; yan jsonb='[]'; once jsonb; bosalt boolean=false;
BEGIN
 IF kod='MESAI.GIRDIM' THEN bosalt=true;
 ELSIF kod IN ('MESAI.CIKTIM','PAYDOS') THEN d=kg.ac(d,'MESAI_DISI',NULL,NULL,neden)||'{"acik_is":null}';
 ELSIF kod='MOLA_BASI' THEN IF (d->>'durum')<>'MESAI_DISI' THEN d=kg.ac(d||jsonb_build_object('mola_onceki',hal),'SABIT_MOLADA','SABIT_MOLA',NULL,neden); END IF;
 ELSIF kod='MOLA_SONU' THEN IF (d->>'durum')='SABIT_MOLADA' THEN once=(d->'mola_onceki'); d=once; IF (once->>'durum') IN ('CALISIYOR','MOLADA','DEVAM_BEKLIYOR') THEN d=kg.ac(d,CASE WHEN irp.dogru((once->'acik_is')) THEN 'DEVAM_BEKLIYOR' ELSE 'CALISMIYOR' END,'TANIMSIZ',NULL,neden); END IF; d=d||'{"mola_onceki":null}'; END IF;
 ELSIF kod='IS.BASLADIM' THEN d=kg.ac(d||jsonb_build_object('acik_is',(i->'kimlik'),'onceki_kova','CALISMA'),'CALISIYOR','CALISMA',(i->>'kimlik'),neden);
 ELSIF kod='IS.MOLA_VERDIM' THEN d=kg.ac(d,'MOLADA','MOLA',NULL,neden);
 ELSIF kod='IS.ARIZA_BILDIRDIM' THEN d=kg.ac(d||jsonb_build_object('acik_is',(i->'kimlik'),'devam_izni',false),'ARIZADA','BEKLEME_ARIZA',(i->>'kimlik'),neden); yan='["R07"]';
 ELSIF kod='IS.DEVAM_ONAYLADIM' THEN d=d||'{"devam_izni":true}';
 ELSIF kod='IS.DEVAM_ETTIM' THEN d=d||jsonb_build_object('acik_is',(i->'kimlik')); IF (i->>'durum')='REDDEDILDI' THEN d=d||'{"onceki_kova":"YENIDEN_ISLEME"}'; END IF;
  IF (i->>'tur')='ANLIK' THEN d=kg.ac(d,'CALISMIYOR','TANIMSIZ',NULL,neden)||'{"acik_is":null}'; ELSE d=kg.ac(d,'CALISIYOR',(d->>'onceki_kova'),(i->>'kimlik'),neden); END IF;
 ELSIF kod='IS.TAMAMLADIM' THEN IF irp.dogru((i->'onay_gerekli')) THEN d=kg.ac(d||'{"acik_is":null}','ONAY_BEKLIYOR','BEKLEME_ONAY',(i->>'kimlik'),neden); yan='["R05"]'; ELSIF (i->>'tur')<>'ANLIK' THEN bosalt=true; END IF;
 ELSIF kod='IS.ONAYLADIM' THEN bosalt=true;
 ELSIF kod='IS.REDDETTIM' THEN d=kg.ac(d||'{"acik_is":null}','CALISMIYOR','GECIS',NULL,neden);
 ELSIF kod='LISTE_DEGISTI' THEN
  IF (d->>'durum')<>'MESAI_DISI' AND NOT irp.dogru(bas_is) THEN d=kg.ac(d||'{"acik_is":null}','CALISMIYOR','TANIMSIZ',NULL,neden); yan='["R08"]';
  ELSIF (d->>'durum') IN ('CALISIYOR','MOLADA','ARIZADA','DEVAM_BEKLIYOR','ON_IS_BEKLIYOR') AND (NOT irp.dogru(bas_is) OR (bas_is->>'kimlik') IS DISTINCT FROM (d->>'acik_is')) THEN
   d=d||'{"acik_is":null}'; IF irp.dogru((bas_is->'kilitli')) THEN d=kg.ac(d,'ON_IS_BEKLIYOR','BEKLEME_ON_IS',(bas_is->>'kimlik'),neden); yan=yan||'"R04"'::jsonb; ELSE d=kg.ac(d,'CALISMIYOR','GECIS',NULL,neden); END IF; yan=yan||'"R01"'::jsonb;
  ELSIF (d->>'durum')='CALISMIYOR' AND irp.dogru((bas_is->'kilitli')) THEN d=kg.ac(d,'ON_IS_BEKLIYOR','BEKLEME_ON_IS',(bas_is->>'kimlik'),neden); yan=yan||'"R04"'::jsonb; END IF;
 ELSIF kod='ON_IS_BITTI' AND (d->>'durum')='ON_IS_BEKLIYOR' THEN d=d||'{"durum":"CALISMIYOR"}'; END IF;
 IF bosalt THEN d=d||'{"acik_is":null}'; IF coalesce(((bas_is->>'kilitli'))::boolean,(bas_is->>'durum')='ON_IS_BEKLIYOR',false) THEN d=kg.ac(d,'ON_IS_BEKLIYOR','BEKLEME_ON_IS',(bas_is->>'kimlik'),neden); yan=yan||'"R04"'::jsonb; ELSE d=kg.ac(d,'CALISMIYOR','TANIMSIZ',NULL,neden); END IF; END IF;
 IF kod='MESAI.GIRDIM' THEN
  IF (bas_is->>'durum')='ONAY_BEKLIYOR' THEN d=kg.ac(d,'ONAY_BEKLIYOR','BEKLEME_ONAY',(bas_is->>'kimlik'),neden);
  ELSIF irp.dogru((bas_is->'acik_ariza')) THEN d=kg.ac(d||jsonb_build_object('acik_is',(bas_is->'kimlik'),'devam_izni',coalesce((bas_is->'devam_izni'),'false'),'onceki_kova',coalesce((bas_is->'calisma_kovasi'),'"CALISMA"')),'ARIZADA','BEKLEME_ARIZA',(bas_is->>'kimlik'),(bas_is->>'acik_ariza')); END IF; END IF;
 RETURN jsonb_build_object('hal',d,'yan',yan);
END $$;
-- kisi_gunu.py:129 hal_yaz, 143 uygula.
CREATE FUNCTION kg.hal_yaz(m text,kisi text,yeni jsonb,t timestamptz,e jsonb DEFAULT NULL,kural text DEFAULT NULL,sistem boolean DEFAULT false,zorla boolean DEFAULT false) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE eski jsonb=motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal()); degisti boolean; BEGIN
 degisti=((eski->'kova') IS DISTINCT FROM (yeni->'kova') OR (eski->'aralik_is') IS DISTINCT FROM (yeni->'aralik_is') OR (eski->'neden') IS DISTINCT FROM (yeni->'neden') OR zorla);
 IF degisti AND irp.dogru((eski->'kova')) AND irp.dogru((eski->'baslangic')) THEN PERFORM takvim.aralik_ekle(m,kisi,eski,t,e,kural,sistem); END IF;
 IF degisti THEN yeni=yeni||jsonb_build_object('baslangic',CASE WHEN irp.dogru((yeni->'kova')) THEN saat.kodla(t) END,'acan_olay',(e->'olay_kimligi'),'acan_kural',kural); END IF;
 PERFORM motor.kaydet(m,'kisi_durumu',kisi,yeni); END $$;
CREATE FUNCTION kg.uygula(m text,kisi text,kod text,t timestamptz,e jsonb DEFAULT NULL,i jsonb DEFAULT NULL,neden text DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE d jsonb=motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal()); b jsonb=motor.kayit(m,'isler',motor.kayit(m,'listeler',kisi,'[]')->>0,'null'); y jsonb; r jsonb; k text; BEGIN
 IF d ? '_kesinti_onceki' AND kod NOT IN ('PAYDOS','MOLA_BASI','MOLA_SONU') THEN
  PERFORM motor.kaydet(m,'kisi_durumu',kisi,(d->'_kesinti_onceki')); PERFORM kg.uygula(m,kisi,kod,t,e,i,neden); y=motor.kayit(m,'kisi_durumu',kisi);
  PERFORM motor.kaydet(m,'kisi_durumu',kisi,d||jsonb_build_object('_kesinti_onceki',y,'acik_is',(y->'acik_is'))); RETURN; END IF;
 IF (d->>'durum')='SABIT_MOLADA' AND kod NOT IN ('MOLA_SONU','PAYDOS','MOLA_BASI') THEN r=kg.gecis((d->'mola_onceki'),kod,i,b,neden); y=d||jsonb_build_object('mola_onceki',(r->'hal'),'acik_is',(r#>'{hal,acik_is}')); ELSE r=kg.gecis(d,kod,i,b,neden); y=(r->'hal'); END IF;
 k=CASE WHEN kod LIKE 'MOLA_%' THEN 'R03' WHEN kod='PAYDOS' THEN 'R13' ELSE 'R02' END;
 PERFORM kg.hal_yaz(m,kisi,y,t,e,k,kod='PAYDOS');
 FOR k IN SELECT jsonb_array_elements_text((r->'yan')) LOOP IF k<>'R01' THEN PERFORM motor.bildir(m,e,k,coalesce(nullif(i,'null'),nullif(b,'null'),'{}')->>'atayan',t,kisi); END IF; END LOOP;
 IF irp.sabit('calisan') ? ((e->>'eylem_kodu')) THEN PERFORM motor.kaydet(m,'kisi_durumu',kisi,motor.kayit(m,'kisi_durumu',kisi)||jsonb_build_object('son_olay_ani',saat.kodla(t))); END IF;
END $$;
-- kisi_gunu.py:169 is_dogur; 185 isleri_guncelle.
CREATE FUNCTION kg.is_dogur(m text,e jsonb,satir jsonb,kimlik text,plansiz boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE i jsonb; n integer; BEGIN
 i='{"iptal_oncesi_durum":null,"iptal_eden":null,"onay_beklet":false,"tamamlayan":null,"onay_bekleme_ani":null,"iptal_ani":null,"on_isler":[],"onay_gerekli":false,"tahmini_sure_dk":0,"tur":"SURELI","kisi_sayisi":1}'::jsonb||satir||jsonb_build_object('kimlik',kimlik,'doguran_olay',(e->'olay_kimligi'),'son_olay',(e->'olay_kimligi'),'kural_versiyonu',1,'durum','HAVUZDA','plansiz',plansiz,'bitis_ani',NULL,'kisi',NULL,'sira',NULL,'atayan',NULL,'acik_ariza',NULL,'devam_izni',false);
 i=i||jsonb_build_object('on_isler',(SELECT coalesce(jsonb_agg(CASE WHEN jsonb_typeof(x)='object' THEN to_jsonb((e->>'olay_kimligi')||'/'||(x->>'satir')) ELSE x END ORDER BY n),'[]') FROM jsonb_array_elements((i->'on_isler')) WITH ORDINALITY z(x,n)),'kilitli',irp.dogru((i->'on_isler')));
 PERFORM motor.kaydet(m,'isler',kimlik,i);
 IF ((i->>'kisi_sayisi'))::integer>1 THEN FOR n IN 1..((i->>'kisi_sayisi'))::integer LOOP PERFORM kg.is_dogur(m,e,satir||jsonb_build_object('kisi_sayisi',1,'ana_is',kimlik),kimlik||'/k'||n); END LOOP;
  i=i||jsonb_build_object('tahmini_sure_dk',((i->>'tahmini_sure_dk'))::int*((i->>'kisi_sayisi'))::int); PERFORM motor.kaydet(m,'isler',kimlik,i); END IF; RETURN i;
END $$;
CREATE FUNCTION kg.isleri_guncelle(m text,t timestamptz,e jsonb DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kisi text; l jsonb; k text; n bigint; i jsonb; d jsonb; durum text; BEGIN
 FOR kisi,l IN SELECT * FROM motor.satirlar(m,'listeler') LOOP
  FOR k,n IN SELECT * FROM jsonb_array_elements_text(l) WITH ORDINALITY LOOP
   i=motor.kayit(m,'isler',k)||jsonb_build_object('kisi',kisi,'sira',n);
   i=i||jsonb_build_object('kilitli',EXISTS(SELECT FROM jsonb_array_elements_text((i->'on_isler')) x WHERE coalesce(motor.kayit(m,'isler',x)->>'durum','') NOT IN ('BITTI','IPTAL')));
   IF (i->>'durum') IN ('SIRADA','ON_IS_BEKLIYOR') THEN i=i||jsonb_build_object('durum',CASE WHEN irp.dogru((i->'kilitli')) THEN 'ON_IS_BEKLIYOR' ELSE 'SIRADA' END); END IF;
   PERFORM motor.kaydet(m,'isler',k,i); END LOOP;
  d=motor.kayit(m,'kisi_durumu',kisi); IF irp.dogru(d) AND irp.dogru(l) AND motor.kayit(m,'isler',l->>0)->>'durum'<>'ON_IS_BEKLIYOR' THEN
   durum=CASE WHEN (d->>'durum')='SABIT_MOLADA' THEN (d#>>'{mola_onceki,durum}') ELSE (d->>'durum') END;
   IF durum='ON_IS_BEKLIYOR' AND (e IS NULL OR (e->>'eylem_kodu') NOT IN ('IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM')) THEN PERFORM kg.uygula(m,kisi,'ON_IS_BITTI',t,e); END IF; END IF;
 END LOOP; END $$;
-- kisi_gunu.py:375 ana_isleri_guncelle.
CREATE FUNCTION kg.ana_isleri_guncelle(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE k text; i jsonb; ds text[]; alt jsonb; t text; BEGIN
 FOR k,i IN SELECT * FROM motor.satirlar(m,'isler') LOOP
  IF coalesce(((i->>'kisi_sayisi'))::int,1)<=1 OR (i->>'durum')='IPTAL' THEN CONTINUE; END IF;
  SELECT coalesce(jsonb_agg(hal),'[]') INTO alt FROM motor.satirlar(m,'isler') WHERE (hal->>'ana_is')=k;
  SELECT coalesce(array_agg((x->>'durum')),'{}') INTO ds FROM jsonb_array_elements(alt) x WHERE (x->>'durum')<>'IPTAL';
  IF cardinality(ds)=0 THEN SELECT max((x->>'iptal_ani')) INTO t FROM jsonb_array_elements(alt) x; i=i||jsonb_build_object('durum','IPTAL','bitis_ani',NULL,'iptal_ani',t);
  ELSE t=CASE WHEN ds<@ARRAY['BITTI'] THEN 'BITTI' WHEN 'CALISILIYOR'=ANY(ds) THEN 'CALISILIYOR' WHEN ds<@ARRAY['BITTI','ONAY_BEKLIYOR'] THEN 'ONAY_BEKLIYOR' WHEN ds<@ARRAY['HAVUZDA'] THEN 'HAVUZDA' WHEN ds&&ARRAY['YARIM','BITTI'] THEN 'YARIM' ELSE 'SIRADA' END;
   i=i||jsonb_build_object('durum',t,'kisi',NULL,'sira',NULL,'bitis_ani',CASE WHEN t='BITTI' THEN (SELECT max(coalesce((x->>'bitis_ani'),(x->>'iptal_ani'))) FROM jsonb_array_elements(alt) x) END); END IF;
  PERFORM motor.kaydet(m,'isler',k,i); END LOOP;
END $$;
-- kisi_gunu.py:197 atolye_isle; yaşam dalları yasam_v5.isle tarafından çevrilir.
CREATE FUNCTION kg.atolye_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); t timestamptz=saat.an((e->>'oldugu_an')); i jsonb; k text; kisi text; ks text[]; l jsonb; d jsonb; onceki jsonb='{}'; eski text; yeni text; acik text; n bigint; s jsonb; alt jsonb; uygun boolean; onay boolean;
BEGIN
 IF yasam_v5.isle(m,e) THEN RETURN; END IF;
 IF kod='IS.TANIMLADIM' THEN FOR s,n IN SELECT * FROM jsonb_array_elements((g->'isler')) WITH ORDINALITY LOOP PERFORM kg.is_dogur(m,e,s,(e->>'olay_kimligi')||CASE WHEN jsonb_array_length((g->'isler'))>1 THEN '/'||n ELSE '' END); END LOOP; RETURN; END IF;
 IF kod='IS.SURE_EKLEDIM' THEN PERFORM motor.ekle(m,'elle_olaylar',e); RETURN; END IF;
 IF kod='ELLE_BITIS' THEN
  IF irp.dogru(g->'is_bitti') THEN i=motor.kayit(m,'isler',(kapi.hedefler(e,'IS'))[1]);
   IF irp.dogru(i) THEN k=i->>'kimlik'; onay=irp.dogru(i->'onay_gerekli'); i=i||jsonb_build_object('tamamlayan',e->'adina','onay_bekleme_ani',CASE WHEN onay THEN saat.kodla(t) END,'durum',CASE WHEN onay THEN 'ONAY_BEKLIYOR' ELSE 'BITTI' END,'bitis_ani',saat.kodla(saat.an(g->>'bitis'))); PERFORM motor.kaydet(m,'isler',k,i);
    IF NOT onay THEN PERFORM liste.cikar(m,k); END IF; kisi=e->>'adina'; IF motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal())->>'durum'<>'MESAI_DISI' THEN PERFORM kg.uygula(m,kisi,'IS.TAMAMLADIM',t,e,i); END IF; PERFORM kg.isleri_guncelle(m,t,e);
   END IF; END IF; RETURN;
 END IF;
 k=(kapi.hedefler(e,'IS'))[1]; i=motor.kayit(m,'isler',k,'null');
 IF kod='IS.PLANSIZ_TANIMLADIM' THEN i=kg.is_dogur(m,e,g||jsonb_build_object('birim',coalesce((g->>'birim'),motor.kayit(m,'kisiler',(e->>'kim'))->>'birim')),(e->>'olay_kimligi'),true); k=(i->>'kimlik'); END IF;
 IF kod IN ('IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM') THEN
  IF NOT irp.dogru(i) THEN PERFORM motor.supheli(m,e,'Is yok'); RETURN; END IF;
  IF kod='IS.ATADIM' AND coalesce(((g->>'kisi_sayisi'))::int,((i->>'kisi_sayisi'))::int,1)>1 THEN
   IF coalesce(((i->>'kisi_sayisi'))::int,1)=1 THEN
    i=i||jsonb_build_object('kisi_sayisi',(g->'kisi_sayisi')); FOR n IN 1..((i->>'kisi_sayisi'))::int LOOP PERFORM kg.is_dogur(m,e,i||jsonb_build_object('kisi_sayisi',1,'ana_is',k),k||'/k'||n); END LOOP;
    i=i||jsonb_build_object('tahmini_sure_dk',((i->>'tahmini_sure_dk'))::int*((i->>'kisi_sayisi'))::int); PERFORM motor.kaydet(m,'isler',k,i); END IF;
   FOR kisi,n IN SELECT * FROM jsonb_array_elements_text((g->'kisiler')) WITH ORDINALITY LOOP alt=e||jsonb_build_object('neyin_ustunde',jsonb_build_array(jsonb_build_object('tur','IS','kimlik',k||'/k'||n)),'girdiler',jsonb_build_object('kisi',kisi,'sira',(g->'sira'))); PERFORM kg.atolye_isle(m,alt); END LOOP;
   PERFORM kg.ana_isleri_guncelle(m); RETURN; END IF;
  ks=CASE WHEN kod='IS.DEVRETTIM' THEN ARRAY[(g->>'kimden'),(g->>'kime')] ELSE ARRAY[(g->>'kisi')] END;
  FOR kisi,l IN SELECT * FROM motor.satirlar(m,'listeler') LOOP IF l ? k AND NOT kisi=ANY(ks) THEN ks=array_append(ks,kisi); END IF; END LOOP;
  FOREACH kisi IN ARRAY ks LOOP onceki=onceki||jsonb_build_object(kisi,motor.kayit(m,'listeler',kisi,'[]')); END LOOP;
  IF kod='IS.ATADIM' THEN PERFORM liste.cikar(m,k); END IF;
  IF kod='IS.DEVRETTIM' THEN
   l=motor.kayit(m,'listeler',(g->>'kimden'),'[]'); IF NOT l ? k OR (g->>'kimden')=(g->>'kime') THEN PERFORM motor.supheli(m,e,'Devir kapisi'); END IF;
   l=(SELECT coalesce(jsonb_agg(x ORDER BY n),'[]') FROM jsonb_array_elements(l) WITH ORDINALITY z(x,n) WHERE x<>to_jsonb(k)); IF irp.dogru((g->'kimden_yeni_is')) THEN l=liste.yerlestir(l,(g->>'kimden_yeni_is'),1); END IF;
   PERFORM motor.kaydet(m,'listeler',(g->>'kimden'),l); PERFORM motor.kaydet(m,'listeler',(g->>'kime'),liste.yerlestir(motor.kayit(m,'listeler',(g->>'kime'),'[]'),k,coalesce(((g->>'kime_sira'))::int,1)));
   uygun=EXISTS(SELECT FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) a WHERE (a->>'is')=k AND (a->>'kova') IN ('CALISMA','YENIDEN_ISLEME')) OR (i->>'durum') IN ('CALISILIYOR','YARIM');
   i=i||jsonb_build_object('durum',CASE WHEN uygun THEN 'YARIM' ELSE 'SIRADA' END,'atayan',(e->'kim'),'acik_ariza',NULL,'devam_izni',false);
  ELSE
   l=motor.kayit(m,'listeler',(g->>'kisi'),'[]'); IF kod='IS.SIRALADIM' AND NOT l ? k THEN PERFORM motor.supheli(m,e,'Siralama kapisi'); END IF;
   IF kod='IS.ATADIM' AND (i->>'durum') NOT IN ('HAVUZDA','REDDEDILDI') THEN PERFORM motor.supheli(m,e,'Atama kapisi'); END IF;
   PERFORM motor.kaydet(m,'listeler',(g->>'kisi'),liste.yerlestir(l,k,coalesce(((g->>'sira'))::int,((g->>'yeni_sira'))::int,1)));
   IF kod<>'IS.SIRALADIM' THEN i=i||jsonb_build_object('durum',CASE WHEN (i->>'durum')='REDDEDILDI' THEN 'REDDEDILDI' ELSE 'SIRADA' END,'atayan',(e->'kim')); END IF;
  END IF;
  PERFORM motor.kaydet(m,'isler',k,i); PERFORM kg.isleri_guncelle(m,t,e); i=motor.kayit(m,'isler',k);
  FOREACH kisi IN ARRAY ks LOOP eski=onceki->kisi->>0; yeni=motor.kayit(m,'listeler',kisi,'[]')->>0; IF eski IS DISTINCT FROM yeni THEN
   d=motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal()); acik=(d->>'acik_is'); IF motor.kayit(m,'isler',acik)->>'durum'='CALISILIYOR' THEN PERFORM motor.kaydet(m,'isler',acik,motor.kayit(m,'isler',acik)||'{"durum":"YARIM"}'); END IF;
   PERFORM kg.uygula(m,kisi,'LISTE_DEGISTI',t,e,i); END IF; END LOOP;
  PERFORM kg.ana_isleri_guncelle(m); RETURN;
 END IF;
 IF irp.sabit('calisan') ? kod THEN
  kisi=coalesce((e->>'adina'),(e->>'kim')); d=motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal()); PERFORM motor.kaydet(m,'kisi_durumu',kisi,d);
  IF takvim.kesinti(m,kisi,t) IS NOT NULL OR (kod='MESAI.GIRDIM' AND EXISTS(SELECT FROM jsonb_array_elements(takvim.izinler(m,kisi)) x WHERE saat.an(x->>0)<=saat.gun_ani(saat.gun(saat.kodla(t)),motor.takvim(m,saat.kodla(t),kisi)->>'mesai_baslangic') AND saat.gun_ani(saat.gun(saat.kodla(t)),motor.takvim(m,saat.kodla(t),kisi)->>'mesai_baslangic')<saat.an(x->>1))) THEN
   PERFORM motor.supheli(m,e,'Izin/durus araliginda calisan olayi'); PERFORM motor.kaydet(m,'kisi_durumu',kisi,d||jsonb_build_object('son_olay_ani',saat.kodla(t))); RETURN; END IF;
  l=motor.kayit(m,'listeler',kisi,'[]'); uygun=kg.kapi(d,kod,i,l->>0,motor.sabit_molada(m,t,kisi));
  IF NOT uygun AND kod<>'MESAI.GIRDIM' AND NOT EXISTS(SELECT FROM jsonb_array_elements(takvim.normal(m,saat.gun(saat.kodla(t)),false,kisi)||takvim.ekler(m,kisi,NULL,true)) x WHERE saat.an(x->>0)<=t AND t<=saat.an(x->>1)) THEN
   PERFORM motor.kaydet(m,'mesai_sonrasi_isaretleri',(e->>'olay_kimligi'),jsonb_build_object('kisi',kisi,'an',saat.kodla(t),'olay',(e->'olay_kimligi'))); FOREACH eski IN ARRAY yetki_v6.yoneticiler(m,motor.kayit(m,'kisiler',kisi)->>'birim') LOOP PERFORM motor.bildir(m,e,'R31',eski,t,kisi); END LOOP; END IF;
  IF NOT uygun THEN
   PERFORM motor.supheli(m,e,'Calisan kapisi kapali'); d=d||jsonb_build_object('son_olay_ani',saat.kodla(t)); PERFORM motor.kaydet(m,'kisi_durumu',kisi,d);
   IF kod<>'IS.TAMAMLADIM' OR NOT irp.dogru(i) OR (i->>'durum') NOT IN ('SIRADA','YARIM','CALISILIYOR','REDDEDILDI') THEN RETURN; END IF;
   onay=irp.dogru((i->'onay_gerekli')) OR (i->>'durum')='REDDEDILDI'; i=i||jsonb_build_object('tamamlayan',kisi,'onay_bekleme_ani',CASE WHEN onay THEN saat.kodla(t) END,'durum',CASE WHEN onay THEN 'ONAY_BEKLIYOR' ELSE 'BITTI' END,'bitis_ani',CASE WHEN NOT onay THEN saat.kodla(t) END); PERFORM motor.kaydet(m,'isler',k,i);
   IF NOT onay THEN PERFORM liste.cikar(m,k); END IF;
   FOR eski,d IN SELECT * FROM motor.satirlar(m,'kisi_durumu') LOOP
    IF (d->>'acik_is')=k AND onay AND (d->>'durum')<>'SABIT_MOLADA' THEN d=d||jsonb_build_object('acik_is',NULL,'durum','ONAY_BEKLIYOR','kova','BEKLEME_ONAY','aralik_is',k,'neden',NULL); PERFORM kg.hal_yaz(m,eski,d,t,e,'R05'); d=motor.kayit(m,'kisi_durumu',eski);
    ELSIF (d->>'acik_is')=k THEN d=d||'{"acik_is":null}'; END IF;
    IF (d#>>'{mola_onceki,acik_is}')=k THEN d=jsonb_set(d,'{mola_onceki}',(d->'mola_onceki')||jsonb_build_object('acik_is',NULL,'durum',CASE WHEN onay THEN 'ONAY_BEKLIYOR' ELSE 'CALISMIYOR' END,'kova',CASE WHEN onay THEN 'BEKLEME_ONAY' ELSE 'TANIMSIZ' END,'aralik_is',CASE WHEN onay THEN k END)); END IF; PERFORM motor.kaydet(m,'kisi_durumu',eski,d); END LOOP;
   IF onay THEN PERFORM motor.bildir(m,e,'R05',(i->>'atayan'),t,kisi); END IF;
   PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); RETURN;
  END IF;
  IF kod='IS.TAMAMLADIM' AND irp.dogru(i) THEN
   onay=irp.dogru((i->'onay_gerekli')); i=i||jsonb_build_object('tamamlayan',kisi,'onay_bekleme_ani',CASE WHEN onay THEN saat.kodla(t) END,'durum',CASE WHEN onay THEN 'ONAY_BEKLIYOR' ELSE 'BITTI' END);
   IF NOT onay THEN i=i||jsonb_build_object('bitis_ani',saat.kodla(t)); PERFORM liste.cikar(m,k); IF NOT irp.dogru(motor.kayit(m,'listeler',kisi,'[]')) THEN PERFORM motor.bildir(m,e,'R08',(i->>'atayan'),t,kisi); END IF; END IF; END IF;
  IF irp.dogru(i) AND kod='IS.ARIZA_BILDIRDIM' THEN i=i||jsonb_build_object('acik_ariza',coalesce(nullif((g->>'neden'),''),'BELIRTILMEDI'),'devam_izni',false); END IF;
  IF irp.dogru(i) AND kod IN ('IS.DEVAM_ETTIM','IS.TAMAMLADIM') THEN i=i||'{"acik_ariza":null}'; END IF;
  PERFORM kg.uygula(m,kisi,kod,t,e,i,CASE WHEN kod='IS.ARIZA_BILDIRDIM' THEN coalesce(nullif((g->>'neden'),''),'BELIRTILMEDI') ELSE (g->>'neden') END);
  IF irp.dogru(i) THEN IF kod IN ('IS.BASLADIM','IS.DEVAM_ETTIM') AND (i->>'tur')<>'ANLIK' THEN i=i||'{"durum":"CALISILIYOR"}'; END IF; PERFORM motor.kaydet(m,'isler',k,i); END IF;
  IF kod='MESAI.CIKTIM' THEN FOR eski,s IN SELECT * FROM motor.satirlar(m,'isler') LOOP IF (s->>'kisi')=kisi AND (s->>'durum')='CALISILIYOR' THEN PERFORM motor.kaydet(m,'isler',eski,s||'{"durum":"YARIM"}'); END IF; END LOOP; END IF;
  PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); RETURN;
 END IF;
 IF irp.dogru(i) AND kod IN ('IS.ONAYLADIM','IS.REDDETTIM','IS.DEVAM_ONAYLADIM') THEN
  kisi=(i->>'kisi'); IF kisi IS NULL THEN PERFORM motor.supheli(m,e,'Atanan kisi yok'); RETURN; END IF;
  IF (e->>'kim')<>(i->>'atayan') AND NOT kapi.lider(m,(e->>'kim'),(i->>'birim')) THEN PERFORM motor.supheli(m,e,'Atayan/lider farkli'); END IF;
  IF kod='IS.ONAYLADIM' THEN IF (i->>'durum')<>'ONAY_BEKLIYOR' THEN PERFORM motor.supheli(m,e,'Onay kapisi'); END IF; i=i||jsonb_build_object('durum','BITTI','bitis_ani',saat.kodla(t)); PERFORM liste.cikar(m,k); IF NOT irp.dogru(motor.kayit(m,'listeler',kisi,'[]')) THEN PERFORM motor.bildir(m,e,'R08',(i->>'atayan'),t,kisi); END IF;
  ELSIF kod='IS.REDDETTIM' THEN i=i||'{"durum":"REDDEDILDI"}'; ELSE i=i||'{"devam_izni":true}'; END IF;
  PERFORM motor.kaydet(m,'isler',k,i); PERFORM kg.uygula(m,kisi,kod,t,e,i); PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m);
 END IF;
END $$;
-- kisi_gunu.py:341 elle_uygula; çevirisi tamamlanmayan manuel aralık açıkça durdurulur.
CREATE FUNCTION kg.elle_uygula(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE e jsonb; g jsonb; kisi text; bas timestamptz; bitis timestamptz; a jsonb;
 son timestamptz; x timestamptz; y timestamptz; yeni jsonb; i jsonb;
BEGIN
 FOR e IN SELECT value FROM jsonb_array_elements(motor.oku(m,'elle_olaylar','[]')) LOOP
  g=e->'girdiler'; kisi=e->>'adina'; bas=saat.an(g->>'baslangic'); bitis=least(saat.an(g->>'bitis'),saat.simdi());
  IF to_char(bas AT TIME ZONE 'Europe/Istanbul','IYYY-IW')<>to_char(saat.an(e->>'oldugu_an') AT TIME ZONE 'Europe/Istanbul','IYYY-IW') THEN PERFORM motor.supheli(m,e,'Ayni hafta disinda'); END IF;
  yeni='[]';
  FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) LOOP
   son=coalesce(saat.an(a->>'bitis'),saat.simdi()); x=greatest(saat.an(a->>'baslangic'),bas); y=least(son,bitis);
   IF a->>'kisi' IS DISTINCT FROM kisi OR a->>'kova' NOT IN ('TANIMSIZ','GECIS') OR x>=y THEN yeni=yeni||jsonb_build_array(a); CONTINUE; END IF;
   IF saat.an(a->>'baslangic')<x THEN yeni=yeni||jsonb_build_array(a||jsonb_build_object('bitis',saat.kodla(x))); END IF;
   i=motor.kayit(m,'isler',(kapi.hedefler(e,'IS'))[1]);
   yeni=yeni||jsonb_build_array(a||jsonb_build_object('baslangic',saat.kodla(x),'bitis',saat.kodla(y),'kova','CALISMA','is_',NULL,'is',i->'kimlik','proje',i->'proje','kategori',i->'kategori','plansiz',coalesce(i->'plansiz','false'),'elle',true,'aciklama',g->'aciklama','yazan',e->'kim','acan_olay',e->'olay_kimligi'));
   IF y<son THEN yeni=yeni||jsonb_build_array(a||jsonb_build_object('baslangic',saat.kodla(y))); END IF;
  END LOOP;
  PERFORM motor.yaz(m,'araliklar',yeni);
 END LOOP;
END $$;
-- kisi_gunu.py:392 birlestir.
CREATE FUNCTION kg.birlestir(araliklar jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column

DECLARE sonuc jsonb='[]'; a jsonb; once jsonb; ayni boolean; alan text; n int; BEGIN
 FOR a IN SELECT x FROM jsonb_array_elements(araliklar) WITH ORDINALITY z(x,n) ORDER BY coalesce((x->>'kisi'),'') COLLATE "C",(x->>'baslangic'),n LOOP
  n=jsonb_array_length(sonuc); once=sonuc->(n-1); ayni=(once->'bitis')=(a->'baslangic');
  FOREACH alan IN ARRAY ARRAY['kisi','gun','kova','is','neden','elle','yazan','aciklama','plansiz','fazla_mesai','katsayi'] LOOP ayni=ayni AND (once->alan IS NOT DISTINCT FROM a->alan); END LOOP;
  IF ayni THEN sonuc=jsonb_set(sonuc,ARRAY[(n-1)::text],once||jsonb_build_object('bitis',(a->'bitis'),'kapatan_olay',(a->'kapatan_olay'),'kapatan_kural',(a->'kapatan_kural'),'sistem_kapatti',coalesce((a->'sistem_kapatti'),'false'))); ELSE sonuc=sonuc||jsonb_build_array(a); END IF;
 END LOOP; RETURN sonuc; END $$;
RESET ROLE;
