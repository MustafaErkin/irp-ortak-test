SET ROLE irp_sahibi;
-- kurallar_v9.py:155,313,409. Değişiklik işi kaynakla aynı projede doğar.
CREATE FUNCTION k9.degisiklik_bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql STABLE AS $$
DECLARE g jsonb=e->'girdiler'; s jsonb; deg jsonb; a text; BEGIN
 FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',g->'isler',jsonb_build_array(coalesce(g->'degisenler',g)))) LOOP
  IF s ? 'oncelik' AND s->>'oncelik' NOT IN ('NORMAL','YUKSEK','ACIL') THEN PERFORM kapi.bicim_hatasi('Gorev onceligi'); END IF;
  FOREACH a IN ARRAY ARRAY['baslangic_tarihi','kesin_kabul_tarihi'] LOOP IF irp.dogru(s->a) THEN PERFORM saat.gun(s->>a); END IF; END LOOP;
  deg=nullif(s->'degisiklik','null'); IF deg IS NULL THEN CONTINUE; END IF;
  IF jsonb_typeof(deg)<>'object' OR jsonb_typeof(deg->'kaynak') IS DISTINCT FROM 'string' OR coalesce(deg->>'neden','') NOT IN ('MUSTERI','HATA','IYILESTIRME') THEN PERFORM kapi.bicim_hatasi('Degisiklik bicimi'); END IF;
  IF deg->>'neden'<>'HATA' AND irp.dogru(deg->'sorumlular') THEN PERFORM kapi.bicim_hatasi('Yalniz hatada sorumlular'); END IF;
  PERFORM k9.pay_bicimi(coalesce(deg->'sorumlular','[]'));
 END LOOP;
END $$;
CREATE FUNCTION k9.degisiklik_durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; s jsonb; deg jsonb; x jsonb; BEGIN
 FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',g->'isler',CASE WHEN kod='IS.PLANSIZ_TANIMLADIM' THEN jsonb_build_array(g) ELSE '[]'::jsonb END)) LOOP
  deg=s->'degisiklik'; IF NOT irp.dogru(deg) THEN CONTINUE; END IF;
  x=motor.kayit(d,CASE WHEN kod LIKE 'GOREV.%' THEN 'gorevler' ELSE 'isler' END,deg->>'kaynak');
  IF NOT irp.dogru(x) OR x->>'durum'='IPTAL' OR kod LIKE 'GOREV.%' AND x->>'tur' NOT IN ('NORMAL','REVIZYON','DEGISIKLIK') THEN RETURN false; END IF;
  IF s->>'proje' IS DISTINCT FROM x->>'proje' OR NOT k9.sorumlular_var(d,coalesce(deg->'sorumlular','[]')) THEN RETURN false; END IF;
 END LOOP; RETURN NULL;
END $$;
CREATE FUNCTION k9.degisiklik_sonra(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE tablo text=CASE WHEN e->>'eylem_kodu' LIKE 'GOREV.%' THEN 'gorevler' ELSE 'isler' END; key text; x jsonb; deg jsonb; BEGIN
 FOR key,x IN SELECT * FROM motor.satirlar(m,tablo) WHERE hal->'doguran_olay'=e->'olay_kimligi' AND irp.dogru(hal->'degisiklik') LOOP
  deg=x->'degisiklik'; x=x||jsonb_build_object('degisiklik_kaynagi',deg->'kaynak');
  IF tablo='gorevler' THEN x=x||'{"tur":"DEGISIKLIK"}'; END IF;
  PERFORM motor.kaydet(m,tablo,key,x);
  IF deg->>'neden'='HATA' THEN PERFORM k9.sorumluluk_dogur(m,e,coalesce(deg->'sorumlular','[]'),jsonb_build_array(jsonb_build_object('tur',CASE WHEN tablo='gorevler' THEN 'GOREV' ELSE 'IS' END,'kimlik',key)),'DEGISIKLIK',key); END IF;
 END LOOP;
END $$;
RESET ROLE;
