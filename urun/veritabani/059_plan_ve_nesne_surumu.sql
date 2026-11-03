SET ROLE irp_sahibi;
-- kurallar_v10_1.surum_satirlari, gecerli ve bagli_nesneler.
CREATE FUNCTION k10_1.gecerli(d text,hedef text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; BEGIN SELECT hal INTO x FROM motor.satirlar(d,'nesne_surumleri') WHERE hal->>'nesne'=hedef AND hal->>'durum'='ONAYLI' ORDER BY (hal->>'surum_no')::int DESC LIMIT 1; RETURN x; END $$;
CREATE FUNCTION k10_1.bagli_nesneler(d text,tur text,key text,x jsonb) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE baglar text[]=CASE WHEN irp.dogru(x->'nesne') THEN ARRAY[x->>'nesne'] ELSE '{}'::text[] END; e jsonb; duzeltme boolean; hs text[]; BEGIN
 FOR e IN SELECT value FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) LOOP
  IF saat.an(e->>'oldugu_an')>yetki_v6.simdi(d) THEN CONTINUE; END IF;
  duzeltme=e->>'eylem_kodu'='IS.BAGLANTI_DUZELTTIM' AND key=ANY(kapi.hedefler(e,tur));
  IF NOT (e->>'olay_kimligi'=x->>'doguran_olay' OR duzeltme) THEN CONTINUE; END IF;
  hs=kapi.hedefler(e,'NESNE'); IF cardinality(hs)>0 THEN baglar=hs; END IF;
  IF duzeltme AND e#>'{girdiler,degisenler}' ? 'nesne' THEN baglar=CASE WHEN irp.dogru(e#>'{girdiler,degisenler,nesne}') THEN ARRAY[e#>>'{girdiler,degisenler,nesne}'] ELSE '{}'::text[] END; END IF;
 END LOOP; RETURN baglar; END $$;
CREATE FUNCTION k10_2.bir_basamak(d text,hedef text) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc text[]=ARRAY[hedef]; k text; x jsonb; bs text[]; BEGIN
 FOR k,x IN SELECT * FROM motor.satirlar(d,'nesneler') LOOP SELECT coalesce(array_agg(value->>'kimlik'),'{}') INTO bs FROM jsonb_array_elements(coalesce(x->'baglar','[]')) WHERE value->>'tur'='NESNE'; IF k=hedef THEN sonuc=sonuc||bs; END IF; IF hedef=ANY(bs) THEN sonuc=array_append(sonuc,k); END IF; END LOOP;
 RETURN ARRAY(SELECT DISTINCT z FROM unnest(sonuc) z); END $$;
CREATE FUNCTION k10_1.onaylayabilir(d text,kim text,nesne jsonb,surum jsonb DEFAULT NULL) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE r jsonb; BEGIN IF NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) OR kim=surum->>'ekleyen' THEN RETURN false; END IF;
 r=motor.kayit(d,'nesne_turleri',nesne->>'tur')->'surum_onaylayanlar'; IF NOT irp.dogru(r) THEN RETURN kim=ANY(yetki_v6.ustler(d,nesne->>'sorumlu')); END IF;
 RETURN k7.rol_izni(d,kim,r,motor.kayit(d,'kisiler',nesne->>'sorumlu')->>'birim'); END $$;
CREATE FUNCTION k10_1.yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; h jsonb; x jsonb; s jsonb; p text; BEGIN
 IF NOT irp.sabit('kabul_sirali') ? kod THEN RETURN NULL; END IF;
 IF irp.dogru(e->'adina') OR NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 IF kod='MODUL.TANIMLADIM' THEN RETURN coalesce(motor.kayit(d,'kisiler',kim)->'roller' ? 'YETKILI',false); END IF;
 IF kod='PLAN.TARIHLEDIM' THEN
  FOR h IN SELECT value FROM jsonb_array_elements(g->'hedefler') LOOP x=kapi.nesne(d,h->>'tur',h->>'kimlik'); IF NOT irp.dogru(x) THEN CONTINUE; END IF;
   IF h->>'tur'='GOREV' AND NOT irp.dogru(x->'proje') THEN IF kim IS DISTINCT FROM x->>'veren' AND NOT kim=ANY(yetki_v6.ustler(d,x->>'veren')) THEN RETURN false; END IF;
   ELSIF NOT EXISTS(SELECT FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) r WHERE r->>'eylem_kodu'=kod AND NOT irp.dogru(r->'gecerli_bitis') AND k7.rol_izni(d,kim,r,coalesce(x->>'birim',motor.kayit(d,'kisiler',x->>'kisi')->>'birim'))) THEN RETURN false; END IF;
   IF irp.dogru(x->'proje') AND motor.ayar(d,'proje_gorunurlugu',yetki_v6.simdi(d),'"HERKES"')='"UYELER"' AND NOT k10.projede_yetkili(d,kim,x->>'proje') THEN RETURN false; END IF;
  END LOOP; RETURN true;
 END IF;
 x=motor.kayit(d,'nesneler',g->>'hedef');
 IF NOT k10.proje_yazma_kapisi(d,e) THEN IF kod<>'NESNE.SURUM_EKLEDIM' OR kim IS DISTINCT FROM x->>'sorumlu' THEN RETURN false; END IF;
  FOREACH p IN ARRAY k10.olay_projeleri(d,e) LOOP IF NOT (CASE WHEN p=x->>'proje' THEN k9.proje_gorebilir(d,kim,p) ELSE k10.projede_yetkili(d,kim,p) END) THEN RETURN false; END IF; END LOOP;
 END IF;
 IF NOT irp.dogru(x) THEN RETURN true; END IF;
 IF kod='NESNE.SURUM_EKLEDIM' THEN RETURN coalesce(kim=x->>'sorumlu' OR kim=ANY(yetki_v6.ustler(d,x->>'sorumlu')) OR motor.kayit(d,'kisiler',kim)->'roller' ? 'YETKILI',false); END IF;
 SELECT hal INTO s FROM motor.satirlar(d,'nesne_surumleri') WHERE hal->'nesne'=g->'hedef' AND hal->'surum_no'=g->'surum_no' LIMIT 1;
 RETURN k10_1.onaylayabilir(d,kim,x,s); END $$;
CREATE FUNCTION k10_1.durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; h jsonb; x jsonb; ss jsonb; s jsonb; no int; ad text; t timestamptz=saat.an(e->>'oldugu_an'); son timestamptz; a text; BEGIN
 IF kod='PLAN.TARIHLEDIM' THEN FOR h IN SELECT value FROM jsonb_array_elements(g->'hedefler') LOOP x=kapi.nesne(d,h->>'tur',h->>'kimlik'); IF NOT irp.dogru(x) OR x->>'durum' IN ('BITTI','IPTAL') THEN RETURN false; END IF; END LOOP; RETURN true; END IF;
 IF kod='MODUL.TANIMLADIM' THEN
  x=motor.kayit(d,'moduller',g->>'kod'); IF irp.dogru(x->'cihaz_harfi') AND x->'cihaz_harfi' IS DISTINCT FROM g->'cihaz_harfi' THEN RETURN false; END IF;
  IF irp.dogru(g->'cihaz_harfi') AND (EXISTS(SELECT FROM motor.satirlar(d,'moduller') WHERE hal->'kod'<>g->'kod' AND hal->'cihaz_harfi'=g->'cihaz_harfi') OR EXISTS(SELECT FROM public.cihaz_harfleri WHERE hal=g->'cihaz_harfi') OR EXISTS(SELECT FROM public.olaylar WHERE right(olay_kimligi,1)=g->>'cihaz_harfi' AND icerik->>'cihaz' NOT LIKE 'MODUL-%')) THEN RETURN false; END IF;
  RETURN NOT EXISTS(SELECT FROM motor.satirlar(d,'moduller') WHERE hal->'kod'<>g->'kod' AND hal->'servis_kimligi'=g->'servis_kimligi');
 END IF;
 IF kod NOT LIKE 'NESNE.SURUM_%' THEN RETURN NULL; END IF; x=motor.kayit(d,'nesneler',g->>'hedef'); IF NOT irp.dogru(x) OR t<saat.an(x->>'olusma_ani') THEN RETURN false; END IF;
 SELECT coalesce(jsonb_agg(hal ORDER BY (hal->>'surum_no')::int),'[]') INTO ss FROM motor.satirlar(d,'nesne_surumleri') WHERE hal->'nesne'=g->'hedef';
 IF kod='NESNE.SURUM_EKLEDIM' THEN no=coalesce((e->>'nesne_surum_no')::int,jsonb_array_length(ss)+1); ad=coalesce(nullif(trim(g->>'surum_adi'),''),no::text);
  RETURN NOT EXISTS(SELECT FROM jsonb_array_elements(ss) s WHERE s->>'surum_adi'=ad OR (s->>'surum_no')::int=no) AND NOT EXISTS(SELECT FROM jsonb_array_elements_text(g->'dosyalar') f WHERE NOT motor.oku(d,'dosyalar') ? f AND NOT EXISTS(SELECT FROM jsonb_array_elements(e->'kanit') z WHERE z->>'dosya_kimligi'=f)); END IF;
 SELECT value INTO s FROM jsonb_array_elements(ss) WHERE value->'surum_no'=g->'surum_no' LIMIT 1; son=NULL; FOREACH a IN ARRAY ARRAY['eklenme_ani','onay_ani','geri_cekme_ani'] LOOP son=greatest(son,saat.an(s->>a)); END LOOP; son=coalesce(son,t);
 RETURN t>=son AND coalesce(s->>'durum'=ANY(CASE WHEN kod='NESNE.SURUM_ONAYLADIM' THEN ARRAY['TASLAK'] ELSE ARRAY['TASLAK','ONAYLI'] END),false); END $$;
CREATE FUNCTION k10_1.isle(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; oid text=e->>'olay_kimligi'; t text=saat.kodla(saat.an(e->>'oldugu_an')); h jsonb; x jsonb; s jsonb; once jsonb; sonra jsonb; no int; key text; hedef text; a text; k text; bagli text[]; ks text[]; alicilar text[]='{}'; BEGIN
 IF NOT irp.sabit('kabul_sirali') ? kod THEN RETURN false; END IF;
 IF NOT k10_1.durum(m,e) THEN PERFORM motor.supheli(m,e,'T10 karari yeniden hesapta duruma uymuyor'); RETURN true; END IF;
 IF kod='MODUL.TANIMLADIM' THEN PERFORM motor.kaydet(m,'moduller',g->>'kod',g);
 ELSIF kod='PLAN.TARIHLEDIM' THEN FOR h IN SELECT value FROM jsonb_array_elements(g->'hedefler') LOOP a=CASE WHEN h->>'tur'='IS' THEN 'isler' ELSE 'gorevler' END; key=h->>'kimlik'; x=motor.kayit(m,a,key); PERFORM motor.kaydet(m,a,key,x||jsonb_build_object('planlanan_baslangic',saat.kodla(saat.an(h->>'planlanan_baslangic')),'planlanan_bitis',saat.kodla(saat.an(h->>'planlanan_bitis')))); END LOOP;
 ELSE hedef=g->>'hedef'; once=k10_1.gecerli(m,hedef);
  IF kod='NESNE.SURUM_EKLEDIM' THEN SELECT count(*)+1 INTO no FROM motor.satirlar(m,'nesne_surumleri') WHERE hal->>'nesne'=hedef; no=coalesce((e->>'nesne_surum_no')::int,no); key=hedef||'/surum/'||no;
   s=jsonb_build_object('kimlik',key,'nesne',hedef,'surum_no',no,'surum_adi',coalesce(nullif(trim(g->>'surum_adi'),''),no::text),'dosyalar',g->'dosyalar','aciklama',coalesce(g->>'aciklama',''),'durum','TASLAK','ekleyen',e->'kim','eklenme_ani',t,'onaylayan',NULL,'onay_ani',NULL,'geri_ceken',NULL,'geri_cekme_ani',NULL,'gerekce',NULL,'doguran_olay',oid);
  ELSE SELECT anahtar,hal INTO key,s FROM motor.satirlar(m,'nesne_surumleri') WHERE hal->>'nesne'=hedef AND hal->'surum_no'=g->'surum_no' LIMIT 1;
   IF kod='NESNE.SURUM_ONAYLADIM' THEN s=s||jsonb_build_object('durum','ONAYLI','onaylayan',e->'kim','onay_ani',t); ELSE s=s||jsonb_build_object('durum','GERI_CEKILDI','geri_ceken',e->'kim','geri_cekme_ani',t,'gerekce',g->'gerekce'); END IF;
  END IF; PERFORM motor.kaydet(m,'nesne_surumleri',key,s); x=motor.kayit(m,'nesneler',hedef); PERFORM motor.kaydet(m,'nesneler',hedef,x||jsonb_build_object('olaylar',(x->'olaylar')||jsonb_build_array(oid))); sonra=k10_1.gecerli(m,hedef);
  IF once->'surum_no' IS DISTINCT FROM sonra->'surum_no' THEN bagli=k10_2.bir_basamak(m,hedef);
   FOREACH a IN ARRAY ARRAY['isler','gorevler'] LOOP FOR key,x IN SELECT * FROM motor.satirlar(m,a) LOOP
    IF x->>'durum' IN ('BITTI','IPTAL') OR NOT bagli&&k10_1.bagli_nesneler(m,CASE WHEN a='isler' THEN 'IS' ELSE 'GOREV' END,key,x) THEN CONTINUE; END IF;
    IF a='isler' THEN SELECT coalesce(array_agg(anahtar),'{}') INTO ks FROM motor.satirlar(m,'listeler') WHERE hal ? key; ELSE ks=ARRAY[x->>'kisi']; END IF;
    FOREACH k IN ARRAY ks LOOP IF k IS DISTINCT FROM e->>'kim' AND k10_1.alici_gorebilir(m,k,jsonb_build_object('tur',CASE WHEN a='isler' THEN 'IS' ELSE 'GOREV' END,'kimlik',key)) THEN alicilar=array_append(alicilar,k); END IF; END LOOP;
   END LOOP; END LOOP;
   FOR k IN SELECT z FROM (SELECT DISTINCT z FROM unnest(alicilar) z) q ORDER BY z COLLATE "C" LOOP PERFORM motor.bildir(m,e,'R43',k,saat.an(t),hedef); END LOOP;
  END IF;
 END IF; RETURN true; END $$;
RESET ROLE;
