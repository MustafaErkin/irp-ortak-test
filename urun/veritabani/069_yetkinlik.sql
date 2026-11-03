SET ROLE irp_sahibi;
-- kurallar_v10_2.py:46,56,78. İleri geçerlilik ayrıca bir motor noktasıdır.
CREATE FUNCTION k10_2.yetkinlik_yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kim text=e->>'kim'; b text=motor.kayit(d,'kisiler',e->'girdiler'->>'kisi')->>'birim'; BEGIN
 IF irp.dogru(e->'adina') OR NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 RETURN EXISTS(SELECT FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) r WHERE r->>'eylem_kodu'=e->>'eylem_kodu' AND NOT irp.dogru(r->'gecerli_bitis') AND k7.rol_izni(d,kim,r,b));
END $$;
CREATE FUNCTION k10_2.yetkinlik_durum(d text,e jsonb) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT motor.oku(d,'kisiler') ? (e->'girdiler'->>'kisi') AND saat.gun(e->'girdiler'->>'gecerli_baslangic')>=saat.gun(e->>'oldugu_an')
 AND NOT EXISTS(SELECT FROM jsonb_array_elements_text(e->'girdiler'->'yetkinlikler') x WHERE NOT k6.kod_aktif(d,'YETKINLIK',x)) $$;
CREATE FUNCTION k10_2.yetkinlik_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE g jsonb=e->'girdiler'; k text=g->>'kisi'; p jsonb=motor.kayit(m,'kisiler',k); BEGIN
 IF NOT irp.dogru(p) OR saat.gun(g->>'gecerli_baslangic')>saat.gun(motor.oku(m,'_an')#>>'{}') THEN RETURN; END IF;
 p=p||jsonb_build_object('yetkinlikler',g->'yetkinlikler'); PERFORM motor.kaydet(m,'kisiler',k,p);
 PERFORM motor.yaz(m,'kisi_gecmisi',(SELECT coalesce(jsonb_agg(CASE WHEN x->>'kisi'=k AND x->'gecerli_bitis'='null' THEN x||jsonb_build_object('gecerli_bitis',g->'gecerli_baslangic') ELSE x END ORDER BY n),'[]') FROM jsonb_array_elements(motor.oku(m,'kisi_gecmisi','[]')) WITH ORDINALITY z(x,n)));
 PERFORM motor.ekle(m,'kisi_gecmisi',(p-'istihdam_donemleri'-'ayrilis_tarihi')||jsonb_build_object('kisi',k,'gecerli_baslangic',g->'gecerli_baslangic','gecerli_bitis',NULL));
END $$;
RESET ROLE;
