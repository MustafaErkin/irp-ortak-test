SET ROLE irp_sahibi;
-- kurallar_v7.rol_izni: rol ve üst ilişkisi, tarihli çalışma alanında.
CREATE FUNCTION k7.rol_izni(d text,kim text,r jsonb,birim text DEFAULT NULL) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ks text[]; roller text[]=irp.dizi(motor.kayit(d,'kisiler',kim)->'roller'); k text; p jsonb; BEGIN
 IF jsonb_typeof(r)='array' THEN r=jsonb_build_object('kimler',r,'kapsam','FIRMA'); END IF;
 ks=irp.dizi(r->'kimler'); IF cardinality(ks)=0 THEN RETURN false; END IF;
 IF 'YETKILI'=ANY(ks) AND 'YETKILI'=ANY(roller) THEN RETURN true; END IF;
 IF coalesce(r->>'kapsam','FIRMA')='FIRMA' THEN
  IF roller&&array_remove(ks,'YETKILI') THEN RETURN true; END IF;
  FOR k,p IN SELECT * FROM motor.satirlar(d,'kisiler') LOOP IF kim=ANY(yetki_v6.ustler(d,k)) AND irp.dizi(p->'roller')&&array_remove(ks,'YETKILI') AND yetki_v6.istihdamda(d,k,yetki_v6.simdi(d)) THEN RETURN true; END IF; END LOOP; RETURN false;
 END IF;
 RETURN coalesce(motor.kayit(d,'kisiler',kim)->>'birim'=birim AND ('BIRIM_UYESI'=ANY(ks) OR roller&&ks) OR 'BIRIM_YONETICISI'=ANY(ks) AND kim=ANY(yetki_v6.yoneticiler(d,birim)) OR 'BIRIM_BASI'=ANY(ks) AND kim=motor.kayit(d,'birimler',birim)->>'basi' OR kim=ANY(yetki_v6.birim_ustleri(d,birim)),false);
END $$;
-- kurallar_v10: genel_yonetim, projede_yetkili, ek_erisim, birim_dahil, kisi_dahil.
CREATE FUNCTION k10.genel_yonetim(d text,kim text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN RETURN yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) AND (coalesce(motor.kayit(d,'kisiler',kim)->'roller' ? 'YETKILI',false) OR EXISTS(SELECT FROM motor.satirlar(d,'birimler') WHERE NOT irp.dogru(hal->'ust_birim') AND kim=ANY(yetki_v6.yoneticiler(d,anahtar)))); END $$;
CREATE FUNCTION k10.projede_yetkili(d text,kim text,proje text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE s text; x jsonb; b text; BEGIN
 IF NOT motor.oku(d,'projeler') ? proje OR NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 IF k10.genel_yonetim(d,kim) THEN RETURN true; END IF; s=motor.kayit(d,'projeler',proje)->>'sorumlu';
 IF s IS NOT NULL AND (kim=s OR kim=ANY(yetki_v6.ustler(d,s))) THEN RETURN true; END IF;
 FOR x IN SELECT hal FROM motor.satirlar(d,'etaplar') WHERE hal->>'proje'=proje LOOP b=x->>'birim'; s=coalesce(x->>'sorumlu',motor.kayit(d,'birimler',b)->>'basi');
  IF kim=ANY(yetki_v6.yoneticiler(d,b)||yetki_v6.birim_ustleri(d,b)) OR s IS NOT NULL AND (kim=s OR kim=ANY(yetki_v6.ustler(d,s))) THEN RETURN true; END IF;
 END LOOP; RETURN false; END $$;
CREATE FUNCTION k10.ek_erisim(d text,kim text,proje text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; BEGIN SELECT hal INTO x FROM motor.satirlar(d,'proje_erisimleri') WHERE hal->>'proje'=proje AND hal->>'kisi'=kim AND saat.an(hal->>'an')<=yetki_v6.simdi(d) ORDER BY saat.an(hal->>'an') DESC,hal->>'kimlik' COLLATE "C" DESC LIMIT 1; RETURN irp.dogru(x->'acik'); END $$;
CREATE FUNCTION k10.birim_dahil(d text,birim text,proje text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN RETURN EXISTS(SELECT FROM motor.satirlar(d,'etaplar') WHERE hal->>'proje'=proje AND hal->>'birim'=birim); END $$;
CREATE FUNCTION k10.kisi_dahil(d text,kim text,proje text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN RETURN k10.birim_dahil(d,motor.kayit(d,'kisiler',kim)->>'birim',proje) OR k10.ek_erisim(d,kim,proje); END $$;
-- gorunum_v9.proje_uyeleri: üyelik geçmişteki etkin bağları da korur.
CREATE FUNCTION k9.proje_uyeleri(d text,proje text) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc text[]='{}'; birimler text[]='{}'; x jsonb; e jsonb; g jsonb; s jsonb; h jsonb; kod text; oid text; k text; a text; n bigint; ss jsonb; baglar jsonb='{}'; sahipler jsonb='{}'; kisiler jsonb='{}'; erisim jsonb='{}'; BEGIN
 FOR x IN SELECT hal FROM motor.satirlar(d,'isler') UNION ALL SELECT hal FROM motor.satirlar(d,'gorevler') LOOP
  IF x->>'proje' IS DISTINCT FROM proje THEN CONTINUE; END IF; FOREACH a IN ARRAY ARRAY['kisi','atayan','veren','onaylayan'] LOOP sonuc=array_append(sonuc,x->>a); END LOOP;
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(x->'kisi_gecmisi','[]')) LOOP sonuc=array_append(sonuc,s->>'kisi'); END LOOP; IF irp.dogru(x->'birim') THEN birimler=array_append(birimler,x->>'birim'); END IF;
 END LOOP;
 SELECT birimler||coalesce(array_agg(hal->>'birim'),'{}') INTO birimler FROM motor.satirlar(d,'etaplar') WHERE hal->>'proje'=proje;
 sonuc=array_append(sonuc,motor.kayit(d,'projeler',proje)->>'sorumlu');
 FOR e IN SELECT value FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) ORDER BY value->>'oldugu_an',value->>'olay_kimligi' COLLATE "C" LOOP
  g=e->'girdiler'; kod=e->>'eylem_kodu'; oid=e->>'olay_kimligi'; IF saat.an(e->>'oldugu_an')>saat.simdi() THEN CONTINUE; END IF;
  IF kod='PROJE.ACTIM' AND coalesce(g->>'kimlik',g->>'kod')=proje THEN sonuc=array_append(sonuc,g->>'sorumlu'); END IF;
  IF kod='PROJE.DEGISTIRDIM' AND proje=ANY(kapi.hedefler(e,'PROJE')) THEN sonuc=array_append(sonuc,g#>>'{degisenler,sorumlu}'); END IF;
  IF kod IN ('GOREV.ATADIM','IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') THEN ss=coalesce(g->'gorevler',g->'isler',jsonb_build_array(g));
   FOR s,n IN SELECT * FROM jsonb_array_elements(ss) WITH ORDINALITY LOOP k=oid||CASE WHEN kod LIKE 'GOREV%' OR jsonb_array_length(ss)>1 THEN '/'||n ELSE '' END;
    baglar=baglar||jsonb_build_object(k,s->'proje'); sahipler=sahipler||jsonb_build_object(k,jsonb_build_array(e->'kim',s->'kisi',s->'onaylayan'));
    IF s->>'proje'=proje THEN sonuc=sonuc||irp.dizi(sahipler->k); IF irp.dogru(s->'birim') THEN birimler=array_append(birimler,s->>'birim'); END IF; END IF;
   END LOOP;
  END IF;
  FOR h IN SELECT value FROM jsonb_array_elements(e->'neyin_ustunde') WHERE value->>'tur' IN ('IS','GOREV') LOOP k=h->>'kimlik';
   IF kod IN ('IS.BAGLANTI_DUZELTTIM','GOREV.DEGISTIRDIM') AND g->'degisenler' ? 'proje' THEN baglar=baglar||jsonb_build_object(k,g#>'{degisenler,proje}'); END IF;
   IF kod IN ('IS.ATADIM','IS.DEVRETTIM','GOREV.DEGISTIRDIM','IS.ONAYLADIM','GOREV.ONAYLADIM') THEN s=coalesce(g->'degisenler',g); sahipler=sahipler||jsonb_build_object(k,coalesce(sahipler->k,'[]')||jsonb_build_array(e->'kim',s->'kisi',s->'kime',s->'onaylayan')||coalesce(s->'kisiler','[]')); END IF;
   IF baglar->>k=proje THEN sonuc=sonuc||irp.dizi(sahipler->k); END IF;
  END LOOP;
 END LOOP;
 FOREACH k IN ARRAY birimler LOOP sonuc=sonuc||yetki_v6.yoneticiler(d,k); END LOOP;
 FOR e IN SELECT value FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) ORDER BY saat.an(coalesce(value#>>'{girdiler,gecerli_baslangic}',value->>'oldugu_an')),value->>'olay_kimligi' COLLATE "C" LOOP
  g=e->'girdiler'; kod=e->>'eylem_kodu'; IF saat.an(coalesce(g->>'gecerli_baslangic',e->>'oldugu_an'))>saat.simdi() THEN CONTINUE; END IF;
  IF kod='BIRIM.TANIMLADIM' AND g->>'kod'=ANY(birimler) THEN sonuc=array_append(sonuc,g->>'basi'); END IF;
  IF kod='KISI.EKLEDIM' THEN kisiler=kisiler||jsonb_build_object(g->>'kod',g); END IF;
  IF kod='KISI.DEGISTIRDIM' AND kisiler ? (g->>'kisi') THEN kisiler=kisiler||jsonb_build_object(g->>'kisi',(kisiler->(g->>'kisi'))||(g->'degisenler')); END IF;
  k=CASE WHEN kod='KISI.EKLEDIM' THEN g->>'kod' WHEN kod='KISI.DEGISTIRDIM' THEN g->>'kisi' END; x=kisiler->k;
  IF x->>'birim'=ANY(birimler) AND x->'roller' ? 'EKIP_LIDERI' THEN sonuc=array_append(sonuc,k); END IF;
 END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(d,'proje_erisimleri') ORDER BY hal->>'an',hal->>'kimlik' COLLATE "C" LOOP IF x->>'proje'=proje THEN erisim=erisim||jsonb_build_object(x->>'kisi',x->'acik'); END IF; END LOOP;
 FOR k,x IN SELECT * FROM jsonb_each(erisim) LOOP IF irp.dogru(x) THEN sonuc=array_append(sonuc,k); END IF; END LOOP;
 RETURN ARRAY(SELECT z FROM (SELECT DISTINCT z FROM unnest(sonuc) z WHERE z IS NOT NULL) q ORDER BY z COLLATE "C"); END $$;
CREATE FUNCTION k9.proje_gorebilir(d text,kim text,proje text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE p text; k text; ps text[]; BEGIN
 IF NOT motor.oku(d,'projeler') ? proje OR NOT yetki_v6.istihdamda(d,kim,saat.simdi()) THEN RETURN false; END IF;
 IF motor.ayar(d,'proje_gorunurlugu',saat.simdi(),'"HERKES"')='"HERKES"' OR k10.projede_yetkili(d,kim,proje) THEN RETURN true; END IF;
 ps=ARRAY[proje,motor.kayit(d,'projeler',proje)->>'ana_proje']; SELECT ps||coalesce(array_agg(anahtar),'{}') INTO ps FROM motor.satirlar(d,'projeler') WHERE hal->>'ana_proje'=proje;
 FOREACH p IN ARRAY ps LOOP IF p IS NULL THEN CONTINUE; END IF; IF k10.projede_yetkili(d,kim,p) THEN RETURN true; END IF;
  FOREACH k IN ARRAY k9.proje_uyeleri(d,p) LOOP IF kim=k OR kim=ANY(yetki_v6.ustler(d,k)) THEN RETURN true; END IF; END LOOP;
 END LOOP; RETURN false; END $$;
-- gorunum_v9.bagli_projeler; not ve dosya çoklu hedeflerini dolaşır.
CREATE FUNCTION k9.bagli_projeler(d text,tur text,key text,gezilen text[] DEFAULT '{}') RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; hs jsonb; h jsonb; p text; oid text; sonuc text[]='{}'; a text; k text; BEGIN
 IF (tur||':'||key)=ANY(gezilen) THEN RETURN '{}'; END IF; gezilen=array_append(gezilen,tur||':'||key);
 IF tur='NOT' THEN hs=motor.kayit(d,'notlar',key)->'neyin_ustunde';
 ELSIF tur='DOSYA' THEN oid=motor.kayit(d,'dosyalar',key)->>'doguran_olay'; SELECT value->'neyin_ustunde' INTO hs FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) WHERE value->>'olay_kimligi'=oid LIMIT 1; hs=coalesce(hs,'[]');
  IF motor.oku(d,'notlar') ? oid THEN hs=hs||jsonb_build_array(jsonb_build_object('tur','NOT','kimlik',oid)); END IF;
  FOREACH a IN ARRAY ARRAY['isler','gorevler'] LOOP FOR k,x IN SELECT * FROM motor.satirlar(d,a) WHERE hal->>'doguran_olay'=oid LOOP hs=hs||jsonb_build_array(jsonb_build_object('tur',CASE WHEN a='isler' THEN 'IS' ELSE 'GOREV' END,'kimlik',k)); END LOOP; END LOOP;
 ELSE IF tur='PROJE' THEN p=CASE WHEN motor.oku(d,'projeler') ? key THEN key END; ELSE p=kapi.nesne(d,tur,key)->>'proje'; END IF; RETURN CASE WHEN p IS NOT NULL THEN ARRAY[p] ELSE '{}'::text[] END; END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(coalesce(hs,'[]')) LOOP sonuc=sonuc||k9.bagli_projeler(d,h->>'tur',h->>'kimlik',gezilen); END LOOP;
 RETURN ARRAY(SELECT DISTINCT z FROM unnest(sonuc) z); END $$;
CREATE FUNCTION k10.olay_projeleri(d text,e jsonb) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; sonuc text[]='{}'; s jsonb; h jsonb; BEGIN
 IF kod='PROJE.ACTIM' THEN RETURN '{}'; END IF;
 IF kod='PLAN.TARIHLEDIM' THEN FOR h IN SELECT value FROM jsonb_array_elements(g->'hedefler') LOOP sonuc=sonuc||k9.bagli_projeler(d,h->>'tur',h->>'kimlik'); END LOOP; END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(e->'neyin_ustunde') LOOP sonuc=sonuc||k9.bagli_projeler(d,h->>'tur',h->>'kimlik'); END LOOP;
 FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',g->'isler',jsonb_build_array(g))) LOOP IF irp.dogru(s->'proje') THEN sonuc=array_append(sonuc,s->>'proje'); END IF; END LOOP;
 IF irp.dogru(g#>'{degisenler,proje}') THEN sonuc=array_append(sonuc,g#>>'{degisenler,proje}'); END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(jsonb_build_array(g,coalesce(g->'degisenler','{}'))) LOOP FOR h IN SELECT value FROM jsonb_array_elements(coalesce(s->'baglar','[]')) WHERE value->>'tur'='PROJE' LOOP sonuc=array_append(sonuc,h->>'kimlik'); END LOOP; END LOOP;
 IF kod LIKE 'NESNE.%' AND irp.dogru(g->'hedef') THEN sonuc=sonuc||k9.bagli_projeler(d,'NESNE',g->>'hedef'); END IF;
 IF kod='GECIKME.DEGERLENDIRDIM' THEN s=k9.gecikme_hedefi(d,g->>'hedef'); IF irp.dogru(s->'proje') THEN sonuc=array_append(sonuc,s->>'proje'); END IF; END IF;
 RETURN ARRAY(SELECT DISTINCT z FROM unnest(sonuc) z); END $$;
CREATE FUNCTION k10.proje_yazma_kapisi(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; ps text[]; p text; x jsonb; s jsonb; h jsonb; k text; ks text[]; b text; BEGIN
 IF kod='NOT.YAZDIM' THEN FOR h IN SELECT value FROM jsonb_array_elements(e->'neyin_ustunde') WHERE value->>'tur'='NESNE' LOOP IF NOT motor.oku(d,'nesneler') ? (h->>'kimlik') THEN RETURN false; END IF; END LOOP; END IF;
 IF motor.ayar(d,'proje_gorunurlugu',saat.an(coalesce(e->>'oldugu_an',saat.kodla(yetki_v6.simdi(d)))),'"HERKES"')<>'"UYELER"' THEN RETURN true; END IF;
 ps=k10.olay_projeleri(d,e);
 IF kod='NOT.YAZDIM' THEN FOREACH p IN ARRAY ps LOOP IF NOT k9.proje_gorebilir(d,kim,p) THEN RETURN false; END IF; END LOOP; RETURN true; END IF;
 IF irp.sabit('taniklik') ? kod THEN RETURN true; END IF;
 IF kod='NESNE.ASAMA_GECIRDIM' THEN x=motor.kayit(d,'nesneler',g->>'hedef'); IF kim=x->>'sorumlu' THEN FOREACH p IN ARRAY ps LOOP IF NOT (CASE WHEN p=x->>'proje' THEN k9.proje_gorebilir(d,kim,p) ELSE k10.projede_yetkili(d,kim,p) END) THEN RETURN false; END IF; END LOOP; RETURN true; END IF; END IF;
 FOREACH p IN ARRAY ps LOOP IF NOT k10.projede_yetkili(d,kim,p) THEN RETURN false; END IF; END LOOP;
 IF kod IN ('GOREV.ATADIM','IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') THEN FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',g->'isler',jsonb_build_array(g))) LOOP p=s->>'proje'; IF p IS NULL THEN CONTINUE; END IF;
  b=coalesce(s->>'birim',motor.kayit(d,'kisiler',kim)->>'birim'); IF kod LIKE 'IS.%' AND NOT k10.birim_dahil(d,b,p) OR irp.dogru(s->'kisi') AND NOT k10.kisi_dahil(d,s->>'kisi',p) THEN RETURN false; END IF; END LOOP; END IF;
 IF kod IN ('IS.ATADIM','IS.DEVRETTIM') OR kod='GOREV.REDDETTIM' AND irp.dogru(g->'revizyon_ver') OR kod IN ('GOREV.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') AND g->'degisenler' ?| ARRAY['kisi','proje'] THEN
  FOR h IN SELECT value FROM jsonb_array_elements(e->'neyin_ustunde') WHERE value->>'tur' IN ('IS','GOREV') LOOP s=kapi.nesne(d,h->>'tur',h->>'kimlik')||coalesce(g->'degisenler','{}'); p=s->>'proje'; IF p IS NULL THEN CONTINUE; END IF;
   ks=CASE WHEN g ? 'kisiler' THEN irp.dizi(g->'kisiler') ELSE ARRAY[coalesce(g->>'kime',g->>'kisi',s->>'kisi')] END; FOREACH k IN ARRAY ks LOOP IF k IS NOT NULL AND NOT k10.kisi_dahil(d,k,p) THEN RETURN false; END IF; END LOOP;
   IF h->>'tur'='IS' AND NOT k10.birim_dahil(d,s->>'birim',p) THEN RETURN false; END IF;
  END LOOP;
 END IF; RETURN true; END $$;
CREATE FUNCTION k10_2.nesne_projesi(g jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE ps text[]; BEGIN IF irp.dogru(g->'proje') THEN RETURN g->>'proje'; END IF; SELECT array_agg(value->>'kimlik') INTO ps FROM jsonb_array_elements(coalesce(g->'baglar','[]')) WHERE value->>'tur'='PROJE'; RETURN CASE WHEN cardinality(ps)=1 THEN ps[1] END; END $$;
-- kurallar_v7 nesne kapıları ve yürütme dalları.
CREATE FUNCTION k7.baglar_gecerli(d text,tur jsonb,baglar jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE h jsonb; BEGIN FOR h IN SELECT value FROM jsonb_array_elements(coalesce(baglar,'[]')) LOOP IF NOT coalesce(tur->'baglanabilir_turler' ? (h->>'tur'),false) OR NOT irp.dogru(kapi.nesne(d,h->>'tur',h->>'kimlik')) THEN RETURN false; END IF; END LOOP; RETURN true; END $$;
CREATE FUNCTION k7.nesne_durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; x jsonb; tur jsonb; s jsonb; yol jsonb; a jsonb; b jsonb; asamalar jsonb; n int; BEGIN
 x=motor.kayit(d,'nesneler',g->>'hedef');
 IF kod='AYAR.DEGISTIRDIM' THEN RETURN true; END IF;
 IF kod='NESNE.ACTIM' THEN g=g||jsonb_build_object('proje',k10_2.nesne_projesi(g)); tur=motor.kayit(d,'nesne_turleri',g->>'tur'); RETURN irp.dogru(tur) AND NOT EXISTS(SELECT FROM motor.satirlar(d,'nesneler') WHERE hal->'tur'=g->'tur' AND hal->'ad'=g->'ad' AND hal->>'proje' IS NOT DISTINCT FROM g->>'proje') AND yetki_v6.istihdamda(d,g->>'sorumlu',saat.an(e->>'oldugu_an')) AND (NOT irp.dogru(g->'proje') OR irp.dogru(motor.kayit(d,'projeler',g->>'proje')->'aktif')) AND k7.baglar_gecerli(d,tur,g->'baglar');
 ELSIF kod='NESNE_TURU.TANIMLADIM' THEN
  SELECT jsonb_agg(CASE WHEN jsonb_typeof(value)='object' THEN value->'kod' ELSE value END) INTO asamalar FROM jsonb_array_elements(g->'asamalar');
  FOR x IN SELECT hal FROM motor.satirlar(d,'nesneler') WHERE hal->'tur'=g->'kod' LOOP SELECT coalesce(jsonb_agg(value->'asama'),'[]') INTO yol FROM jsonb_array_elements(x->'asama_gecmisi'); yol=yol||jsonb_build_array(x->'asama');
   FOR n IN 0..jsonb_array_length(yol)-1 LOOP a=yol->n; IF NOT asamalar @> jsonb_build_array(a) THEN RETURN false; END IF; IF n+1<jsonb_array_length(yol) THEN b=yol->(n+1); IF NOT EXISTS(SELECT FROM jsonb_array_elements(g->'gecisler') WHERE value->'den'=a AND value->'e'=b) THEN RETURN false; END IF; END IF; END LOOP;
  END LOOP; RETURN true;
 ELSIF kod='NESNE.ASAMA_GECIRDIM' THEN IF NOT irp.dogru(x) THEN RETURN false; END IF; tur=motor.kayit(d,'nesne_turleri',x->>'tur'); RETURN NOT EXISTS(SELECT FROM jsonb_array_elements(tur->'asamalar') WHERE jsonb_typeof(value)='object' AND irp.dogru(value->'son') AND value->'kod'=x->'asama') AND EXISTS(SELECT FROM jsonb_array_elements(tur->'gecisler') WHERE value->'den'=x->'asama' AND value->'e'=g->'yeni_asama');
 ELSIF kod='NESNE.GUNCELLEDIM' THEN s=g->'degisenler'; RETURN irp.dogru(x) AND NOT EXISTS(SELECT FROM jsonb_object_keys(s) a WHERE a<>ALL(ARRAY['ad','baglar','sorumlu','kod'])) AND (NOT irp.dogru(s->'sorumlu') OR motor.oku(d,'kisiler') ? (s->>'sorumlu')) AND k7.baglar_gecerli(d,motor.kayit(d,'nesne_turleri',x->>'tur'),s->'baglar'); END IF;
 RETURN NULL; END $$;
CREATE FUNCTION k7.nesne_yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; x jsonb; tur jsonb; b text; r jsonb; iliski boolean; BEGIN
 IF kod NOT IN ('NESNE.ACTIM','NESNE.ASAMA_GECIRDIM','NESNE.GUNCELLEDIM') THEN RETURN NULL; END IF;
 IF NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF; x=CASE WHEN kod='NESNE.ACTIM' THEN g ELSE motor.kayit(d,'nesneler',g->>'hedef',g) END;
 b=motor.kayit(d,'kisiler',x->>'sorumlu')->>'birim'; tur=motor.kayit(d,'nesne_turleri',x->>'tur');
 IF kod='NESNE.ACTIM' THEN RETURN k7.rol_izni(d,kim,coalesce(tur->'acabilenler','{}'),b); END IF;
 iliski=kim=x->>'sorumlu' OR kim=ANY(yetki_v6.ustler(d,x->>'sorumlu'));
 IF kod='NESNE.GUNCELLEDIM' THEN RETURN coalesce(iliski OR motor.kayit(d,'kisiler',kim)->'roller' ? 'YETKILI',false); END IF;
 SELECT value INTO r FROM jsonb_array_elements(tur->'gecisler') WHERE value->'den'=x->'asama' AND value->'e'=g->'yeni_asama' LIMIT 1;
 RETURN r IS NULL OR coalesce(iliski,false) OR k7.rol_izni(d,kim,r,b); END $$;
CREATE FUNCTION k7.nesne_isle(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; oid text=e->>'olay_kimligi'; t text=saat.kodla(saat.an(e->>'oldugu_an')); x jsonb; p text; BEGIN
 IF kod='AYAR.DEGISTIRDIM' THEN RETURN true;
 ELSIF kod='NESNE_TURU.TANIMLADIM' THEN PERFORM motor.kaydet(m,'nesne_turleri',g->>'kod',g);
 ELSIF kod='NESNE.ACTIM' THEN p=k10_2.nesne_projesi(g); IF p IS NOT NULL THEN g=g||jsonb_build_object('proje',p); END IF;
  x=g||jsonb_build_object('kimlik',oid,'asama',motor.kayit(m,'nesne_turleri',g->>'tur')->'baslangic_asamasi','asama_ani',t,'olusma_ani',t,'olusturan',e->'kim','asama_gecmisi','[]'::jsonb,'olaylar',jsonb_build_array(oid),'dosyalar',e->'kanit'); PERFORM motor.kaydet(m,'nesneler',oid,x);
 ELSIF kod IN ('NESNE.GUNCELLEDIM','NESNE.ASAMA_GECIRDIM') THEN x=motor.kayit(m,'nesneler',g->>'hedef'); x=x||jsonb_build_object('olaylar',(x->'olaylar')||jsonb_build_array(oid),'dosyalar',(x->'dosyalar')||(e->'kanit'));
  IF kod='NESNE.GUNCELLEDIM' THEN x=x||(g->'degisenler'); ELSE x=x||jsonb_build_object('asama_gecmisi',(x->'asama_gecmisi')||jsonb_build_array(jsonb_build_object('asama',x->'asama','baslangic',x->'asama_ani','bitis',t)),'asama',g->'yeni_asama','asama_ani',t); END IF; PERFORM motor.kaydet(m,'nesneler',g->>'hedef',x);
 ELSE RETURN false; END IF; RETURN true; END $$;
-- kurallar_v10.yetki: proje sorumlusu ve kök yönetimi ilişkileri.
CREATE FUNCTION k10.yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; p text; s text; iliski boolean; r jsonb; BEGIN
 IF NOT k10.proje_yazma_kapisi(d,e) THEN RETURN false; END IF;
 IF kod LIKE 'PROJE.ERISIM_%' AND motor.ayar(d,'proje_gorunurlugu',yetki_v6.simdi(d),'"HERKES"')='"UYELER"' THEN RETURN k10.projede_yetkili(d,kim,g->>'proje'); END IF;
 IF kod IN ('ETAP.TANIMLADIM','ETAP.DEGISTIRDIM','PLAN.ONAYLADIM') THEN
  IF NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
  p=coalesce(g->>'proje',(kapi.hedefler(e,'PROJE'))[1]); IF kod='ETAP.DEGISTIRDIM' THEN p=motor.kayit(d,'etaplar',e#>>'{neyin_ustunde,0,kimlik}')->>'proje'; END IF;
  s=motor.kayit(d,'projeler',p)->>'sorumlu'; iliski=s IS NOT NULL AND (kim=s OR kim=ANY(yetki_v6.ustler(d,s)));
  IF kod='PLAN.ONAYLADIM' THEN IF motor.ayar(d,'proje_gorunurlugu',yetki_v6.simdi(d),'"HERKES"')='"UYELER"' THEN RETURN iliski OR coalesce(motor.kayit(d,'kisiler',kim)->'roller' ? 'YETKILI',false); END IF; IF iliski THEN RETURN true; END IF; END IF;
  FOR r IN SELECT value FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) WHERE value->>'eylem_kodu'=kod AND NOT irp.dogru(value->'gecerli_bitis') LOOP
   IF r->'kimler' ? 'PROJE_SORUMLUSU' AND iliski OR r->'kimler' ? 'YETKILI' AND k10.genel_yonetim(d,kim) OR k7.rol_izni(d,kim,r) THEN RETURN true; END IF;
  END LOOP; RETURN false;
 END IF; RETURN NULL; END $$;
RESET ROLE;
