SET ROLE irp_sahibi;
-- kurallar_v10_2.HEDEF_TABLOLARI ve kayit_turu: sıra modeldeki sözlük sırasıdır.
CREATE FUNCTION k10_2.hedef_tablolari() RETURNS TABLE(tur text,tablo text) LANGUAGE sql IMMUTABLE AS $$
 SELECT * FROM (VALUES ('IZIN','izinler'),('EK_MESAI','ek_mesai_planlari'),('DURUS','duruslar'),('BAKIM','bakimlar'),('SORUMLULUK','sorumluluklar'),('ITIRAZ','itirazlar'),('NESNE','nesneler'),('IS','isler'),('GOREV','gorevler'),('PROJE','projeler'),('ETAP','etaplar'),('KISI','kisiler'),('BIRIM','birimler'),('TEZGAH','tezgahlar'),('NESNE_TURU','nesne_turleri'),('MODUL','moduller'),('NOT','notlar'),('KOD','kod_listesi'),('DOSYA','dosyalar')) t(tur,tablo) $$;
CREATE FUNCTION k10_2.kayit_turu(d text,key text) RETURNS text LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r record; BEGIN FOR r IN SELECT * FROM k10_2.hedef_tablolari() LOOP IF motor.oku(d,r.tablo) ? key THEN RETURN r.tur; END IF; END LOOP; RETURN 'OLAY'; END $$;
CREATE FUNCTION k10_2.kayit(d text,tur text,key text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t text; BEGIN SELECT tablo INTO t FROM k10_2.hedef_tablolari() x WHERE x.tur=tur; RETURN motor.kayit(d,t,key); END $$;
CREATE FUNCTION k10_2.ek(hs jsonb,tur text,key text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT CASE WHEN key IS NULL OR key='' THEN hs ELSE hs||jsonb_build_array(jsonb_build_array(tur,key)) END $$;
CREATE FUNCTION k10_2.ic_basvurular(d text,s jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE hs jsonb='[]'; x jsonb; deg jsonb=s->'degisiklik'; BEGIN
 hs=k10_2.ek(hs,'PROJE',s->>'ana_proje'); hs=k10_2.ek(hs,'KISI',s->>'sebep_olan'); hs=k10_2.ek(hs,'KISI',s->>'basi');
 FOR x IN SELECT value FROM jsonb_array_elements(coalesce(s->'sorumlular','[]')) WHERE value->>'tur' IN ('KISI','BIRIM') LOOP hs=k10_2.ek(hs,x->>'tur',x->>'kimlik'); END LOOP;
 IF irp.dogru(deg) THEN hs=k10_2.ek(hs,k10_2.kayit_turu(d,deg->>'kaynak'),deg->>'kaynak'); hs=hs||k10_2.ic_basvurular(d,deg); END IF; RETURN hs; END $$;
CREATE FUNCTION k10_2.takvim_kayitlari(d text,kisi text,bas timestamptz,bitis timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE hs jsonb='[["TAKVIM","FIRMA"]]'; b text=motor.kayit(d,'kisiler',kisi)->>'birim'; seen text[]='{}'; tarih date; BEGIN
 hs=k10_2.ek(hs,'KISI',kisi); WHILE b IS NOT NULL AND NOT b=ANY(seen) LOOP seen=array_append(seen,b); hs=k10_2.ek(hs,'BIRIM',b); b=motor.kayit(d,'birimler',b)->>'ust_birim'; END LOOP;
 tarih=saat.gun(saat.kodla(bas)); WHILE tarih<=saat.gun(saat.kodla(bitis-interval '1 microsecond')) LOOP hs=k10_2.ek(hs,'TAKVIM_GUNU',tarih::text); tarih=tarih+1; END LOOP; RETURN hs; END $$;
CREATE FUNCTION k10_2.dayandigi_kayitlar(d text,e jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; hs jsonb='[]'; h jsonb; s jsonb; x jsonb; y jsonb; r record; key text; k text; a text; tur text; t text; seen text[]; todo jsonb; ps text[]; bas timestamptz; bit timestamptz; BEGIN
 FOR h IN SELECT value FROM jsonb_array_elements(e->'neyin_ustunde') LOOP hs=k10_2.ek(hs,h->>'tur',h->>'kimlik'); END LOOP; hs=hs||k10_2.ic_basvurular(d,g); hs=k10_2.ek(hs,'KISI',e->>'adina');
 IF irp.dogru(g->'hedef') AND kod<>'AYAR.SAAT_KAYDIRDIM' THEN key=g->>'hedef'; hs=k10_2.ek(hs,k10_2.kayit_turu(d,key),key);
  IF kod LIKE 'SORUMLULUK.%' THEN s=k9.sorumluluk_satiri(d,g); hs=k10_2.ek(hs,'OLAY',s->>'ret');
   FOR k,x IN SELECT * FROM motor.satirlar(d,'sorumluluklar') WHERE hal->'ret'=s->'ret' LOOP hs=k10_2.ek(hs,'SORUMLULUK',k); END LOOP;
  END IF;
 END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(coalesce(g->'hedefler','[]')) LOOP hs=k10_2.ek(hs,h->>'tur',h->>'kimlik'); END LOOP;
 FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'isler',g->'gorevler',jsonb_build_array(coalesce(g->'degisenler',g)))) LOOP hs=hs||k10_2.ic_basvurular(d,s);
  FOR a,tur IN SELECT * FROM (VALUES ('proje','PROJE'),('etap','ETAP'),('birim','BIRIM'),('tezgah','TEZGAH'),('nesne','NESNE'),('kisi','KISI'),('sorumlu','KISI'),('onaylayan','KISI')) q LOOP hs=k10_2.ek(hs,tur,s->>a); END LOOP;
  FOR key IN SELECT value#>>'{}' FROM jsonb_array_elements(coalesce(s->'on_isler','[]')||coalesce(s->'on_kosul','[]')) WHERE jsonb_typeof(value)='string' LOOP hs=k10_2.ek(hs,k10_2.kayit_turu(d,key),key); END LOOP;
  FOR h IN SELECT value FROM jsonb_array_elements(coalesce(s->'baglar','[]')) LOOP hs=k10_2.ek(hs,h->>'tur',h->>'kimlik'); END LOOP;
  FOREACH k IN ARRAY irp.dizi(s->'roller') LOOP hs=k10_2.ek(hs,'KOD','ROL:'||k); END LOOP;
  IF irp.dogru(s->'kategori') THEN hs=k10_2.ek(hs,'KOD','PD:'||(s->>'kategori')); END IF;
  IF irp.dogru(s->'yetkinlik') THEN hs=k10_2.ek(hs,'KOD','YETKINLIK:'||(s->>'yetkinlik')); END IF;
 END LOOP;
 FOREACH a IN ARRAY ARRAY['kisi','kimden','kime'] LOOP hs=k10_2.ek(hs,'KISI',g->>a); END LOOP;
 FOREACH k IN ARRAY irp.dizi(g->'kisiler') LOOP hs=k10_2.ek(hs,'KISI',k); END LOOP;
 FOREACH k IN ARRAY irp.dizi(g->'yetkinlikler') LOOP hs=k10_2.ek(hs,'KOD','YETKINLIK:'||k); END LOOP;
 FOREACH k IN ARRAY irp.dizi(g->'dosyalar') LOOP hs=k10_2.ek(hs,'DOSYA',k); END LOOP;
 FOREACH k IN ARRAY irp.dizi(g->'kimler') LOOP hs=k10_2.ek(hs,'KOD','ROL:'||k); END LOOP;
 IF kod='KOD.TANIMLADIM' THEN hs=k10_2.ek(hs,'KOD',(g->>'liste')||':'||(g->>'kod'));
  IF g->>'liste'='DURUS_NEDENI' THEN IF irp.dogru(g->'ust') THEN hs=k10_2.ek(hs,'KOD','DURUS_NEDENI:'||(g->>'ust')); END IF; FOR key,x IN SELECT * FROM motor.satirlar(d,'kod_listesi') WHERE hal->>'liste'='DURUS_NEDENI' AND hal->'ust'=g->'kod' LOOP hs=k10_2.ek(hs,'KOD',key); END LOOP; END IF;
 END IF;
 IF kod='YETKI.TANIMLADIM' THEN hs=k10_2.ek(hs,'YETKI',g->>'eylem_kodu'); END IF;
 IF kod LIKE 'AYAR.%' AND kod<>'AYAR.SAAT_KAYDIRDIM' THEN hs=k10_2.ek(hs,'AYAR',coalesce(nullif(g->>'anahtar',''),split_part(kod,'.',2))); END IF;
 IF kod='TAKVIM.TANIMLADIM' THEN hs=k10_2.ek(hs,'TAKVIM','FIRMA'); END IF;
 IF kod='GUN_ONAYI.AYARLADIM' THEN hs=k10_2.ek(hs,'GUN_ONAY_AYARI',g->>'birim'); END IF;
 IF kod LIKE 'GUN.%' OR kod LIKE 'TATIL.%' THEN hs=k10_2.ek(hs,'TAKVIM_GUNU',g->>'tarih'); END IF;
 IF kod='PROJE.ACTIM' THEN hs=k10_2.ek(hs,'PROJE',g->>'kod'); END IF;
 IF kod='MAAS.GUNCELLEDIM' AND motor.oku(d,'tezgahlar') ? (g->>'kisi') THEN hs=k10_2.ek(hs,'TEZGAH',g->>'kisi'); END IF;
 IF kod='BIRIM.TANIMLADIM' THEN key=g->>'ust_birim'; seen='{}'; WHILE key IS NOT NULL AND NOT key=ANY(seen) LOOP seen=array_append(seen,key); hs=k10_2.ek(hs,'BIRIM',key); key=motor.kayit(d,'birimler',key)->>'ust_birim'; END LOOP; hs=k10_2.ek(hs,'KISI',g->>'basi'); END IF;
 FOREACH k IN ARRAY kapilar_v3.liste_hedefleri(e) LOOP hs=k10_2.ek(hs,'LISTE',k); END LOOP;
 FOR h IN SELECT value FROM jsonb_array_elements(hs) LOOP tur=h->>0; key=h->>1;
  IF tur='LISTE' THEN FOREACH k IN ARRAY irp.dizi(motor.kayit(d,'listeler',key,'[]')) LOOP hs=k10_2.ek(hs,'IS',k); END LOOP; END IF;
  x=k10_2.kayit(d,tur,key);
  IF tur IN ('IS','GOREV') THEN
   FOR a,t IN SELECT * FROM (VALUES ('proje','PROJE'),('etap','ETAP'),('birim','BIRIM'),('tezgah','TEZGAH'),('nesne','NESNE'),('kisi','KISI'),('onaylayan','KISI')) q LOOP hs=k10_2.ek(hs,t,x->>a); END LOOP;
   IF kod='IS.DEVAM_ONAYLADIM' AND irp.dogru(x->'kisi') THEN hs=k10_2.ek(hs,'KISI_GUNU',(x->>'kisi')||':'||saat.gun(saat.kodla(saat.simdi()))); END IF;
   todo=coalesce(x->'on_isler','[]')||coalesce(x->'on_kosul','[]'); seen='{}';
   WHILE jsonb_array_length(todo)>0 LOOP s=todo->(jsonb_array_length(todo)-1); todo=todo-(jsonb_array_length(todo)-1); IF jsonb_typeof(s)<>'string' THEN CONTINUE; END IF; k=s#>>'{}'; IF k=ANY(seen) THEN CONTINUE; END IF; seen=array_append(seen,k); t=k10_2.kayit_turu(d,k); hs=k10_2.ek(hs,t,k); y=k10_2.kayit(d,t,k); todo=todo||coalesce(y->'on_isler','[]')||coalesce(y->'on_kosul','[]'); END LOOP;
   IF tur='IS' AND kod='IS.DEGISTIRDIM' THEN FOR k IN SELECT anahtar FROM motor.satirlar(d,'isler') WHERE hal->>'ana_is'=key LOOP hs=k10_2.ek(hs,'IS',k); END LOOP; END IF;
  END IF;
 END LOOP;
 IF kod='NESNE.ACTIM' THEN hs=k10_2.ek(hs,'NESNE_TURU',g->>'tur'); END IF;
 IF kod LIKE 'NESNE.%' AND irp.dogru(g->'hedef') THEN hs=k10_2.ek(hs,'NESNE_TURU',motor.kayit(d,'nesneler',g->>'hedef')->>'tur'); END IF;
 IF kod='NESNE_TURU.TANIMLADIM' THEN FOR k IN SELECT anahtar FROM motor.satirlar(d,'nesneler') WHERE hal->'tur'=g->'kod' LOOP hs=k10_2.ek(hs,'NESNE',k); END LOOP; END IF;
 IF kod='MODUL.TANIMLADIM' THEN FOR k IN SELECT anahtar FROM motor.satirlar(d,'moduller') LOOP hs=k10_2.ek(hs,'MODUL',k); END LOOP; END IF;
 IF kod='KISI.AYRILDI' OR kod='KISI.DEGISTIRDIM' AND g->'degisenler' ? 'roller' THEN
  FOR k IN SELECT anahtar FROM motor.satirlar(d,'kisiler') LOOP hs=k10_2.ek(hs,'KISI',k); END LOOP;
  IF kod='KISI.AYRILDI' THEN hs=k10_2.ek(hs,'LISTE',g->>'kisi'); FOR k IN SELECT anahtar FROM motor.satirlar(d,'gorevler') WHERE g->'kisi' IN (hal->'kisi',hal->'onaylayan') LOOP hs=k10_2.ek(hs,'GOREV',k); END LOOP; FOR k IN SELECT anahtar FROM motor.satirlar(d,'birimler') LOOP hs=k10_2.ek(hs,'BIRIM',k); END LOOP; END IF; hs=k10_2.ek(hs,'AYAR','izin_ik_onayi');
 END IF;
 IF kod='AYAR.DEGISTIRDIM' AND g->>'anahtar'='izin_ik_onayi' THEN FOR k IN SELECT anahtar FROM motor.satirlar(d,'kisiler') LOOP hs=k10_2.ek(hs,'KISI',k); END LOOP; END IF;
 IF kod='KOD.TANIMLADIM' AND g->>'liste'='ROL' AND g->>'kod'='IK' THEN hs=k10_2.ek(hs,'AYAR','izin_ik_onayi'); END IF;
 IF kod LIKE 'EK_MESAI.%' OR kod LIKE 'IZIN.%' THEN x=k10_2.kayit(d,k10_2.kayit_turu(d,g->>'hedef'),g->>'hedef'); k=coalesce(x->>'kisi',g->>'kisi'); hs=k10_2.ek(hs,'KISI',k); FOR r IN SELECT * FROM (VALUES ('IZIN','izinler'),('EK_MESAI','ek_mesai_planlari')) q(tur,tablo) LOOP FOR key IN SELECT anahtar FROM motor.satirlar(d,r.tablo) WHERE hal->>'kisi'=k LOOP hs=k10_2.ek(hs,r.tur,key); END LOOP; END LOOP; END IF;
 IF kod IN ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM') THEN hs=hs||k10_2.takvim_kayitlari(d,g->>'kisi',saat.an(takvim.pencere(g)->>0),saat.an(takvim.pencere(g)->>1)); END IF;
 IF kod IN ('IS.ATADIM','GOREV.ATADIM') THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',jsonb_build_array(g))) LOOP
   IF NOT irp.dogru(s->'ek_mesai') THEN CONTINUE; END IF;
   FOREACH k IN ARRAY irp.dizi(coalesce(s->'kisiler',jsonb_build_array(s->'kisi'))) LOOP
    hs=hs||k10_2.takvim_kayitlari(d,k,saat.an(takvim.pencere(s->'ek_mesai')->>0),saat.an(takvim.pencere(s->'ek_mesai')->>1));
    FOR r IN SELECT * FROM (VALUES ('IZIN','izinler'),('EK_MESAI','ek_mesai_planlari')) q(tur,tablo) LOOP FOR key IN SELECT anahtar FROM motor.satirlar(d,r.tablo) WHERE hal->>'kisi'=k LOOP hs=k10_2.ek(hs,r.tur,key); END LOOP; END LOOP;
   END LOOP;
  END LOOP;
 END IF;
 IF kod='IS.SURE_EKLEDIM' THEN hs=hs||k10_2.takvim_kayitlari(d,e->>'adina',saat.an(g->>'baslangic'),saat.an(g->>'bitis')); END IF;
 IF kod IN ('PLAN.ONAYLADIM','PROJE.KAPATTIM') THEN SELECT array_agg(value->>1) INTO ps FROM jsonb_array_elements(hs) WHERE value->>0='PROJE'; FOREACH tur IN ARRAY ARRAY['ETAP','IS','GOREV'] LOOP SELECT tablo INTO a FROM k10_2.hedef_tablolari() h WHERE h.tur=tur; FOR key IN SELECT anahtar FROM motor.satirlar(d,a) WHERE hal->>'proje'=ANY(ps) LOOP hs=k10_2.ek(hs,tur,key); END LOOP; END LOOP; END IF;
 IF kod LIKE 'GUN_SONU.%' THEN FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gunler',jsonb_build_array(g))) LOOP k=coalesce(s->>'kisi',e->>'adina',e->>'kim'); hs=k10_2.ek(hs,'KISI',k); hs=k10_2.ek(hs,'KISI_GUNU',k||':'||(s->>'gun')); END LOOP; END IF;
 IF kod IN ('BIRIM.TANIMLADIM','TEZGAH.TANIMLADIM','KISI.EKLEDIM','NESNE_TURU.TANIMLADIM','MODUL.TANIMLADIM') THEN hs=k10_2.ek(hs,split_part(kod,'.',1),g->>'kod'); END IF;
 RETURN (SELECT coalesce(jsonb_agg(value),'[]') FROM (SELECT DISTINCT value FROM jsonb_array_elements(hs)) q); END $$;
CREATE FUNCTION k10_2.kaydin_olaylari(d text,tur text,key text) RETURNS SETOF jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb=k10_2.kayit(d,tur,key); dogum text; e jsonb; g jsonb; kod text; ait boolean; a text; BEGIN
 dogum=coalesce(x->>'doguran_olay',CASE WHEN key LIKE 'K%-%' THEN split_part(key,'/',1) END);
 FOR e IN SELECT icerik FROM public.olaylar WHERE olay_kimligi NOT IN (SELECT icerik#>>'{girdiler,hedef}' FROM public.olaylar WHERE eylem_kodu='KAYIT.GECERSIZ_SAYDIM') ORDER BY kabul_no LOOP
  g=e->'girdiler'; kod=e->>'eylem_kodu'; ait=coalesce(e->>'olay_kimligi'=dogum,false) OR tur='OLAY' AND e->>'olay_kimligi'=key OR key=ANY(kapi.hedefler(e,tur)) OR g->>'hedef'=key AND kod<>'AYAR.SAAT_KAYDIRDIM' OR EXISTS(SELECT FROM jsonb_array_elements(coalesce(g->'hedefler','[]')) h WHERE h->>'tur'=tur AND h->>'kimlik'=key);
  ait=coalesce(ait,false);
  IF tur IN ('KISI','BIRIM','TEZGAH','NESNE_TURU','MODUL','PROJE') AND starts_with(kod,tur||'.') THEN FOREACH a IN ARRAY ARRAY['kisi','kod','proje','kimlik','tezgah','birim'] LOOP ait=ait OR coalesce(g->>a=key,false); END LOOP; END IF;
  IF tur='PROJE' THEN ait=ait OR kod='PLAN.ONAYLADIM' AND g->>'proje'=key; END IF;
  IF tur='KISI_GUNU' THEN ait=ait OR coalesce(e->>'adina',e->>'kim')=split_part(key,':',1) AND saat.gun(e->>'oldugu_an')::text=split_part(key,':',2) OR kod LIKE 'GUN_SONU.%' AND EXISTS(SELECT FROM jsonb_array_elements(coalesce(g->'gunler',jsonb_build_array(g))) s WHERE s->>'kisi'=split_part(key,':',1) AND s->>'gun'=split_part(key,':',2)); END IF;
  IF tur='LISTE' THEN ait=ait OR key=ANY(kapilar_v3.liste_hedefleri(e)); END IF;
  IF tur='KOD' THEN ait=ait OR kod='KOD.TANIMLADIM' AND (g->>'liste')||':'||(g->>'kod')=key; END IF;
  IF tur='YETKI' THEN ait=ait OR kod='YETKI.TANIMLADIM' AND g->>'eylem_kodu'=key; END IF;
  IF tur='AYAR' THEN ait=ait OR kod LIKE 'AYAR.%' AND coalesce(nullif(g->>'anahtar',''),split_part(kod,'.',2))=key; END IF;
  IF tur='TAKVIM' THEN ait=ait OR kod='TAKVIM.TANIMLADIM'; END IF;
  IF tur='GUN_ONAY_AYARI' THEN ait=ait OR kod='GUN_ONAYI.AYARLADIM' AND g->>'birim'=key; END IF;
  IF tur='DOSYA' THEN ait=ait OR EXISTS(SELECT FROM jsonb_array_elements(e->'kanit') z WHERE z->>'dosya_kimligi'=key); END IF;
  IF tur='TAKVIM_GUNU' THEN ait=ait OR (kod LIKE 'GUN.%' OR kod LIKE 'TATIL.%') AND g->>'tarih'=key; END IF;
  IF tur='BIRIM' THEN ait=ait OR kod='AYAR.YONLENDIRDIM' AND g->>'birim'=key; END IF;
  IF ait THEN RETURN NEXT e; END IF;
 END LOOP; END $$;
CREATE OR REPLACE FUNCTION k10_2.sira_siniri(d text,e jsonb) RETURNS text LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sinir text=motor.konum(saat.an(e->>'oldugu_an'),1,e->>'olay_kimligi'); h jsonb; x jsonb; BEGIN
 IF NOT EXISTS(SELECT FROM public.olaylar WHERE konum>sinir COLLATE "C" AND olay_kimligi NOT IN (SELECT icerik#>>'{girdiler,hedef}' FROM public.olaylar WHERE eylem_kodu='KAYIT.GECERSIZ_SAYDIM')) THEN RETURN NULL; END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(k10_2.dayandigi_kayitlar(d,e)) ORDER BY (value->>0) COLLATE "C",(value->>1) COLLATE "C" LOOP
  FOR x IN SELECT * FROM k10_2.kaydin_olaylari(d,h->>0,h->>1) LOOP IF motor.konum(saat.an(x->>'oldugu_an'),1,x->>'olay_kimligi')>sinir COLLATE "C" THEN RETURN x->>'olay_kimligi'; END IF; END LOOP;
 END LOOP; RETURN NULL; END $$;
RESET ROLE;
