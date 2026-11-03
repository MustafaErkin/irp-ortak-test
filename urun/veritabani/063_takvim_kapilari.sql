SET ROLE irp_sahibi;
-- kurallar_v7: takvim olaylarının biçim, yetki, durum ve yürütme dalları.
CREATE FUNCTION k7.takvim_hedef(m text,e jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; tablo text;
BEGIN
 tablo=CASE WHEN kod LIKE 'IZIN.%' THEN 'izinler' WHEN kod LIKE 'EK_MESAI.%' THEN 'ek_mesai_planlari' WHEN kod LIKE 'DURUS.%' THEN 'duruslar' WHEN kod LIKE 'TEZGAH.BAKIM_%' THEN 'bakimlar' END;
 RETURN CASE WHEN tablo IS NULL THEN g ELSE motor.kayit(m,tablo,g->>'hedef',g) END;
END $$;
CREATE FUNCTION k7.takvim_yetki(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; x jsonb=k7.takvim_hedef(m,e); kisi text; b text; bs text[]; r jsonb; s jsonb;
BEGIN
 IF kod IN ('IS.ATADIM','GOREV.ATADIM') THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',jsonb_build_array(g))) LOOP
   IF irp.dogru(s->'ek_mesai') THEN FOREACH kisi IN ARRAY irp.dizi(coalesce(s->'kisiler',jsonb_build_array(s->'kisi'))) LOOP IF NOT kim=ANY(yetki_v6.ustler(m,kisi)) THEN RETURN false; END IF; END LOOP; END IF;
  END LOOP; RETURN NULL;
 END IF;
 IF NOT (kod LIKE 'GUN.%' OR kod LIKE 'EK_MESAI.%' OR kod LIKE 'IZIN.%' OR kod LIKE 'DURUS.%' OR kod IN ('TEZGAH.TAKVIM_TANIMLADIM','TEZGAH.BAKIM_PLANLADIM','TEZGAH.BAKIM_IPTAL_ETTIM','TEZGAH.DURUS_BILDIRDIM','TEZGAH.DURUS_BITTI')) THEN RETURN NULL; END IF;
 IF NOT yetki_v6.istihdamda(m,kim,yetki_v6.simdi(m)) THEN RETURN false; END IF;
 kisi=coalesce(x->>'kisi',e->>'adina',kim);
 IF kod LIKE 'EK_MESAI.%' THEN RETURN kim=ANY(yetki_v6.ustler(m,kisi)); END IF;
 IF kod='IZIN.IK_ONAYLADIM' OR (kod='IZIN.REDDETTIM' AND x->>'durum'='IK_BEKLIYOR') THEN RETURN kim<>kisi AND yetki_v6.tablo_izni(m,kim,kod,NULL); END IF;
 IF kod='IZIN.TALEP_ETTIM' THEN RETURN kim=kisi OR kim=ANY(yetki_v6.ustler(m,kisi)); END IF;
 IF kod LIKE 'IZIN.%' THEN RETURN kim=ANY(yetki_v6.ustler(m,kisi)) OR (kod='IZIN.IPTAL_ETTIM' AND kim=kisi AND x->>'durum'='TALEP'); END IF;
 IF kod LIKE 'DURUS.%' AND x->'kapsam'='"FIRMA"' THEN RETURN motor.kayit(m,'kisiler',kim)->'roller' ? 'YETKILI' OR EXISTS(SELECT FROM motor.satirlar(m,'birimler') z WHERE NOT irp.dogru(z.hal->'ust_birim') AND kim=ANY(yetki_v6.yoneticiler(m,z.anahtar))); END IF;
 bs=CASE WHEN kod LIKE 'TEZGAH.%' THEN ARRAY[motor.kayit(m,'tezgahlar',x->>'tezgah')->>'birim'] WHEN kod LIKE 'DURUS.%' THEN irp.dizi(x->'kapsam') ELSE ARRAY[NULL::text] END;
 FOREACH b IN ARRAY bs LOOP
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(motor.oku(m,'yetki_kurallari','[]')) z WHERE z->>'eylem_kodu'=kod AND NOT irp.dogru(z->'gecerli_bitis') AND k7.rol_izni(m,kim,z,b)) THEN RETURN false; END IF;
 END LOOP; RETURN true;
END $$;
CREATE FUNCTION k7.ek_kapi(m text,e jsonb,g jsonb,kisi text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE p jsonb=takvim.pencere(g); a timestamptz=saat.an(p->>0); b timestamptz=saat.an(p->>1); t timestamptz=saat.an(e->>'oldugu_an'); damga boolean=e->>'eylem_kodu'='EK_MESAI.ONAYLADIM'; gun date; x jsonb; q jsonb;
BEGIN
 IF damga THEN IF b>t OR a<t-interval '7 days' THEN RETURN false; END IF; ELSIF a<=t THEN RETURN false; END IF;
 gun=saat.gun(saat.kodla(a)); WHILE gun<=saat.gun(saat.kodla(b-interval '1 microsecond')) LOOP IF NOT yetki_v6.istihdamda(m,kisi,saat.gun_ani(gun)) THEN RETURN false; END IF; gun=gun+1; END LOOP;
 gun=saat.gun(saat.kodla(a)); WHILE gun<=saat.gun(saat.kodla(b)) LOOP
  IF EXISTS(SELECT FROM jsonb_array_elements(takvim.normal(m,gun,false,kisi)) v WHERE greatest(a,saat.an(v->>0))<least(b,saat.an(v->>1))) THEN RETURN false; END IF; gun=gun+1;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(takvim.izinler(m,kisi)) v WHERE greatest(a,saat.an(v->>0))<least(b,saat.an(v->>1))) THEN RETURN false; END IF;
 FOR x IN SELECT hal FROM motor.satirlar(m,'ek_mesai_planlari') LOOP
  IF x->>'kimlik'=e->>'olay_kimligi' OR starts_with(x->>'kimlik',(e->>'olay_kimligi')||'/ek/') OR x->>'kisi'<>kisi OR irp.dogru(x->'iptal') THEN CONTINUE; END IF;
  q=takvim.pencere(x); IF greatest(a,saat.an(q->>0))>=least(b,saat.an(q->>1)) THEN CONTINUE; END IF;
  IF damga AND motor.kayit(m,'kisiler',kisi)->>'yaka'='BEYAZ' AND NOT irp.dogru(x->'damga') AND saat.an(q->>0)<=a AND b<=saat.an(q->>1) THEN CONTINUE; END IF; RETURN false;
 END LOOP; RETURN true;
END $$;
CREATE FUNCTION k7.takvim_durum(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; x jsonb=k7.takvim_hedef(m,e); t timestamptz=saat.an(e->>'oldugu_an'); a timestamptz; b timestamptz; gun date; kisi text; s jsonb;
BEGIN
 IF kod IN ('IS.ATADIM','GOREV.ATADIM') AND NOT irp.dogru(motor.oku(m,'_an','null')) THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',jsonb_build_array(g))) LOOP IF irp.dogru(s->'ek_mesai') THEN
   FOREACH kisi IN ARRAY irp.dizi(coalesce(s->'kisiler',jsonb_build_array(s->'kisi'))) LOOP IF NOT k7.ek_kapi(m,e,s->'ek_mesai',kisi) THEN RETURN false; END IF; END LOOP;
  END IF; END LOOP; RETURN NULL;
 END IF;
 IF kod LIKE 'GUN.%' THEN RETURN saat.gun(g->>'tarih')>saat.gun(saat.kodla(t)); END IF;
 IF kod IN ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM') THEN RETURN k7.ek_kapi(m,e,g,g->>'kisi'); END IF;
 IF kod='EK_MESAI.IPTAL_ETTIM' THEN RETURN x<>g AND NOT irp.dogru(x->'iptal') AND t<saat.an(takvim.pencere(x)->>0); END IF;
 IF kod='IZIN.TALEP_ETTIM' THEN
  a=saat.an(g->>'baslangic'); b=saat.an(g->>'bitis');
  IF NOT (a>=t OR to_char(a AT TIME ZONE 'Europe/Istanbul','IYYY-IW')=to_char(t AT TIME ZONE 'Europe/Istanbul','IYYY-IW')) THEN RETURN false; END IF;
  kisi=g->>'kisi';
 ELSIF kod LIKE 'IZIN.%' THEN
  IF x=g THEN RETURN false; END IF;
  IF kod IN ('IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM') THEN
   IF x->>'durum'<>(CASE WHEN kod='IZIN.ONAYLADIM' THEN 'TALEP' ELSE 'IK_BEKLIYOR' END) THEN RETURN false; END IF;
   a=saat.an(x->>'baslangic'); b=saat.an(x->>'bitis'); kisi=x->>'kisi';
   IF EXISTS(SELECT FROM motor.satirlar(m,'izinler') y WHERE y.hal->>'kimlik'<>x->>'kimlik' AND y.hal->>'kisi'=kisi AND y.hal->>'durum'='ONAYLI' AND greatest(a,saat.an(y.hal->>'baslangic'))<least(b,saat.an(y.hal->>'bitis'))) THEN RETURN false; END IF;
  ELSE RETURN x->>'durum' NOT IN ('IPTAL','REDDEDILDI','RET') AND (kod<>'IZIN.REDDETTIM' OR x->>'durum' IN ('TALEP','IK_BEKLIYOR')); END IF;
 ELSIF kod='TEZGAH.TAKVIM_TANIMLADIM' THEN RETURN motor.oku(m,'tezgahlar') ? (g->>'tezgah') AND saat.gun(g->>'gecerli_baslangic')>saat.gun(saat.kodla(t));
 ELSIF kod='TEZGAH.BAKIM_PLANLADIM' THEN RETURN motor.oku(m,'tezgahlar') ? (g->>'tezgah') AND saat.an(g->>'baslangic')>t;
 ELSIF kod='TEZGAH.BAKIM_IPTAL_ETTIM' THEN RETURN x<>g AND NOT irp.dogru(x->'iptal') AND t<saat.an(x->>'baslangic');
 ELSE RETURN NULL; END IF;
 gun=saat.gun(saat.kodla(a)); WHILE gun<=saat.gun(saat.kodla(b-interval '1 microsecond')) LOOP IF NOT yetki_v6.istihdamda(m,kisi,saat.gun_ani(gun)) THEN RETURN false; END IF; gun=gun+1; END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION k7.takvim_bicim(m text,e jsonb) RETURNS void LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; x jsonb; p jsonb; a timestamptz; b timestamptz; c timestamptz; d timestamptz; araliklar jsonb='[]';
BEGIN
 IF kod='AYAR.DEGISTIRDIM' THEN
  IF g->>'anahtar' NOT IN ('standart_gunluk_saat','fazla_mesai_katsayilari','gun_sonu_raporu_zorunlu','gun_sonu_hatirlatma','izin_ik_onayi','proje_gorunurlugu','sessiz_kabul_is_gunu') THEN PERFORM kapi.bicim_hatasi('T8 ayari'); END IF;
  IF g->>'anahtar'='standart_gunluk_saat' AND (jsonb_typeof(g->'deger')<>'number' OR (g->>'deger')::numeric<=0 OR (g->>'deger')::numeric>24) THEN PERFORM kapi.bicim_hatasi('Standart saat'); END IF;
  IF g->>'anahtar'='fazla_mesai_katsayilari' THEN
   IF jsonb_typeof(g->'deger')<>'object' THEN PERFORM kapi.bicim_hatasi('Katsayi en az bir'); END IF;
   IF NOT (g->'deger') ?& ARRAY['TATIL','PAZAR','CUMARTESI','HAFTA_ICI'] OR (SELECT count(*) FROM jsonb_object_keys(g->'deger'))<>4 THEN PERFORM kapi.bicim_hatasi('Katsayi en az bir'); END IF;
   FOR x IN SELECT value FROM jsonb_each(g->'deger') LOOP IF jsonb_typeof(x)<>'number' OR (x#>>'{}')::numeric<1 THEN PERFORM kapi.bicim_hatasi('Katsayi en az bir'); END IF; END LOOP;
  END IF;
  IF g->>'anahtar'='gun_sonu_raporu_zorunlu' AND jsonb_typeof(g->'deger')<>'boolean' THEN PERFORM kapi.bicim_hatasi('Zorunluluk bool'); END IF;
  IF g->>'anahtar'='sessiz_kabul_is_gunu' AND (jsonb_typeof(g->'deger')<>'number' OR (g->>'deger') !~ '^[0-9]+$') THEN PERFORM kapi.bicim_hatasi('Sessiz kabul negatif olmayan tam is gunu'); END IF;
  IF g->>'anahtar'='proje_gorunurlugu' AND g->>'deger' NOT IN ('HERKES','UYELER') THEN PERFORM kapi.bicim_hatasi('Proje gorunurlugu'); END IF;
  IF g->>'anahtar'='izin_ik_onayi' THEN
   IF jsonb_typeof(g->'deger')<>'object' THEN PERFORM kapi.bicim_hatasi('Izin IK ayari'); END IF;
   IF EXISTS(SELECT FROM jsonb_each(g->'deger') z WHERE jsonb_typeof(z.value)<>'boolean' OR z.key NOT IN ('YILLIK','SAATLIK','MAZERET','UCRETLI','UCRETSIZ','SAGLIK','SERBEST_ZAMAN')) THEN PERFORM kapi.bicim_hatasi('Izin IK ayari'); END IF;
  END IF;
 END IF;
 IF kod='GUN.TANIMLADIM' THEN
  IF g->>'tur' NOT IN ('TATIL','YARIM_GUN','OZEL_MESAI') THEN PERFORM kapi.bicim_hatasi('Gun turu'); END IF;
  IF g->>'tur'<>'TATIL' THEN
   a=saat.gun_ani(saat.gun(g->>'tarih'),g->>'mesai_baslangic'); b=saat.gun_ani(saat.gun(g->>'tarih'),g->>'mesai_bitis'); IF a>=b THEN PERFORM kapi.bicim_hatasi('Gun mesaisi'); END IF;
   FOR x IN SELECT value FROM jsonb_array_elements(g->'sabit_molalar') LOOP
    c=saat.gun_ani(saat.gun(g->>'tarih'),x->>'bas'); d=saat.gun_ani(saat.gun(g->>'tarih'),x->>'bit');
    IF NOT (a<=c AND c<d AND d<=b) OR EXISTS(SELECT FROM jsonb_array_elements(araliklar) v WHERE greatest(c,saat.an(v->>0))<least(d,saat.an(v->>1))) THEN PERFORM kapi.bicim_hatasi('Mola araligi'); END IF;
    araliklar=araliklar||jsonb_build_array(jsonb_build_array(saat.kodla(c),saat.kodla(d)));
   END LOOP;
  END IF;
 END IF;
 IF kod IN ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM') THEN
  p=takvim.pencere(g); IF saat.an(p->>0)>=saat.an(p->>1) THEN PERFORM kapi.bicim_hatasi('Ek mesai araligi'); END IF;
  IF cardinality(kapi.hedefler(e,'IS')||kapi.hedefler(e,'GOREV'))=0 THEN PERFORM kapi.bicim_hatasi('Ek mesai hedefi'); END IF;
 END IF;
 IF kod IN ('IZIN.TALEP_ETTIM','TEZGAH.BAKIM_PLANLADIM') AND saat.an(g->>'baslangic')>=saat.an(g->>'bitis') THEN PERFORM kapi.bicim_hatasi('Tarih araligi'); END IF;
 IF kod='IZIN.TALEP_ETTIM' AND g->>'tur' NOT IN ('YILLIK','SAATLIK','MAZERET','UCRETLI','UCRETSIZ','SAGLIK','SERBEST_ZAMAN') THEN PERFORM kapi.bicim_hatasi('Izin turu'); END IF;
 IF kod='DURUS.BASLADI' AND g->'kapsam'<>'"FIRMA"' THEN
  IF jsonb_typeof(g->'kapsam')<>'array' OR g->'kapsam'='[]' THEN PERFORM kapi.bicim_hatasi('Durus kapsami'); END IF;
  IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(g->'kapsam')) THEN PERFORM kapi.bicim_hatasi('Durus kapsami'); END IF;
 END IF;
 IF kod='TEZGAH.TAKVIM_TANIMLADIM' THEN
  IF jsonb_typeof(g->'vardiyalar')<>'array' OR g->'vardiyalar'='[]' THEN PERFORM kapi.bicim_hatasi('Vardiyalar'); END IF;
  FOR x IN SELECT value FROM jsonb_array_elements(g->'vardiyalar') LOOP
   IF NOT irp.dogru(x->'gunler') OR NOT '[1,2,3,4,5,6,7]'::jsonb @> (x->'gunler') THEN PERFORM kapi.bicim_hatasi('Vardiya gunleri'); END IF;
   IF saat.gun_ani('2026-01-01',x->>'bas')>=saat.gun_ani('2026-01-01',x->>'bit') THEN PERFORM kapi.bicim_hatasi('Vardiya araligi'); END IF;
  END LOOP;
 END IF;
END $$;
CREATE FUNCTION k7.takvim_isle(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; oid text=e->>'olay_kimligi'; t timestamptz=saat.an(e->>'oldugu_an'); x jsonb; y jsonb; k text; b text; cakisti boolean; alicilar text[]='{}';
BEGIN
 IF kod LIKE 'DURUS.%' THEN
  IF kod='DURUS.BASLADI' THEN
   FOR y IN SELECT hal FROM motor.satirlar(m,'duruslar') WHERE NOT irp.dogru(hal->'bitis') LOOP
    cakisti=y->'kapsam'='"FIRMA"' OR g->'kapsam'='"FIRMA"';
    IF NOT cakisti THEN cakisti=EXISTS(SELECT FROM jsonb_array_elements_text(g->'kapsam') z WHERE takvim.birim_kapsamda(m,z,y->'kapsam')) OR EXISTS(SELECT FROM jsonb_array_elements_text(y->'kapsam') z WHERE takvim.birim_kapsamda(m,z,g->'kapsam')); END IF;
    IF cakisti THEN PERFORM motor.supheli(m,e,'Ayni kapsamda acik durus'); RETURN true; END IF;
   END LOOP;
   k=oid; x=g||jsonb_build_object('kimlik',oid,'baslangic',saat.kodla(t),'bitis',NULL);
  ELSE
   k=g->>'hedef'; x=motor.kayit(m,'duruslar',k);
   IF NOT irp.dogru(x) OR irp.dogru(x->'bitis') THEN PERFORM motor.supheli(m,e,'Acik durus yok'); RETURN true; END IF; x=x||jsonb_build_object('bitis',saat.kodla(t));
  END IF;
  PERFORM motor.kaydet(m,'duruslar',k,x);
  FOR b IN SELECT anahtar FROM motor.satirlar(m,'birimler') WHERE takvim.birim_kapsamda(m,anahtar,x->'kapsam') LOOP alicilar=alicilar||yetki_v6.yoneticiler(m,b)||yetki_v6.birim_ustleri(m,b); END LOOP;
  PERFORM k7.bildirim(m,e,'R34',ARRAY(SELECT DISTINCT z COLLATE "C" FROM unnest(alicilar) z ORDER BY z COLLATE "C")); PERFORM takvim.katman_guncelle(m,t);
 ELSIF kod='TEZGAH.TAKVIM_TANIMLADIM' THEN PERFORM motor.kaydet(m,'tezgah_takvimleri',oid,g||jsonb_build_object('kimlik',oid));
 ELSIF kod='TEZGAH.BAKIM_PLANLADIM' THEN PERFORM motor.kaydet(m,'bakimlar',oid,g||jsonb_build_object('kimlik',oid,'iptal',false));
 ELSIF kod='TEZGAH.BAKIM_IPTAL_ETTIM' THEN PERFORM motor.kaydet(m,'bakimlar',g->>'hedef',motor.kayit(m,'bakimlar',g->>'hedef')||'{"iptal":true}');
 ELSIF kod LIKE 'TEZGAH.DURUS_%' THEN
  SELECT anahtar,hal INTO k,x FROM motor.satirlar(m,'tezgah_duruslari') WHERE hal->>'tezgah'=g->>'tezgah' AND NOT irp.dogru(hal->'bitis') LIMIT 1;
  IF kod='TEZGAH.DURUS_BILDIRDIM' THEN
   IF x IS NOT NULL THEN PERFORM motor.supheli(m,e,'Tezgah durusu acik'); ELSE PERFORM motor.kaydet(m,'tezgah_duruslari',oid,g||jsonb_build_object('kimlik',oid,'baslangic',saat.kodla(t),'bitis',NULL)); END IF;
  ELSIF x IS NULL THEN PERFORM motor.supheli(m,e,'Acik tezgah durusu yok'); ELSE PERFORM motor.kaydet(m,'tezgah_duruslari',k,x||jsonb_build_object('bitis',saat.kodla(t))); END IF;
 ELSIF kod LIKE 'IZIN.%' THEN
  x=k7.takvim_hedef(m,e); PERFORM k7.bildirim(m,e,CASE WHEN kod='IZIN.TALEP_ETTIM' THEN 'R35' ELSE 'R36' END,CASE WHEN kod='IZIN.TALEP_ETTIM' THEN yetki_v6.ustler(m,x->>'kisi') ELSE ARRAY[x->>'kisi'] END);
 ELSIF kod NOT LIKE 'GUN.%' AND kod NOT LIKE 'EK_MESAI.%' THEN RETURN false;
 END IF; RETURN true;
END $$;
-- kurallar_v9.ik_kalir: ileri rol/ayrılış/ayar sınırlarının tamamı.
CREATE FUNCTION k9.ik_kalir(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE es jsonb; x jsonb; g jsonb; kod text; sinirlar timestamptz[]=ARRAY[saat.an(e->>'oldugu_an')]; t timestamptz; acik jsonb; kisiler jsonb; k text;
BEGIN
 SELECT coalesce(jsonb_agg(icerik),'[]') INTO es FROM public.olaylar WHERE olay_kimligi<>e->>'olay_kimligi' AND olay_kimligi NOT IN (SELECT icerik#>>'{girdiler,hedef}' FROM public.olaylar WHERE eylem_kodu='KAYIT.GECERSIZ_SAYDIM'); es=es||jsonb_build_array(e);
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(es) z WHERE z->>'eylem_kodu'='AYAR.DEGISTIRDIM' AND z#>>'{girdiler,anahtar}'='izin_ik_onayi' AND EXISTS(SELECT FROM jsonb_each(z#>'{girdiler,deger}') v WHERE irp.dogru(v.value))) THEN RETURN true; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(es) LOOP
  g=x->'girdiler'; kod=x->>'eylem_kodu';
  IF kod='KISI.DEGISTIRDIM' THEN sinirlar=array_append(sinirlar,saat.an(g->>'gecerli_baslangic')); END IF;
  IF kod='KISI.AYRILDI' AND NOT irp.dogru(g->'iptal') THEN sinirlar=array_append(sinirlar,saat.gun_ani(saat.gun(g->>'ayrilis_tarihi')+1)); END IF;
  IF kod='AYAR.DEGISTIRDIM' AND g->>'anahtar'='izin_ik_onayi' THEN sinirlar=array_append(sinirlar,saat.an(coalesce(g->>'gecerli_baslangic',x->>'oldugu_an'))); END IF;
 END LOOP;
 FOREACH t IN ARRAY sinirlar LOOP
  IF t<saat.an(e->>'oldugu_an') THEN CONTINUE; END IF;
  SELECT z#>'{girdiler,deger}' INTO acik FROM jsonb_array_elements(es) z WHERE z->>'eylem_kodu'='AYAR.DEGISTIRDIM' AND z#>>'{girdiler,anahtar}'='izin_ik_onayi' AND saat.an(coalesce(z#>>'{girdiler,gecerli_baslangic}',z->>'oldugu_an'))<=t ORDER BY saat.an(coalesce(z#>>'{girdiler,gecerli_baslangic}',z->>'oldugu_an')) DESC,(z->>'olay_kimligi') COLLATE "C" DESC LIMIT 1;
  IF NOT EXISTS(SELECT FROM jsonb_each(coalesce(acik,'{}')) v WHERE irp.dogru(v.value)) THEN CONTINUE; END IF;
  kisiler='{}';
  FOR x IN SELECT value FROM jsonb_array_elements(es) WHERE saat.an(coalesce(value#>>'{girdiler,gecerli_baslangic}',value->>'oldugu_an'))<=t ORDER BY saat.an(coalesce(value#>>'{girdiler,gecerli_baslangic}',value->>'oldugu_an')),(value->>'olay_kimligi') COLLATE "C" LOOP
   g=x->'girdiler'; kod=x->>'eylem_kodu'; k=g->>'kisi';
   IF kod='KISI.EKLEDIM' THEN kisiler=jsonb_set(kisiler,ARRAY[g->>'kod'],g);
   ELSIF kod='KISI.DEGISTIRDIM' AND kisiler ? k THEN kisiler=jsonb_set(kisiler,ARRAY[k],(kisiler->k)||(g->'degisenler'));
   ELSIF kod='KISI.AYRILDI' AND kisiler ? k THEN kisiler=jsonb_set(kisiler,ARRAY[k],(kisiler->k)||jsonb_build_object('ayrilis_tarihi',CASE WHEN NOT irp.dogru(g->'iptal') THEN g->'ayrilis_tarihi' END)); END IF;
  END LOOP;
  IF NOT EXISTS(SELECT FROM jsonb_each(kisiler) p WHERE p.value->'roller' ? 'IK' AND saat.gun(p.value->>'giris_tarihi')<=saat.gun(saat.kodla(t)) AND (NOT irp.dogru(p.value->'ayrilis_tarihi') OR saat.gun(saat.kodla(t))<=saat.gun(p.value->>'ayrilis_tarihi'))) THEN RETURN false; END IF;
 END LOOP; RETURN true;
END $$;
RESET ROLE;
