SET ROLE irp_sahibi;
-- maliyet_izi_v6.py:7 maliyet_izleri. Para izinin yuvarlanmamış alanları float8.
CREATE FUNCTION maliyet_izi_v6.maliyet_izleri(d text,bas date,bitis date,maaslar jsonb DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE izler jsonb='{}'; sonuc jsonb; a jsonb; x jsonb; g jsonb; m jsonb; r record; k text;
 p timestamptz; q timestamptz; son timestamptz; key text; alan text; kalem text;
 sa double precision; oran numeric; toplam double precision; makine boolean;
 sifir jsonb='{"emek_saat":0.0,"iscilik":0.0,"tezgah":0.0,"maas":0.0}';
BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) WHERE value->>'kova' IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY','TEZGAH') AND irp.dogru(value->'is') LOOP
  p=greatest(saat.an(a->>'baslangic'),saat.gun_ani(bas)); son=least(coalesce(saat.an(a->>'bitis'),saat.simdi()),saat.gun_ani(bitis+1));
  WHILE p<son LOOP
   q=least(son,saat.gun_ani(saat.gun(saat.kodla(p))+1));
   key=jsonb_build_array('IS',a->>'is',a->'proje',saat.gun(saat.kodla(p))::text)::text;
   x=coalesce(izler->key,sifir)||jsonb_build_object('tur','IS','kimlik',a->'is','proje',a->'proje','gun',saat.gun(saat.kodla(p))::text);
   sa=extract(epoch FROM q-p)::double precision/3600;
   IF a->>'kova' IN ('CALISMA','YENIDEN_ISLEME') THEN x=x||jsonb_build_object('emek_saat',irp.kayan_sayi((x->>'emek_saat')::double precision+sa)); END IF;
   makine=a->>'kova'='TEZGAH'; alan=CASE WHEN makine THEN 'tezgah' ELSE 'iscilik' END;
   oran=CASE WHEN makine THEN zaman.tutar_bul(a->>'tezgah','SAAT_UCRETI',saat.gun(saat.kodla(p))) ELSE zaman.saat_maliyeti(d,a->>'kisi',saat.gun(saat.kodla(p))) END;
   x=x||jsonb_build_object(alan,CASE WHEN oran IS NULL OR x->>alan='VERI_EKSIK' THEN '"VERI_EKSIK"'::jsonb ELSE irp.kayan_sayi((x->>alan)::double precision+sa*oran::double precision) END);
   izler=izler||jsonb_build_object(key,x); p=q;
  END LOOP;
 END LOOP;
 IF maaslar IS NULL THEN
  maaslar='{}'; FOR k IN SELECT anahtar FROM motor.satirlar(d,'kisiler') LOOP maaslar=maaslar||jsonb_build_object(k,zaman.maas_dagilimi(d,k,bas)); END LOOP;
 END IF;
 FOR g IN SELECT hal FROM motor.satirlar(d,'gorevler') LOOP
  kalem=coalesce(nullif(g->>'proje',''),nullif(g->>'kategori',''),'BELIRSIZ');
  IF g->>'durum'='IPTAL' THEN kalem='iptal:'||kalem; ELSIF g->>'tur'='REVIZYON' THEN kalem='revizyon:'||kalem; END IF;
  FOR r IN SELECT * FROM zaman.gorev_pay_satirlari(d,g,bas,bitis) ORDER BY gun,kisi COLLATE "C" LOOP
   IF r.saat=0 THEN CONTINUE; END IF;
   m=maaslar->r.kisi; toplam=coalesce((m->'paylar'->>kalem)::double precision,0);
   key=jsonb_build_array('GOREV',g->>'kimlik',g->'proje',r.gun::text)::text;
   x=coalesce(izler->key,sifir)||jsonb_build_object('tur','GOREV','kimlik',g->'kimlik','proje',g->'proje','gun',r.gun::text);
   x=x||jsonb_build_object('emek_saat',irp.kayan_sayi((x->>'emek_saat')::double precision+r.saat));
   IF m->'tutarlar'->>kalem='VERI_EKSIK' THEN x=x||'{"maas":"VERI_EKSIK"}';
   ELSIF toplam<>0 AND x->>'maas'<>'VERI_EKSIK' THEN x=x||jsonb_build_object('maas',irp.kayan_sayi((x->>'maas')::double precision+coalesce((m->'tutarlar'->>kalem)::double precision,0)*r.saat/toplam)); END IF;
   izler=izler||jsonb_build_object(key,x);
  END LOOP;
 END LOOP;
 SELECT coalesce(jsonb_agg(value ORDER BY (value->>'tur') COLLATE "C",(value->>'kimlik') COLLATE "C",coalesce(value->>'proje','None') COLLATE "C",(value->>'gun') COLLATE "C"),'[]') INTO sonuc FROM jsonb_each(izler);
 RETURN sonuc;
END $$;

-- gorunum_v7.py:398. Kapanışta bilinenler ve eski döneme ait geç tanıklık.
CREATE FUNCTION zaman.duzeltme_defteri(d text,ay date) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE bitis date=(ay+interval '1 month - 1 day')::date; kapanis timestamptz; kabul text[]; es jsonb;
BEGIN
 SELECT saat.an(hal->>'kapanis_ani') INTO kapanis FROM public.ay_kapanislari WHERE left(anahtar,11)=ay::text||':' AND hal ? 'kapanis_ani' ORDER BY anahtar COLLATE "C" LIMIT 1;
 IF kapanis IS NULL THEN RAISE EXCEPTION 'Kapanış anı yok: %',ay; END IF;
 SELECT coalesce(array_agg(olay_kimligi),'{}') INTO kabul FROM public.olaylar
 WHERE bulut_ulasma_ani<=kapanis OR saat.gun(icerik->>'oldugu_an')<=bitis
  OR icerik->>'eylem_kodu' IN ('IS.SURE_EKLEDIM','EK_MESAI.ONAYLADIM','IZIN.TALEP_ETTIM')
   AND saat.gun(coalesce(nullif(icerik->'girdiler'->>'tarih',''),icerik->'girdiler'->>'baslangic'))<=bitis;
 SELECT kabul||coalesce(array_agg(olay_kimligi),'{}') INTO kabul FROM public.olaylar
 WHERE icerik->>'eylem_kodu' IN ('KAYIT.GECERSIZ_SAYDIM','IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM','IZIN.IPTAL_ETTIM') AND icerik->'girdiler'->>'hedef'=ANY(kabul);
 SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]') INTO es FROM public.olaylar WHERE olay_kimligi=ANY(kabul);
 RETURN motor.fotograf(es,saat.simdi(),'donem_defteri',NULL,ay,bitis);
END $$;
CREATE FUNCTION zaman.onceki_donem_duzeltmeleri(d text) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; ay date; bitis date; hedef date; kapali date[]; yeni jsonb; eski jsonb; x jsonb; y jsonb; once jsonb;
 key text; sa double precision; tutar numeric; once_yazilan jsonb;
BEGIN
 SELECT coalesce(array_agg(left(anahtar,10)::date ORDER BY anahtar),'{}') INTO kapali FROM public.ay_kapanislari WHERE anahtar LIKE '%:DEFTER_V7';
 FOREACH ay IN ARRAY kapali LOOP
  yeni=zaman.duzeltme_defteri(d,ay); SELECT hal INTO eski FROM public.ay_kapanislari WHERE anahtar=ay::text||':DEFTER_V7';
  hedef=(ay+interval '1 month')::date;
  WHILE hedef=ANY(kapali) LOOP hedef=(hedef+interval '1 month')::date; END LOOP;
  FOR key IN SELECT z FROM jsonb_object_keys(yeni||eski) z ORDER BY z COLLATE "C" LOOP
   x=coalesce(yeni->key,'{"saat":0,"tutar":"0"}'); y=coalesce(eski->key,'{"saat":0,"tutar":"0"}');
   SELECT coalesce(jsonb_agg(v ORDER BY a.anahtar,n),'[]') INTO once_yazilan FROM public.ay_kapanislari a,
    jsonb_array_elements(CASE WHEN a.anahtar LIKE '%:DUZELTMELER' THEN a.hal ELSE '[]'::jsonb END) WITH ORDINALITY z(v,n)
    WHERE a.anahtar LIKE '%:DUZELTMELER' AND v->>'kaynak_ay'=ay::text AND v->>'anahtar'=key;
   IF x=y AND once_yazilan='[]' THEN CONTINUE; END IF;
   tutar=CASE WHEN x->>'tutar'='VERI_EKSIK' OR y->>'tutar'='VERI_EKSIK' THEN NULL ELSE (x->>'tutar')::numeric-(y->>'tutar')::numeric END;
   sa=(x->>'saat')::double precision-(y->>'saat')::double precision;
   FOR once IN SELECT value FROM jsonb_array_elements(once_yazilan) LOOP
    IF tutar IS NOT NULL AND once->>'tutar'<>'VERI_EKSIK' THEN tutar=tutar-(once->>'tutar')::numeric; END IF;
    sa=sa-(once->>'saat')::double precision;
   END LOOP;
   IF abs(sa)<1e-9 AND tutar=0 THEN CONTINUE; END IF;
   sonuc=sonuc||jsonb_build_array(jsonb_build_object('anahtar',key,'kalem','ONCEKI_DONEM_DUZELTMESI','kaynak_kalem',split_part(key,'|',3),
    'proje',split_part(key,'|',1),'kisi',split_part(key,'|',2),'kaynak_ay',ay::text,'ay',hedef::text,'saat',irp.kayan_sayi(sa),'tutar',coalesce(zaman.para(tutar),'VERI_EKSIK')));
  END LOOP;
 END LOOP; RETURN sonuc;
END $$;
RESET ROLE;
