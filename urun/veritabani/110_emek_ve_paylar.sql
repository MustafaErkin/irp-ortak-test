SET ROLE irp_sahibi;
-- is_.emek; üst iş yalnız yapraklarının emeğini toplar.
CREATE FUNCTION okuma.emek(kimlik text) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE n numeric; BEGIN
 IF coalesce((okuma.satir('isler',kimlik)->>'kisi_sayisi')::int,1)>1 THEN
  SELECT coalesce(sum(okuma.emek(k)),0) INTO n FROM okuma.satirlar('isler') WHERE x->>'ana_is'=kimlik;
 ELSE SELECT coalesce(sum(extract(epoch FROM coalesce(saat.an(x->>'bitis'),saat.simdi())-saat.an(x->>'baslangic'))/60),0)
 INTO n FROM jsonb_array_elements(okuma.tablo('araliklar')) x WHERE x->>'is'=kimlik AND x->>'kova' IN ('CALISMA','YENIDEN_ISLEME'); END IF;
 RETURN n; END $$;
CREATE FUNCTION okuma.kisinin_gunu(kisi text,tarih text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE xs jsonb; kovalar jsonb='{}'; a jsonb; BEGIN
 SELECT coalesce(jsonb_agg(x),'[]') INTO xs FROM jsonb_array_elements(okuma.tablo('araliklar')) x WHERE x->>'kisi'=kisi AND x->>'gun'=saat.gun(tarih)::text;
 FOR a IN SELECT value FROM jsonb_array_elements(xs) LOOP kovalar=okuma.ekle(kovalar,a->>'kova',extract(epoch FROM coalesce(saat.an(a->>'bitis'),saat.simdi())-saat.an(a->>'baslangic'))/60); END LOOP;
 RETURN jsonb_build_object('araliklar',xs,'kovalar',kovalar); END $$;
CREATE FUNCTION okuma.kapasite(kisi text,bas text,bit_ text) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t date; n numeric=0; BEGIN
 FOR t IN SELECT okuma.gunler(bas,bit_) LOOP IF yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(t)) THEN
  n=n+okuma.saatler(takvim.cikar(takvim.kisi_normal('OKUMA',kisi,t)||takvim.ekler('OKUMA',kisi,t),takvim.izinler('OKUMA',kisi)));
 END IF; END LOOP; RETURN n; END $$;
CREATE FUNCTION okuma.kapasite_araligi(kisi text,a timestamptz,b timestamptz,birim text DEFAULT NULL) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t date; xs jsonb='[]'; ar jsonb; p timestamptz; q timestamptz; BEGIN
 IF a>=b THEN RETURN 0; END IF;
 FOR t IN SELECT okuma.gunler(saat.kodla(a),saat.kodla(b-interval '1 microsecond')) LOOP
  IF kisi IS NOT NULL THEN
   IF NOT yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(t)) THEN CONTINUE; END IF;
   ar=takvim.kisi_normal('OKUMA',kisi,t)||takvim.ekler('OKUMA',kisi,t);
  ELSE ar=takvim.normal('OKUMA',t,true,NULL,birim); END IF;
  FOR p,q IN SELECT greatest(a,saat.an(x->>0)),least(b,saat.an(x->>1)) FROM jsonb_array_elements(ar) x LOOP
   IF p<q THEN xs=xs||jsonb_build_array(jsonb_build_array(saat.kodla(p),saat.kodla(q))); END IF;
  END LOOP;
 END LOOP;
 RETURN okuma.saatler(CASE WHEN kisi IS NULL THEN xs ELSE takvim.cikar(xs,takvim.izinler('OKUMA',kisi)) END); END $$;
CREATE FUNCTION okuma.gorevin_kisisi(g jsonb,tarih date) RETURNS text LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT x->>'kisi' FROM jsonb_array_elements(coalesce(g->'kisi_gecmisi','[]')) x
 WHERE saat.gun(x->>'baslangic')<=tarih ORDER BY x->>'baslangic' DESC LIMIT 1),g->>'kisi') $$;
CREATE FUNCTION okuma.gorev_gunluk_paylar(g jsonb,yuk boolean DEFAULT false) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t text=coalesce(g->>'ilk_kabul_ani',g->>'kabul_ani',CASE WHEN yuk THEN g->>'atama_ani' END);
 alan text=CASE WHEN yuk THEN 'yuk' ELSE 'maas' END; kapali text[]; donmus jsonb; gun date; adaylar jsonb='[]'; agirlik numeric; toplam numeric=0; kalan numeric; s jsonb; BEGIN
 SELECT coalesce(array_agg(left(anahtar,10)),'{}') INTO kapali FROM public.ay_kapanislari WHERE anahtar LIKE '%:GOREV_PAYLARI';
 SELECT coalesce(jsonb_agg(z.value ORDER BY a.anahtar COLLATE "C",z.n),'[]') INTO donmus FROM public.ay_kapanislari a
 CROSS JOIN LATERAL jsonb_array_elements(coalesce(a.hal->(g->>'kimlik')->alan,'[]')) WITH ORDINALITY z(value,n) WHERE a.anahtar LIKE '%:GOREV_PAYLARI';
 IF t IS NULL OR g->>'teslim_tarihi' IS NULL THEN RETURN donmus; END IF;
 SELECT greatest(0,(g->>'zaman_degeri')::numeric-coalesce(sum((x->>'saat')::numeric),0)) INTO kalan FROM jsonb_array_elements(donmus) x;
 FOR gun IN SELECT okuma.gunler(t,g->>'teslim_tarihi') LOOP
  IF date_trunc('month',gun)::date::text=ANY(kapali) OR NOT motor.is_gunu('OKUMA',gun::text,okuma.gorevin_kisisi(g,gun)) THEN CONTINUE; END IF;
  agirlik=okuma.saatler(takvim.kisi_normal('OKUMA',okuma.gorevin_kisisi(g,gun),gun)); toplam=toplam+agirlik;
  adaylar=adaylar||jsonb_build_array(jsonb_build_object('gun',gun,'kisi',okuma.gorevin_kisisi(g,gun),'saat',agirlik));
 END LOOP;
 IF toplam=0 THEN RETURN donmus; END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(adaylar) LOOP
  IF (s->>'saat')::numeric<>0 AND (g->>'iptal_ani' IS NULL OR (s->>'gun')::date<=saat.gun(g->>'iptal_ani')) THEN
   donmus=donmus||jsonb_build_array(s||jsonb_build_object('saat',kalan*(s->>'saat')::numeric/toplam)); END IF;
 END LOOP; RETURN donmus; END $$;
CREATE FUNCTION okuma.gorev_payi(g jsonb,bas text,bit_ text,yuk boolean DEFAULT false,kisi text DEFAULT NULL) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t text; n numeric; BEGIN
 IF g->>'tur'='NOT' OR (g->>'durum'='IPTAL' AND (yuk OR g->>'tur'='ONAY')) THEN RETURN 0; END IF;
 IF g->>'tur'='ONAY' THEN
  IF kisi IS NOT NULL AND g->>'kisi'<>kisi THEN RETURN 0; END IF;
  t=g->>CASE WHEN yuk THEN 'atama_ani' ELSE 'onay_ani' END;
  RETURN CASE WHEN saat.gun(t) BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN (g->>'zaman_degeri')::numeric ELSE 0 END;
 END IF;
 SELECT coalesce(sum((s->>'saat')::numeric),0) INTO n FROM jsonb_array_elements(okuma.gorev_gunluk_paylar(g,yuk)) s
 WHERE (s->>'gun')::date BETWEEN saat.gun(bas) AND saat.gun(bit_) AND (kisi IS NULL OR s->>'kisi'=kisi); RETURN n;
END $$;
CREATE FUNCTION okuma.gorev_paylari(g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t text=g->>'onay_ani'; BEGIN
 IF g->>'tur'='NOT' THEN RETURN '[]'; END IF;
 IF g->>'tur'='ONAY' THEN
  IF g->>'durum'='IPTAL' OR t IS NULL THEN RETURN '[]'; END IF;
  RETURN jsonb_build_array(jsonb_build_object('gun',saat.gun(t),'kisi',g->'kisi','saat',g->'zaman_degeri'));
 END IF; RETURN okuma.gorev_gunluk_paylar(g); END $$;
CREATE FUNCTION okuma.yuk(kisi text,bas text,bit_ text) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE toplam numeric; gun date; gunler date[]='{}'; kaplar jsonb='{}'; g jsonb; k text; kalan numeric; agirlik numeric; donem numeric; pay numeric; kullanilan numeric=0; n int=1;
 bugun date=saat.gun(saat.kodla(saat.simdi())); kap numeric; BEGIN
 SELECT coalesce(sum(okuma.gorev_payi(x,bas,bit_,true)),0) INTO toplam FROM okuma.satirlar('gorevler') WHERE x->>'kisi'=kisi AND x->>'durum' NOT IN ('BITTI','IPTAL');
 IF coalesce(okuma.satir('listeler',kisi),'[]')='[]' THEN RETURN toplam; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements_text(okuma.satir('listeler',kisi)) i WHERE okuma.satir('isler',i)->>'teslim_tarihi' IS NULL) THEN
  -- Teslimi belli işlerde 365 günlük sıra takvimini kurmak sonucu değiştirmez.
  FOR k IN SELECT jsonb_array_elements_text(okuma.satir('listeler',kisi)) LOOP
   g=okuma.satir('isler',k); kalan=greatest(0,coalesce((g->>'tahmini_sure_dk')::numeric,0)-okuma.emek(k))/60;
   agirlik=0; donem=0;
   FOR gun IN SELECT okuma.gunler(bugun::text,greatest(saat.gun(g->>'teslim_tarihi'),bugun)::text) LOOP
    kap=okuma.kapasite(kisi,gun::text,gun::text); agirlik=agirlik+kap;
    IF gun BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN donem=donem+kap; END IF;
   END LOOP;
   IF agirlik>0 THEN toplam=toplam+kalan*donem/agirlik; END IF;
  END LOOP; RETURN toplam;
 END IF;
 FOR gun IN SELECT okuma.gunler(bugun::text,(greatest(saat.gun(bit_),bugun)+365)::text) LOOP
  kap=okuma.kapasite(kisi,gun::text,gun::text); kaplar=kaplar||jsonb_build_object(gun::text,kap); IF kap>0 THEN gunler=array_append(gunler,gun); END IF;
 END LOOP;
 FOR k IN SELECT jsonb_array_elements_text(coalesce(okuma.satir('listeler',kisi),'[]')) LOOP
  g=okuma.satir('isler',k); kalan=greatest(0,coalesce((g->>'tahmini_sure_dk')::numeric,0)-okuma.emek(k))/60;
  IF g->>'teslim_tarihi' IS NOT NULL THEN
   agirlik=0; donem=0; FOR gun IN SELECT okuma.gunler(bugun::text,greatest(saat.gun(g->>'teslim_tarihi'),bugun)::text) LOOP
    kap=coalesce((kaplar->>gun::text)::numeric,okuma.kapasite(kisi,gun::text,gun::text)); agirlik=agirlik+kap;
    IF gun BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN donem=donem+kap; END IF;
   END LOOP; IF agirlik>0 THEN toplam=toplam+kalan*donem/agirlik; END IF;
  ELSE
   WHILE kalan>0.000000001 AND n<=cardinality(gunler) LOOP
    gun=gunler[n]; kap=(kaplar->>gun::text)::numeric; pay=least(kalan,greatest(0,kap-kullanilan));
    IF gun BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN toplam=toplam+pay; END IF;
    kalan=kalan-pay; kullanilan=kullanilan+pay; IF kullanilan>=kap-0.000000001 THEN n=n+1; kullanilan=0; END IF;
   END LOOP;
  END IF;
 END LOOP; RETURN toplam; END $$;
CREATE FUNCTION okuma.gun_agirligi(tarih text,kisi text DEFAULT NULL) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE tak jsonb; standart numeric; x jsonb; BEGIN
 IF okuma.tablo('kisiler') ? tarih AND kisi IS NOT NULL THEN RETURN okuma.gun_agirligi(kisi,tarih); END IF;
 tak=takvim.birim_takvimi('OKUMA',tarih,kisi);
 IF tak IS NOT NULL THEN
  standart=extract(epoch FROM saat.gun_ani(saat.gun(tarih),tak->>'mesai_bitis')-saat.gun_ani(saat.gun(tarih),tak->>'mesai_baslangic'))/3600;
  FOR x IN SELECT value FROM jsonb_array_elements(tak->'sabit_molalar') LOOP standart=standart-extract(epoch FROM saat.gun_ani(saat.gun(tarih),x->>'bit')-saat.gun_ani(saat.gun(tarih),x->>'bas'))/3600; END LOOP;
 ELSE standart=(motor.ayar('OKUMA','standart_gunluk_saat',saat.gun_ani(saat.gun(tarih)),'9')#>>'{}')::numeric; END IF;
 RETURN okuma.saatler(takvim.normal('OKUMA',saat.gun(tarih),true,kisi))/standart;
END $$;
RESET ROLE;
