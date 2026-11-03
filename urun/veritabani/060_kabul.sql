SET ROLE irp_sahibi;
-- olay.py:81 bicim_kontrol. Hata metinleri donmuş modelden korunur.
CREATE FUNCTION kapi.bicim_hatasi(neden text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN RAISE EXCEPTION 'IRP|BICIM|%',neden; END $$;
CREATE FUNCTION kapi.bicim_kontrol(d text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE g jsonb=(e->'girdiler'); kod text=(e->>'eylem_kodu'); a text; s jsonb; ss jsonb; desen text;
BEGIN
 FOREACH a IN ARRAY ARRAY['olay_kimligi','eylem_kodu','eylem_versiyonu','neyin_ustunde','giris_sekli','kim','cihaz','uygulama_surumu','oldugu_an','saat_dilimi','bildigi_son_hal_ani','girdiler','kanit','yol'] LOOP
  IF NOT e ? a OR e->a='null' THEN PERFORM kapi.bicim_hatasi('Eksik olay alani'); END IF; END LOOP;
 IF ((e->>'olay_kimligi')) !~ '^K[0-9]{3}-[0-9]{10}-[A-Z]$' THEN PERFORM kapi.bicim_hatasi('Kimlik deseni'); END IF;
 IF NOT irp.sabit('eylemler') ? kod OR (e->'eylem_versiyonu')<>'1' THEN PERFORM kapi.bicim_hatasi('Bilinmeyen eylem/surum'); END IF;
 IF (e->>'giris_sekli') NOT IN ('QR','LISTE','ELLE','AKTARIM') OR (e->>'yol') NOT IN ('ATOLYE','DISARIDA') THEN PERFORM kapi.bicim_hatasi('Giris/yol'); END IF;
 IF jsonb_typeof(g)<>'object' OR jsonb_typeof((e->'neyin_ustunde'))<>'array' OR jsonb_typeof((e->'kanit'))<>'array' THEN PERFORM kapi.bicim_hatasi('Olay alan tipi'); END IF;
 PERFORM saat.an((e->>'oldugu_an')); PERFORM saat.an((e->>'bildigi_son_hal_ani'));
 FOREACH a IN ARRAY irp.dizi(irp.sabit('eylemler')->kod) LOOP IF NOT g ? a THEN PERFORM kapi.bicim_hatasi('Eksik eylem girdisi: '||kod); END IF; END LOOP;
 IF g ? 'degisenler' AND (jsonb_typeof((g->'degisenler'))<>'object' OR NOT irp.dogru((g->'degisenler'))) THEN PERFORM kapi.bicim_hatasi('Degisenler dolu nesne olmali'); END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(jsonb_build_array(g)||CASE WHEN jsonb_typeof((g->'degisenler'))='object' THEN jsonb_build_array((g->'degisenler')) ELSE '[]'::jsonb END) LOOP
  FOREACH a IN ARRAY ARRAY['tarih','teslim_tarihi','giris_tarihi','ayrilis_tarihi'] LOOP IF irp.dogru(s->a) THEN PERFORM (s->>a)::date; END IF; END LOOP;
  IF s ? 'hedef_saat' AND (jsonb_typeof((s->'hedef_saat'))<>'number' OR ((s->>'hedef_saat'))::numeric<0) THEN PERFORM kapi.bicim_hatasi('Hedef saat negatif olmayan sonlu sayi'); END IF;
  IF kod LIKE 'ETAP.%' THEN FOREACH a IN ARRAY ARRAY['baslangic','bitis'] LOOP IF s ? a THEN PERFORM (s->>a)::date; END IF; END LOOP; END IF;
 END LOOP;
 IF kod IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM','IS.DEGISTIRDIM') THEN
  ss=CASE WHEN kod='IS.TANIMLADIM' THEN (g->'isler') WHEN kod='IS.DEGISTIRDIM' THEN jsonb_build_array((g->'degisenler')) ELSE jsonb_build_array(g) END;
  FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP
   IF irp.dogru((s->'onay_gerekli')) AND NOT s ? 'onay_beklet' THEN PERFORM kapi.bicim_hatasi('Onayli iste onay_beklet zorunlu'); END IF;
   FOREACH a IN ARRAY ARRAY['onay_beklet','onay_gerekli'] LOOP IF s ? a AND jsonb_typeof(s->a)<>'boolean' THEN PERFORM kapi.bicim_hatasi('Bool onay alani'); END IF; END LOOP;
   IF s ? 'tahmini_sure_dk' AND (((s->>'tahmini_sure_dk')) !~ '^[0-9]+$') THEN PERFORM kapi.bicim_hatasi('Tahmini sure'); END IF;
  END LOOP;
 END IF;
 -- bicim_v6.py:4 denetle.
 IF kod='KISI.AYRILDI' THEN
  IF g->'iptal'='true' THEN IF irp.dogru(g->'ayrilis_tarihi') THEN PERFORM kapi.bicim_hatasi('Iptal ve tarih birlikte olmaz'); END IF;
  ELSIF NOT irp.dogru(g->'ayrilis_tarihi') THEN PERFORM kapi.bicim_hatasi('Ayrilis tarihi ya da iptal gerekli'); END IF;
  IF g ? 'iptal' AND jsonb_typeof(g->'iptal')<>'boolean' THEN PERFORM kapi.bicim_hatasi('Iptal bool olmali'); END IF;
 END IF;
 IF kod='KISI.EKLEDIM' AND g ? 'ust' THEN PERFORM kapi.bicim_hatasi('Ust yalniz birim agacindan gelir'); END IF;
 IF kod='IS.DEGISTIRDIM' AND (g->'degisenler') ?| ARRAY['nereye','proje','etap','parca_kodu','kategori'] THEN PERFORM kapi.bicim_hatasi('Baglanti icin IS.BAGLANTI_DUZELTTIM gerekli'); END IF;
 IF kod='IS.BAGLANTI_DUZELTTIM' THEN
  IF cardinality(kapi.hedefler(e,'IS'))<>1 THEN PERFORM kapi.bicim_hatasi('Tek is hedefi gerekli'); END IF;
  IF EXISTS(SELECT FROM jsonb_object_keys(g->'degisenler') a WHERE a<>ALL(ARRAY['nereye','proje','etap','parca_kodu','kategori','nesne'])) THEN PERFORM kapi.bicim_hatasi('Baglanti alanlari'); END IF;
 END IF;
 IF kod='KOD.TANIMLADIM' AND (g->>'liste' NOT IN ('ARIZA','MOLA','PD','ROL','IZIN','DURUS','DURUS_NEDENI','YETKINLIK') OR jsonb_typeof(g->'kod')<>'string' OR trim(g->>'kod')='' OR jsonb_typeof(g->'ad')<>'string' OR jsonb_typeof(g->'aktif')<>'boolean') THEN PERFORM kapi.bicim_hatasi('Kod listesi bicimi'); END IF;
 IF kod='YETKI.TANIMLADIM' AND (jsonb_typeof(g->'kimler')<>'array' OR EXISTS(SELECT FROM jsonb_array_elements(g->'kimler') r WHERE jsonb_typeof(r)<>'string') OR (SELECT count(DISTINCT value)<>count(*) FROM jsonb_array_elements(g->'kimler'))) THEN PERFORM kapi.bicim_hatasi('Kimler benzersiz rol listesi'); END IF;
 IF kod='AYAR.MAAS_PAYDASI' AND (jsonb_typeof((g->'deger'))<>'number' OR ((g->>'deger'))::numeric<=0) THEN PERFORM kapi.bicim_hatasi('Maas paydasi pozitif sonlu sayi'); END IF;
 IF kod='AYAR.PARCA_KODU_DESENI' THEN IF jsonb_typeof((g->'deger'))<>'string' THEN PERFORM kapi.bicim_hatasi('Desen metin olmali'); END IF; BEGIN PERFORM '' ~ ((g->>'deger')); EXCEPTION WHEN invalid_regular_expression THEN PERFORM kapi.bicim_hatasi('Gecersiz parca kodu deseni'); END; END IF;
 IF (kod IN ('IS.DEGISTIRDIM','IS.IPTAL_ETTIM') AND cardinality(kapi.hedefler(e,'IS'))<>1) OR (kod IN ('PROJE.DEGISTIRDIM','PROJE.KAPATTIM') AND cardinality(kapi.hedefler(e,'PROJE'))<>1) OR (kod='ETAP.DEGISTIRDIM' AND cardinality(kapi.hedefler(e,'ETAP'))<>1) THEN PERFORM kapi.bicim_hatasi('Tek hedef gerekli'); END IF;
 FOREACH a IN ARRAY ARRAY['is_bitti','onay_gerekli','revizyon_ver','onay_beklet','aktif'] LOOP IF g ? a AND jsonb_typeof(g->a)<>'boolean' THEN PERFORM kapi.bicim_hatasi('Bool alan: '||a); END IF; END LOOP;
 FOREACH a IN ARRAY ARRAY['sira','yeni_sira','kime_sira','zaman_degeri'] LOOP IF g ? a AND ((g->>a) !~ '^[0-9]+$' OR (g->>a)::numeric<1) THEN PERFORM kapi.bicim_hatasi('Pozitif tamsayi: '||a); END IF; END LOOP;
 IF kod='AYAR.ONAY_ORANI' AND (jsonb_typeof((g->'deger'))<>'number' OR ((g->>'deger'))::numeric NOT BETWEEN 0 AND 1) THEN PERFORM kapi.bicim_hatasi('Oran 0..1'); END IF;
 IF kod IN ('IS.TANIMLADIM','GOREV.ATADIM') THEN
  ss=g->CASE WHEN kod='IS.TANIMLADIM' THEN 'isler' ELSE 'gorevler' END; IF jsonb_typeof(ss)<>'array' OR ss='[]' OR EXISTS(SELECT FROM jsonb_array_elements(ss) z WHERE jsonb_typeof(z)<>'object') THEN PERFORM kapi.bicim_hatasi('Bos/bozuk satir listesi'); END IF;
  FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP
   FOREACH a IN ARRAY ARRAY['onay_gerekli','dosya_gerekli'] LOOP IF s ? a AND jsonb_typeof(s->a)<>'boolean' THEN PERFORM kapi.bicim_hatasi('Bool satir alani'); END IF; END LOOP;
   IF s ? 'tahmini_sure_dk' AND ((s->>'tahmini_sure_dk')) !~ '^[0-9]+$' THEN PERFORM kapi.bicim_hatasi('Tahmini sure'); END IF;
   IF (s->>'nereye')='PROJE_DISI' AND NOT irp.dogru((s->'kategori')) THEN PERFORM kapi.bicim_hatasi('PD kategori gerekli'); END IF;
   IF irp.dogru((s->'teslim_tarihi')) THEN PERFORM ((s->>'teslim_tarihi'))::date; END IF;
  END LOOP;
 END IF;
 FOREACH a IN ARRAY ARRAY['not','aciklama','metin','gerekce'] LOOP IF irp.sabit('eylemler')->kod ? a AND trim(coalesce(g->>a,''))='' THEN PERFORM kapi.bicim_hatasi('Bos '||a); END IF; END LOOP;
 IF kod='IS.ARIZA_BILDIRDIM' AND (g->>'neden')='ARIZA.DIGER' AND trim(coalesce((g->>'not'),''))='' THEN PERFORM kapi.bicim_hatasi('Diger icin not zorunlu'); END IF;
 IF kod='IS.SURE_EKLEDIM' AND (NOT irp.dogru((e->'adina')) OR (e->>'giris_sekli') NOT IN ('ELLE','AKTARIM') OR saat.an((g->>'bitis'))<=saat.an((g->>'baslangic'))) THEN PERFORM kapi.bicim_hatasi('Elle sure bicimi'); END IF;
 IF kod='GOREV.REDDETTIM' AND irp.dogru((g->'revizyon_ver')) AND NOT g ?& ARRAY['yeni_teslim_tarihi','zaman_degeri','kime'] THEN PERFORM kapi.bicim_hatasi('Revizyon alanlari'); END IF;
 IF irp.dogru((e->'duzelttigi_olay')) AND kod<>'KAYIT.GECERSIZ_SAYDIM' THEN PERFORM kapi.bicim_hatasi('Duzeltme yalniz isarette'); END IF;
 IF kod='KAYIT.GECERSIZ_SAYDIM' AND (g->'hedef') IS DISTINCT FROM (e->'duzelttigi_olay') THEN PERFORM kapi.bicim_hatasi('Hedef esit olmali'); END IF;
 IF kod='IS.ATADIM' AND NOT (irp.dogru((g->'kisi')) OR irp.dogru((g->'kisiler'))) THEN PERFORM kapi.bicim_hatasi('Atanan gerekli'); END IF;
 IF kod LIKE 'IS.%' AND kod NOT IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') AND cardinality(kapi.hedefler(e,'IS'))=0 THEN PERFORM kapi.bicim_hatasi('Is hedefi gerekli'); END IF;
 IF kod LIKE 'GOREV.%' AND kod<>'GOREV.ATADIM' AND cardinality(kapi.hedefler(e,'GOREV'))=0 THEN PERFORM kapi.bicim_hatasi('Gorev hedefi gerekli'); END IF;
 IF kod IN ('GOREV.TAMAMLADIM','GOREV.REDDETTIM','GOREV.DEGISTIRDIM','GOREV.IPTAL_ETTIM') AND cardinality(kapi.hedefler(e,'GOREV'))<>1 THEN PERFORM kapi.bicim_hatasi('Karar 44: tek gorev hedefi'); END IF;
 IF kod='NOT.YAZDIM' AND NOT EXISTS(SELECT FROM jsonb_array_elements((e->'neyin_ustunde')) h WHERE (h->>'tur') IN ('PARCA','GOREV','PROJE','NESNE')) THEN PERFORM kapi.bicim_hatasi('Not hedefi gerekli'); END IF;
 IF kod='GOREV.ATADIM' THEN FOR s IN SELECT value FROM jsonb_array_elements((g->'gorevler')) LOOP
  FOREACH a IN ARRAY ARRAY['ad','nereye','teslim_tarihi','zaman_degeri','zorluk','kisi','onay_gerekli','dosya_gerekli'] LOOP IF NOT s ? a THEN PERFORM kapi.bicim_hatasi('Gorev satiri: '||a); END IF; END LOOP;
  IF ((s->>'zaman_degeri')) !~ '^[0-9]+$' OR ((s->>'zaman_degeri'))::numeric<1 OR ((s->>'zorluk'))::numeric NOT BETWEEN 1 AND 5 THEN PERFORM kapi.bicim_hatasi('Gorev sayisal alan'); END IF;
  IF irp.dogru((s->'onay_gerekli')) AND NOT irp.dogru((s->'onaylayan')) THEN PERFORM kapi.bicim_hatasi('Onaylayan gerekli'); END IF;
 END LOOP; END IF;
 -- kapilar_v5.py:30 bicim.
 desen=motor.ayar(d,'parca_kodu_deseni',saat.an((e->>'oldugu_an')),'""')#>>'{}';
 ss=CASE WHEN kod='IS.TANIMLADIM' THEN (g->'isler') WHEN kod='IS.PLANSIZ_TANIMLADIM' THEN jsonb_build_array(g) WHEN kod IN ('IS.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') AND (g->'degisenler') ? 'parca_kodu' THEN jsonb_build_array((g->'degisenler')) ELSE '[]'::jsonb END;
 FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP IF desen<>'' AND irp.dogru((s->'parca_kodu')) AND NOT ((s->>'parca_kodu')) ~ ('^(?:'||desen||')$') THEN PERFORM kapi.bicim_hatasi('Parca kodu sirket desenine uymuyor'); END IF; END LOOP;
 IF irp.sabit('kabul_sirali') ? kod AND saat.an((e->>'oldugu_an'))>saat.simdi() THEN PERFORM kapi.bicim_hatasi('T10 yonetim olayi gelecekte olamaz'); END IF;
 PERFORM k10_1.bicim(d,e); PERFORM k10_2.bicim(d,e); PERFORM k7.takvim_bicim(d,e); PERFORM k9.gun_sonu_bicim(d,e); PERFORM k9.sorumluluk_bicim(d,e);
 PERFORM k9.durus_nedeni_bicim(d,e); PERFORM k9.degisiklik_bicim(d,e);
 IF kod='PLAN.ONAYLADIM' AND irp.dogru(motor.kayit(d,'plan_surumleri',g->>'proje','[]')) AND trim(coalesce(g->>'gerekce',''))='' THEN PERFORM kapi.bicim_hatasi('B1 ve sonrasi gerekce zorunlu'); END IF;
END $$;
-- kabul.py:30 nesne, 39 lider; surum.py liste_surumu.
CREATE FUNCTION kapi.nesne(d text,tur text,k text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 DECLARE a text; BEGIN
 IF tur='LISTE' THEN RETURN CASE WHEN motor.oku(d,'kisiler') ? k THEN jsonb_build_object('surum',surum.ozet(motor.kayit(d,'listeler',k,'[]'))) ELSE '{}'::jsonb END; END IF;
 a=CASE tur WHEN 'IS' THEN 'isler' WHEN 'GOREV' THEN 'gorevler' WHEN 'KISI' THEN 'kisiler' WHEN 'BIRIM' THEN 'birimler' WHEN 'ETAP' THEN 'etaplar' WHEN 'PROJE' THEN 'projeler' WHEN 'NOT' THEN 'notlar' WHEN 'TEZGAH' THEN 'tezgahlar' WHEN 'NESNE' THEN 'nesneler' END;
 RETURN motor.kayit(d,a,k); END $$;
CREATE FUNCTION kapi.lider(d text,kim text,b text) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT coalesce(motor.kayit(d,'kisiler',kim)->>'birim'=b AND motor.kayit(d,'kisiler',kim)->'roller' ? 'EKIP_LIDERI',false) $$;
CREATE FUNCTION yetki_v6.tablo_izni(d text,kim text,kod text,b text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE r jsonb; ks text[]; roller text[]=irp.dizi(motor.kayit(d,'kisiler',kim)->'roller'); p jsonb; k text; BEGIN
 FOR r IN SELECT value FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) WHERE (value->>'eylem_kodu')=kod AND NOT irp.dogru((value->'gecerli_bitis')) AND irp.dogru((value->'kimler')) LOOP
  ks=irp.dizi((r->'kimler')); IF (r->>'kapsam')='FIRMA' THEN
   IF roller&&ks THEN RETURN true; END IF;
   FOR k,p IN SELECT * FROM motor.satirlar(d,'kisiler') LOOP IF irp.dizi((p->'roller'))&&ks AND yetki_v6.istihdamda(d,k,yetki_v6.simdi(d)) AND kim=ANY(yetki_v6.ustler(d,k)) THEN RETURN true; END IF; END LOOP;
  ELSIF b IS NOT NULL THEN
   IF motor.kayit(d,'kisiler',kim)->>'birim'=b AND roller&&ks OR 'BIRIM_YONETICISI'=ANY(ks) AND kim=ANY(yetki_v6.yoneticiler(d,b)) OR 'BIRIM_BASI'=ANY(ks) AND kim=motor.kayit(d,'birimler',b)->>'basi' OR kim=ANY(yetki_v6.birim_ustleri(d,b)) THEN RETURN true; END IF;
  END IF;
 END LOOP; RETURN false; END $$;
-- yetki_v6.py:85 yetkili_mi. Her toplu hedef ayrı değerlendirilir.
CREATE FUNCTION yetki_v6.yetkili_mi(d text,e jsonb,servis boolean DEFAULT false) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE kim text=(e->>'kim'); kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); t timestamptz=yetki_v6.simdi(d); roller text[]=irp.dizi(motor.kayit(d,'kisiler',(e->>'kim'))->'roller'); isler jsonb; gorevler jsonb; x jsonb; birimler text[]='{}'; iliskiler text[]='{}'; k text; alan text; n int; j int; karar boolean;
BEGIN
 IF (e->>'giris_sekli')='AKTARIM' THEN RETURN servis; END IF;
 IF kod='KISI.YETKINLIK_TANIMLADIM' THEN RETURN k10_2.yetkinlik_yetki(d,e); END IF;
 karar=k10_1.yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k10.yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k9.gun_sonu_yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k9.sorumluluk_yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k7.nesne_yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k7.takvim_yetki(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 IF NOT yetki_v6.istihdamda(d,kim,t) OR irp.dogru((e->'adina')) AND NOT yetki_v6.istihdamda(d,(e->>'adina'),t) THEN RETURN false; END IF;
 IF kod='KURULUM.TAMAMLADIM' THEN RETURN false; END IF;
 IF kod LIKE 'MAAS.%' OR kod='YETKI.TANIMLADIM' THEN RETURN 'YETKILI'=ANY(roller); END IF;
 IF kod='MODUL.TANIMLADIM' THEN RETURN NOT irp.dogru((e->'adina')) AND 'YETKILI'=ANY(roller); END IF;
 IF kod='BILDIRIM.GORDUM' THEN RETURN NOT irp.dogru((e->'adina')) AND NOT EXISTS(SELECT FROM jsonb_array_elements_text((g->'bildirimler')) h WHERE irp.dogru(k9.bildirim_bul(d,h)) AND k9.bildirim_bul(d,h)->>'alici'<>kim); END IF;
 IF kod LIKE 'PROJE.ERISIM_%' THEN RETURN kim=motor.kayit(d,'projeler',g->>'proje')->>'sorumlu' OR yetki_v6.tablo_izni(d,kim,kod,NULL); END IF;
 SELECT coalesce(jsonb_agg(motor.kayit(d,'isler',a)),'[]') INTO isler FROM unnest(kapi.hedefler(e,'IS')) a;
 SELECT coalesce(jsonb_agg(motor.kayit(d,'gorevler',a)),'[]') INTO gorevler FROM unnest(kapi.hedefler(e,'GOREV')) a;
 IF kod IN ('GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM') AND EXISTS(SELECT FROM jsonb_array_elements(gorevler) x WHERE irp.dogru(x) AND NOT yetki_v6.istihdamda(d,(x->>'kisi'),t)) THEN RETURN false; END IF;
 IF kod IN ('IS.ONAYLADIM','IS.REDDETTIM') AND EXISTS(SELECT FROM jsonb_array_elements(isler) x WHERE (x->>'tamamlayan')=kim) THEN RETURN false; END IF;
 IF kod IN ('GOREV.ONAYLADIM','GOREV.REDDETTIM') AND EXISTS(SELECT FROM jsonb_array_elements(gorevler) x WHERE (x->>'kisi')=kim) THEN RETURN false; END IF;
 IF kod='GOREV.ATADIM' AND EXISTS(SELECT FROM jsonb_array_elements((g->'gorevler')) x WHERE (x->>'kisi')=kim OR (x->'onaylayan')=(x->'kisi')) THEN RETURN false; END IF;
 IF kod='GOREV.DEGISTIRDIM' THEN FOR x IN SELECT value||((g->'degisenler')) FROM jsonb_array_elements(gorevler) LOOP IF (x->'onaylayan')=(x->'kisi') THEN RETURN false; END IF; END LOOP; END IF;
 IF kod='NOT.YAZDIM' THEN RETURN true; END IF;
 IF irp.sabit('calisan') ? kod THEN
  IF NOT irp.dogru((e->'adina')) THEN RETURN true; END IF; iliskiler=ARRAY[(e->>'adina')]; SELECT coalesce(array_agg((x->>'birim')),ARRAY[motor.kayit(d,'kisiler',(e->>'adina'))->>'birim']) INTO birimler FROM jsonb_array_elements(isler) x;
 ELSIF kod LIKE 'IS.%' THEN
  SELECT coalesce(array_agg((x->>'birim')),'{}') INTO birimler FROM jsonb_array_elements(isler) x;
  IF kod IN ('IS.ONAYLADIM','IS.REDDETTIM') THEN SELECT coalesce(array_agg((x->>'atayan')),'{}') INTO iliskiler FROM jsonb_array_elements(isler) x; END IF;
  IF kod='IS.TANIMLADIM' THEN SELECT array_agg((x->>'birim')) INTO birimler FROM jsonb_array_elements((g->'isler')) x; END IF;
  IF kod='IS.PLANSIZ_TANIMLADIM' THEN birimler=ARRAY[coalesce((g->>'birim'),motor.kayit(d,'kisiler',kim)->>'birim')]; END IF;
 ELSIF kod LIKE 'GOREV.%' THEN
  alan=CASE WHEN kod IN ('GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM') THEN 'kisi' WHEN kod IN ('GOREV.ONAYLADIM','GOREV.REDDETTIM') THEN 'onaylayan' ELSE 'veren' END;
  SELECT coalesce(array_agg(x->>alan),'{}'),coalesce(array_agg(motor.kayit(d,'kisiler',(x->>'kisi'))->>'birim'),'{}') INTO iliskiler,birimler FROM jsonb_array_elements(gorevler) x;
  IF kod='GOREV.ATADIM' THEN SELECT array_agg(motor.kayit(d,'kisiler',(x->>'kisi'))->>'birim') INTO birimler FROM jsonb_array_elements((g->'gorevler')) x; END IF;
 ELSIF kod='KAYIT.GECERSIZ_SAYDIM' THEN
  -- Depo.olaylar kaynak kayıtları içerir; Motor.olaylar etkin olaylarla sınırlıdır.
  IF NOT irp.dogru(motor.oku(d,'_an','null')) THEN SELECT icerik INTO x FROM public.olaylar WHERE olay_kimligi=g->>'hedef';
  ELSE SELECT z INTO x FROM jsonb_array_elements(motor.oku(d,'olaylar','[]')) z WHERE z->'olay_kimligi'=g->'hedef' LIMIT 1; END IF;
  iliskiler=ARRAY[x->>'kim']; birimler=ARRAY[motor.kayit(d,'kisiler',coalesce(x->>'adina',x->>'kim'))->>'birim'];
 ELSE birimler=ARRAY[coalesce((g->>'birim'),motor.kayit(d,'kisiler',(g->>'kisi'))->>'birim')]; END IF;
 n=greatest(cardinality(birimler),cardinality(iliskiler),1);
 FOR j IN 1..n LOOP k=iliskiler[j]; IF NOT (coalesce(k=kim OR kim=ANY(yetki_v6.ustler(d,k)),false) OR yetki_v6.tablo_izni(d,kim,kod,birimler[j])) THEN RETURN false; END IF; END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION kapilar_v3.liste_hedefleri(e jsonb) RETURNS text[] LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
 DECLARE g jsonb=(e->'girdiler'); BEGIN
 IF (e->>'eylem_kodu')='IS.DEVRETTIM' THEN RETURN ARRAY[(g->>'kimden'),(g->>'kime')]; END IF;
 IF (e->>'eylem_kodu') IN ('IS.ATADIM','IS.PLANSIZ_TANIMLADIM','IS.SIRALADIM') THEN RETURN CASE WHEN irp.dogru((g->'kisiler')) THEN irp.dizi((g->'kisiler')) ELSE ARRAY[(g->>'kisi')] END; END IF; RETURN '{}'; END $$;
CREATE FUNCTION kapilar_v5.aktif_kisi(d text,k text) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT irp.dogru(motor.kayit(d,'kisiler',k)) AND NOT irp.dogru(motor.kayit(d,'kisiler',k)->'ayrilis_tarihi') $$;
CREATE FUNCTION kapilar_v5.proje_etap(d text,s jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 DECLARE p text=(s->>'proje'); et text=(s->>'etap'); BEGIN
 IF (s->>'nereye')='PROJE' AND coalesce(p,'')='' THEN RETURN false; END IF;
 IF coalesce(p,'')<>'' AND (NOT motor.oku(d,'projeler') ? p OR NOT coalesce((motor.kayit(d,'projeler',p)->>'aktif')::boolean,true)) THEN RETURN false; END IF;
 RETURN coalesce(et,'')='' OR (motor.oku(d,'etaplar') ? et AND motor.kayit(d,'etaplar',et)->>'proje'=p); END $$;
CREATE FUNCTION kapilar_v5.is_basvurulari(d text,s jsonb) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT coalesce(kapilar_v5.proje_etap(d,s) AND motor.kayit(d,'birimler',(s->>'birim'))->>'tur'='ATOLYE' AND (NOT irp.dogru((s->'tezgah')) OR motor.oku(d,'tezgahlar') ? ((s->>'tezgah')) AND coalesce((motor.kayit(d,'tezgahlar',(s->>'tezgah'))->>'aktif')::boolean,true)),false) $$;
-- kabul.py:90 durum; çevrilen kapı dalları, bilinmeyen dal için açık ürün hatası.
CREATE FUNCTION kapi.durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); ids text[]=kapi.hedefler(e,'IS'); i jsonb; s jsonb; l jsonb; k text; n int; b text; h jsonb; t timestamptz=saat.an((e->>'oldugu_an')); karar boolean; bas timestamptz; bitis timestamptz; tak jsonb;
BEGIN
 IF (kod IN ('KISI.DEGISTIRDIM','KISI.AYRILDI') OR (kod='AYAR.DEGISTIRDIM' AND g->>'anahtar'='izin_ik_onayi')) AND NOT k9.ik_kalir(d,e) THEN RETURN false; END IF;
 IF kod='KOD.TANIMLADIM' AND g->>'liste'='ROL' AND g->>'kod'='IK' AND NOT irp.dogru(g->'aktif') AND EXISTS(SELECT FROM jsonb_each(motor.ayar(d,'izin_ik_onayi',t,'{}')) z WHERE irp.dogru(z.value)) THEN RETURN false; END IF;
 IF kod='BIRIM.TANIMLADIM' AND g ? 'takvim' AND saat.gun(g->>'takvim_gecerli')<=saat.gun(e->>'oldugu_an') THEN RETURN false; END IF;
 karar=k10_1.durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 IF kod='KISI.YETKINLIK_TANIMLADIM' THEN RETURN k10_2.yetkinlik_durum(d,e); END IF;
 karar=k9.gun_sonu_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k9.sorumluluk_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k9.durus_nedeni_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k9.degisiklik_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 IF kod='PLAN.ONAYLADIM' THEN RETURN k7.plan_durum(d,e); END IF;
 karar=k7.nesne_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 karar=k7.takvim_durum(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 IF NOT kapilar_v3.ek_kapilar(d,e) OR NOT kapilar_v5.ek_denetim(d,e) THEN RETURN false; END IF;
 karar=k6.kapilar(d,e); IF karar IS NOT NULL THEN RETURN karar; END IF;
 i=motor.kayit(d,'isler',ids[1]);
 FOREACH k IN ARRAY kapilar_v3.liste_hedefleri(e) LOOP
  l=motor.kayit(d,'listeler',k,'[]'); h=motor.kayit(d,'isler',l->>0);
  IF (h->>'durum')='ONAY_BEKLIYOR' AND irp.dogru((h->'onay_beklet')) THEN
   IF kod='IS.DEVRETTIM' AND k=(g->>'kimden') THEN IF ids[1]=l->>0 OR irp.dogru((g->'kimden_yeni_is')) AND (g->'kimden_yeni_is')<>l->0 THEN RETURN false; END IF;
   ELSE n=coalesce(((g->>'sira'))::int,((g->>'yeni_sira'))::int,((g->>'kime_sira'))::int,1); IF ids[1]=l->>0 AND n<>1 OR ids[1] IS DISTINCT FROM l->>0 AND n=1 THEN RETURN false; END IF; END IF;
  END IF;
 END LOOP;
 IF kod='IS.ATADIM' THEN
  FOREACH k IN ARRAY kapilar_v3.liste_hedefleri(e) LOOP IF NOT kapilar_v5.aktif_kisi(d,k) THEN RETURN false; END IF; END LOOP;
  n=coalesce(((g->>'kisi_sayisi'))::int,((i->>'kisi_sayisi'))::int,1);
  RETURN coalesce((i->>'durum') IN ('HAVUZDA','REDDEDILDI') AND NOT EXISTS(SELECT FROM motor.satirlar(d,'listeler') z WHERE z.hal ? ids[1]) AND (n=1 OR jsonb_array_length(coalesce((g->'kisiler'),'[]'))=n),false);
 ELSIF kod='IS.SIRALADIM' THEN l=motor.kayit(d,'listeler',(g->>'kisi'),'[]'); RETURN l ? ids[1] AND (i->>'durum')<>'BITTI';
 ELSIF kod='IS.DEVRETTIM' THEN RETURN kapilar_v5.aktif_kisi(d,(g->>'kime')) AND motor.kayit(d,'listeler',(g->>'kimden'),'[]') ? ids[1] AND (g->>'kimden')<>(g->>'kime') AND (i->>'durum')<>'ONAY_BEKLIYOR';
 ELSIF kod IN ('IS.ONAYLADIM','IS.REDDETTIM') THEN RETURN coalesce((i->>'durum')='ONAY_BEKLIYOR',false);
 ELSIF kod='IS.DEVAM_ONAYLADIM' THEN h=motor.kayit(d,'kisi_durumu',(i->>'kisi')); IF (h->>'durum')='SABIT_MOLADA' THEN h=(h->'mola_onceki'); END IF; RETURN coalesce((h->>'durum')='ARIZADA' AND (h->'acik_is')=(i->'kimlik'),false);
 ELSIF kod IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') THEN
  FOR s IN SELECT value FROM jsonb_array_elements(CASE WHEN kod='IS.TANIMLADIM' THEN (g->'isler') ELSE jsonb_build_array(g||jsonb_build_object('birim',coalesce((g->>'birim'),motor.kayit(d,'kisiler',(e->>'kim'))->>'birim'))) END) LOOP
   IF NOT kapilar_v5.is_basvurulari(d,s) OR (s->>'nereye')='PROJE_DISI' AND NOT k6.kod_aktif(d,'PD',(s->>'kategori')) THEN RETURN false; END IF; END LOOP;
  RETURN kod<>'IS.PLANSIZ_TANIMLADIM' OR kapilar_v5.aktif_kisi(d,(g->>'kisi'));
 ELSIF kod='GOREV.ATADIM' THEN FOR s IN SELECT value FROM jsonb_array_elements((g->'gorevler')) LOOP IF NOT kapilar_v5.proje_etap(d,s) OR NOT kapilar_v5.aktif_kisi(d,(s->>'kisi')) OR irp.dogru((s->'onay_gerekli')) AND NOT kapilar_v5.aktif_kisi(d,(s->>'onaylayan')) OR (s->>'kisi')=(e->>'kim') OR (s->>'nereye')='PROJE_DISI' AND NOT k6.kod_aktif(d,'PD',(s->>'kategori')) THEN RETURN false; END IF; END LOOP; RETURN true;
 ELSIF kod LIKE 'GOREV.%' THEN
  FOREACH k IN ARRAY kapi.hedefler(e,'GOREV') LOOP s=motor.kayit(d,'gorevler',k); IF NOT irp.dogru(s) OR NOT gorev.kapi(d,s,e) THEN RETURN false; END IF;
   IF kod='GOREV.DEGISTIRDIM' AND NOT kapilar_v5.proje_etap(d,s||((g->'degisenler'))) THEN RETURN false; END IF; END LOOP;
  IF kod='GOREV.REDDETTIM' AND irp.dogru((g->'revizyon_ver')) THEN RETURN kapilar_v5.aktif_kisi(d,(g->>'kime')); END IF; RETURN true;
 ELSIF kod IN ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM') THEN
  IF EXISTS(SELECT FROM motor.satirlar(d,'projeler') p CROSS JOIN LATERAL jsonb_array_elements((p.hal->'kod_gecmisi')) x WHERE (x->'kod')=(g->'kod') AND coalesce((x->>'ek'),'')=coalesce((g->>'ek'),'')) THEN RETURN false; END IF;
  IF kod='PROJE.KOD_DEGISTIRDIM' THEN RETURN motor.oku(d,'projeler') ? coalesce((g->>'proje'),(kapi.hedefler(e,'PROJE'))[1]); END IF;
  RETURN NOT motor.oku(d,'projeler') ? coalesce((g->>'kimlik'),(g->>'kod')) AND (NOT irp.dogru((g->'ana_proje')) OR motor.oku(d,'projeler') ? ((g->>'ana_proje')) AND NOT irp.dogru(motor.kayit(d,'projeler',(g->>'ana_proje'))->'ana_proje')) AND (NOT irp.dogru((g->'sorumlu')) OR kapilar_v5.aktif_kisi(d,(g->>'sorumlu')));
 ELSIF kod='PROJE.DEGISTIRDIM' THEN s=motor.kayit(d,'projeler',(kapi.hedefler(e,'PROJE'))[1]); RETURN irp.dogru((s->'aktif')) AND NOT EXISTS(SELECT FROM jsonb_object_keys((g->'degisenler')) a WHERE a<>ALL(ARRAY['ad','musteri','teslim_tarihi','baslangic_tarihi','kesin_kabul_tarihi','sorumlu']));
 ELSIF kod IN ('ETAP.TANIMLADIM','ETAP.DEGISTIRDIM') THEN s=CASE WHEN kod='ETAP.TANIMLADIM' THEN g ELSE motor.kayit(d,'etaplar',(kapi.hedefler(e,'ETAP'))[1])||((g->'degisenler')) END; RETURN irp.dogru(motor.kayit(d,'projeler',(s->>'proje'))->'aktif') AND motor.oku(d,'birimler') ? ((s->>'birim')) AND saat.an((s->>'baslangic'))<=saat.an((s->>'bitis')) AND ((s->>'hedef_saat'))::numeric>=0 AND (NOT irp.dogru((s->'sorumlu')) OR kapilar_v5.aktif_kisi(d,(s->>'sorumlu')));
 ELSIF kod='KISI.EKLEDIM' THEN s=motor.kayit(d,'kisiler',(g->>'kod')); IF irp.dogru(s) AND (NOT irp.dogru((s->'ayrilis_tarihi')) OR ((s->>'ayrilis_tarihi'))::date>=saat.gun(saat.kodla(t)) OR ((g->>'giris_tarihi'))::date<=((s->>'ayrilis_tarihi'))::date) THEN RETURN false; END IF;
  RETURN motor.oku(d,'birimler') ? ((g->>'birim')) AND (g->>'yaka') IN ('MAVI','BEYAZ') AND irp.dogru((g->'roller')) AND NOT EXISTS(SELECT FROM jsonb_array_elements_text((g->'roller')) r WHERE NOT k6.kod_aktif(d,'ROL',r));
 ELSIF kod='KISI.DEGISTIRDIM' THEN RETURN kapilar_v5.aktif_kisi(d,(g->>'kisi')) AND saat.an((g->>'gecerli_baslangic'))>=t;
 ELSIF kod='BIRIM.TANIMLADIM' THEN IF irp.dogru((g->'ust_birim')) AND NOT motor.oku(d,'birimler') ? ((g->>'ust_birim')) THEN RETURN false; END IF; RETURN (g->>'tur') IN ('ATOLYE','MASA_BASI') AND (NOT irp.dogru((g->'basi')) OR kapilar_v5.aktif_kisi(d,(g->>'basi')));
 ELSIF kod='TEZGAH.TANIMLADIM' THEN RETURN motor.kayit(d,'birimler',(g->>'birim'))->>'tur'='ATOLYE';
 ELSIF kod='AYAR.YONLENDIRDIM' THEN RETURN motor.oku(d,'birimler') ? ((g->>'birim')) AND NOT EXISTS(SELECT FROM jsonb_array_elements_text((g->'kisiler')) x WHERE NOT kapilar_v5.aktif_kisi(d,x));
 ELSIF kod='KOD.TANIMLADIM' THEN RETURN NOT ((g->>'liste')='ROL' AND (g->>'kod')='YETKILI' AND NOT irp.dogru((g->'aktif')));
 ELSIF kod='YETKI.TANIMLADIM' THEN RETURN (irp.sabit('eylemler') ? ((g->>'eylem_kodu')) OR (g->>'eylem_kodu')='PROJE.HEPSINI_GORUR') AND (g->>'kapsam') IN ('BIRIM','FIRMA') AND NOT EXISTS(SELECT FROM jsonb_array_elements_text((g->'kimler')) r WHERE r NOT IN ('BIRIM_YONETICISI','BIRIM_BASI','BIRIM_UYESI','PROJE_SORUMLUSU') AND NOT k6.kod_aktif(d,'ROL',r));
 ELSIF kod='KURULUM.TAMAMLADIM' THEN RETURN false;
 ELSIF kod='AYAR.ONAY_ORANI' OR kod='AYAR.PARCA_KODU_DESENI' THEN RETURN saat.an(coalesce((g->>'gecerli_baslangic'),(e->>'oldugu_an')))>=t;
 ELSIF kod='MAAS.GUNCELLEDIM' THEN RETURN motor.oku(d,'kisiler') ? ((g->>'kisi')) OR motor.oku(d,'tezgahlar') ? ((g->>'kisi'));
 ELSIF kod='AYAR.SAAT_KAYDIRDIM' OR kod='NOT.YAZDIM' THEN RETURN true;
 ELSIF kod IN ('TAKVIM.TANIMLADIM','TATIL.EKLEDIM','IS.DEGISTIRDIM','AYAR.MAAS_PAYDASI') THEN RETURN true;
 ELSIF kod='PROJE.KAPATTIM' THEN k=(kapi.hedefler(e,'PROJE'))[1]; RETURN irp.dogru(motor.kayit(d,'projeler',k)->'aktif') AND NOT EXISTS(SELECT FROM (SELECT hal FROM motor.satirlar(d,'isler') UNION ALL SELECT hal FROM motor.satirlar(d,'gorevler')) q WHERE hal->>'proje'=k AND hal->>'durum' NOT IN ('BITTI','IPTAL'));
 ELSIF kod='IS.SURE_EKLEDIM' THEN bas=saat.an(g->>'baslangic'); bitis=saat.an(g->>'bitis'); k=e->>'adina'; tak=motor.takvim(d,g->>'baslangic',k);
  RETURN saat.gun(g->>'baslangic')=saat.gun(g->>'bitis') AND to_char(bas AT TIME ZONE 'Europe/Istanbul','IYYY-IW')=to_char(t AT TIME ZONE 'Europe/Istanbul','IYYY-IW') AND bitis<=t AND bitis<=saat.simdi() AND motor.is_gunu(d,g->>'baslangic',k) AND saat.gun_ani(saat.gun(g->>'baslangic'),tak->>'mesai_baslangic')<=bas AND bas<bitis AND bitis<=saat.gun_ani(saat.gun(g->>'baslangic'),tak->>'mesai_bitis') AND (i->>'kisi'=k OR EXISTS(SELECT FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) a WHERE a->>'kisi'=k AND a->'is'=i->'kimlik'));
 ELSIF kod='KAYIT.GECERSIZ_SAYDIM' THEN SELECT icerik INTO h FROM public.olaylar WHERE olay_kimligi=g->>'hedef'; RETURN irp.dogru(h) AND irp.sabit('calisan') ? (h->>'eylem_kodu') AND to_char(saat.an(h->>'oldugu_an') AT TIME ZONE 'Europe/Istanbul','IYYY-IW')=to_char(t AT TIME ZONE 'Europe/Istanbul','IYYY-IW') AND NOT EXISTS(SELECT FROM public.olaylar WHERE eylem_kodu=kod AND icerik#>'{girdiler,hedef}'=g->'hedef');
 ELSIF kod LIKE 'PROJE.ERISIM_%' THEN RETURN motor.oku(d,'projeler') ? (g->>'proje') AND kapilar_v5.aktif_kisi(d,g->>'kisi') AND (kod='PROJE.ERISIM_VERDIM' OR k10.ek_erisim(d,g->>'kisi',g->>'proje'));
 ELSIF kod='BILDIRIM.GORDUM' THEN RETURN NOT EXISTS(SELECT FROM jsonb_array_elements_text((g->'bildirimler')) h WHERE NOT irp.dogru(k9.bildirim_bul(d,h)));
 END IF;
 -- kabul.py:128 varsayılanı; tanımsız eylem biçim kapısında elenir.
 RETURN true;
END $$;
RESET ROLE;
