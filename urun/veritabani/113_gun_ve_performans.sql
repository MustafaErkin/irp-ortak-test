SET ROLE irp_sahibi;
CREATE FUNCTION okuma.kisi_birimi(kisi text,tarih text) RETURNS text LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT x->>2 FROM jsonb_array_elements(coalesce(okuma.satir('_v9_kisi_birimleri',kisi),'[]')) x
 WHERE saat.an(x->>0)<=saat.gun_ani(saat.gun(tarih)) ORDER BY x->>0 DESC,(x->>1) COLLATE "C" DESC LIMIT 1),okuma.satir('kisiler',kisi)->>'birim') $$;
CREATE FUNCTION okuma.gun_onayi_gerekli(kisi text,tarih text) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT (x->>'gerekli')::boolean FROM okuma.satirlar('gun_onay_ayarlari')
 WHERE x->>'birim'=okuma.kisi_birimi(kisi,tarih) AND saat.gun(x->>'gecerli_baslangic')<=saat.gun(tarih)
 ORDER BY x->>'gecerli_baslangic' DESC,x->>'an' DESC,x->>'kimlik' COLLATE "C" DESC LIMIT 1),false) $$;
CREATE FUNCTION okuma.json_kodla(j jsonb,ondalik boolean DEFAULT false) RETURNS text LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE r text; BEGIN
 IF jsonb_typeof(j)='object' THEN
  SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||okuma.json_kodla(value,ondalik OR key IN ('kovalar','isler')),',' ORDER BY key COLLATE "C"),'')||'}' INTO r FROM jsonb_each(j);
 ELSIF jsonb_typeof(j)='array' THEN SELECT '['||coalesce(string_agg(okuma.json_kodla(value,ondalik),',' ORDER BY n),'')||']' INTO r FROM jsonb_array_elements(j) WITH ORDINALITY z(value,n);
 ELSIF jsonb_typeof(j)='number' THEN r=((j#>>'{}')::double precision)::text; IF ondalik AND position('.' IN r)=0 AND position('e' IN r)=0 THEN r=r||'.0'; END IF;
 ELSE r=coalesce(j::text,'null'); END IF; RETURN r;
END $$;
CREATE FUNCTION okuma.gun_ozeti(kisi text,tarih text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb=okuma.kisinin_gunu(kisi,tarih); isler jsonb='{}'; gs jsonb; notlar jsonb; fm jsonb; a jsonb; BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(r->'araliklar') WHERE value->>'is' IS NOT NULL AND value->>'kova' IN ('CALISMA','YENIDEN_ISLEME') LOOP
  isler=okuma.ekle(isler,a->>'is',extract(epoch FROM coalesce(saat.an(a->>'bitis'),saat.simdi())-saat.an(a->>'baslangic'))/60);
 END LOOP;
 SELECT coalesce(jsonb_object_agg(k,jsonb_build_object('durum',x->'durum','kabul_ani',x->'kabul_ani','teslim_ani',x->'teslim_ani','bitis_ani',x->'bitis_ani')),'{}') INTO gs FROM okuma.satirlar('gorevler')
 WHERE x->>'kisi'=kisi AND saat.gun(x->>'atama_ani')<=saat.gun(tarih) AND (x->>'bitis_ani' IS NULL OR saat.gun(x->>'bitis_ani')>=saat.gun(tarih));
 SELECT coalesce(jsonb_agg(k),'[]') INTO notlar FROM okuma.satirlar('notlar') WHERE x->>'yazan'=kisi AND saat.gun(x->>'an')=saat.gun(tarih);
 SELECT coalesce(jsonb_agg(x-'prim'),'[]') INTO fm FROM jsonb_array_elements(okuma.fazla_mesai_kayitlari()) x WHERE x->>'kisi'=kisi AND x->>'tarih'=saat.gun(tarih)::text;
 RETURN jsonb_build_object('kovalar',r->'kovalar','isler',isler,'gorevler',gs,'notlar',notlar,'fazla_mesai',fm); END $$;
CREATE FUNCTION okuma.gun_sonu_raporu(kisi text,tarih text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE key text=kisi||':'||saat.gun(tarih); r jsonb; ozet jsonb; h text; BEGIN
 SELECT hal->key INTO r FROM public.ay_kapanislari WHERE anahtar=date_trunc('month',saat.gun(tarih))::date::text||':RAPORLAR'; IF r IS NOT NULL THEN RETURN r; END IF;
 r=coalesce(okuma.satir('gun_sonu_raporlari',key),jsonb_build_object('kisi',kisi,'gun',saat.gun(tarih),'durum','TASLAK'));
 ozet=okuma.gun_ozeti(kisi,tarih); h=encode(sha256(convert_to(okuma.json_kodla(ozet),'UTF8')),'hex'); r=r||jsonb_build_object('ozet',ozet,'ozet_surumu',h);
 IF r->>'onaylanan_ozet_surumu' IS NOT NULL THEN
  IF r->>'durum'='ONAYLANDI' AND r->>'onaylanan_ozet_surumu'<>h THEN r=r||'{"durum":"DEGISTI"}'; END IF;
  r=r||jsonb_build_object('onaylanan_ozet',okuma.gecmis(r->>'onay_ani','gun_ozeti',jsonb_build_object('kisi',kisi,'tarih',tarih)));
 END IF;
 RETURN r||jsonb_build_object('onay_durumu',CASE WHEN okuma.gun_onayi_gerekli(kisi,tarih) OR r->>'durum'='ONAYLANDI' THEN r->>'durum' ELSE 'ONAY_GEREKMIYOR' END); END $$;
CREATE FUNCTION okuma.onay_bekliyor(kisi text,tarih text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN IF NOT okuma.gun_onayi_gerekli(kisi,tarih) THEN RETURN false; END IF; RETURN okuma.gun_sonu_raporu(kisi,tarih)->>'durum'<>'ONAYLANDI'; END $$;
CREATE FUNCTION okuma.gun_isleri(kisi text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; p jsonb=okuma.satir('kisiler',kisi); rap jsonb; t date; k text; b text; gruplar jsonb='{}'; key text; ks jsonb; BEGIN
 IF p IS NULL THEN RETURN r; END IF;
 IF p->>'yaka'='BEYAZ' THEN FOR t IN SELECT okuma.gunler(p->>'giris_tarihi',saat.kodla(saat.simdi())) LOOP
  IF NOT yetki_v6.istihdamda('OKUMA',kisi,saat.gun_ani(t)) OR takvim.kisi_normal('OKUMA',kisi,t)='[]' OR saat.simdi()<saat.gun_ani(t,motor.takvim('OKUMA',t::text,kisi)->>'mesai_baslangic') THEN CONTINUE; END IF;
  rap=okuma.gun_sonu_raporu(kisi,t::text);
  IF rap->>'durum'='IADE' OR NOT EXISTS(SELECT FROM jsonb_array_elements(coalesce(rap->'gecmis','[]')) e WHERE e->>'eylem_kodu'='GUN_SONU.GONDERDIM') THEN r=r||jsonb_build_array(jsonb_build_object('tur','MESAI_SONU','kisi',kisi,'gun',t)); END IF;
 END LOOP; END IF;
 FOR k,p IN SELECT * FROM okuma.satirlar('kisiler') LOOP
  IF k=kisi OR NOT kisi=ANY(yetki_v6.ustler('OKUMA',k)) THEN CONTINUE; END IF;
  FOR t IN SELECT okuma.gunler(p->>'giris_tarihi',saat.kodla(saat.simdi())) LOOP
   IF NOT yetki_v6.istihdamda('OKUMA',k,saat.gun_ani(t)) OR takvim.kisi_normal('OKUMA',k,t)='[]' OR NOT okuma.onay_bekliyor(k,t::text) THEN CONTINUE; END IF;
   b=okuma.kisi_birimi(k,t::text); IF kisi=ANY(yetki_v6.yoneticiler('OKUMA',b)) AND k=ANY(yetki_v6.yoneticiler('OKUMA',b)) THEN CONTINUE; END IF;
   IF saat.simdi()<saat.gun_ani(t,motor.takvim('OKUMA',t::text,k)->>'mesai_bitis') THEN CONTINUE; END IF;
   key=b||':'||t; gruplar=gruplar||jsonb_build_object(key,coalesce(gruplar->key,'[]')||jsonb_build_array(k));
  END LOOP;
 END LOOP;
 FOR key,ks IN SELECT * FROM jsonb_each(gruplar) ORDER BY key COLLATE "C" LOOP
  r=r||jsonb_build_array(jsonb_build_object('tur','GUN_ONAYI','birim',split_part(key,':',1),'gun',split_part(key,':',2),'kisiler',(SELECT jsonb_agg(value ORDER BY value#>>'{}' COLLATE "C") FROM jsonb_array_elements(ks))));
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.hatirlatmalar() RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; k text; p jsonb; t date; sonraki date; i int; esik timestamptz; ayar jsonb; rap jsonb; gerekli boolean; alici text; zorunlu boolean=irp.dogru(motor.ayar('OKUMA','gun_sonu_raporu_zorunlu',saat.simdi(),'false')); BEGIN
 IF NOT zorunlu AND okuma.tablo('gun_onay_ayarlari')='{}' AND NOT EXISTS(SELECT FROM okuma.satirlar('gun_sonu_raporlari') WHERE x->>'durum'='GONDERILDI') THEN RETURN r; END IF;
 FOR k,p IN SELECT * FROM okuma.satirlar('kisiler') LOOP
  FOR t IN SELECT okuma.gunler(p->>'giris_tarihi',(saat.gun(saat.kodla(saat.simdi()))-1)::text) LOOP
   IF NOT yetki_v6.istihdamda('OKUMA',k,saat.gun_ani(t)) OR takvim.kisi_normal('OKUMA',k,t)='[]' THEN CONTINUE; END IF;
   sonraki=t+1; FOR i IN 1..370 LOOP EXIT WHEN motor.is_gunu('OKUMA',sonraki::text,k); sonraki=sonraki+1; END LOOP;
   esik=saat.gun_ani(sonraki,motor.takvim('OKUMA',sonraki::text,k)->>'mesai_baslangic'); ayar=motor.ayar('OKUMA','gun_sonu_hatirlatma',saat.simdi(),'"ERTESI_IS_GUNU"');
   IF jsonb_typeof(ayar)='number' THEN esik=esik+(ayar#>>'{}')::numeric*interval '1 hour'; END IF;
   IF saat.simdi()<esik THEN CONTINUE; END IF; rap=okuma.gun_sonu_raporu(k,t::text); gerekli=okuma.gun_onayi_gerekli(k,t::text); IF rap->>'durum'='ONAYLANDI' THEN CONTINUE; END IF;
   IF p->>'yaka'='BEYAZ' AND zorunlu AND rap->>'durum' IN ('TASLAK','IADE') THEN
    FOR alici IN SELECT DISTINCT a FROM unnest(ARRAY[k]||CASE WHEN gerekli THEN yetki_v6.ustler('OKUMA',k) ELSE '{}'::text[] END) a ORDER BY a COLLATE "C" LOOP r=r||jsonb_build_array(jsonb_build_object('kural','R32','alici',alici,'kisi',k,'gun',t,'an',saat.kodla(esik))); END LOOP;
   END IF;
   IF gerekli OR (p->>'yaka'='BEYAZ' AND rap->>'durum' IN ('GONDERILDI','DEGISTI')) THEN FOREACH alici IN ARRAY yetki_v6.ustler('OKUMA',k) LOOP r=r||jsonb_build_array(jsonb_build_object('kural','R33','alici',alici,'kisi',k,'gun',t,'an',saat.kodla(esik))); END LOOP; END IF;
  END LOOP;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.etkin_pay(x jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE t timestamptz; n int; BEGIN
 IF coalesce((x->>'yuzde')::numeric,0)<=0 OR irp.dogru(x->'itirazda') THEN RETURN false; END IF;
 IF irp.dogru(x->'dogrulandi') OR x->>'tur'='DIS' THEN RETURN true; END IF;
 IF x->>'kaynak_turu' IS DISTINCT FROM 'GECIKME' OR EXISTS(SELECT FROM jsonb_array_elements(coalesce(x->'gecmis','[]')) e WHERE e->>'eylem_kodu' LIKE 'SORUMLULUK.%') THEN RETURN false; END IF;
 t=saat.an(x->>'an'); n=(motor.ayar('OKUMA','sessiz_kabul_is_gunu',t,'0')#>>'{}')::int; IF n=0 THEN RETURN false; END IF;
 WHILE n>0 AND t<=saat.simdi() LOOP t=t+interval '1 day';
  IF motor.is_gunu('OKUMA',saat.kodla(t),CASE WHEN x->>'tur'='KISI' THEN x->>'kimlik' END,CASE WHEN x->>'tur'<>'KISI' THEN x->>'kimlik' END) THEN n=n-1; END IF;
 END LOOP; RETURN n=0 AND t<=saat.simdi(); END $$;
CREATE FUNCTION okuma.son_degerlendirme(hedef text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT x FROM okuma.satirlar('gecikme_degerlendirmeleri') WHERE x->>'hedef'=hedef ORDER BY x->>'an' DESC,x->>'kimlik' COLLATE "C" DESC LIMIT 1 $$;
CREATE FUNCTION okuma.sorumluluk_performansi(kisi text,bas text,bit_ text,tur text DEFAULT 'KISI') RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kalite numeric=0; gec numeric=0; x jsonb; h jsonb; g jsonb; ret jsonb; ek jsonb; BEGIN
 FOR x IN SELECT s.x FROM okuma.satirlar('sorumluluklar') s WHERE s.x->>'tur'=tur AND s.x->>'kimlik'=kisi AND irp.dogru(s.x->'dogrulandi') AND NOT irp.dogru(s.x->'itirazda') AND coalesce(s.x->>'kaynak_turu','') NOT IN ('GECIKME','DEGISIKLIK') LOOP
  IF saat.gun(x->>'an') BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN kalite=kalite+(x->>'yuzde')::numeric/100; END IF;
  FOR h IN SELECT value FROM jsonb_array_elements(x->'hedef') LOOP
   g=okuma.satir('gorevler',h->>'kimlik');
   IF g->>'durum'='BITTI' AND saat.gun(g->>'bitis_ani') BETWEEN saat.gun(bas) AND saat.gun(bit_) AND saat.an(g->>'bitis_ani')>gorev.son_teslim_ani(g,'OKUMA') THEN
    SELECT value INTO ret FROM jsonb_array_elements(okuma.tablo('retler')) WHERE value->>'olay'=x->>'ret' LIMIT 1;
    gec=gec+coalesce((ret->>'zaman_degeri')::numeric,(g->>'zaman_degeri')::numeric)*(x->>'yuzde')::numeric/100;
   END IF;
  END LOOP;
 END LOOP; ek=okuma.sorumluluk_ekleri(kisi,bas,bit_,tur);
 RETURN jsonb_build_object('kalite_ret',kalite+(ek->>'kalite_ret')::numeric,'sebep_olunan_gecikme',gec+(ek->>'sebep_olunan_gecikme')::numeric); END $$;
CREATE FUNCTION okuma.adil_performans(kisi text,bas text,bit_ text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE gs jsonb; g jsonb; x jsonb; ev jsonb; evler text[]='{}'; sayi int=0; zamaninda int=0; kredi numeric=0; cozum jsonb='[]'; katki numeric=0; bek int; bekleyen int=0; s jsonb; BEGIN
 IF cagiran IS NOT NULL AND NOT okuma.gorebilir(cagiran,'PERFORMANS',kisi) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') WHERE x->>'kisi'=kisi LOOP
  IF g->>'tur' IN ('NORMAL','DEGISIKLIK') AND saat.gun(g->>'ilk_teslim_ani') BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN
   sayi=sayi+1; ev=okuma.son_degerlendirme(g->>'kimlik'); IF ev IS NOT NULL THEN evler=array_append(evler,ev->>'kimlik'); END IF;
   IF saat.an(g->>'ilk_teslim_ani')<=gorev.son_teslim_ani(g,'OKUMA') THEN zamaninda=zamaninda+1; kredi=kredi+1;
   ELSIF ev IS NOT NULL THEN SELECT kredi+coalesce(sum((x->>'yuzde')::numeric/100),0) INTO kredi FROM okuma.satirlar('sorumluluklar') WHERE x->>'ret'=ev->>'kimlik' AND okuma.etkin_pay(x) AND NOT (x->>'tur'='KISI' AND x->>'kimlik'=g->>'kisi'); END IF;
  END IF;
  IF irp.dogru(g->'sorun_kaynakli') AND saat.gun(g->>'teslim_ani') BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN cozum=cozum||jsonb_build_array(extract(epoch FROM saat.an(g->>'teslim_ani')-saat.an(g->>'atama_ani'))/3600); END IF;
  IF g->>'nereye'='PROJE_DISI' AND saat.gun(g->>'bitis_ani') BETWEEN saat.gun(bas) AND saat.gun(bit_) THEN katki=katki+(g->>'zaman_degeri')::numeric; END IF;
 END LOOP;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') WHERE x->>'kisi'=kisi AND x->>'tur'='ONAY' AND saat.gun(x->>'onay_ani') BETWEEN saat.gun(bas) AND saat.gun(bit_) LOOP cozum=cozum||jsonb_build_array(extract(epoch FROM saat.an(g->>'onay_ani')-saat.an(g->>'atama_ani'))/3600); END LOOP;
 SELECT count(*) INTO bekleyen FROM okuma.satirlar('sorumluluklar') WHERE x->>'ret'=ANY(evler) AND (x->>'yuzde')::numeric>0 AND (irp.dogru(x->'itirazda') OR NOT okuma.etkin_pay(x));
 SELECT count(*) INTO bek FROM okuma.satirlar('bekletmeler') WHERE x->>'geciktiren'=kisi AND saat.gun(x->>'an') BETWEEN saat.gun(bas) AND saat.gun(bit_);
 s=okuma.sorumluluk_performansi(kisi,bas,bit_);
 RETURN s||jsonb_build_object('kesinlesmedi',bekleyen>0,'bekleyen_satir_sayisi',bekleyen,'zamaninda',zamaninda,'teslim',sayi,'zaman_orani',CASE WHEN sayi>0 THEN kredi/sayi END,'cozum_saatleri',cozum,'katki_saat',katki,'bekletme',bek);
END $$;
RESET ROLE;
