SET ROLE irp_sahibi;
-- kurallar_v9.py:58,193. Hedef kimliği hem eski satırı hem değerlendirme/satır çiftini çözer.
CREATE FUNCTION k9.sorumluluk_satiri(d text,g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE h text=g->>'hedef'; BEGIN
 h=coalesce(motor.kayit(d,'itirazlar',h)->>'sorumluluk',h);
 IF g ? 'satir' THEN h=h||'/'||(g->>'satir'); END IF;
 RETURN motor.kayit(d,'sorumluluklar',h);
END $$;
CREATE FUNCTION k9.gecikme_hedefi(d text,hedef text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE g jsonb=motor.kayit(d,'gorevler',hedef); son timestamptz; e jsonb; i jsonb;
BEGIN
 IF irp.dogru(g) THEN
  son=gorev.son_teslim_ani(g,d);
  IF g->>'tur' IN ('NORMAL','DEGISIKLIK') AND irp.dogru(g->'ilk_teslim_ani') AND saat.an(g->>'ilk_teslim_ani')>son THEN
   RETURN jsonb_build_object('tur','GOREV','kisi',g->'kisi','birim',motor.kayit(d,'kisiler',g->>'kisi')->'birim','proje',g->'proje','an',g->'ilk_teslim_ani','zaman_degeri',g->'zaman_degeri');
  END IF;
 END IF;
 SELECT x INTO e FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) x WHERE x->>'olay_kimligi'=hedef AND x->>'eylem_kodu'='IS.ARIZA_BILDIRDIM' LIMIT 1;
 IF e IS NOT NULL AND NOT motor.oku(d,'supheliler') ? hedef THEN
  i=motor.kayit(d,'isler',(kapi.hedefler(e,'IS'))[1]);
  RETURN jsonb_build_object('tur','DURUS','kisi',coalesce(nullif(e->'adina','null'),e->'kim'),'birim',i->'birim','proje',i->'proje','an',e->'oldugu_an','zaman_degeri',0);
 END IF; RETURN '{}';
END $$;
CREATE FUNCTION k9.neden_bicimi(d text,kod jsonb,aciklama text DEFAULT '',eski boolean DEFAULT false) RETURNS void LANGUAGE plpgsql STABLE AS $$
DECLARE ad text=kod#>>'{}'; s jsonb; BEGIN
 IF eski AND jsonb_typeof(kod)='string' AND starts_with(ad,'ARIZA.') THEN RETURN; END IF;
 IF starts_with(ad,'DURUS_NEDENI.') THEN ad=substr(ad,14); END IF;
 s=motor.kayit(d,'kod_listesi','DURUS_NEDENI:'||ad);
 IF jsonb_typeof(kod) IS DISTINCT FROM 'string' OR NOT irp.dogru(s->'aktif') OR NOT irp.dogru(s->'ust') THEN PERFORM kapi.bicim_hatasi('DURUS_NEDENI aktif alt nedeni gerekli'); END IF;
 IF right(ad,6)='_DIGER' AND trim(coalesce(aciklama,''))='' THEN PERFORM kapi.bicim_hatasi('Diger nedeninde aciklama gerekli'); END IF;
END $$;
CREATE FUNCTION k9.pay_bicimi(ss jsonb,tam boolean DEFAULT false,dis boolean DEFAULT false) RETURNS void LANGUAGE plpgsql STABLE AS $$
DECLARE s jsonb; toplam numeric=0; gorulen jsonb='[]'; key jsonb; BEGIN
 IF jsonb_typeof(ss) IS DISTINCT FROM 'array' THEN PERFORM kapi.bicim_hatasi('Sorumlular dizi olmali'); END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP
  IF jsonb_typeof(s)<>'object' THEN PERFORM kapi.bicim_hatasi('Sorumlular dizi olmali'); END IF;
  IF coalesce(s->>'tur','') NOT IN ('KISI','BIRIM') AND NOT (dis AND s->>'tur'='DIS') THEN PERFORM kapi.bicim_hatasi('Sorumlu turu'); END IF;
  IF jsonb_typeof(s->'kimlik') IS DISTINCT FROM 'string' OR s->>'kimlik'='' THEN PERFORM kapi.bicim_hatasi('Sorumlu kimligi'); END IF;
  IF jsonb_typeof(s->'yuzde') IS DISTINCT FROM 'number' THEN PERFORM kapi.bicim_hatasi('Sorumlu yuzdesi'); END IF;
  IF (s->>'yuzde')::numeric NOT BETWEEN 0 AND 100 THEN PERFORM kapi.bicim_hatasi('Sorumlu yuzdesi'); END IF;
  IF s->>'tur'='DIS' AND s->>'kimlik' NOT IN ('MUSTERI','TEDARIKCI','ISLETME') THEN PERFORM kapi.bicim_hatasi('Dis sorumlu kimligi'); END IF;
  key=jsonb_build_array(s->'tur',s->'kimlik');
  IF EXISTS(SELECT FROM jsonb_array_elements(gorulen) x WHERE x=key) THEN PERFORM kapi.bicim_hatasi('Tekil sorumlular'); END IF;
  gorulen=gorulen||jsonb_build_array(key); toplam=toplam+(s->>'yuzde')::numeric;
 END LOOP;
 IF tam AND toplam<>100 OR toplam>100 THEN PERFORM kapi.bicim_hatasi(CASE WHEN tam THEN 'Sorumluluk toplami tam 100' ELSE 'Sorumluluk toplami en cok 100' END); END IF;
END $$;
CREATE FUNCTION k9.sorumluluk_bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; x jsonb; ss jsonb; toplam double precision=0; BEGIN
 IF kod IN ('IS.REDDETTIM','GOREV.REDDETTIM') THEN
  ss=coalesce(g->'sorumlular','[]');
  IF jsonb_typeof(ss)<>'array' THEN PERFORM kapi.bicim_hatasi('Sorumlular dizi'); END IF;
  FOR x IN SELECT value FROM jsonb_array_elements(ss) LOOP
   IF coalesce(x->>'tur','') NOT IN ('KISI','BIRIM') OR jsonb_typeof(x->'kimlik') IS DISTINCT FROM 'string' OR jsonb_typeof(x->'yuzde') IS DISTINCT FROM 'number' THEN PERFORM kapi.bicim_hatasi('Sorumluluk bicimi'); END IF;
   IF (x->>'yuzde')::double precision NOT BETWEEN 0 AND 100 THEN PERFORM kapi.bicim_hatasi('Sorumluluk bicimi'); END IF;
   toplam=toplam+(x->>'yuzde')::double precision;
  END LOOP;
  IF toplam>100 THEN PERFORM kapi.bicim_hatasi('Sorumluluk toplami 100'); END IF;
  IF (SELECT count(*)<>count(DISTINCT (z->'tur',z->'kimlik')) FROM jsonb_array_elements(ss) z) THEN PERFORM kapi.bicim_hatasi('Tekil sorumlular'); END IF;
 END IF;
 IF kod='GECIKME.DEGERLENDIRDIM' THEN PERFORM k9.neden_bicimi(d,g->'neden',g->>'gerekce'); PERFORM k9.pay_bicimi(g->'sorumlular',true,true); END IF;
 IF kod NOT LIKE 'SORUMLULUK.%' THEN RETURN; END IF;
 IF kod='SORUMLULUK.DOGRULADIM' AND g->>'karar' NOT IN ('ONAY','DEGISTIR','KALDIR') THEN PERFORM kapi.bicim_hatasi('Dogrulama karari'); END IF;
 IF kod='SORUMLULUK.ITIRAZI_DEGERLENDIRDIM' AND g->>'karar' NOT IN ('KABUL','RET') THEN PERFORM kapi.bicim_hatasi('Itiraz karari'); END IF;
 IF g->>'karar'='DEGISTIR' AND NOT g ? 'yuzde' THEN PERFORM kapi.bicim_hatasi('Yeni yuzde gerekli'); END IF;
 IF g ? 'yuzde' THEN
  IF jsonb_typeof(g->'yuzde')<>'number' THEN PERFORM kapi.bicim_hatasi('Yuzde'); END IF;
  IF (g->>'yuzde')::numeric NOT BETWEEN 0 AND 100 THEN PERFORM kapi.bicim_hatasi('Yuzde'); END IF;
 END IF;
 x=k9.sorumluluk_satiri(d,g);
 IF kod IN ('SORUMLULUK.DOGRULADIM','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM') AND x->>'kaynak_turu' IS DISTINCT FROM 'GECIKME' AND trim(coalesce(g->>'gerekce',''))='' THEN PERFORM kapi.bicim_hatasi('Hata sorumlulugunda gerekce gerekli'); END IF;
END $$;
CREATE FUNCTION k9.sorumlular_var(d text,ss jsonb) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT NOT EXISTS(SELECT FROM jsonb_array_elements(ss) s WHERE s->>'tur'<>'DIS' AND NOT motor.oku(d,CASE WHEN s->>'tur'='KISI' THEN 'kisiler' ELSE 'birimler' END) ? (s->>'kimlik')) $$;
CREATE FUNCTION k9.sorumluluk_yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; x jsonb; ustler text[];
BEGIN
 IF kod<>'GECIKME.DEGERLENDIRDIM' AND kod NOT LIKE 'SORUMLULUK.%' THEN RETURN NULL; END IF;
 IF NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 IF kod='GECIKME.DEGERLENDIRDIM' THEN
  x=k9.gecikme_hedefi(d,g->>'hedef'); IF NOT irp.dogru(x) THEN RETURN true; END IF;
  ustler=CASE WHEN x->>'tur'='GOREV' THEN yetki_v6.ustler(d,x->>'kisi') ELSE yetki_v6.yoneticiler(d,x->>'birim')||yetki_v6.birim_ustleri(d,x->>'birim') END;
  RETURN kim<>x->>'kisi' AND kim=ANY(ustler);
 END IF;
 x=k9.sorumluluk_satiri(d,g); IF NOT irp.dogru(x) OR x->>'tur'='DIS' THEN RETURN false; END IF;
 IF kod='SORUMLULUK.ITIRAZ_ETTIM' THEN RETURN CASE WHEN x->>'tur'='KISI' THEN kim=x->>'kimlik' ELSE kim=ANY(yetki_v6.yoneticiler(d,x->>'kimlik')) END; END IF;
 RETURN kim<>x->>'kimlik' AND kim=ANY(k7.satir_ustleri(d,x));
END $$;
CREATE FUNCTION k9.sorumluluk_durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; x jsonb; toplam numeric; BEGIN
 IF kod IN ('IS.REDDETTIM','GOREV.REDDETTIM') AND NOT k9.sorumlular_var(d,coalesce(g->'sorumlular','[]')) THEN RETURN false; END IF;
 IF kod='GECIKME.DEGERLENDIRDIM' THEN RETURN irp.dogru(k9.gecikme_hedefi(d,g->>'hedef')) AND k9.sorumlular_var(d,g->'sorumlular'); END IF;
 IF kod NOT LIKE 'SORUMLULUK.%' THEN RETURN NULL; END IF;
 x=k9.sorumluluk_satiri(d,g); IF NOT irp.dogru(x) THEN RETURN false; END IF;
 IF kod='SORUMLULUK.ITIRAZ_ETTIM' THEN RETURN NOT irp.dogru(x->'itirazda') AND (x->>'yuzde')::numeric>0; END IF;
 IF kod='SORUMLULUK.ITIRAZI_DEGERLENDIRDIM' AND NOT irp.dogru(x->'itirazda') THEN RETURN false; END IF;
 SELECT coalesce(sum((hal->>'yuzde')::numeric),0) INTO toplam FROM motor.satirlar(d,'sorumluluklar') WHERE hal->'ret'=x->'ret' AND hal->'satir'<>x->'satir';
 RETURN toplam+coalesce((g->>'yuzde')::numeric,(x->>'yuzde')::numeric)<=100;
END $$;
CREATE FUNCTION k9.sorumluluk_dogur(m text,e jsonb,ss jsonb,hedef jsonb,kaynak_turu text,onek text DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
DECLARE s jsonb; n bigint; key text; ustler text[]; dogru boolean; BEGIN
 FOR s,n IN SELECT * FROM jsonb_array_elements(ss) WITH ORDINALITY LOOP
  key=coalesce(onek,e->>'olay_kimligi')||'/'||n; ustler=k7.satir_ustleri(m,s); dogru=s->>'tur'='DIS' OR e->>'kim'=ANY(ustler);
  PERFORM motor.kaydet(m,'sorumluluklar',key,s||jsonb_build_object('satir',key,'ret',coalesce(onek,e->>'olay_kimligi'),'an',e->'oldugu_an','dogrulandi',dogru,'itirazda',false,'kanit',e->'kanit','hedef',hedef,'kaynak_turu',kaynak_turu));
  IF NOT dogru THEN PERFORM k7.bildirim(m,e,'R38',ustler); END IF;
 END LOOP;
END $$;
-- kurallar_v7.py:311 ve v9.py:381. Tarihçeye çözümlenmiş olay zarfı girer.
CREATE FUNCTION k9.sorumluluk_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; oid text=e->>'olay_kimligi'; x jsonb; h jsonb; yeni jsonb=e; itiraz text; ozel boolean;
BEGIN
 IF kod='GECIKME.DEGERLENDIRDIM' THEN
  h=k9.gecikme_hedefi(m,g->>'hedef'); IF NOT irp.dogru(h) THEN PERFORM motor.supheli(m,e,'Gecikme hedefi etkin degil'); RETURN; END IF;
  PERFORM motor.kaydet(m,'gecikme_degerlendirmeleri',oid,g||jsonb_build_object('kimlik',oid,'an',e->'oldugu_an','yazan',e->'kim','kaynak',h));
  PERFORM k9.sorumluluk_dogur(m,e,g->'sorumlular',jsonb_build_array(jsonb_build_object('tur',h->'tur','kimlik',g->'hedef')),'GECIKME'); RETURN;
 END IF;
 x=k9.sorumluluk_satiri(m,g); IF NOT irp.dogru(x) THEN PERFORM motor.supheli(m,e,'Sorumluluk yok'); RETURN; END IF;
 ozel=g ? 'satir' OR motor.oku(m,'gecikme_degerlendirmeleri') ? (g->>'hedef');
 IF ozel THEN
  g=(g-'satir')||jsonb_build_object('hedef',x->'satir');
  IF kod='SORUMLULUK.ITIRAZI_DEGERLENDIRDIM' THEN
   SELECT anahtar INTO itiraz FROM motor.satirlar(m,'itirazlar') WITH ORDINALITY z(anahtar,hal,n) WHERE hal->'sorumluluk'=x->'satir' AND hal->'karar'='null' ORDER BY n DESC LIMIT 1;
   IF itiraz IS NULL THEN PERFORM motor.supheli(m,e,'Acik itiraz yok'); RETURN; END IF;
   g=g||jsonb_build_object('hedef',itiraz);
  END IF;
  yeni=e||jsonb_build_object('girdiler',g);
 END IF;
 x=x||jsonb_build_object('gecmis',coalesce(x->'gecmis','[]')||jsonb_build_array(yeni));
 IF kod='SORUMLULUK.DOGRULADIM' THEN
  x=x||'{"dogrulandi":true}';
  IF g->>'karar'='KALDIR' THEN x=x||'{"yuzde":0}'; ELSIF g->>'karar'='DEGISTIR' THEN x=x||jsonb_build_object('yuzde',g->'yuzde'); END IF;
 ELSIF kod='SORUMLULUK.ITIRAZ_ETTIM' THEN
  x=x||'{"itirazda":true}'; PERFORM motor.kaydet(m,'itirazlar',oid,jsonb_build_object('sorumluluk',x->'satir','karar',NULL)); PERFORM k7.bildirim(m,e,'R39',k7.satir_ustleri(m,x));
 ELSE
  x=x||'{"itirazda":false}'; PERFORM motor.kaydet(m,'itirazlar',g->>'hedef',motor.kayit(m,'itirazlar',g->>'hedef')||jsonb_build_object('karar',g->'karar'));
  IF g->>'karar'='KABUL' THEN x=x||jsonb_build_object('yuzde',coalesce(g->'yuzde','0')); END IF;
  IF ozel AND x->>'kaynak_turu'='GECIKME' THEN x=x||'{"dogrulandi":true}'; END IF;
 END IF;
 PERFORM motor.kaydet(m,'sorumluluklar',x->>'satir',x);
END $$;
RESET ROLE;
