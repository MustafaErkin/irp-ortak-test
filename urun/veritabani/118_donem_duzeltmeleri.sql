SET ROLE irp_sahibi;
CREATE OR REPLACE VIEW okuma.gecmis_olaylar AS SELECT * FROM public.olaylar
WHERE oldugu_an<=saat.simdi() AND
 CASE WHEN nullif(current_setting('irp.okuma_kabul',true),'') IS NOT NULL THEN current_setting('irp.okuma_kabul')::jsonb ? olay_kimligi ELSE bulut_ulasma_ani<=saat.simdi() END;
CREATE FUNCTION okuma.gorev_payi_canli(g jsonb,bas text,bit_ text,kisi text) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ilk text=coalesce(g->>'ilk_kabul_ani',g->>'kabul_ani'); t date; agirlik numeric; toplam numeric=0; pay numeric=0; k text; BEGIN
 IF g->>'tur' IN ('NOT','ONAY') THEN RETURN okuma.gorev_payi(g,bas,bit_,false,kisi); END IF;
 IF ilk IS NULL OR g->>'teslim_tarihi' IS NULL THEN RETURN 0; END IF;
 FOR t IN SELECT okuma.gunler(ilk,g->>'teslim_tarihi') LOOP
  k=okuma.gorevin_kisisi(g,t); IF NOT motor.is_gunu('OKUMA',t::text,k) THEN CONTINUE; END IF;
  agirlik=okuma.saatler(takvim.kisi_normal('OKUMA',k,t)); toplam=toplam+agirlik;
  IF k=kisi AND t BETWEEN saat.gun(bas) AND saat.gun(bit_) AND (g->>'iptal_ani' IS NULL OR t<=saat.gun(g->>'iptal_ani')) THEN pay=pay+agirlik; END IF;
 END LOOP; RETURN CASE WHEN toplam=0 THEN 0 ELSE (g->>'zaman_degeri')::numeric*pay/toplam END; END $$;
CREATE FUNCTION okuma.gorev_paylari_canli(g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ilk text=coalesce(g->>'ilk_kabul_ani',g->>'kabul_ani'); t date; k text; agirlik numeric;
 toplam numeric=0; aday jsonb='[]'; r jsonb='[]'; s jsonb; BEGIN
 IF g->>'tur'='NOT' THEN RETURN r; END IF;
 IF g->>'tur'='ONAY' THEN
  IF g->>'durum'='IPTAL' OR g->>'onay_ani' IS NULL THEN RETURN r; END IF;
  RETURN jsonb_build_array(jsonb_build_object('gun',saat.gun(g->>'onay_ani'),'kisi',g->'kisi','saat',g->'zaman_degeri'));
 END IF;
 IF ilk IS NULL OR g->>'teslim_tarihi' IS NULL THEN RETURN r; END IF;
 FOR t IN SELECT okuma.gunler(ilk,g->>'teslim_tarihi') LOOP
  k=okuma.gorevin_kisisi(g,t); IF NOT motor.is_gunu('OKUMA',t::text,k) THEN CONTINUE; END IF;
  agirlik=okuma.saatler(takvim.kisi_normal('OKUMA',k,t)); toplam=toplam+agirlik;
  aday=aday||jsonb_build_array(jsonb_build_object('gun',t,'kisi',k,'saat',agirlik));
 END LOOP;
 IF toplam=0 THEN RETURN r; END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(aday) LOOP
  IF (s->>'saat')::numeric<>0 AND (g->>'iptal_ani' IS NULL OR (s->>'gun')::date<=saat.gun(g->>'iptal_ani')) THEN
   r=r||jsonb_build_array(s||jsonb_build_object('saat',(g->>'zaman_degeri')::numeric*(s->>'saat')::numeric/toplam));
  END IF;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.duzeltme_defteri(ay text) RETURNS jsonb LANGUAGE plpgsql VOLATILE AS $$
#variable_conflict use_column
DECLARE b date=(date_trunc('month',saat.gun(ay))+interval '1 month - 1 day')::date; kapanis timestamptz; kabul jsonb='[]'; e jsonb; g jsonb; t date; n motor.noktalar; sonuc jsonb; BEGIN
 SELECT saat.an(hal->>'kapanis_ani') INTO kapanis FROM public.ay_kapanislari WHERE starts_with(anahtar,ay||':') AND hal ? 'kapanis_ani' LIMIT 1;
 IF kapanis IS NULL THEN RAISE EXCEPTION 'IRP|BICIM|Kapanis ani yok'; END IF;
 FOR e IN SELECT icerik FROM public.olaylar ORDER BY kabul_no LOOP
  g=e->'girdiler'; t=saat.gun(e->>'oldugu_an');
  IF e->>'eylem_kodu' IN ('IS.SURE_EKLEDIM','EK_MESAI.ONAYLADIM','IZIN.TALEP_ETTIM') THEN t=least(t,saat.gun(coalesce(g->>'tarih',g->>'baslangic'))); END IF;
  IF saat.an(e->>'bulut_ulasma_ani')<=kapanis OR t<=b THEN kabul=kabul||jsonb_build_array(e->'olay_kimligi'); END IF;
 END LOOP;
 FOR e IN SELECT icerik FROM public.olaylar ORDER BY kabul_no LOOP
  IF e->>'eylem_kodu' IN ('KAYIT.GECERSIZ_SAYDIM','IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM','IZIN.IPTAL_ETTIM') AND kabul ? (e#>>'{girdiler,hedef}') THEN kabul=kabul||jsonb_build_array(e->'olay_kimligi'); END IF;
 END LOOP;
 PERFORM pg_advisory_xact_lock(202620,1);
 BEGIN
  PERFORM set_config('irp.okuma_kabul',kabul::text,true);
  DELETE FROM motor.hal WHERE true; DELETE FROM motor.baglam WHERE true; DELETE FROM motor.noktalar WHERE true; DELETE FROM public.ay_kapanislari WHERE true;
  PERFORM motor.bosalt('MOTOR'); PERFORM motor.yaz('MOTOR','kod_listesi',irp.sabit('kodlar9')); PERFORM motor.yaz('MOTOR','yetki_kurallari',irp.sabit('yetkiler9'));
  PERFORM okuma.gecmis_hazirla('MOTOR');
  FOR n IN SELECT * FROM motor.noktalar WHERE an<=saat.simdi() ORDER BY konum COLLATE "C" LOOP PERFORM motor.nokta_isle('MOTOR',n); END LOOP;
  DELETE FROM motor.yayin WHERE true; PERFORM motor.yayinla(); sonuc=okuma.donem_defteri(ay,b::text);
  RAISE EXCEPTION USING ERRCODE='P2222',MESSAGE='Duzeltme defteri tamamlandi';
 EXCEPTION WHEN SQLSTATE 'P2222' THEN NULL; END;
 RETURN sonuc; END $$;
CREATE FUNCTION okuma.onceki_donem_duzeltmeleri() RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; kapali text[]; ay text; yeni jsonb; eski jsonb; hedef date; key text; x jsonb; y jsonb; once jsonb; tutar numeric; sa numeric; kayitlar jsonb; BEGIN
 SELECT coalesce(array_agg(left(anahtar,10) ORDER BY anahtar COLLATE "C"),'{}') INTO kapali FROM public.ay_kapanislari WHERE anahtar LIKE '%:DEFTER_V7';
 FOREACH ay IN ARRAY kapali LOOP
  yeni=okuma.duzeltme_defteri(ay); SELECT hal INTO eski FROM public.ay_kapanislari WHERE anahtar=ay||':DEFTER_V7'; hedef=(ay::date+interval '1 month')::date;
  WHILE hedef::text=ANY(kapali) LOOP hedef=(hedef+interval '1 month')::date; END LOOP;
  FOR key IN SELECT jsonb_object_keys(yeni) UNION SELECT jsonb_object_keys(eski) ORDER BY 1 LOOP
   x=coalesce(yeni->key,'{"saat":0,"tutar":"0.00"}'); y=coalesce(eski->key,'{"saat":0,"tutar":"0.00"}');
   SELECT coalesce(jsonb_agg(z),'[]') INTO kayitlar FROM public.ay_kapanislari a CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN a.anahtar LIKE '%:DUZELTMELER' THEN a.hal ELSE '[]'::jsonb END) z WHERE z->>'kaynak_ay'=ay AND z->>'anahtar'=key;
   IF x=y AND kayitlar='[]' THEN CONTINUE; END IF;
   tutar=CASE WHEN x->>'tutar'='VERI_EKSIK' OR y->>'tutar'='VERI_EKSIK' THEN NULL ELSE (x->>'tutar')::numeric-(y->>'tutar')::numeric END; sa=(x->>'saat')::numeric-(y->>'saat')::numeric;
   FOR once IN SELECT value FROM jsonb_array_elements(kayitlar) LOOP IF tutar IS NOT NULL AND once->>'tutar'<>'VERI_EKSIK' THEN tutar=tutar-(once->>'tutar')::numeric; END IF; sa=sa-(once->>'saat')::numeric; END LOOP;
   IF abs(sa)<0.000000001 AND tutar=0 THEN CONTINUE; END IF;
   r=r||jsonb_build_array(jsonb_build_object('anahtar',key,'kalem','ONCEKI_DONEM_DUZELTMESI','kaynak_kalem',split_part(key,'|',3),'proje',split_part(key,'|',1),'kisi',split_part(key,'|',2),'kaynak_ay',ay,'ay',hedef,'saat',sa,'tutar',coalesce(okuma.para(tutar),'"VERI_EKSIK"')));
  END LOOP;
 END LOOP; RETURN r; END $$;
RESET ROLE;
