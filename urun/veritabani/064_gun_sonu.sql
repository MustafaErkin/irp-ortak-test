SET ROLE irp_sahibi;
-- gorunum_v7.py:247 gun_ozeti ve olay.py:8 kodla. Gün özeti bir iş alanıdır;
-- nesne sürümleri gibi sürücüde çevrilmez. Sayı ve anahtar biçimi korunur.
CREATE FUNCTION irp.kayan_sayi(x double precision) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE WHEN position('.' IN (x::text::jsonb)::text)=0 THEN ((x::text::jsonb)::text||'.0')::jsonb ELSE x::text::jsonb END $$;
CREATE FUNCTION irp.kanonik_json(x jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE sonuc text; f double precision; BEGIN
 IF jsonb_typeof(x)='object' THEN
  SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||irp.kanonik_json(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO sonuc FROM jsonb_each(x);
 ELSIF jsonb_typeof(x)='array' THEN
  SELECT '['||coalesce(string_agg(irp.kanonik_json(value),',' ORDER BY n),'')||']' INTO sonuc FROM jsonb_array_elements(x) WITH ORDINALITY a(value,n);
 ELSIF jsonb_typeof(x)='number' AND position('.' IN x::text)>0 THEN
  -- Python json.dumps, küçük/büyük float değerlerde üs gösterimini kullanır.
  f=(x#>>'{}')::double precision;
  IF f=0 OR abs(f)>=0.0001 AND abs(f)<1e16 THEN
   sonuc=f::text::numeric::text; IF position('.' IN sonuc)=0 THEN sonuc=sonuc||'.0'; END IF;
  ELSE sonuc=f::text; END IF;
 ELSE sonuc=x::text; END IF;
 RETURN sonuc;
END $$;

-- gorunumler.py:112 para, 116 tutar_bul; gorunum_v7.py:34 saat_maliyeti.
-- Sayısal NULL, yalnız iç hesapta VERI_EKSIK değeridir; sıfıra çevrilmez.
CREATE FUNCTION zaman.para(x numeric) RETURNS text LANGUAGE sql IMMUTABLE AS $$
 SELECT round(x,2)::numeric(1000,2)::text $$;
CREATE FUNCTION zaman.tutar_bul(kimlik text,tur text,tarih date,varsayilan numeric DEFAULT 0) RETURNS numeric LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT (h.ek->>'tutar')::numeric FROM public.hassas_ekler h
 JOIN public.olaylar o ON o.olay_kimligi=h.olay
 WHERE h.ek->>'nesne_kimlik'=kimlik AND h.ek->>'tur'=tur
 AND saat.gun(h.ek->>'gecerli_baslangic')<=tarih
 ORDER BY h.ek->>'gecerli_baslangic' DESC,o.kabul_no LIMIT 1),varsayilan) $$;
CREATE FUNCTION zaman.saat_maliyeti(d text,kisi text,tarih date) RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE maas numeric; BEGIN
 IF motor.oku(d,'tezgahlar') ? kisi THEN RETURN zaman.tutar_bul(kisi,'SAAT_UCRETI',tarih,NULL); END IF;
 maas=zaman.tutar_bul(kisi,'MAAS_AYLIK',tarih,NULL);
 IF maas IS NULL THEN RETURN NULL; END IF;
 RETURN (maas+zaman.tutar_bul(kisi,'GENEL_GIDER_PAYI',tarih,0)) /
  (motor.ayar(d,'maas_paydasi_saat',saat.gun_ani(tarih),'180')#>>'{}')::numeric;
END $$;

-- gorunum_v7.py:120 fazla_mesai_kayitlari. Yayın özeti prim alanını çıkarır.
CREATE FUNCTION zaman.fazla_mesai_kayitlari(d text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; x jsonb; a jsonb; g jsonb; p jsonb; q jsonb; engeller jsonb;
 kisi text; hedef text; tarih date; bas timestamptz; bit timestamptz; u timestamptz; v timestamptz;
 sa double precision; oran numeric; BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) WHERE irp.dogru(value->'fazla_mesai') LOOP
  sonuc=sonuc||jsonb_build_array(jsonb_build_object('kisi',a->'kisi','hedef',a->'is','proje',a->'proje','kategori',a->'kategori','tarih',a->'gun','baslangic',a->'baslangic','bitis',coalesce(nullif(a->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))),'katsayi',a->'katsayi'));
 END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(d,'ek_mesai_planlari') LOOP
  kisi=x->>'kisi';
  IF NOT irp.dogru(x->'damga') OR irp.dogru(x->'iptal') OR motor.kayit(d,'kisiler',kisi)->>'yaka'<>'BEYAZ' THEN CONTINUE; END IF;
  SELECT z->>'kimlik' INTO hedef FROM jsonb_array_elements(x->'hedef') z WHERE z->>'tur'='GOREV' LIMIT 1;
  g=motor.kayit(d,'gorevler',hedef); p=takvim.pencere(x); engeller=takvim.izinler(d,kisi);
  FOR a IN SELECT hal FROM motor.satirlar(d,'duruslar') WHERE takvim.birim_kapsamda(d,motor.kayit(d,'kisiler',kisi)->>'birim',hal->'kapsam') LOOP
   engeller=engeller||jsonb_build_array(jsonb_build_array(a->'baslangic',coalesce(nullif(a->'bitis','null'),to_jsonb(saat.kodla(saat.simdi())))));
  END LOOP;
  FOR q IN SELECT value FROM jsonb_array_elements(takvim.cikar(jsonb_build_array(p),engeller)) LOOP
   bas=saat.an(q->>0); bit=saat.an(q->>1); tarih=saat.gun(saat.kodla(bas));
   WHILE tarih<=saat.gun(saat.kodla(bit-interval '1 microsecond')) LOOP
    u=greatest(bas,saat.gun_ani(tarih)); v=least(bit,saat.gun_ani(tarih+1));
    sonuc=sonuc||jsonb_build_array(jsonb_build_object('kisi',kisi,'hedef',hedef,'proje',g->'proje','kategori',g->'kategori','tarih',tarih::text,'baslangic',saat.kodla(u),'bitis',saat.kodla(v),'katsayi',takvim.katsayi(d,tarih)));
    tarih=tarih+1;
   END LOOP;
  END LOOP;
 END LOOP;
 q='[]';
 FOR x IN SELECT value FROM jsonb_array_elements(sonuc) LOOP
  sa=extract(epoch FROM saat.an(x->>'bitis')-saat.an(x->>'baslangic'))::double precision/3600;
  oran=zaman.saat_maliyeti(d,x->>'kisi',saat.gun(x->>'tarih'));
  q=q||jsonb_build_array(x||jsonb_build_object('saat',irp.kayan_sayi(sa),'prim',coalesce(zaman.para(sa::text::numeric*oran*((x->>'katsayi')::numeric-1)),'VERI_EKSIK'),'kalem','FAZLA_MESAI_PRIMI'));
 END LOOP;
 RETURN q;
END $$;

-- takvim_v9.py:20 kisi_birimi; gorunum_v9.py:280 gun_onayi_gerekli.
CREATE FUNCTION takvim.kisi_birimi(d text,kisi text,tarih date) RETURNS text LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT value->>2 FROM jsonb_array_elements(motor.kayit(d,'_v9_kisi_birimleri',kisi,'[]'))
  WHERE saat.an(value->>0)<=saat.gun_ani(tarih) ORDER BY saat.an(value->>0) DESC,(value->>1) COLLATE "C" DESC,(value->>2) COLLATE "C" DESC LIMIT 1),motor.kayit(d,'kisiler',kisi)->>'birim') $$;
CREATE FUNCTION k9.gun_onayi_gerekli(d text,kisi text,tarih date) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT irp.dogru(hal->'gerekli') FROM motor.satirlar(d,'gun_onay_ayarlari')
  WHERE hal->>'birim'=takvim.kisi_birimi(d,kisi,tarih) AND saat.gun(hal->>'gecerli_baslangic')<=tarih
  ORDER BY hal->>'gecerli_baslangic' DESC,saat.an(hal->>'an') DESC,(hal->>'kimlik') COLLATE "C" DESC LIMIT 1),false) $$;
CREATE FUNCTION k7.gun_ozeti(d text,kisi text,tarih date) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kovalar jsonb='{}'; isler jsonb='{}'; gorevler jsonb='{}'; notlar jsonb='[]'; fm jsonb='[]'; x jsonb; k text; dk double precision; BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) WHERE value->>'kisi'=kisi AND saat.gun(value->>'gun')=tarih LOOP
  dk=extract(epoch FROM coalesce(saat.an(x->>'bitis'),saat.simdi())-saat.an(x->>'baslangic'))::double precision/60;
  k=x->>'kova'; kovalar=kovalar||jsonb_build_object(k,irp.kayan_sayi(coalesce((kovalar->>k)::double precision,0)+dk));
  IF irp.dogru(x->'is') AND k IN ('CALISMA','YENIDEN_ISLEME') THEN k=x->>'is'; isler=isler||jsonb_build_object(k,irp.kayan_sayi(coalesce((isler->>k)::double precision,0)+dk)); END IF;
 END LOOP;
 FOR k,x IN SELECT * FROM motor.satirlar(d,'gorevler') WHERE hal->>'kisi'=kisi AND saat.gun(hal->>'atama_ani')<=tarih AND (NOT irp.dogru(hal->'bitis_ani') OR saat.gun(hal->>'bitis_ani')>=tarih) LOOP
  gorevler=gorevler||jsonb_build_object(k,jsonb_build_object('durum',x->'durum','kabul_ani',x->'kabul_ani','teslim_ani',x->'teslim_ani','bitis_ani',x->'bitis_ani'));
 END LOOP;
 FOR k IN SELECT anahtar FROM motor.satirlar(d,'notlar') WHERE hal->>'yazan'=kisi AND saat.gun(hal->>'an')=tarih LOOP notlar=notlar||jsonb_build_array(k); END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(zaman.fazla_mesai_kayitlari(d)) WHERE value->>'kisi'=kisi AND value->>'tarih'=tarih::text LOOP fm=fm||jsonb_build_array(x-'prim'); END LOOP;
 RETURN jsonb_build_object('kovalar',kovalar,'isler',isler,'gorevler',gorevler,'notlar',notlar,'fazla_mesai',fm);
END $$;
CREATE FUNCTION k7.ozet_surumu(ozet jsonb) RETURNS text LANGUAGE sql IMMUTABLE AS $$
 SELECT encode(sha256(convert_to(irp.kanonik_json(ozet),'UTF8')),'hex') $$;

-- gorunum_v7.py:264 gun_sonu_raporu. Onay fotoğrafı, o anda bilinen olaylarla
-- aynı yerel motorun geçici bir kopyasında kurulur; kaynak olay değişmez.
CREATE TABLE motor.rapor_onay_onbellegi(anahtar text PRIMARY KEY,ozet jsonb NOT NULL);
CREATE FUNCTION k7.gun_sonu_raporu(d text,kisi text,tarih date) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE key text=kisi||':'||tarih; r jsonb; ozet jsonb; es jsonb; etkin jsonb; hash text; onay jsonb;
BEGIN
 SELECT hal->key INTO r FROM public.ay_kapanislari WHERE anahtar=date_trunc('month',tarih)::date||':RAPORLAR';
 IF r IS NOT NULL THEN RETURN r; END IF;
 r=motor.kayit(d,'gun_sonu_raporlari',key,jsonb_build_object('kisi',kisi,'gun',tarih::text,'durum','TASLAK'));
 ozet=k7.gun_ozeti(d,kisi,tarih); r=r||jsonb_build_object('ozet',ozet,'ozet_surumu',k7.ozet_surumu(ozet));
 IF irp.dogru(r->'onaylanan_ozet_surumu') THEN
  IF r->>'durum'='ONAYLANDI' AND r->'onaylanan_ozet_surumu'<>r->'ozet_surumu' THEN r=r||'{"durum":"DEGISTI"}'; END IF;
  SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]') INTO es FROM public.olaylar
   WHERE oldugu_an<=saat.an(r->>'onay_ani') AND bulut_ulasma_ani<=saat.an(r->>'onay_ani');
  hash=surum.ozet(jsonb_build_array(kisi,tarih,r->'onay_ani',r->'onaylanan_ozet_surumu',es));
  SELECT o.ozet INTO onay FROM motor.rapor_onay_onbellegi o WHERE anahtar=hash;
  IF onay IS NULL THEN
   -- Yayın bitirme geçişleri aynı anda ve aynı etkin kaynaklarla tamamlandıysa
   -- fotoğraf zaten elimizdedir. Geç olay veya farklı saat tam kuruluma gider.
   IF d='YAYIN' AND nullif(current_setting('irp.yayin_fotografi_ani',true),'')=r->>'onay_ani' THEN
    SELECT coalesce(jsonb_agg(x ORDER BY saat.an(x->>'oldugu_an'),(x->>'olay_kimligi') COLLATE "C"),'[]') INTO etkin
    FROM jsonb_array_elements(es) x WHERE x->>'olay_kimligi' NOT IN
     (SELECT y#>>'{girdiler,hedef}' FROM jsonb_array_elements(es) y WHERE y->>'eylem_kodu'='KAYIT.GECERSIZ_SAYDIM');
    IF etkin=motor.oku(d,'olaylar','[]') THEN onay=ozet; END IF;
   END IF;
   IF onay IS NULL THEN onay=motor.fotograf(es,saat.an(r->>'onay_ani'),'gun_ozeti',kisi,tarih); END IF;
   INSERT INTO motor.rapor_onay_onbellegi VALUES(hash,onay) ON CONFLICT DO NOTHING;
  END IF;
  r=r||jsonb_build_object('onaylanan_ozet',onay);
 END IF;
 RETURN r||jsonb_build_object('onay_durumu',CASE WHEN k9.gun_onayi_gerekli(d,kisi,tarih) OR r->>'durum'='ONAYLANDI' THEN r->>'durum' ELSE 'ONAY_GEREKMIYOR' END);
END $$;

-- gorunum_v9.py:320 hatirlatmalar. Zaman eşiği motor.saat_isi yayınına dahildir.
CREATE FUNCTION k9.hatirlatmalar(d text) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE sonuc jsonb='[]'; zorunlu boolean=irp.dogru(motor.ayar(d,'gun_sonu_raporu_zorunlu',saat.simdi(),'false'));
 kisi text; p jsonb; tarih date; sonraki date; n int; esik timestamptz; ayar jsonb; r jsonb; gerekli boolean; alici text; alicilar text[];
BEGIN
 IF NOT zorunlu AND NOT irp.dogru(motor.oku(d,'gun_onay_ayarlari')) AND NOT EXISTS(SELECT FROM motor.satirlar(d,'gun_sonu_raporlari') WHERE hal->>'durum'='GONDERILDI') THEN RETURN sonuc; END IF;
 FOR kisi,p IN SELECT * FROM motor.satirlar(d,'kisiler') LOOP
  tarih=saat.gun(p->>'giris_tarihi');
  WHILE tarih<saat.gun(saat.kodla(saat.simdi())) LOOP
   PERFORM motor.butce_denetle();
   IF yetki_v6.istihdamda(d,kisi,saat.gun_ani(tarih)) AND irp.dogru(takvim.kisi_normal(d,kisi,tarih)) THEN
    sonraki=tarih+1;
    FOR n IN 1..370 LOOP EXIT WHEN motor.is_gunu(d,sonraki::text,kisi); sonraki=sonraki+1; END LOOP;
    esik=saat.gun_ani(sonraki,motor.takvim(d,sonraki::text,kisi)->>'mesai_baslangic');
    ayar=motor.ayar(d,'gun_sonu_hatirlatma',saat.simdi(),'"ERTESI_IS_GUNU"');
    IF jsonb_typeof(ayar)='number' THEN esik=esik+(ayar#>>'{}')::double precision*interval '1 hour'; END IF;
    IF saat.simdi()>=esik THEN
     -- Burada raporun yalnız durumu kullanılır. Taslak/gönderilmiş günler
     -- için bütün saat ve fazla mesai özetini tekrar hesaplamak gerekmez.
     -- Kapanıştaki durum donuktur; açık onayda özet değişimi yine denetlenir.
     SELECT hal->(kisi||':'||tarih::text) INTO r FROM public.ay_kapanislari
      WHERE anahtar=date_trunc('month',tarih)::date||':RAPORLAR';
     IF r IS NULL THEN
      r=motor.kayit(d,'gun_sonu_raporlari',kisi||':'||tarih::text,'{"durum":"TASLAK"}');
      IF r->>'durum'='ONAYLANDI' AND irp.dogru(r->'onaylanan_ozet_surumu')
       AND r->>'onaylanan_ozet_surumu'<>k7.ozet_surumu(k7.gun_ozeti(d,kisi,tarih)) THEN r=r||'{"durum":"DEGISTI"}'; END IF;
     END IF;
     gerekli=k9.gun_onayi_gerekli(d,kisi,tarih);
     IF r->>'durum'<>'ONAYLANDI' THEN
      IF p->>'yaka'='BEYAZ' AND zorunlu AND r->>'durum' IN ('TASLAK','IADE') THEN
       alicilar=ARRAY[kisi]||CASE WHEN gerekli THEN yetki_v6.ustler(d,kisi) ELSE '{}'::text[] END;
       FOR alici IN SELECT DISTINCT z COLLATE "C" FROM unnest(alicilar) z ORDER BY z COLLATE "C" LOOP
        sonuc=sonuc||jsonb_build_array(jsonb_build_object('kural','R32','alici',alici,'kisi',kisi,'gun',tarih::text,'an',saat.kodla(esik)));
       END LOOP;
      END IF;
      IF gerekli OR p->>'yaka'='BEYAZ' AND r->>'durum' IN ('GONDERILDI','DEGISTI') THEN
       FOREACH alici IN ARRAY yetki_v6.ustler(d,kisi) LOOP
        sonuc=sonuc||jsonb_build_array(jsonb_build_object('kural','R33','alici',alici,'kisi',kisi,'gun',tarih::text,'an',saat.kodla(esik)));
       END LOOP;
      END IF;
     END IF;
    END IF;
   END IF;
   tarih=tarih+1;
  END LOOP;
 END LOOP;
 RETURN sonuc;
END $$;

-- kurallar_v7.py:293 isle; v9.py:366 toplu onay ve mavi yaka gönderimi.
CREATE FUNCTION k7.gun_sonu_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE g jsonb=e->'girdiler'; kisi text=coalesce(g->>'kisi',e->>'adina',e->>'kim'); key text=kisi||':'||(g->>'gun'); x jsonb; BEGIN
 x=motor.kayit(m,'gun_sonu_raporlari',key,jsonb_build_object('kisi',kisi,'gun',g->'gun','durum','TASLAK','gecmis','[]'::jsonb));
 x=x||jsonb_build_object('gecmis',(x->'gecmis')||jsonb_build_array(e));
 IF e->>'eylem_kodu'='GUN_SONU.GONDERDIM' THEN x=x||jsonb_build_object('durum','GONDERILDI','aciklama',g->'aciklama','tanimsiz_aciklama',g->'tanimsiz_aciklama');
 ELSIF e->>'eylem_kodu'='GUN_SONU.IADE_ETTIM' THEN x=x||jsonb_build_object('durum','IADE','iade_gerekcesi',g->'gerekce');
 ELSE x=x||jsonb_build_object('durum','ONAYLANDI','onaylanan_ozet_surumu',g->'ozet_surumu','onaylayan',e->'kim','onay_ani',saat.kodla(saat.an(e->>'oldugu_an')),'onay_olayi',e->'olay_kimligi'); END IF;
 PERFORM motor.kaydet(m,'gun_sonu_raporlari',key,x);
END $$;
CREATE FUNCTION k9.gun_sonu_isle(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE g jsonb=e->'girdiler'; s jsonb; yeni jsonb; kisi text; key text; once text; BEGIN
 IF e->>'eylem_kodu'='GUN_SONU.ONAYLADIM' THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gunler',jsonb_build_array(g))) LOOP
   IF g ? 'not' THEN s=s||jsonb_build_object('not',g->'not'); END IF;
   PERFORM k7.gun_sonu_isle(m,e||jsonb_build_object('girdiler',s));
  END LOOP;
 ELSIF e->>'eylem_kodu'='GUN_SONU.GONDERDIM' THEN
  yeni=e||jsonb_build_object('girdiler','{"aciklama":"","tanimsiz_aciklama":""}'::jsonb||g);
  kisi=coalesce(g->>'kisi',e->>'adina',e->>'kim'); key=kisi||':'||(g->>'gun'); once=coalesce(motor.kayit(m,'gun_sonu_raporlari',key)->>'durum','TASLAK');
  PERFORM k7.gun_sonu_isle(m,yeni);
  IF motor.kayit(m,'kisiler',kisi)->>'yaka'='MAVI' THEN PERFORM motor.kaydet(m,'gun_sonu_raporlari',key,motor.kayit(m,'gun_sonu_raporlari',key)||jsonb_build_object('durum',once)); END IF;
 ELSE PERFORM k7.gun_sonu_isle(m,e); END IF;
END $$;
CREATE FUNCTION k9.gun_sonu_bicim(d text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE g jsonb=e->'girdiler'; ss jsonb; s jsonb; BEGIN
 IF e->>'eylem_kodu'='GUN_ONAYI.AYARLADIM' THEN
  IF jsonb_typeof(g->'gerekli') IS DISTINCT FROM 'boolean' THEN PERFORM kapi.bicim_hatasi('Gerekli bool'); END IF; PERFORM saat.gun(g->>'gecerli_baslangic');
 ELSIF e->>'eylem_kodu'='GUN_SONU.ONAYLADIM' THEN
  ss=coalesce(g->'gunler',jsonb_build_array(g));
  IF jsonb_typeof(ss)<>'array' OR ss='[]' THEN PERFORM kapi.bicim_hatasi('Gun onay satirlari'); END IF;
  FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP IF jsonb_typeof(s)<>'object' OR NOT s ?& ARRAY['kisi','gun','ozet_surumu'] THEN PERFORM kapi.bicim_hatasi('Gun onay satirlari'); END IF; END LOOP;
  IF (SELECT count(*)<>count(DISTINCT (value->'kisi',value->'gun')) FROM jsonb_array_elements(ss)) THEN PERFORM kapi.bicim_hatasi('Gun onayi tekil'); END IF;
  FOR s IN SELECT value FROM jsonb_array_elements(ss) LOOP PERFORM saat.gun(s->>'gun'); END LOOP;
 END IF;
END $$;
CREATE FUNCTION k9.gun_sonu_yetki(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; kim text=e->>'kim'; kisi text; s jsonb; BEGIN
 IF kod NOT IN ('GUN_ONAYI.AYARLADIM','GUN_SONU.GONDERDIM','GUN_SONU.ONAYLADIM','GUN_SONU.IADE_ETTIM') THEN RETURN NULL; END IF;
 IF NOT yetki_v6.istihdamda(d,kim,yetki_v6.simdi(d)) THEN RETURN false; END IF;
 IF kod='GUN_ONAYI.AYARLADIM' THEN RETURN kim=ANY(yetki_v6.birim_ustleri(d,g->>'birim')) OR yetki_v6.tablo_izni(d,kim,kod,NULL); END IF;
 IF kod='GUN_SONU.ONAYLADIM' THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gunler',jsonb_build_array(g))) LOOP IF kim=s->>'kisi' OR NOT kim=ANY(yetki_v6.ustler(d,s->>'kisi')) THEN RETURN false; END IF; END LOOP; RETURN true;
 END IF;
 kisi=coalesce(g->>'kisi',e->>'adina',kim);
 RETURN kim=ANY(yetki_v6.ustler(d,kisi)) OR kod='GUN_SONU.GONDERDIM' AND kim=kisi;
END $$;
CREATE FUNCTION k9.gun_sonu_durum(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; t date=saat.gun(e->>'oldugu_an'); s jsonb; r jsonb; izin text[]; BEGIN
 IF kod='GUN_ONAYI.AYARLADIM' THEN RETURN motor.oku(d,'birimler') ? (g->>'birim') AND saat.gun(g->>'gecerli_baslangic')>=t; END IF;
 IF kod NOT LIKE 'GUN_SONU.%' THEN RETURN NULL; END IF;
 IF kod='GUN_SONU.ONAYLADIM' THEN
  FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gunler',jsonb_build_array(g))) LOOP
   IF saat.gun(s->>'gun')>t OR NOT yetki_v6.istihdamda(d,s->>'kisi',saat.an(s->>'gun')) THEN RETURN false; END IF;
   r=k7.gun_sonu_raporu(d,s->>'kisi',saat.gun(s->>'gun'));
   izin=CASE WHEN motor.kayit(d,'kisiler',s->>'kisi')->>'yaka'='MAVI' THEN ARRAY['TASLAK','GONDERILDI','DEGISTI'] ELSE ARRAY['GONDERILDI','DEGISTI'] END;
   IF NOT r->>'durum'=ANY(izin) OR r->'ozet_surumu' IS DISTINCT FROM s->'ozet_surumu' THEN RETURN false; END IF;
  END LOOP; RETURN true;
 END IF;
 IF saat.gun(g->>'gun')>t THEN RETURN false; END IF;
 IF kod='GUN_SONU.GONDERDIM' THEN RETURN true; END IF;
 IF motor.kayit(d,'kisiler',g->>'kisi')->>'yaka'='MAVI' THEN RETURN false; END IF;
 RETURN k7.gun_sonu_raporu(d,g->>'kisi',saat.gun(g->>'gun'))->>'durum' IN ('GONDERILDI','DEGISTI');
END $$;
RESET ROLE;
