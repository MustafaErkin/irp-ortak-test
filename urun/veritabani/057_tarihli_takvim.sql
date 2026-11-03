SET ROLE irp_sahibi;
-- takvim_v7 / takvim_v9: yarı açık aralıklar ve tarihli takvim bağlamı.
CREATE FUNCTION takvim.pencere(g jsonb) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT jsonb_build_array(saat.kodla(CASE WHEN position('T' IN g->>'baslangic')>0 THEN saat.an(g->>'baslangic') ELSE saat.gun_ani(saat.gun(g->>'tarih'),g->>'baslangic') END),
 saat.kodla(CASE WHEN position('T' IN g->>'bitis')>0 THEN saat.an(g->>'bitis') ELSE saat.gun_ani(saat.gun(g->>'tarih'),g->>'bitis') END)) $$;
CREATE FUNCTION takvim.birlesim(xs jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; x jsonb; a timestamptz; b timestamptz; n int;
BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(xs) ORDER BY saat.an(value->>0),saat.an(value->>1) LOOP
  a=saat.an(x->>0); b=saat.an(x->>1); IF a>=b THEN CONTINUE; END IF; n=jsonb_array_length(r);
  IF n>0 AND a<=saat.an((r->(n-1))->>1) THEN r=jsonb_set(r,ARRAY[(n-1)::text,'1'],to_jsonb(saat.kodla(greatest(b,saat.an((r->(n-1))->>1)))));
  ELSE r=r||jsonb_build_array(jsonb_build_array(saat.kodla(a),saat.kodla(b))); END IF;
 END LOOP; RETURN r;
END $$;
CREATE FUNCTION takvim.cikar(xs jsonb,engeller jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb=xs; yeni jsonb; x jsonb; e jsonb; a timestamptz; b timestamptz; p timestamptz; q timestamptz;
BEGIN
 FOR e IN SELECT value FROM jsonb_array_elements(takvim.birlesim(engeller)) LOOP
  p=saat.an(e->>0); q=saat.an(e->>1); yeni='[]';
  FOR x IN SELECT value FROM jsonb_array_elements(sonuc) LOOP a=saat.an(x->>0); b=saat.an(x->>1);
   IF greatest(a,p)>=least(b,q) THEN yeni=yeni||jsonb_build_array(x); CONTINUE; END IF;
   IF a<p THEN yeni=yeni||jsonb_build_array(jsonb_build_array(saat.kodla(a),saat.kodla(p))); END IF;
   IF q<b THEN yeni=yeni||jsonb_build_array(jsonb_build_array(saat.kodla(q),saat.kodla(b))); END IF;
  END LOOP; sonuc=yeni;
 END LOOP; RETURN sonuc;
END $$;
CREATE FUNCTION takvim.birim_takvimi(m text,tarih text,kisi text DEFAULT NULL,birim text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE b text=birim; x jsonb;
BEGIN
 IF b IS NULL AND kisi IS NOT NULL THEN
  SELECT value->>2 INTO b FROM jsonb_array_elements(motor.kayit(m,'_v9_kisi_birimleri',kisi,'[]')) WHERE saat.an(value->>0)<=saat.gun_ani(saat.gun(tarih)) ORDER BY saat.an(value->>0) DESC,(value->>1) COLLATE "C" DESC LIMIT 1;
  b=coalesce(b,motor.kayit(m,'kisiler',kisi)->>'birim');
 END IF;
 SELECT value->2 INTO x FROM jsonb_array_elements(motor.kayit(m,'_v9_birim_takvimleri',b,'[]')) WHERE saat.gun(value->>0)<=saat.gun(tarih) ORDER BY saat.gun(value->>0) DESC,(value->>1) COLLATE "C" DESC LIMIT 1;
 RETURN x||jsonb_build_object('calisma_gunleri',x->'gunler');
END $$;
CREATE FUNCTION takvim.normal(m text,tarih date,mola boolean DEFAULT true,kisi text DEFAULT NULL,birim text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t jsonb; xs jsonb; engeller jsonb;
BEGIN
 IF NOT motor.is_gunu(m,tarih::text,kisi,birim) THEN RETURN '[]'; END IF;
 t=motor.takvim(m,tarih::text,kisi,birim);
 xs=jsonb_build_array(jsonb_build_array(saat.kodla(saat.gun_ani(tarih,t->>'mesai_baslangic')),saat.kodla(saat.gun_ani(tarih,t->>'mesai_bitis'))));
 IF NOT mola THEN RETURN xs; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_array(saat.kodla(saat.gun_ani(tarih,x->>'bas')),saat.kodla(saat.gun_ani(tarih,x->>'bit')))),'[]') INTO engeller FROM jsonb_array_elements(t->'sabit_molalar') x;
 RETURN takvim.cikar(xs,engeller);
END $$;
CREATE FUNCTION takvim.izinler(m text,kisi text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_array(hal->'baslangic',hal->'bitis')),'[]') FROM motor.satirlar(m,'izinler') WHERE hal->>'kisi'=kisi AND hal->>'durum'='ONAYLI' $$;
CREATE FUNCTION takvim.ekler(m text,kisi text,tarih date DEFAULT NULL,gercek boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; engeller jsonb='[]'; x jsonb; p jsonb; a timestamptz; b timestamptz; gun date;
BEGIN
 IF gercek AND motor.kayit(m,'kisiler',kisi)->>'yaka' IS DISTINCT FROM 'MAVI' THEN RETURN sonuc; END IF;
 FOR x IN SELECT hal FROM motor.satirlar(m,'ek_mesai_planlari') WHERE hal->>'kisi'=kisi AND NOT irp.dogru(hal->'iptal') LOOP
  p=takvim.pencere(x); a=saat.an(p->>0); b=saat.an(p->>1);
  IF tarih IS NOT NULL THEN a=greatest(a,saat.gun_ani(tarih)); b=least(b,saat.gun_ani(tarih+1)); END IF;
  IF a<b THEN sonuc=sonuc||jsonb_build_array(jsonb_build_array(saat.kodla(a),saat.kodla(b))); END IF;
 END LOOP; sonuc=takvim.birlesim(sonuc);
 FOR p IN SELECT value FROM jsonb_array_elements(sonuc) LOOP
  gun=saat.gun(p->>0); WHILE gun<=saat.gun(p->>1) LOOP engeller=engeller||takvim.normal(m,gun,false,kisi); gun=gun+1; END LOOP;
 END LOOP; RETURN takvim.cikar(sonuc,engeller);
END $$;
CREATE FUNCTION takvim.kisi_normal(m text,kisi text,tarih date) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN yetki_v6.istihdamda(m,kisi,saat.gun_ani(tarih)) THEN takvim.cikar(takvim.normal(m,tarih,true,kisi),takvim.izinler(m,kisi)) ELSE '[]'::jsonb END $$;
CREATE FUNCTION takvim.katsayi(m text,tarih date) RETURNS numeric LANGUAGE sql STABLE AS $$
 SELECT (motor.ayar(m,'fazla_mesai_katsayilari',saat.gun_ani(tarih),'{"TATIL":2,"PAZAR":2,"CUMARTESI":1.5,"HAFTA_ICI":1.5}')->>CASE WHEN NOT motor.is_gunu(m,tarih::text) AND motor.oku(m,'tatiller','[]') ? tarih::text THEN 'TATIL' WHEN extract(isodow FROM tarih)=7 THEN 'PAZAR' WHEN extract(isodow FROM tarih)=6 THEN 'CUMARTESI' ELSE 'HAFTA_ICI' END)::numeric $$;
CREATE FUNCTION takvim.birim_kapsamda(m text,b text,kapsam jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE birim text=b; gorulen text[]='{}';
BEGIN
 IF kapsam='"FIRMA"' THEN RETURN true; END IF;
 WHILE birim IS NOT NULL AND birim<>'' AND NOT birim=ANY(gorulen) LOOP
  IF kapsam ? birim THEN RETURN true; END IF; gorulen=array_append(gorulen,birim); birim=motor.kayit(m,'birimler',birim)->>'ust_birim';
 END LOOP; RETURN false;
END $$;
CREATE FUNCTION takvim.kesinti(m text,kisi text,t timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; n jsonb=takvim.normal(m,saat.gun(saat.kodla(t)),false,kisi);
BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(takvim.izinler(m,kisi)) LOOP
  IF saat.an(x->>0)<=t AND t<saat.an(x->>1) AND saat.an(n#>>'{0,0}')<=t AND t<saat.an(n#>>'{0,1}') THEN RETURN '["IZIN",null]'; END IF;
 END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(m,'duruslar') LOOP
  IF saat.an(x->>'baslangic')<=t AND (NOT irp.dogru(x->'bitis') OR t<saat.an(x->>'bitis')) AND takvim.birim_kapsamda(m,motor.kayit(m,'kisiler',kisi)->>'birim',x->'kapsam') THEN RETURN jsonb_build_array('BEKLEME_DURUS',x->'neden'); END IF;
 END LOOP; RETURN NULL;
END $$;
CREATE FUNCTION takvim.katman_guncelle(m text,t timestamptz) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kisi text; d jsonb; hedef jsonb; once jsonb; yeni jsonb;
BEGIN
 FOR kisi IN SELECT anahtar FROM motor.satirlar(m,'kisi_durumu') UNION SELECT hal->>'kisi' FROM motor.satirlar(m,'izinler') WHERE hal->>'durum'='ONAYLI' LOOP
  d=motor.kayit(m,'kisi_durumu',kisi,kg.bos_hal()); PERFORM motor.kaydet(m,'kisi_durumu',kisi,d);
  IF NOT yetki_v6.istihdamda(m,kisi,t) THEN CONTINUE; END IF; hedef=takvim.kesinti(m,kisi,t);
  IF hedef IS NOT NULL AND hedef->>0<>'IZIN' AND d->>'durum'='MESAI_DISI' THEN CONTINUE; END IF;
  IF hedef->>0='BEKLEME_DURUS' AND motor.sabit_molada(m,t,kisi) THEN hedef='["SABIT_MOLA",null]'; END IF;
  IF hedef IS NOT NULL THEN
   once=coalesce(d->'_kesinti_onceki',CASE WHEN d->>'durum'='SABIT_MOLADA' THEN d->'mola_onceki' ELSE d END);
   yeni=d||jsonb_build_object('durum',CASE WHEN hedef->>0='IZIN' THEN 'IZINLI' ELSE 'DURUSTA' END,'kova',hedef->0,'aralik_is',NULL,'neden',hedef->1,'_kesinti_onceki',once);
   PERFORM kg.hal_yaz(m,kisi,yeni,t,NULL,'T8_KESINTI');
  ELSIF d ? '_kesinti_onceki' THEN
   yeni=d->'_kesinti_onceki'; IF yeni->>'durum' IN ('CALISIYOR','MOLADA','DEVAM_BEKLIYOR') THEN yeni=yeni||jsonb_build_object('durum',CASE WHEN irp.dogru(yeni->'acik_is') THEN 'DEVAM_BEKLIYOR' ELSE 'CALISMIYOR' END,'kova','TANIMSIZ','aralik_is',NULL,'neden',NULL); END IF;
   PERFORM kg.hal_yaz(m,kisi,yeni,t,NULL,'T8_KESINTI');
  END IF;
 END LOOP;
END $$;
CREATE FUNCTION takvim.nokta_kisiye_ait(m text,kisi text,kod text,t timestamptz) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE tak jsonb=motor.takvim(m,saat.kodla(t),kisi); gun date=saat.gun(saat.kodla(t));
BEGIN
 IF kod='PAYDOS' THEN RETURN t=saat.gun_ani(gun,tak->>'mesai_bitis'); END IF;
 IF kod IN ('MOLA_BASI','MOLA_SONU') THEN RETURN EXISTS(SELECT FROM jsonb_array_elements(tak->'sabit_molalar') x WHERE t=saat.gun_ani(gun,x->>CASE WHEN kod='MOLA_BASI' THEN 'bas' ELSE 'bit' END)); END IF;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION takvim.sistem_isle(m text,kod text,t timestamptz) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kisi text; d jsonb; eski text; ek jsonb;
BEGIN
 IF kod IN ('MOLA_BASI','MOLA_SONU') THEN
  FOR kisi,d IN SELECT * FROM motor.satirlar(m,'kisi_durumu') LOOP
   IF d->>'durum'='MESAI_DISI' OR d ? '_kesinti_onceki' OR NOT takvim.nokta_kisiye_ait(m,kisi,kod,t) THEN CONTINUE; END IF;
   PERFORM kg.uygula(m,kisi,kod,t);
  END LOOP; PERFORM takvim.katman_guncelle(m,t); RETURN;
 END IF;
 IF kod='V7_IZIN' THEN PERFORM takvim.katman_guncelle(m,t); RETURN; END IF;
 FOR kisi,d IN SELECT * FROM motor.satirlar(m,'kisi_durumu') LOOP
  IF d->>'durum'='MESAI_DISI' OR NOT takvim.nokta_kisiye_ait(m,kisi,kod,t) THEN CONTINUE; END IF;
  ek=takvim.ekler(m,kisi,NULL,true);
  IF EXISTS(SELECT FROM jsonb_array_elements(ek) x WHERE saat.an(x->>0)<=t AND t<saat.an(x->>1)) THEN CONTINUE; END IF;
  IF kod='V7_EK_BITIS' AND NOT EXISTS(SELECT FROM jsonb_array_elements(ek) x WHERE saat.an(x->>1)=t) THEN CONTINUE; END IF;
  eski=d->>'acik_is'; PERFORM kg.uygula(m,kisi,'PAYDOS',t);
  PERFORM motor.kaydet(m,'kisi_durumu',kisi,motor.kayit(m,'kisi_durumu',kisi)-'_kesinti_onceki');
  IF motor.kayit(m,'isler',eski)->>'durum'='CALISILIYOR' THEN PERFORM motor.kaydet(m,'isler',eski,motor.kayit(m,'isler',eski)||'{"durum":"YARIM"}'); END IF;
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION takvim.aralik_ekle(m text,kisi text,d jsonb,bitis timestamptz,e jsonb DEFAULT NULL,kural text DEFAULT NULL,sistem boolean DEFAULT false) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE i jsonb=motor.kayit(m,'isler',d->>'aralik_is'); bas timestamptz=saat.an(d->>'baslangic'); son timestamptz=least(coalesce(bitis,saat.simdi()),saat.simdi()); tarih date=saat.gun(saat.kodla(bas)); normal_p jsonb; ek_p jsonb; tum jsonb; p jsonb; x timestamptz; y timestamptz; a timestamptz; b timestamptz; sinirlar timestamptz[]; n int; fm boolean; acik boolean;
BEGIN
 WHILE tarih<=saat.gun(saat.kodla(son)) LOOP
  IF motor.oku(m,'kisiler') ? kisi AND NOT yetki_v6.istihdamda(m,kisi,saat.gun_ani(tarih)) THEN tarih=tarih+1; CONTINUE; END IF;
  normal_p=takvim.normal(m,tarih,false,kisi); ek_p=takvim.ekler(m,kisi,tarih,true); tum=takvim.birlesim(normal_p||ek_p);
  FOR p IN SELECT value FROM jsonb_array_elements(tum) LOOP
   x=greatest(bas,saat.an(p->>0)); y=least(son,saat.an(p->>1)); IF x>=y THEN CONTINUE; END IF;
   SELECT array_agg(z ORDER BY z) INTO sinirlar FROM (SELECT x z UNION SELECT y UNION SELECT saat.an(v#>>'{}') FROM jsonb_array_elements(normal_p||ek_p) w CROSS JOIN LATERAL jsonb_array_elements(w) v WHERE saat.an(v#>>'{}')>x AND saat.an(v#>>'{}')<y) s;
   FOR n IN 1..cardinality(sinirlar)-1 LOOP
    a=sinirlar[n]; b=sinirlar[n+1]; fm=d->>'kova' IN ('CALISMA','YENIDEN_ISLEME') AND EXISTS(SELECT FROM jsonb_array_elements(ek_p) w WHERE saat.an(w->>0)<=a AND b<=saat.an(w->>1));
    acik=bitis IS NULL AND b=son AND NOT EXISTS(SELECT FROM jsonb_array_elements(tum) w WHERE b=saat.an(w->>1));
    PERFORM motor.ekle(m,'araliklar',jsonb_build_object('kisi',kisi,'gun',tarih::text,'baslangic',saat.kodla(a),'bitis',CASE WHEN NOT acik THEN saat.kodla(b) END,'kova',d->'kova','is',d->'aralik_is','proje',i->'proje','kategori',i->'kategori','tezgah',NULL,'neden',d->'neden','plansiz',coalesce(i->'plansiz','false'),'sistem_kapatti',sistem,'elle',false,'aciklama',NULL,'yazan',NULL,'acan_olay',d->'acan_olay','kapatan_olay',e->'olay_kimligi','acan_kural',d->'acan_kural','kapatan_kural',kural,'kural_versiyonu',1,'fazla_mesai',fm,'katsayi',CASE WHEN fm THEN takvim.katsayi(m,tarih) ELSE 1 END));
   END LOOP;
  END LOOP; tarih=tarih+1;
 END LOOP;
END $$;
CREATE FUNCTION takvim.hazirla(m text,es jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE e jsonb; g jsonb; kod text; oid text; x jsonb; s jsonb; n bigint; k text; a text; hedef jsonb; tat jsonb=motor.oku(m,'tatiller','[]');
BEGIN
 FOREACH a IN ARRAY ARRAY['gun_tanimlari','ek_mesai_planlari','izinler','_v9_birim_takvimleri','_v9_kisi_birimleri'] LOOP PERFORM motor.yaz(m,a,'{}'); END LOOP;
 FOR e IN SELECT value FROM jsonb_array_elements(es) LOOP
  PERFORM motor.butce_denetle();
  g=e->'girdiler'; kod=e->>'eylem_kodu'; oid=e->>'olay_kimligi';
  IF kod='GUN.TANIMLADIM' THEN PERFORM motor.kaydet(m,'gun_tanimlari',g->>'tarih',g);
   tat=(SELECT coalesce(jsonb_agg(value),'[]') FROM jsonb_array_elements(tat) WHERE value<>g->'tarih'); IF g->>'tur'='TATIL' THEN tat=tat||jsonb_build_array(g->'tarih'); END IF;
  ELSIF kod IN ('GUN.KALDIRDIM','TATIL.KALDIRDIM','TATIL.EKLEDIM') THEN
   PERFORM motor.yaz(m,'gun_tanimlari',motor.oku(m,'gun_tanimlari')-(g->>'tarih'));
   tat=(SELECT coalesce(jsonb_agg(value),'[]') FROM jsonb_array_elements(tat) WHERE value<>g->'tarih'); IF kod='TATIL.EKLEDIM' THEN tat=tat||jsonb_build_array(g->'tarih'); END IF;
  END IF;
  IF kod IN ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM') THEN PERFORM motor.kaydet(m,'ek_mesai_planlari',oid,g||jsonb_build_object('kimlik',oid,'damga',kod='EK_MESAI.ONAYLADIM','hedef',e->'neyin_ustunde','iptal',false));
  ELSIF kod='EK_MESAI.IPTAL_ETTIM' AND motor.oku(m,'ek_mesai_planlari') ? (g->>'hedef') THEN PERFORM motor.kaydet(m,'ek_mesai_planlari',g->>'hedef',motor.kayit(m,'ek_mesai_planlari',g->>'hedef')||'{"iptal":true}');
  ELSIF kod IN ('IS.ATADIM','GOREV.ATADIM') THEN
   FOR s,n IN SELECT * FROM jsonb_array_elements(coalesce(g->'gorevler',jsonb_build_array(g))) WITH ORDINALITY LOOP
    IF NOT irp.dogru(s->'ek_mesai') THEN CONTINUE; END IF;
    FOREACH k IN ARRAY irp.dizi(coalesce(s->'kisiler',jsonb_build_array(s->'kisi'))) LOOP
     a=oid||'/ek/'||n||'/'||k; hedef=CASE WHEN kod='GOREV.ATADIM' THEN jsonb_build_array(jsonb_build_object('tur','GOREV','kimlik',oid||'/'||n)) ELSE e->'neyin_ustunde' END;
     PERFORM motor.kaydet(m,'ek_mesai_planlari',a,(s->'ek_mesai')||jsonb_build_object('kimlik',a,'kisi',k,'damga',false,'hedef',hedef,'iptal',false));
    END LOOP;
   END LOOP;
  END IF;
  IF kod='IZIN.TALEP_ETTIM' THEN PERFORM motor.kaydet(m,'izinler',oid,g||jsonb_build_object('kimlik',oid,'durum','TALEP','olay',e));
  ELSIF kod LIKE 'IZIN.%' AND motor.oku(m,'izinler') ? (g->>'hedef') THEN
   x=motor.kayit(m,'izinler',g->>'hedef');
   IF kod='IZIN.ONAYLADIM' THEN x=x||jsonb_build_object('durum',CASE WHEN irp.dogru(motor.ayar(m,'izin_ik_onayi',saat.an(e->>'oldugu_an'),'{}')->(x->>'tur')) THEN 'IK_BEKLIYOR' ELSE 'ONAYLI' END,'onaylayan',e->'kim');
   ELSIF kod='IZIN.IK_ONAYLADIM' THEN x=x||'{"durum":"ONAYLI"}';
   ELSIF kod='IZIN.REDDETTIM' THEN x=x||jsonb_build_object('durum',CASE WHEN x->>'durum'='IK_BEKLIYOR' THEN 'RET' ELSE 'REDDEDILDI' END,'gerekce',g->'gerekce');
   ELSIF kod='IZIN.IPTAL_ETTIM' THEN x=x||'{"durum":"IPTAL"}'; END IF;
   PERFORM motor.kaydet(m,'izinler',g->>'hedef',x);
  END IF;
  IF kod='BIRIM.TANIMLADIM' AND irp.dogru(g->'takvim') THEN k=g->>'kod'; PERFORM motor.kaydet(m,'_v9_birim_takvimleri',k,motor.kayit(m,'_v9_birim_takvimleri',k,'[]')||jsonb_build_array(jsonb_build_array(g->'takvim_gecerli',oid,g->'takvim'))); END IF;
  IF kod='KISI.EKLEDIM' THEN k=g->>'kod'; x=jsonb_build_array(g->'giris_tarihi',oid,g->'birim');
  ELSIF kod='KISI.DEGISTIRDIM' AND (g->'degisenler') ? 'birim' THEN k=g->>'kisi'; x=jsonb_build_array(g->'gecerli_baslangic',oid,g#>'{degisenler,birim}'); ELSE CONTINUE; END IF;
  PERFORM motor.kaydet(m,'_v9_kisi_birimleri',k,motor.kayit(m,'_v9_kisi_birimleri',k,'[]')||jsonb_build_array(x));
 END LOOP; PERFORM motor.yaz(m,'tatiller',tat);
END $$;
RESET ROLE;
