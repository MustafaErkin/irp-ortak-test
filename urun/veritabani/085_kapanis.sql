SET ROLE irp_sahibi;
-- zaman.py:10 ve gorunum_v7.py:423. Önce bütün hesaplar; sonra tek atomik yazı.
CREATE FUNCTION zaman.ay_kapanisi(ay date) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE bas date=date_trunc('month',ay)::date; bitis date=(date_trunc('month',ay)+interval '1 month - 1 day')::date;
 sonuc jsonb; yeni jsonb='{}'; paylar jsonb='{}'; maaslar jsonb='{}'; maliyet jsonb='{}'; iptal jsonb='{}'; raporlar jsonb='{}';
 k text; g jsonb; x jsonb; maas jsonb; yuk jsonb; cihazlar jsonb; duzeltmeler jsonb; d text='YAYIN';
BEGIN
 IF saat.gun(saat.kodla(saat.simdi()))<=bitis THEN RAISE EXCEPTION 'IRP|BICIM|Ay henuz bitmedi'; END IF;
 IF EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar=bas::text||':GOREV_PAYLARI') THEN SELECT jsonb_object_agg(anahtar,hal) INTO sonuc FROM public.ay_kapanislari; RETURN sonuc; END IF;
 FOR k,g IN SELECT * FROM motor.satirlar(d,'gorevler') WHERE hal->>'tur' IN ('NORMAL','REVIZYON','DEGISIKLIK') LOOP
  SELECT coalesce(jsonb_agg(v),'[]') INTO maas FROM jsonb_array_elements(zaman.gorev_gunluk_paylar(d,g)) v WHERE saat.gun(v->>'gun') BETWEEN bas AND bitis;
  SELECT coalesce(jsonb_agg(v),'[]') INTO yuk FROM jsonb_array_elements(zaman.gorev_gunluk_paylar(d,g,true)) v WHERE saat.gun(v->>'gun') BETWEEN bas AND bitis;
  paylar=paylar||jsonb_build_object(k,jsonb_build_object('maas',maas,'yuk',yuk));
 END LOOP;
 FOR k IN SELECT anahtar FROM motor.satirlar(d,'kisiler') LOOP
  SELECT hal->'maas' INTO maas FROM public.ay_kapanislari WHERE anahtar=bas::text||':'||k;
  IF maas IS NULL THEN
   maas=zaman.maas_dagilimi(d,k,bas,true);
   yeni=yeni||jsonb_build_object(bas::text||':'||k,jsonb_build_object('maas',maas,'kapanis_ani',saat.kodla(saat.simdi())));
  END IF;
  maaslar=maaslar||jsonb_build_object(k,maas);
 END LOOP;
 FOR k IN SELECT anahtar FROM motor.satirlar(d,'projeler') LOOP
  maliyet=maliyet||jsonb_build_object(k,zaman.iscilik_maliyeti(d,k,bas,bitis,true));
  iptal=iptal||jsonb_build_object(k,zaman.iscilik_maliyeti(d,k,bas,bitis,true,true));
 END LOOP;
 IF NOT EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar=bas::text||':MALIYET') THEN yeni=yeni||jsonb_build_object(bas::text||':MALIYET',maliyet); END IF;
 yeni=yeni||jsonb_build_object(bas::text||':IPTAL_MALIYET',iptal,bas::text||':GOREV_PAYLARI',paylar,
  bas::text||':MALIYET_IZLERI',maliyet_izi_v6.maliyet_izleri(d,bas,bitis,maaslar),bas::text||':DEFTER_V7',zaman.donem_defteri(d,bas,bitis));
 FOR k,x IN SELECT * FROM motor.satirlar(d,'gun_sonu_raporlari') WHERE saat.gun(hal->>'gun') BETWEEN bas AND bitis LOOP
  raporlar=raporlar||jsonb_build_object(k,k7.gun_sonu_raporu(d,x->>'kisi',saat.gun(x->>'gun')));
 END LOOP;
 SELECT coalesce(jsonb_agg(x),'[]') INTO duzeltmeler FROM jsonb_array_elements(zaman.onceki_donem_duzeltmeleri(d)) x WHERE x->>'ay'=bas::text;
 SELECT coalesce(jsonb_object_agg(cihaz,saat.kodla(t)),'{}') INTO cihazlar FROM (
  SELECT cihaz,max(t) t FROM (SELECT anahtar cihaz,saat.an(hal->>'son_esitleme') t FROM public.cihaz_esitlemeleri
   UNION ALL SELECT icerik->>'cihaz',bulut_ulasma_ani FROM public.olaylar) q GROUP BY cihaz) z WHERE t<saat.simdi();
 yeni=yeni||jsonb_build_object(bas::text||':RAPORLAR',raporlar,bas::text||':DUZELTMELER',duzeltmeler,
  bas::text||':ONAY_UYARILARI',k9.onay_uyarilari(d,bas,bitis),bas::text||':CIHAZ_UYARILARI',cihazlar);
 INSERT INTO public.ay_kapanislari SELECT * FROM jsonb_each(yeni) ON CONFLICT(anahtar) DO UPDATE SET hal=excluded.hal;
 SELECT jsonb_object_agg(anahtar,hal) INTO sonuc FROM public.ay_kapanislari; RETURN sonuc;
END $$;
RESET ROLE;
