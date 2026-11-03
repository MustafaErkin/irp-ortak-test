SET ROLE irp_sahibi;
-- kurallar_v7.py:300. B0/B1 fotoğrafı onay sırasında bilinen etapları saklar.
CREATE FUNCTION k7.plan_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE g jsonb=e->'girdiler'; t timestamptz=saat.an(e->>'oldugu_an');
 kabul timestamptz=saat.an(coalesce(e->>'bulut_ulasma_ani',e->>'oldugu_an'));
 es jsonb=motor.oku(m,'olaylar','[]'); kaynak jsonb=motor.oku(m,'etaplar');
 ss jsonb=motor.kayit(m,'plan_surumleri',g->>'proje','[]'); etaplar jsonb='{}'; k text; v jsonb;
BEGIN
 IF EXISTS(SELECT FROM jsonb_array_elements(es) x WHERE x->>'eylem_kodu' LIKE 'ETAP.%' AND saat.an(x->>'oldugu_an')<=t AND saat.an(coalesce(x->>'bulut_ulasma_ani',x->>'oldugu_an'))>kabul) THEN
  SELECT coalesce(jsonb_agg(x),'[]') INTO es FROM jsonb_array_elements(es) x WHERE x->>'eylem_kodu' NOT LIKE 'PLAN.%' AND saat.an(coalesce(x->>'bulut_ulasma_ani',x->>'oldugu_an'))<=kabul;
  kaynak=motor.fotograf(es,t)->'etaplar';
 END IF;
 FOR k,v IN SELECT * FROM jsonb_each(coalesce(kaynak,'{}')) WHERE value->>'proje'=g->>'proje' LOOP
  etaplar=etaplar||jsonb_build_object(k,jsonb_build_object('ad',v->'ad','birim',v->'birim','baslangic',v->'baslangic','bitis',v->'bitis','hedef_saat',v->'hedef_saat'));
 END LOOP;
 ss=ss||jsonb_build_array(jsonb_build_object('no','B'||jsonb_array_length(ss),'proje',g->'proje','onay_ani',saat.kodla(t),'onaylayan',e->'kim','gerekce',g->'gerekce','etaplar',etaplar));
 PERFORM motor.kaydet(m,'plan_surumleri',g->>'proje',ss);
END $$;
CREATE FUNCTION k7.plan_durum(d text,e jsonb) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT irp.dogru(motor.kayit(d,'projeler',e->'girdiler'->>'proje')->'aktif')
 AND EXISTS(SELECT FROM motor.satirlar(d,'etaplar') WHERE hal->>'proje'=e->'girdiler'->>'proje')
 AND (NOT irp.dogru(motor.kayit(d,'plan_surumleri',e->'girdiler'->>'proje','[]')) OR length(trim(coalesce(e->'girdiler'->>'gerekce','')))>0) $$;
RESET ROLE;
