SET ROLE irp_sahibi;
-- kurallar_v9.py:328 makine_baslangici; ön işlerin kaynak sırası korunur.
CREATE FUNCTION k9.makine_baslangici(d text,i jsonb) RETURNS timestamptz LANGUAGE sql STABLE AS $$
 SELECT saat.an(coalesce(x->>'bitis_ani',x->>'tamamlanma_ani')) FROM (
  SELECT motor.kayit(d,'isler',key) x,n FROM jsonb_array_elements_text(coalesce(i->'on_isler','[]')) WITH ORDINALITY z(key,n)) q
 WHERE x->>'tezgah_rolu'='BASLAT' AND x->'tezgah'=i->'tezgah' AND x->'parca_kodu' IS NOT DISTINCT FROM i->'parca_kodu' ORDER BY n LIMIT 1 $$;
-- kurallar_v9.py:120,128,265. Eski ARIZA tanıklığının tarihsel istisnası korunur.
CREATE FUNCTION k9.durus_nedeni_bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; i jsonb; bas timestamptz; BEGIN
 IF kod='IS.ARIZA_BILDIRDIM' THEN
  IF irp.dogru(g->'neden') THEN PERFORM k9.neden_bicimi(d,g->'neden',g->>'not',true);
  ELSIF jsonb_typeof(g->'not') IS DISTINCT FROM 'string' OR trim(g->>'not')='' THEN PERFORM kapi.bicim_hatasi('Duruş nedeni veya not gerekli'); END IF;
 END IF;
 IF kod='GOREV.TAMAMLADIM' AND irp.dogru(g->'gecikme_nedeni') THEN PERFORM k9.neden_bicimi(d,g->'gecikme_nedeni',g->>'gecikme_aciklamasi'); END IF;
 IF kod='IS.TAMAMLADIM' AND irp.dogru(g->'makine_bitis_ani') THEN
  i=motor.kayit(d,'isler',(kapi.hedefler(e,'IS'))[1]); bas=k9.makine_baslangici(d,i);
  IF i->>'tezgah_rolu' IS DISTINCT FROM 'AL' OR bas IS NULL OR NOT saat.an(g->>'makine_bitis_ani') BETWEEN bas AND saat.an(e->>'oldugu_an') THEN PERFORM kapi.bicim_hatasi('Makine bitis araligi'); END IF;
 END IF;
END $$;
CREATE FUNCTION k9.durus_nedeni_durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE g jsonb=e->'girdiler'; ust text=g->>'ust'; p jsonb; BEGIN
 IF e->>'eylem_kodu'<>'KOD.TANIMLADIM' OR g->>'liste'<>'DURUS_NEDENI' THEN RETURN NULL; END IF;
 IF coalesce(ust,'')<>'' THEN
  p=motor.kayit(d,'kod_listesi','DURUS_NEDENI:'||ust);
  RETURN irp.dogru(p->'aktif') AND NOT irp.dogru(p->'ust') AND ust<>g->>'kod'
   AND NOT EXISTS(SELECT FROM motor.satirlar(d,'kod_listesi') WHERE hal->>'liste'='DURUS_NEDENI' AND hal->'ust'=g->'kod');
 END IF;
 RETURN NOT EXISTS(SELECT FROM motor.satirlar(d,'kod_listesi') WHERE hal->'ust'=g->'kod') OR irp.dogru(g->'aktif');
END $$;
RESET ROLE;
