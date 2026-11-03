SET ROLE irp_sahibi;
CREATE FUNCTION k10_1.dolu(x jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$ SELECT coalesce(jsonb_typeof(x)='string' AND length(trim(x#>>'{}'))>0,false) $$;
-- kurallar_v10_1.bicim; hata metinleri modelle aynı.
CREATE FUNCTION k10_1.bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; ss jsonb='[]'; s jsonb; a timestamptz; b timestamptz; alan text; r jsonb; BEGIN
 IF irp.sabit('kabul_sirali') ? kod AND saat.an(e->>'oldugu_an')>saat.simdi() THEN PERFORM kapi.bicim_hatasi('T10 yonetim olayi gelecekte olamaz'); END IF;
 IF kod='PLAN.TARIHLEDIM' THEN ss=g->'hedefler'; IF jsonb_typeof(ss)<>'array' OR ss='[]' THEN PERFORM kapi.bicim_hatasi('Plan hedefleri gerekli'); END IF;
  FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP IF jsonb_typeof(s)<>'object' OR coalesce(s->>'tur','') NOT IN ('IS','GOREV') OR NOT k10_1.dolu(s->'kimlik') THEN PERFORM kapi.bicim_hatasi('Plan hedefi'); END IF; IF NOT irp.dogru(s->'planlanan_baslangic') OR NOT irp.dogru(s->'planlanan_bitis') THEN PERFORM kapi.bicim_hatasi('Iki plan tarihi gerekli'); END IF; END LOOP;
  IF (SELECT count(DISTINCT (value->'tur',value->'kimlik'))<>count(*) FROM jsonb_array_elements(ss)) THEN PERFORM kapi.bicim_hatasi('Plan hedefi tekil'); END IF;
 ELSIF kod IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM','GOREV.ATADIM') THEN ss=coalesce(g->'isler',g->'gorevler',jsonb_build_array(g)); END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP a=saat.an(s->>'planlanan_baslangic'); b=saat.an(s->>'planlanan_bitis'); IF a IS NOT NULL AND b IS NULL AND kod='GOREV.ATADIM' THEN b=gorev.son_teslim_ani(s,d); END IF; IF a>=b THEN PERFORM kapi.bicim_hatasi('Plan baslangici bitisten once olmali'); END IF; END LOOP;
 FOREACH alan IN ARRAY ARRAY['kaynak','gerekce'] LOOP IF kod='PLAN.TARIHLEDIM' AND g ? alan AND jsonb_typeof(g->alan)<>'string' THEN PERFORM kapi.bicim_hatasi('Plan metin alani'); END IF; END LOOP;
 IF kod LIKE 'NESNE.SURUM_%' THEN
  IF NOT k10_1.dolu(g->'hedef') THEN PERFORM kapi.bicim_hatasi('Surum hedefi'); END IF;
  IF kod='NESNE.SURUM_EKLEDIM' THEN
   IF jsonb_typeof(g->'dosyalar')<>'array' OR g->'dosyalar'='[]' OR EXISTS(SELECT FROM jsonb_array_elements(g->'dosyalar') WHERE NOT k10_1.dolu(value)) THEN PERFORM kapi.bicim_hatasi('En az bir dosya kimligi gerekli'); END IF;
   IF (SELECT count(DISTINCT value)<>count(*) FROM jsonb_array_elements(g->'dosyalar')) THEN PERFORM kapi.bicim_hatasi('Dosya kimlikleri tekil'); END IF;
   IF g->>'surum_adi' IS NOT NULL AND jsonb_typeof(g->'surum_adi')<>'string' THEN PERFORM kapi.bicim_hatasi('Surum adi metin'); END IF;
   IF g ? 'aciklama' AND jsonb_typeof(g->'aciklama')<>'string' THEN PERFORM kapi.bicim_hatasi('Aciklama metin'); END IF;
  ELSIF jsonb_typeof(g->'surum_no')<>'number' OR g->>'surum_no' !~ '^[0-9]+$' OR (g->>'surum_no')::numeric<1 THEN PERFORM kapi.bicim_hatasi('Pozitif surum numarasi'); END IF;
  IF kod='NESNE.SURUM_GERI_CEKTIM' AND NOT k10_1.dolu(g->'gerekce') THEN PERFORM kapi.bicim_hatasi('Geri cekme gerekcesi gerekli'); END IF;
 END IF;
 IF kod='NESNE_TURU.TANIMLADIM' AND g->>'surum_onaylayanlar' IS NOT NULL THEN r=g->'surum_onaylayanlar'; IF jsonb_typeof(r)<>'object' OR irp.dogru(r) AND (jsonb_typeof(r->'kimler') IS DISTINCT FROM 'array' OR EXISTS(SELECT FROM jsonb_array_elements(r->'kimler') WHERE NOT k10_1.dolu(value)) OR coalesce(r->>'kapsam','') NOT IN ('BIRIM','FIRMA')) THEN PERFORM kapi.bicim_hatasi('Surum onaylayanlar yetki satiri'); END IF; END IF;
 IF kod='MODUL.TANIMLADIM' THEN IF NOT k10_1.dolu(g->'kod') OR NOT k10_1.dolu(g->'ad') OR NOT k10_1.dolu(g->'servis_kimligi') OR jsonb_typeof(g->'aktif')<>'boolean' THEN PERFORM kapi.bicim_hatasi('Modul tanimi'); END IF; IF g->>'kod'='CEKIRDEK' THEN PERFORM kapi.bicim_hatasi('CEKIRDEK kaynak adi ayrilmistir'); END IF; END IF;
END $$;
CREATE FUNCTION k10_2.bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; s jsonb; ps text[]; p text; ys jsonb; BEGIN
 IF kod IN ('NESNE.ACTIM','NESNE.GUNCELLEDIM') THEN s=CASE WHEN kod='NESNE.ACTIM' THEN g ELSE g->'degisenler' END;
  IF s ? 'baglar' AND (jsonb_typeof(s->'baglar')<>'array' OR EXISTS(SELECT FROM jsonb_array_elements(s->'baglar') x WHERE jsonb_typeof(x)<>'object' OR jsonb_typeof(x->'tur') IS DISTINCT FROM 'string' OR jsonb_typeof(x->'kimlik') IS DISTINCT FROM 'string' OR x->>'kimlik'='')) THEN PERFORM kapi.bicim_hatasi('Nesne baglari'); END IF;
  SELECT coalesce(array_agg(x->>'kimlik'),'{}') INTO ps FROM jsonb_array_elements(coalesce(s->'baglar','[]')) x WHERE x->>'tur'='PROJE'; p=CASE WHEN kod='NESNE.ACTIM' THEN g->>'proje' ELSE motor.kayit(d,'nesneler',g->>'hedef')->>'proje' END;
  IF kod='NESNE.ACTIM' THEN IF p IS NOT NULL AND (jsonb_typeof(g->'proje')<>'string' OR p='') THEN PERFORM kapi.bicim_hatasi('Nesne projesi'); END IF;
   IF coalesce(p,'')='' AND cardinality(ps)>1 OR coalesce(p,'')<>'' AND EXISTS(SELECT FROM unnest(ps) x WHERE x<>p) THEN PERFORM kapi.bicim_hatasi('Nesne proje baglari uyusmuyor'); END IF;
  ELSIF EXISTS(SELECT FROM unnest(ps) x WHERE x IS DISTINCT FROM p) OR s ? 'proje' THEN PERFORM kapi.bicim_hatasi('Nesnenin projesi degismez'); END IF;
 END IF;
 IF kod='MODUL.TANIMLADIM' AND g ? 'cihaz_harfi' AND (jsonb_typeof(g->'cihaz_harfi')<>'string' OR g->>'cihaz_harfi' !~ '^[A-Z]$') THEN PERFORM kapi.bicim_hatasi('Modul cihaz harfi tek buyuk harf'); END IF;
 IF kod='KISI.YETKINLIK_TANIMLADIM' THEN ys=g->'yetkinlikler'; IF jsonb_typeof(g->'kisi')<>'string' OR jsonb_typeof(ys)<>'array' OR EXISTS(SELECT FROM jsonb_array_elements(ys) x WHERE jsonb_typeof(x)<>'string' OR x='""') OR (SELECT count(DISTINCT value)<>count(*) FROM jsonb_array_elements(ys)) THEN PERFORM kapi.bicim_hatasi('Yetkinlikler tekil kod dizisi'); END IF; PERFORM saat.gun(g->>'gecerli_baslangic'); IF saat.an(e->>'oldugu_an')>saat.simdi() THEN PERFORM kapi.bicim_hatasi('Yonetim olayi gelecekte olamaz'); END IF; END IF;
 IF kod IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM','IS.DEGISTIRDIM') THEN FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'isler',jsonb_build_array(coalesce(g->'degisenler',g)))) LOOP IF s->>'yetkinlik' IS NOT NULL AND (jsonb_typeof(s->'yetkinlik')<>'string' OR s->>'yetkinlik'='') THEN PERFORM kapi.bicim_hatasi('Is yetkinligi tek kod'); END IF; END LOOP; END IF;
END $$;
RESET ROLE;
