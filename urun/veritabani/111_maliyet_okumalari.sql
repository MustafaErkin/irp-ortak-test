SET ROLE irp_sahibi;
CREATE FUNCTION okuma.tutar_bul(kimlik text,tur text,tarih text,varsayilan numeric DEFAULT NULL) RETURNS numeric LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT (h.ek->>'tutar')::numeric FROM public.hassas_ekler h JOIN public.olaylar e ON e.olay_kimligi=h.olay
 WHERE h.ek->>'nesne_kimlik'=kimlik AND h.ek->>'tur'=tur AND saat.gun(h.ek->>'gecerli_baslangic')<=saat.gun(tarih)
 AND e.kabul_no<=(SELECT okuma_kabul_no FROM motor.durum WHERE tek)
 AND (coalesce(current_setting('irp.gecmis_okuma',true),'')<>'evet' OR e.oldugu_an<=saat.simdi() AND e.bulut_ulasma_ani<=saat.simdi())
 ORDER BY h.ek->>'gecerli_baslangic' DESC,e.kabul_no LIMIT 1),varsayilan) $$;
CREATE FUNCTION okuma.saat_maliyeti(kisi text,tarih text) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE maas numeric; BEGIN
 IF okuma.tablo('tezgahlar') ? kisi THEN RETURN okuma.tutar_bul(kisi,'SAAT_UCRETI',tarih); END IF;
 maas=okuma.tutar_bul(kisi,'MAAS_AYLIK',tarih); IF maas IS NULL THEN RETURN NULL; END IF;
 RETURN (maas+okuma.tutar_bul(kisi,'GENEL_GIDER_PAYI',tarih,0))/(motor.ayar('OKUMA','maas_paydasi_saat',saat.gun_ani(saat.gun(tarih)),'180')#>>'{}')::numeric;
END $$;
CREATE FUNCTION okuma.bekleyen_maliyet(bas text,bit_ text,proje text DEFAULT NULL,kisi text DEFAULT NULL,maas boolean DEFAULT false,iptal boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE toplam numeric=0; sa numeric; oran numeric; k text; t date; x jsonb; ab timestamptz[]; p timestamptz; q timestamptz; BEGIN
 IF okuma.tablo('gun_onay_ayarlari')='{}' THEN RETURN okuma.para(0); END IF;
 IF maas THEN
  FOR x IN SELECT s.x FROM okuma.satirlar('gorevler') s WHERE proje IS NULL OR s.x->>'proje'=proje LOOP
   FOR t IN SELECT okuma.gunler(bas,bit_) LOOP
    sa=okuma.gorev_payi(x,t::text,t::text,false,kisi);
    IF sa<>0 AND okuma.onay_bekliyor(kisi,t::text) THEN oran=okuma.saat_maliyeti(kisi,t::text); IF oran IS NULL THEN RETURN '"VERI_EKSIK"'; END IF; toplam=toplam+sa*oran; END IF;
   END LOOP;
  END LOOP;
 ELSE
  ab=okuma.pencere(bas,bit_);
  FOR x IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) LOOP
   k=x->>'kisi'; IF k IS NULL OR (proje IS NOT NULL AND x->>'proje' IS DISTINCT FROM proje) OR (kisi IS NOT NULL AND k<>kisi) THEN CONTINUE; END IF;
   IF coalesce(okuma.satir('isler',x->>'is')->>'durum'='IPTAL',false)<>iptal OR x->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') THEN CONTINUE; END IF;
   p=greatest(ab[1],saat.an(x->>'baslangic')); q=least(ab[2],coalesce(saat.an(x->>'bitis'),saat.simdi()));
   IF p<q AND okuma.onay_bekliyor(k,x->>'gun') THEN oran=okuma.saat_maliyeti(k,x->>'gun'); IF oran IS NULL THEN RETURN '"VERI_EKSIK"'; END IF; toplam=toplam+extract(epoch FROM q-p)/3600*oran; END IF;
  END LOOP;
 END IF; RETURN okuma.para(toplam); END $$;
CREATE FUNCTION okuma.iscilik_maliyeti(proje text,bas text,bit_ text,canli boolean DEFAULT false,iptal boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); a date; b date; donmus jsonb; x jsonb; t date; p timestamptz; q timestamptz; u timestamptz; v timestamptz;
 oran numeric; toplam jsonb='{"iscilik":0,"tezgah":0}'; alan text; eksik boolean=false; BEGIN
 a=date_trunc('month',ab[1] AT TIME ZONE 'Europe/Istanbul')::date; b=(a+interval '1 month - 1 day')::date;
 SELECT hal INTO donmus FROM public.ay_kapanislari WHERE anahtar=a::text||CASE WHEN iptal THEN ':IPTAL_MALIYET' ELSE ':MALIYET' END;
 IF NOT canli AND donmus IS NOT NULL THEN
  IF ab<>ARRAY[saat.gun_ani(a),saat.gun_ani(b+1)] THEN RAISE EXCEPTION 'IRP|BICIM|Karar 49: kapanmis ay yalniz tam ay sorgulanir'; END IF;
  RETURN coalesce(donmus->proje,'{"iscilik":"0.00","tezgah":"0.00","eksik_veri":false}');
 END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) LOOP
  IF x->>'proje' IS DISTINCT FROM proje OR coalesce(okuma.satir('isler',x->>'is')->>'durum'='IPTAL',false)<>iptal THEN CONTINUE; END IF;
  IF x->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY','TEZGAH') THEN CONTINUE; END IF;
  p=greatest(saat.an(x->>'baslangic'),ab[1]); q=least(coalesce(saat.an(x->>'bitis'),saat.simdi()),ab[2]); IF p>=q THEN CONTINUE; END IF;
  alan=CASE WHEN x->>'kova'='TEZGAH' THEN 'tezgah' ELSE 'iscilik' END;
  FOR t IN SELECT okuma.gunler(saat.kodla(p),saat.kodla(q-interval '1 microsecond')) LOOP
   u=greatest(p,saat.gun_ani(t)); v=least(q,saat.gun_ani(t+1));
   oran=CASE WHEN alan='tezgah' THEN okuma.tutar_bul(x->>'tezgah','SAAT_UCRETI',t::text) ELSE okuma.saat_maliyeti(x->>'kisi',t::text) END;
   IF oran IS NULL OR toplam->>alan='VERI_EKSIK' THEN toplam=toplam||jsonb_build_object(alan,'VERI_EKSIK'); eksik=true;
   ELSE toplam=okuma.ekle(toplam,alan,extract(epoch FROM v-u)/3600*oran); END IF;
  END LOOP;
 END LOOP;
 FOREACH alan IN ARRAY ARRAY['iscilik','tezgah'] LOOP IF toplam->>alan<>'VERI_EKSIK' THEN toplam=toplam||jsonb_build_object(alan,okuma.para((toplam->>alan)::numeric)); END IF; END LOOP;
 RETURN toplam||jsonb_build_object('eksik_veri',eksik,'onay_bekleyen',okuma.bekleyen_maliyet(bas,bit_,proje,NULL,false,iptal)); END $$;
CREATE FUNCTION okuma.maas_dagilimi(kisi text,ay text,canli boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE bas date=date_trunc('month',saat.gun(ay))::date; bit_ date=(bas+interval '1 month - 1 day')::date;
 donmus jsonb; paylar jsonb='{}'; gunluk jsonb; tutarlar jsonb='{}'; eksik boolean=false; g jsonb; kalem text; tarih date; pay numeric; oran numeric;
 agirlik numeric=0; toplam_agirlik numeric=0; agir numeric; maas numeric=0; deger numeric; toplam numeric=0; sa numeric; BEGIN
 SELECT hal->'maas' INTO donmus FROM public.ay_kapanislari WHERE anahtar=bas::text||':'||kisi;
 IF NOT canli AND donmus IS NOT NULL THEN RETURN donmus; END IF;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') LOOP
  IF g->>'kisi'<>kisi AND NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(g->'kisi_gecmisi','[]')) h WHERE h->>'kisi'=kisi) THEN CONTINUE; END IF;
  kalem=coalesce(g->>'proje',g->>'kategori','BELIRSIZ');
  IF g->>'durum'='IPTAL' THEN kalem='iptal:'||kalem; ELSIF g->>'tur'='REVIZYON' THEN kalem='revizyon:'||kalem; END IF;
  gunluk=CASE WHEN g->>'tur' IN ('NOT','ONAY') THEN '[]'::jsonb ELSE okuma.gorev_gunluk_paylar(g) END;
  FOR tarih IN SELECT okuma.gunler(bas::text,bit_::text) LOOP
   IF g->>'tur' IN ('NOT','ONAY') THEN pay=okuma.gorev_payi(g,tarih::text,tarih::text,false,kisi);
   ELSE SELECT coalesce(sum((z->>'saat')::numeric),0) INTO pay FROM jsonb_array_elements(gunluk) z WHERE z->>'gun'=tarih::text AND z->>'kisi'=kisi; END IF;
   IF pay=0 THEN CONTINUE; END IF;
   paylar=okuma.ekle(paylar,kalem,pay); oran=okuma.saat_maliyeti(kisi,tarih::text);
   IF oran IS NULL OR tutarlar->>kalem='VERI_EKSIK' THEN tutarlar=tutarlar||jsonb_build_object(kalem,'VERI_EKSIK'); eksik=true;
   ELSE tutarlar=okuma.ekle(tutarlar,kalem,pay*oran); END IF;
  END LOOP;
 END LOOP;
 FOR tarih IN SELECT okuma.gunler(bas::text,bit_::text) LOOP
  agir=okuma.gun_agirligi(tarih::text,kisi); toplam_agirlik=toplam_agirlik+agir;
  IF yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(tarih)) THEN agirlik=agirlik+agir; END IF;
 END LOOP;
 oran=CASE WHEN toplam_agirlik<>0 THEN agirlik/toplam_agirlik ELSE 0 END;
 FOR tarih IN SELECT okuma.gunler(bas::text,bit_::text) LOOP
  agir=okuma.gun_agirligi(tarih::text,kisi);
  IF NOT yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(tarih)) OR agir=0 THEN CONTINUE; END IF;
  deger=okuma.tutar_bul(kisi,'MAAS_AYLIK',tarih::text); IF deger IS NULL THEN maas=NULL; eksik=true; EXIT; END IF;
  maas=maas+deger*agir/toplam_agirlik;
 END LOOP;
 FOR kalem,g IN SELECT * FROM jsonb_each(tutarlar) LOOP IF g<>'"VERI_EKSIK"' THEN
  pay=round((g#>>'{}')::numeric,2); toplam=toplam+pay; tutarlar=tutarlar||jsonb_build_object(kalem,okuma.para(pay)); END IF; END LOOP;
 SELECT coalesce(sum((value#>>'{}')::numeric),0) INTO sa FROM jsonb_each(paylar);
 RETURN jsonb_build_object('paylar',paylar,'toplam_saat',sa,'payda',(motor.ayar('OKUMA','maas_paydasi_saat',saat.gun_ani(bas),'180')#>>'{}')::numeric*oran,
 'tutarlar',tutarlar,'onay_bekleyen',okuma.bekleyen_maliyet(bas::text,bit_::text,NULL,kisi,true),
 'dagitilamayan',CASE WHEN eksik THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(greatest(0,maas-toplam)) END,
 'maasin_ustu',CASE WHEN eksik THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(greatest(0,toplam-maas)) END,
 'maas',coalesce(okuma.para(maas),'"VERI_EKSIK"'),'eksik_veri',eksik);
END $$;
CREATE FUNCTION okuma.fazla_mesai_kayitlari() RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; x jsonb; g jsonb; e jsonb; h text; ar jsonb; eng jsonb; pq jsonb; t date; p timestamptz; q timestamptz; u timestamptz; v timestamptz; sa numeric; oran numeric; r jsonb='[]'; BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) WHERE irp.dogru(value->'fazla_mesai') LOOP
  sonuc=sonuc||jsonb_build_array(jsonb_build_object('kisi',x->'kisi','hedef',x->'is','proje',x->'proje','kategori',x->'kategori','tarih',x->'gun','baslangic',x->'baslangic','bitis',coalesce(nullif(x->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))),'katsayi',x->'katsayi'));
 END LOOP;
 FOR x IN SELECT s.x FROM okuma.satirlar('ek_mesai_planlari') s WHERE irp.dogru(s.x->'damga') AND NOT irp.dogru(s.x->'iptal') AND okuma.satir('kisiler',s.x->>'kisi')->>'yaka'='BEYAZ' LOOP
  SELECT a->>'kimlik' INTO h FROM jsonb_array_elements(x->'hedef') a WHERE a->>'tur'='GOREV' LIMIT 1; g=okuma.satir('gorevler',h); pq=takvim.pencere(x);
  eng=takvim.izinler('OKUMA',x->>'kisi');
  FOR e IN SELECT s.x FROM okuma.satirlar('duruslar') s WHERE takvim.birim_kapsamda('OKUMA',okuma.satir('kisiler',x->>'kisi')->>'birim',s.x->'kapsam') LOOP
   eng=eng||jsonb_build_array(jsonb_build_array(e->'baslangic',coalesce(nullif(e->'bitis','null'),to_jsonb(saat.kodla(saat.simdi())))));
  END LOOP;
  FOR ar IN SELECT value FROM jsonb_array_elements(takvim.cikar(jsonb_build_array(pq),eng)) LOOP
   u=saat.an(ar->>0); v=saat.an(ar->>1);
   FOR t IN SELECT okuma.gunler(saat.kodla(u),saat.kodla(v-interval '1 microsecond')) LOOP
    p=greatest(u,saat.gun_ani(t)); q=least(v,saat.gun_ani(t+1));
    sonuc=sonuc||jsonb_build_array(jsonb_build_object('kisi',x->'kisi','hedef',h,'proje',g->'proje','kategori',g->'kategori','tarih',t,'baslangic',saat.kodla(p),'bitis',saat.kodla(q),'katsayi',takvim.katsayi('OKUMA',t)));
   END LOOP;
  END LOOP;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(sonuc) LOOP
  sa=extract(epoch FROM saat.an(x->>'bitis')-saat.an(x->>'baslangic'))/3600; oran=okuma.saat_maliyeti(x->>'kisi',x->>'tarih');
  r=r||jsonb_build_array(x||jsonb_build_object('saat',sa,'prim',coalesce(okuma.para(sa*oran*((x->>'katsayi')::numeric-1)),'"VERI_EKSIK"'),'kalem','FAZLA_MESAI_PRIMI'));
 END LOOP; RETURN r; END $$;
-- Defterin gruplaması yuvarlamadan önce yapılır; eksik tutar NULL ile yayılır.
CREATE FUNCTION okuma.defter_ekle(j jsonb,p text,k text,kalem text,sa numeric,oran numeric) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE key text=coalesce(p,'BELIRSIZ')||'|'||k||'|'||kalem; x jsonb; n numeric; BEGIN
 x=coalesce(j->key,jsonb_build_object('saat',0,'tutar',0,'proje',coalesce(p,'BELIRSIZ'),'kisi',k,'kaynak_kalem',kalem));
 n=CASE WHEN x->>'tutar'='VERI_EKSIK' THEN NULL ELSE (x->>'tutar')::numeric+sa*oran END;
 RETURN j||jsonb_build_object(key,x||jsonb_build_object('saat',(x->>'saat')::numeric+sa,'tutar',coalesce(to_jsonb(n),'"VERI_EKSIK"'))); END $$;
CREATE FUNCTION okuma.donem_defteri(bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; x jsonb; g jsonb; t date; k text; key text; pay numeric; oran numeric; BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) LOOP
  IF x->>'kisi' IS NULL OR saat.gun(x->>'gun') NOT BETWEEN saat.gun(bas) AND saat.gun(bit_) OR x->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') THEN CONTINUE; END IF;
  r=okuma.defter_ekle(r,coalesce(x->>'proje',x->>'kategori'),x->>'kisi','ISCILIK',extract(epoch FROM coalesce(saat.an(x->>'bitis'),saat.simdi())-saat.an(x->>'baslangic'))/3600,okuma.saat_maliyeti(x->>'kisi',x->>'gun'));
 END LOOP;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') LOOP
  FOR x IN SELECT value FROM jsonb_array_elements(okuma.gorev_paylari_canli(g))
   WHERE (value->>'gun')::date BETWEEN saat.gun(bas) AND saat.gun(bit_) LOOP
   k=x->>'kisi'; t=(x->>'gun')::date; pay=(x->>'saat')::numeric;
   r=okuma.defter_ekle(r,coalesce(g->>'proje',g->>'kategori'),k,'MAAS',pay,okuma.saat_maliyeti(k,t::text));
  END LOOP;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.fazla_mesai_kayitlari()) WHERE saat.gun(value->>'tarih') BETWEEN saat.gun(bas) AND saat.gun(bit_) LOOP
  r=okuma.defter_ekle(r,coalesce(x->>'proje',x->>'kategori'),x->>'kisi','FAZLA_MESAI_PRIMI',(x->>'saat')::numeric,okuma.saat_maliyeti(x->>'kisi',x->>'tarih')*((x->>'katsayi')::numeric-1));
 END LOOP;
 FOR key,x IN SELECT * FROM jsonb_each(r) LOOP IF x->>'tutar'<>'VERI_EKSIK' THEN r=r||jsonb_build_object(key,x||jsonb_build_object('tutar',okuma.para((x->>'tutar')::numeric))); END IF; END LOOP;
 RETURN r; END $$;
CREATE FUNCTION okuma.aylik_maliyet_ozeti(kisi text,ay text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a date=date_trunc('month',saat.gun(ay))::date; b date=(a+interval '1 month - 1 day')::date; m jsonb; df jsonb; x jsonb; paylar jsonb='{}'; tutarlar jsonb='{}'; kalem text; toplam numeric=0; sa numeric; eksik boolean; BEGIN
 m=okuma.maas_dagilimi(kisi,ay); IF okuma.satir('kisiler',kisi)->>'yaka'<>'MAVI' THEN RETURN m; END IF;
 SELECT hal INTO df FROM public.ay_kapanislari WHERE anahtar=a::text||':DEFTER_V7'; df=coalesce(df,okuma.donem_defteri(a::text,b::text));
 FOR x IN SELECT value FROM jsonb_each(df) WHERE value->>'kisi'=kisi AND value->>'kaynak_kalem'='ISCILIK' LOOP
  kalem=x->>'proje'; paylar=okuma.ekle(paylar,kalem,(x->>'saat')::numeric);
  IF x->>'tutar'='VERI_EKSIK' OR tutarlar->>kalem='VERI_EKSIK' THEN tutarlar=tutarlar||jsonb_build_object(kalem,'VERI_EKSIK');
  ELSE tutarlar=okuma.ekle(tutarlar,kalem,(x->>'tutar')::numeric); END IF;
 END LOOP;
 eksik=m->>'maas'='VERI_EKSIK' OR EXISTS(SELECT FROM jsonb_each(tutarlar) WHERE value='"VERI_EKSIK"');
 FOR kalem,x IN SELECT * FROM jsonb_each(tutarlar) LOOP IF x<>'"VERI_EKSIK"' THEN toplam=toplam+(x#>>'{}')::numeric; tutarlar=tutarlar||jsonb_build_object(kalem,okuma.para((x#>>'{}')::numeric)); END IF; END LOOP;
 SELECT coalesce(sum((value#>>'{}')::numeric),0) INTO sa FROM jsonb_each(paylar);
 RETURN jsonb_build_object('paylar',paylar,'tutarlar',tutarlar,'maas',m->'maas','eksik_veri',eksik,'toplam_saat',sa,
 'dagitilamayan',CASE WHEN eksik THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(greatest(0,(m->>'maas')::numeric-toplam)) END,
 'maasin_ustu',CASE WHEN eksik THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(greatest(0,toplam-(m->>'maas')::numeric)) END); END $$;
RESET ROLE;
