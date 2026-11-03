SET ROLE irp_sahibi;
-- gorev.py:8 son_teslim_ani, 13 puan, 23 gorev_dogur, 38 kapi.
CREATE FUNCTION gorev.son_teslim_ani(g jsonb,m text DEFAULT NULL) RETURNS timestamptz LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 BEGIN
 IF NOT irp.dogru((g->'teslim_tarihi')) THEN RETURN NULL; END IF;
 RETURN saat.gun_ani(((g->>'teslim_tarihi'))::date,coalesce(nullif((g->>'teslim_saati'),''),CASE WHEN m IS NOT NULL THEN motor.takvim(m,(g->>'teslim_tarihi'),(g->>'kisi'))->>'mesai_bitis' ELSE coalesce((g->>'takvim_teslim_saati'),'18:00') END)); END $$;
CREATE FUNCTION gorev.puan(g jsonb) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$ SELECT CASE WHEN (g->>'durum')<>'BITTI' THEN NULL WHEN (g->>'tur')='NOT' THEN 0 WHEN (g->>'tur') IN ('REVIZYON','DEGISIKLIK') AND irp.dogru((g->'sorumlulugu_dogrulandi')) THEN NULL ELSE ((g->>'zaman_degeri'))::numeric*CASE WHEN (g->>'tur')='ONAY' THEN 1 ELSE ((g->>'zorluk'))::numeric END END $$;
CREATE FUNCTION gorev.gorev_dogur(m text,e jsonb,satir jsonb,kimlik text,tur text DEFAULT 'NORMAL') RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE g jsonb; BEGIN
 g='{"on_kosul":[],"onay_gerekli":false,"dosya_gerekli":false,"zorluk":1}'::jsonb||satir||jsonb_build_object('kimlik',kimlik,'tur',tur,'doguran_olay',(e->'olay_kimligi'),'son_olay',(e->'olay_kimligi'),'kural_versiyonu',1,'atama_ani',(e->'oldugu_an'),'veren',(e->'kim'),'durum',CASE WHEN tur='ONAY' THEN 'ACIK' ELSE 'ATANDI' END,'kabul_ani',NULL,'ilk_teslim_ani',NULL,'teslim_ani',NULL,'onay_ani',NULL,'bitis_ani',NULL,'is_puani',NULL,'ilk_kabul_ani',NULL,'iptal_ani',NULL,'kisi_gecmisi',jsonb_build_array(jsonb_build_object('kisi',(satir->'kisi'),'baslangic',(e->'oldugu_an'))));
 g=g||jsonb_build_object('on_kosul',(SELECT coalesce(jsonb_agg(CASE WHEN jsonb_typeof(x)='object' THEN to_jsonb(((e->>'olay_kimligi'))||'/'||((x->>'satir'))) ELSE x END ORDER BY n),'[]') FROM jsonb_array_elements((g->'on_kosul')) WITH ORDINALITY z(x,n)));
 PERFORM motor.kaydet(m,'gorevler',kimlik,g); RETURN g; END $$;
CREATE FUNCTION gorev.kapi(m text,g jsonb,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); d text=(g->>'durum'); yapan boolean; BEGIN
 yapan=coalesce((e->>'adina'),(e->>'kim'))=(g->>'kisi') OR (e->>'kim')=ANY(yetki_v6.ustler(m,(g->>'kisi')));
 RETURN coalesce(CASE kod WHEN 'GOREV.KABUL_ETTIM' THEN d='ATANDI' AND yapan
 WHEN 'GOREV.TAMAMLADIM' THEN d IN ('ACIK','REDDEDILDI') AND yapan AND (NOT irp.dogru((g->'dosya_gerekli')) OR irp.dogru((e->'kanit')))
 WHEN 'GOREV.ONAYLADIM' THEN d='ONAY_BEKLIYOR' WHEN 'GOREV.REDDETTIM' THEN d='ONAY_BEKLIYOR'
 WHEN 'GOREV.DEGISTIRDIM' THEN d NOT IN ('BITTI','IPTAL') WHEN 'GOREV.IPTAL_ETTIM' THEN d NOT IN ('BITTI','IPTAL') ELSE true END,false); END $$;
-- gorev.py:53 bagimliliklari_hesapla; sabit noktaya en fazla 50 tur.
CREATE FUNCTION gorev.bagimliliklari_hesapla(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE tur integer; degisti boolean; k text; g jsonb; once jsonb; asil jsonb; rev jsonb; BEGIN
 FOR tur IN 1..50 LOOP degisti=false;
  FOR k IN SELECT anahtar FROM motor.satirlar(m,'gorevler') ORDER BY anahtar COLLATE "C" LOOP
   g=motor.kayit(m,'gorevler',k); once=g; asil=motor.kayit(m,'gorevler',(g->>'kaynak'));
   IF (g->>'tur') IN ('ONAY','REVIZYON') AND (asil->>'durum')='IPTAL' AND (g->>'durum') NOT IN ('BITTI','IPTAL') THEN g=g||jsonb_build_object('durum','IPTAL','iptal_ani',(asil->'iptal_ani')); END IF;
   IF (g->>'durum') IN ('ACIK','ON_IS_BEKLIYOR') THEN g=g||jsonb_build_object('durum',CASE WHEN EXISTS(SELECT FROM jsonb_array_elements_text((g->'on_kosul')) x WHERE coalesce(motor.kayit(m,'gorevler',x,motor.kayit(m,'isler',x))->>'durum','') NOT IN ('BITTI','IPTAL')) THEN 'ON_IS_BEKLIYOR' ELSE 'ACIK' END); END IF;
   rev=motor.kayit(m,'gorevler',(g->>'revizyon_gorevi'));
   IF (g->>'durum')='REVIZYONDA' AND (rev->>'durum')='BITTI' THEN g=g||jsonb_build_object('durum','BITTI','onay_ani',(rev->'onay_ani'),'bitis_ani',(rev->'bitis_ani')); ELSIF (g->>'durum')='REVIZYONDA' AND (rev->>'durum')='IPTAL' THEN g=g||'{"durum":"REDDEDILDI"}'; END IF;
   g=g||jsonb_build_object('is_puani',gorev.puan(g)); degisti=degisti OR once<>g; PERFORM motor.kaydet(m,'gorevler',k,g);
  END LOOP;
  IF NOT degisti THEN PERFORM motor.ekle(m,'yakinsama_turlari',to_jsonb(tur)); RETURN; END IF;
 END LOOP;
 PERFORM motor.ekle(m,'yakinsama_turlari','50'); PERFORM motor.yaz(m,'islenemedi','true'); PERFORM motor.ekle(m,'motor_hatalari',jsonb_build_object('hata','yakinsamadi','kirli',(SELECT jsonb_agg(anahtar ORDER BY anahtar COLLATE "C") FROM motor.satirlar(m,'gorevler')))); END $$;
-- gorev.py:76 bekletme_kayitlari.
CREATE FUNCTION gorev.bekletme_kayitlari(m text,t timestamptz) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE g jsonb; p text; on_ jsonb; son timestamptz; k text; BEGIN
 FOR g IN SELECT hal FROM motor.satirlar(m,'gorevler') WHERE (hal->>'durum')='ON_IS_BEKLIYOR' LOOP
  FOREACH p IN ARRAY irp.dizi((g->'on_kosul')) LOOP on_=motor.kayit(m,'gorevler',p); son=gorev.son_teslim_ani(on_,m);
   IF son IS NOT NULL AND t>son AND coalesce((on_->>'durum'),'') NOT IN ('BITTI','IPTAL') THEN k=p||':'||((g->>'kimlik'));
    IF NOT motor.oku(m,'bekletmeler') ? k THEN PERFORM motor.kaydet(m,'bekletmeler',k,jsonb_build_object('geciktiren',(on_->'kisi'),'on_kosul',p,'bekleyen',(g->'kimlik'),'an',saat.kodla(greatest(son,saat.an((g->>'kabul_ani')))))); END IF; END IF;
  END LOOP; END LOOP; END $$;
-- gorev.py:87 gorev_isle.
CREATE FUNCTION gorev.gorev_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); girdiler jsonb=(e->'girdiler'); t text=(e->>'oldugu_an'); g jsonb; s jsonb; k text; n bigint; once text; oran numeric; o jsonb; ok text; kisi text; onaylayan text;
BEGIN
 PERFORM gorev.bekletme_kayitlari(m,saat.an(t));
 IF kod='GOREV.ATADIM' THEN FOR s,n IN SELECT * FROM jsonb_array_elements((girdiler->'gorevler')) WITH ORDINALITY LOOP
  IF (s->>'kisi')=(e->>'kim') THEN PERFORM motor.supheli(m,e,'Kendine gorev'); END IF; PERFORM gorev.gorev_dogur(m,e,s,((e->>'olay_kimligi'))||'/'||n); END LOOP; RETURN; END IF;
 FOREACH k IN ARRAY kapi.hedefler(e,'GOREV') LOOP
  g=motor.kayit(m,'gorevler',k); IF NOT irp.dogru(g) THEN PERFORM motor.supheli(m,e,'Hedef gorev yok'); CONTINUE; END IF;
  IF NOT gorev.kapi(m,g,e) THEN PERFORM motor.supheli(m,e,'Gorev kapisi kapali'); IF NOT (kod='GOREV.TAMAMLADIM' AND (g->>'durum')='ATANDI' AND (g->>'kisi')=(e->>'kim')) THEN CONTINUE; END IF; END IF;
  once=(g->>'durum');
  IF kod='GOREV.KABUL_ETTIM' THEN g=g||jsonb_build_object('kabul_ani',t,'ilk_kabul_ani',coalesce((g->>'ilk_kabul_ani'),t),'durum',CASE WHEN (g->>'tur')='NOT' THEN 'BITTI' ELSE 'ACIK' END); IF (g->>'durum')='BITTI' THEN g=g||jsonb_build_object('bitis_ani',t); END IF;
  ELSIF kod='GOREV.TAMAMLADIM' THEN
   IF (g->>'durum')='ATANDI' THEN g=g||jsonb_build_object('kabul_ani',t,'ilk_kabul_ani',coalesce((g->>'ilk_kabul_ani'),t)); END IF;
   g=g||jsonb_build_object('ilk_teslim_ani',coalesce((g->>'ilk_teslim_ani'),t),'teslim_ani',t,'durum',CASE WHEN irp.dogru((g->'onay_gerekli')) THEN 'ONAY_BEKLIYOR' ELSE 'BITTI' END);
   IF irp.dogru((g->'onay_gerekli')) THEN oran=(motor.ayar(m,'onay_orani',saat.an(t),'0.1')#>>'{}')::numeric;
    s=g||jsonb_build_object('ad','Onay: '||((g->>'ad')),'kisi',(g->'onaylayan'),'kaynak',k,'zaman_degeri',floor(((g->>'zaman_degeri'))::numeric*oran+1e-12),'teslim_tarihi',NULL,'teslim_saati',NULL,'onay_gerekli',false,'dosya_gerekli',false,'on_kosul','[]'::jsonb,'zorluk',1);
    PERFORM gorev.gorev_dogur(m,e,s,(e->>'olay_kimligi'),'ONAY'); ELSE g=g||jsonb_build_object('bitis_ani',t); END IF;
  ELSIF kod IN ('GOREV.ONAYLADIM','GOREV.REDDETTIM') THEN
   FOR ok,o IN SELECT * FROM motor.satirlar(m,'gorevler') WHERE (hal->>'tur')='ONAY' AND (hal->>'kaynak')=k AND (hal->>'durum') NOT IN ('BITTI','IPTAL') LOOP
    IF (e->>'kim')=(g->>'onaylayan') THEN o=o||jsonb_build_object('durum','BITTI','onay_ani',t,'bitis_ani',t,'son_olay',(e->'olay_kimligi')); ELSE o=o||jsonb_build_object('durum','IPTAL','iptal_ani',t,'is_puani',NULL,'son_olay',(e->'olay_kimligi')); END IF; PERFORM motor.kaydet(m,'gorevler',ok,o); END LOOP;
   IF kod='GOREV.ONAYLADIM' THEN g=g||jsonb_build_object('durum','BITTI','onay_ani',t,'bitis_ani',t);
   ELSE g=g||jsonb_build_object('durum',CASE WHEN irp.dogru((girdiler->'revizyon_ver')) THEN 'REVIZYONDA' ELSE 'REDDEDILDI' END); PERFORM motor.ekle(m,'retler',jsonb_build_object('olay',(e->'olay_kimligi'),'gorev',k,'an',t)||girdiler);
    IF irp.dogru((girdiler->'revizyon_ver')) THEN ok=((e->>'olay_kimligi'))||'/1'; s=g||jsonb_build_object('ad','Revizyon: '||((g->>'ad')),'kisi',(girdiler->'kime'),'kaynak',k,'zaman_degeri',(girdiler->'zaman_degeri'),'teslim_tarihi',(girdiler->'yeni_teslim_tarihi'),'sebep_olan',(girdiler->'sebep_olan'),'revizyon_gorevi',NULL,'on_kosul','[]'::jsonb); PERFORM gorev.gorev_dogur(m,e,s,ok,'REVIZYON'); g=g||jsonb_build_object('revizyon_gorevi',ok); END IF; END IF;
  ELSIF kod='GOREV.DEGISTIRDIM' THEN
   kisi=(g->>'kisi'); onaylayan=(g->>'onaylayan'); g=g||((girdiler->'degisenler'));
   IF (g->>'kisi') IS DISTINCT FROM kisi THEN g=g||jsonb_build_object('durum','ATANDI','kisi_gecmisi',((g->'kisi_gecmisi'))||jsonb_build_array(jsonb_build_object('kisi',(g->'kisi'),'baslangic',t))); END IF;
   IF (g->>'onaylayan') IS DISTINCT FROM onaylayan THEN FOR ok,o IN SELECT * FROM motor.satirlar(m,'gorevler') WHERE (hal->>'tur')='ONAY' AND (hal->>'kaynak')=k AND (hal->>'durum') NOT IN ('BITTI','IPTAL') LOOP
    o=o||jsonb_build_object('durum','IPTAL','iptal_ani',t); PERFORM motor.kaydet(m,'gorevler',ok,o); PERFORM gorev.gorev_dogur(m,e,o||jsonb_build_object('kisi',(g->'onaylayan')),((e->>'olay_kimligi'))||'/1','ONAY'); END LOOP; END IF;
  ELSIF kod='GOREV.IPTAL_ETTIM' THEN g=g||jsonb_build_object('durum','IPTAL','iptal_ani',t); END IF;
  g=g||jsonb_build_object('son_olay',(e->'olay_kimligi')); PERFORM motor.kaydet(m,'gorevler',k,g); PERFORM motor.sonuc(m,e,'R15',k,once,(g->>'durum'));
 END LOOP; PERFORM gorev.bagimliliklari_hesapla(m);
END $$;
RESET ROLE;
