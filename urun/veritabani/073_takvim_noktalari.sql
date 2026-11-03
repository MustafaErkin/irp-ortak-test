SET ROLE irp_sahibi;
CREATE FUNCTION takvim.nokta_ekle(t timestamptz,tur int,kod text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 IF t<=saat.simdi() THEN INSERT INTO motor.noktalar VALUES(motor.konum(t,tur,kod),t,tur,kod,NULL) ON CONFLICT DO NOTHING; END IF;
END $$;
CREATE FUNCTION takvim.sistem_noktalari(m text,es jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE gun date; birim text; tak jsonb; x jsonb; p jsonb; a timestamptz; b timestamptz; c timestamptz; d timestamptz;
BEGIN
 FOR gun IN SELECT DISTINCT saat.gun(z->>'oldugu_an') FROM jsonb_array_elements(es) z WHERE z->>'eylem_kodu' IN ('MESAI.GIRDIM','MESAI.CIKTIM') LOOP
  PERFORM motor.butce_denetle();
  FOR birim IN SELECT NULL::text UNION SELECT anahtar FROM motor.satirlar(m,'_v9_birim_takvimleri') LOOP
   IF NOT motor.is_gunu(m,gun::text,NULL,birim) THEN CONTINUE; END IF; tak=motor.takvim(m,gun::text,NULL,birim);
   FOR x IN SELECT value FROM jsonb_array_elements(tak->'sabit_molalar') LOOP PERFORM takvim.nokta_ekle(saat.gun_ani(gun,x->>'bas'),0,'MOLA_BASI'); PERFORM takvim.nokta_ekle(saat.gun_ani(gun,x->>'bit'),0,'MOLA_SONU'); END LOOP;
   PERFORM takvim.nokta_ekle(saat.gun_ani(gun,tak->>'mesai_bitis'),0,'PAYDOS');
  END LOOP;
 END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(m,'ek_mesai_planlari') WHERE NOT irp.dogru(hal->'iptal') LOOP PERFORM takvim.nokta_ekle(saat.an(takvim.pencere(x)->>1),2,'V7_EK_BITIS'); END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(m,'izinler') WHERE hal->>'durum'='ONAYLI' LOOP
  a=saat.an(x->>'baslangic'); b=saat.an(x->>'bitis'); gun=saat.gun(saat.kodla(a));
  WHILE gun<=saat.gun(saat.kodla(least(b,saat.simdi()))) LOOP
   PERFORM motor.butce_denetle();
   FOR p IN SELECT value FROM jsonb_array_elements(takvim.normal(m,gun,false,x->>'kisi')) LOOP c=greatest(a,saat.an(p->>0)); d=least(b,saat.an(p->>1)); IF c<d THEN PERFORM takvim.nokta_ekle(c,0,'V7_IZIN'); PERFORM takvim.nokta_ekle(d,0,'V7_IZIN'); END IF; END LOOP;
   gun=gun+1;
  END LOOP;
 END LOOP;
END $$;
RESET ROLE;
