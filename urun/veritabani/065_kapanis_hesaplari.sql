SET ROLE irp_sahibi;
-- gorunumler.py:31-73. Kapanmış ayın görev/gün/kişi payı kaynak olarak sabittir.
CREATE FUNCTION zaman.gorevin_kisisi(g jsonb,tarih date) RETURNS text LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce((SELECT x->>'kisi' FROM jsonb_array_elements(coalesce(g->'kisi_gecmisi','[]')) x
 WHERE saat.gun(x->>'baslangic')<=tarih ORDER BY x->>'baslangic' DESC LIMIT 1),g->>'kisi') $$;
CREATE FUNCTION takvim.saatler(xs jsonb) RETURNS double precision LANGUAGE sql STABLE AS $$
 SELECT coalesce(sum(extract(epoch FROM saat.an(x->>1)-saat.an(x->>0))::double precision/3600),0)
 FROM jsonb_array_elements(xs) x $$;
CREATE FUNCTION zaman.gorev_gunluk_paylar(d text,g jsonb,yuk boolean DEFAULT false,
 kapanissiz boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; kapali text[]='{}'; alan text=CASE WHEN yuk THEN 'yuk' ELSE 'maas' END;
 t text=coalesce(nullif(g->>'ilk_kabul_ani',''),nullif(g->>'kabul_ani',''),CASE WHEN yuk THEN g->>'atama_ani' END);
 r record; x jsonb; tarih date; kisi text; agirliklar jsonb='[]'; toplam double precision=0;
 kalan double precision; agirlik double precision; donmus double precision=0;
BEGIN
 IF NOT kapanissiz THEN
  FOR r IN SELECT * FROM public.ay_kapanislari WHERE anahtar LIKE '%:GOREV_PAYLARI' ORDER BY anahtar COLLATE "C" LOOP
   kapali=array_append(kapali,left(r.anahtar,10));
   sonuc=sonuc||coalesce(r.hal->(g->>'kimlik')->alan,'[]');
  END LOOP;
 END IF;
 IF t IS NULL OR NOT irp.dogru(g->'teslim_tarihi') THEN RETURN sonuc; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(sonuc) LOOP donmus=donmus+(x->>'saat')::double precision; END LOOP;
 kalan=greatest(0,(g->>'zaman_degeri')::double precision-donmus);
 tarih=saat.gun(t);
 WHILE tarih<=saat.gun(g->>'teslim_tarihi') LOOP
  kisi=zaman.gorevin_kisisi(g,tarih);
  IF NOT date_trunc('month',tarih)::date::text=ANY(kapali) AND motor.is_gunu(d,tarih::text,kisi) THEN
   agirlik=takvim.saatler(takvim.kisi_normal(d,kisi,tarih)); toplam=toplam+agirlik;
   agirliklar=agirliklar||jsonb_build_array(jsonb_build_object('gun',tarih::text,'kisi',kisi,'saat',agirlik));
  END IF;
  tarih=tarih+1;
 END LOOP;
 IF toplam=0 THEN RETURN sonuc; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(agirliklar) LOOP
  IF (x->>'saat')::double precision<>0 AND (NOT irp.dogru(g->'iptal_ani') OR saat.gun(x->>'gun')<=saat.gun(g->>'iptal_ani')) THEN
   sonuc=sonuc||jsonb_build_array(x||jsonb_build_object('saat',irp.kayan_sayi(kalan*(x->>'saat')::double precision/toplam)));
  END IF;
 END LOOP;
 RETURN sonuc;
END $$;
-- Aynı günlük dağılım bir hesapta bir kez oluşturulur; görev payı kuralları aynıdır.
CREATE FUNCTION zaman.gorev_pay_satirlari(d text,g jsonb,bas date,bitis date,
 yuk boolean DEFAULT false,kapanissiz boolean DEFAULT false)
 RETURNS TABLE(gun date,kisi text,saat double precision) LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t text; BEGIN
 IF g->>'tur'='NOT' OR g->>'durum'='IPTAL' AND (yuk OR g->>'tur'='ONAY') THEN RETURN; END IF;
 IF g->>'tur'='ONAY' THEN
  t=CASE WHEN yuk THEN g->>'atama_ani' ELSE g->>'onay_ani' END;
  IF t IS NOT NULL AND saat.gun(t) BETWEEN bas AND bitis THEN RETURN QUERY SELECT saat.gun(t),g->>'kisi',(g->>'zaman_degeri')::double precision; END IF;
 ELSE RETURN QUERY SELECT saat.gun(x->>'gun'),x->>'kisi',(x->>'saat')::double precision
  FROM jsonb_array_elements(zaman.gorev_gunluk_paylar(d,g,yuk,kapanissiz)) x WHERE saat.gun(x->>'gun') BETWEEN bas AND bitis;
 END IF;
END $$;
CREATE FUNCTION zaman.gun_agirligi(d text,tarih date,kisi text) RETURNS double precision LANGUAGE plpgsql STABLE AS $$
DECLARE tak jsonb=takvim.birim_takvimi(d,tarih::text,kisi); standart double precision; x jsonb; BEGIN
 IF tak IS NOT NULL THEN
  standart=extract(epoch FROM saat.gun_ani(tarih,tak->>'mesai_bitis')-saat.gun_ani(tarih,tak->>'mesai_baslangic'))::double precision/3600;
  SELECT standart-coalesce(sum(extract(epoch FROM saat.gun_ani(tarih,z->>'bit')-saat.gun_ani(tarih,z->>'bas'))::double precision/3600),0)
   INTO standart FROM jsonb_array_elements(tak->'sabit_molalar') z;
 ELSE standart=(motor.ayar(d,'standart_gunluk_saat',saat.gun_ani(tarih),'9')#>>'{}')::double precision; END IF;
 RETURN takvim.saatler(takvim.normal(d,tarih,true,kisi))/standart;
END $$;

-- gorunum_v9.py:287,353,379. Onaysız tutar, toplam tutardan ayrı bir alandır.
CREATE FUNCTION k9.onay_bekliyor(d text,kisi text,tarih date) RETURNS boolean LANGUAGE plpgsql AS $$
BEGIN
 IF NOT k9.gun_onayi_gerekli(d,kisi,tarih) THEN RETURN false; END IF;
 RETURN k7.gun_sonu_raporu(d,kisi,tarih)->>'durum'<>'ONAYLANDI';
END $$;
CREATE FUNCTION k9.bekleyen_maliyet(d text,bas date,bitis date,proje text DEFAULT NULL,
 kisi text DEFAULT NULL,maas boolean DEFAULT false,iptal boolean DEFAULT false) RETURNS text LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE toplam numeric=0; g jsonb; a jsonb; r record; oran numeric; sa double precision; p timestamptz; q timestamptz;
BEGIN
 IF NOT irp.dogru(motor.oku(d,'gun_onay_ayarlari')) THEN RETURN '0.00'; END IF;
 IF maas THEN
  FOR g IN SELECT hal FROM motor.satirlar(d,'gorevler') WHERE proje IS NULL OR hal->>'proje'=proje LOOP
   FOR r IN SELECT * FROM zaman.gorev_pay_satirlari(d,g,bas,bitis) z WHERE bekleyen_maliyet.kisi IS NULL OR z.kisi=bekleyen_maliyet.kisi LOOP
    IF r.saat<>0 AND k9.onay_bekliyor(d,kisi,r.gun) THEN
     oran=zaman.saat_maliyeti(d,kisi,r.gun); toplam=toplam+r.saat::text::numeric*oran;
    END IF;
   END LOOP;
  END LOOP;
 ELSE
  FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) LOOP
   IF NOT irp.dogru(a->'kisi') OR proje IS NOT NULL AND a->>'proje' IS DISTINCT FROM proje OR kisi IS NOT NULL AND a->>'kisi'<>kisi THEN CONTINUE; END IF;
   IF coalesce(motor.kayit(d,'isler',a->>'is')->>'durum'='IPTAL',false)<>iptal OR a->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') THEN CONTINUE; END IF;
   p=greatest(saat.an(a->>'baslangic'),saat.gun_ani(bas)); q=least(coalesce(saat.an(a->>'bitis'),saat.simdi()),saat.gun_ani(bitis+1));
   IF p<q AND k9.onay_bekliyor(d,a->>'kisi',saat.gun(a->>'gun')) THEN
    sa=extract(epoch FROM q-p)::double precision/3600; toplam=toplam+sa::text::numeric*zaman.saat_maliyeti(d,a->>'kisi',saat.gun(a->>'gun'));
   END IF;
  END LOOP;
 END IF;
 RETURN coalesce(zaman.para(toplam),'VERI_EKSIK');
END $$;
CREATE FUNCTION k9.onay_uyarilari(d text,bas date,bitis date) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE gruplar jsonb='{}'; sonuc jsonb='[]'; k text; p jsonb; t date; b text; key text; x jsonb;
BEGIN
 IF NOT irp.dogru(motor.oku(d,'gun_onay_ayarlari')) THEN RETURN sonuc; END IF;
 FOR k,p IN SELECT * FROM motor.satirlar(d,'kisiler') LOOP
  t=greatest(saat.gun(p->>'giris_tarihi'),bas);
  WHILE t<=bitis LOOP
   IF yetki_v6.istihdamda(d,k,saat.gun_ani(t)) AND irp.dogru(takvim.kisi_normal(d,k,t)) AND k9.onay_bekliyor(d,k,t) THEN
    b=takvim.kisi_birimi(d,k,t); key=b||'|'||t;
    gruplar=gruplar||jsonb_build_object(key,coalesce(gruplar->key,'[]')||jsonb_build_array(k));
   END IF; t=t+1;
  END LOOP;
 END LOOP;
 FOR key,x IN SELECT * FROM jsonb_each(gruplar) ORDER BY key COLLATE "C" LOOP
  SELECT jsonb_agg(z ORDER BY (z#>>'{}') COLLATE "C") INTO x FROM jsonb_array_elements(x) z;
  sonuc=sonuc||jsonb_build_array(jsonb_build_object('birim',split_part(key,'|',1),'gun',split_part(key,'|',2),'kisiler',x));
 END LOOP; RETURN sonuc;
END $$;

-- gorunum_v7.py:61 maas_dagilimi. Paralar numeric ile, saatler float8 ile birikir.
CREATE FUNCTION zaman.maas_dagilimi(d text,kisi text,ay date,canli boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE bas date=date_trunc('month',ay)::date; bitis date=(date_trunc('month',ay)+interval '1 month - 1 day')::date;
 sonuc jsonb; paylar jsonb='{}'; tutarlar jsonb='{}'; g jsonb; r record; k text; v jsonb;
 oran numeric; deger numeric; toplam numeric=0; maas numeric=0; eksik boolean=false;
 tarih date; gunluk double precision; agirlik double precision=0; tum double precision=0; oran_f double precision;
 agirliklar jsonb='[]'; saat_toplami double precision=0;
BEGIN
 IF NOT canli THEN SELECT hal->'maas' INTO sonuc FROM public.ay_kapanislari WHERE anahtar=bas||':'||kisi; IF sonuc IS NOT NULL THEN RETURN sonuc; END IF; END IF;
 FOR g IN SELECT hal FROM motor.satirlar(d,'gorevler') LOOP
  k=coalesce(nullif(g->>'proje',''),nullif(g->>'kategori',''),'BELIRSIZ');
  IF g->>'durum'='IPTAL' THEN k='iptal:'||k; ELSIF g->>'tur'='REVIZYON' THEN k='revizyon:'||k; END IF;
  FOR r IN SELECT * FROM zaman.gorev_pay_satirlari(d,g,bas,bitis) z WHERE z.kisi=maas_dagilimi.kisi ORDER BY gun LOOP
   IF r.saat=0 THEN CONTINUE; END IF;
   paylar=paylar||jsonb_build_object(k,irp.kayan_sayi(coalesce((paylar->>k)::double precision,0)+r.saat));
   oran=zaman.saat_maliyeti(d,kisi,r.gun);
   IF oran IS NULL OR tutarlar->>k='VERI_EKSIK' THEN tutarlar=tutarlar||jsonb_build_object(k,'VERI_EKSIK'); eksik=true;
   ELSE tutarlar=tutarlar||jsonb_build_object(k,coalesce((tutarlar->>k)::numeric,0)+r.saat::text::numeric*oran); END IF;
  END LOOP;
 END LOOP;
 tarih=bas;
 WHILE tarih<=bitis LOOP
  gunluk=zaman.gun_agirligi(d,tarih,kisi); tum=tum+gunluk;
  IF yetki_v6.istihdamda(d,kisi,saat.gun_ani(tarih)) THEN
   agirlik=agirlik+gunluk;
   IF gunluk<>0 THEN agirliklar=agirliklar||jsonb_build_array(jsonb_build_object('gun',tarih::text,'agirlik',gunluk)); END IF;
  END IF; tarih=tarih+1;
 END LOOP;
 oran_f=CASE WHEN tum<>0 THEN agirlik/tum ELSE 0 END;
 FOR v IN SELECT value FROM jsonb_array_elements(agirliklar) LOOP
  deger=zaman.tutar_bul(kisi,'MAAS_AYLIK',saat.gun(v->>'gun'),NULL);
  IF deger IS NULL THEN maas=NULL; eksik=true; EXIT; END IF;
  maas=maas+deger*((v->>'agirlik')::double precision/tum)::text::numeric;
 END LOOP;
 sonuc='{}';
 FOR k,v IN SELECT * FROM jsonb_each(tutarlar) LOOP
  IF v#>>'{}'='VERI_EKSIK' THEN sonuc=sonuc||jsonb_build_object(k,'VERI_EKSIK');
  ELSE deger=round((v#>>'{}')::numeric,2); toplam=toplam+deger; sonuc=sonuc||jsonb_build_object(k,zaman.para(deger)); END IF;
 END LOOP;
 FOR v IN SELECT value FROM jsonb_each(paylar) LOOP saat_toplami=saat_toplami+(v#>>'{}')::double precision; END LOOP;
 RETURN jsonb_build_object('paylar',paylar,'toplam_saat',irp.kayan_sayi(saat_toplami),
  'payda',(motor.ayar(d,'maas_paydasi_saat',saat.gun_ani(bas),'180')#>>'{}')::double precision*oran_f,'tutarlar',sonuc,
  'onay_bekleyen',k9.bekleyen_maliyet(d,bas,bitis,NULL,kisi,true),
  'dagitilamayan',CASE WHEN eksik THEN 'VERI_EKSIK' ELSE zaman.para(greatest(0,maas-toplam)) END,
  'maasin_ustu',CASE WHEN eksik THEN 'VERI_EKSIK' ELSE zaman.para(greatest(0,toplam-maas)) END,
  'maas',coalesce(zaman.para(maas),'VERI_EKSIK'),'eksik_veri',eksik);
END $$;
CREATE FUNCTION zaman.iscilik_maliyeti(d text,proje text,bas date,bitis date,canli boolean DEFAULT false,iptal boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE sonuc jsonb; a jsonb; p timestamptz; q timestamptz; u timestamptz; v timestamptz; t date;
 iscilik numeric=0; tezgah numeric=0; oran numeric; sa double precision; makine boolean;
BEGIN
 IF NOT canli THEN
  SELECT hal INTO sonuc FROM public.ay_kapanislari WHERE anahtar=date_trunc('month',bas)::date||CASE WHEN iptal THEN ':IPTAL_MALIYET' ELSE ':MALIYET' END;
  IF sonuc IS NOT NULL THEN
   IF bas<>date_trunc('month',bas)::date OR bitis<>(date_trunc('month',bas)+interval '1 month - 1 day')::date THEN RAISE EXCEPTION 'IRP|BICIM|Karar 49: kapanmis ay yalniz tam ay sorgulanir'; END IF;
   RETURN coalesce(sonuc->proje,'{"iscilik":"0.00","tezgah":"0.00","eksik_veri":false}');
  END IF;
 END IF;
 FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) WHERE value->>'proje'=proje LOOP
  IF coalesce(motor.kayit(d,'isler',a->>'is')->>'durum'='IPTAL',false)<>iptal OR a->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY','TEZGAH') THEN CONTINUE; END IF;
  p=greatest(saat.an(a->>'baslangic'),saat.gun_ani(bas)); q=least(coalesce(saat.an(a->>'bitis'),saat.simdi()),saat.gun_ani(bitis+1)); t=saat.gun(saat.kodla(p));
  WHILE p<q AND t<=saat.gun(saat.kodla(q-interval '1 microsecond')) LOOP
   u=greatest(p,saat.gun_ani(t)); v=least(q,saat.gun_ani(t+1)); makine=a->>'kova'='TEZGAH';
   oran=CASE WHEN makine THEN zaman.tutar_bul(a->>'tezgah','SAAT_UCRETI',t,NULL) ELSE zaman.saat_maliyeti(d,a->>'kisi',t) END;
   sa=extract(epoch FROM v-u)::double precision/3600;
   IF makine THEN tezgah=tezgah+sa::text::numeric*oran; ELSE iscilik=iscilik+sa::text::numeric*oran; END IF;
   t=t+1;
  END LOOP;
 END LOOP;
 RETURN jsonb_build_object('iscilik',coalesce(zaman.para(iscilik),'VERI_EKSIK'),'tezgah',coalesce(zaman.para(tezgah),'VERI_EKSIK'),
  'eksik_veri',iscilik IS NULL OR tezgah IS NULL,'onay_bekleyen',k9.bekleyen_maliyet(d,bas,bitis,proje,NULL,false,iptal));
END $$;

-- gorunum_v7.py:348. Yuvarlama her proje/kişi/kalem grubunda yalnız bir kez.
CREATE FUNCTION zaman.deftere_ekle(defter jsonb,proje text,kisi text,kalem text,sa double precision,oran numeric) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE key text=coalesce(nullif(proje,''),'BELIRSIZ')||'|'||kisi||'|'||kalem; x jsonb; v jsonb; BEGIN
 x=coalesce(defter->key,'{"saat":0.0,"tutar":0}');
 IF oran IS NULL OR x->>'tutar'='VERI_EKSIK' THEN v='"VERI_EKSIK"'; ELSE v=to_jsonb((x->>'tutar')::numeric+sa::text::numeric*oran); END IF;
 RETURN defter||jsonb_build_object(key,jsonb_build_object('saat',irp.kayan_sayi((x->>'saat')::double precision+sa),'tutar',v));
END $$;
CREATE FUNCTION zaman.donem_defteri(d text,bas date,bitis date) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='{}'; defter jsonb='{}'; x jsonb; g jsonb; r record; sa double precision; oran numeric; k text;
BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) WHERE irp.dogru(value->'kisi') AND saat.gun(value->>'gun') BETWEEN bas AND bitis AND value->>'kova' IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') LOOP
  sa=extract(epoch FROM coalesce(saat.an(x->>'bitis'),saat.simdi())-saat.an(x->>'baslangic'))::double precision/3600;
  defter=zaman.deftere_ekle(defter,coalesce(nullif(x->>'proje',''),x->>'kategori'),x->>'kisi','ISCILIK',sa,zaman.saat_maliyeti(d,x->>'kisi',saat.gun(x->>'gun')));
 END LOOP;
 FOR g IN SELECT hal FROM motor.satirlar(d,'gorevler') LOOP
  FOR r IN SELECT * FROM zaman.gorev_pay_satirlari(d,g,bas,bitis,false,true) ORDER BY gun,kisi COLLATE "C" LOOP
   IF r.saat<>0 THEN defter=zaman.deftere_ekle(defter,coalesce(nullif(g->>'proje',''),g->>'kategori'),r.kisi,'MAAS',r.saat,zaman.saat_maliyeti(d,r.kisi,r.gun)); END IF;
  END LOOP;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(zaman.fazla_mesai_kayitlari(d)) WHERE saat.gun(value->>'tarih') BETWEEN bas AND bitis LOOP
  oran=zaman.saat_maliyeti(d,x->>'kisi',saat.gun(x->>'tarih'))*((x->>'katsayi')::numeric-1);
  defter=zaman.deftere_ekle(defter,coalesce(nullif(x->>'proje',''),x->>'kategori'),x->>'kisi','FAZLA_MESAI_PRIMI',(x->>'saat')::double precision,oran);
 END LOOP;
 FOR k,x IN SELECT * FROM jsonb_each(defter) LOOP
  sonuc=sonuc||jsonb_build_object(k,x||jsonb_build_object('proje',split_part(k,'|',1),'kisi',split_part(k,'|',2),'kaynak_kalem',split_part(k,'|',3),
   'tutar',CASE WHEN x->>'tutar'='VERI_EKSIK' THEN 'VERI_EKSIK' ELSE zaman.para((x->>'tutar')::numeric) END));
 END LOOP; RETURN sonuc;
END $$;
RESET ROLE;
